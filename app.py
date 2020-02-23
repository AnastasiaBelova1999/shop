import mysql
from flask import Flask, render_template, request, abort, redirect, flash, url_for
from flask_login import login_required
from collections import namedtuple

from mysql_db import MySQL
import mysql.connector
import flask_login
import hashlib

app = Flask(__name__)
app.secret_key = 'asjdfbajSLDFBhjasbfd'
app.config.from_pyfile('config.py')
db = MySQL(app)
login_manager = flask_login.LoginManager()
login_manager.init_app(app)


class User(flask_login.UserMixin):
    pass

@login_manager.user_loader
def user_loader(login):
    cursor = db.db.cursor(named_tuple=True)
    cursor.execute('select id, login from users where id = %s', (login,))
    user_db = cursor.fetchone()
    if user_db:
        user = User()
        user.id = user_db.id
        user.login = user_db.login
        return user
    return None

@login_manager.unauthorized_handler
def unauthorized_handler():
    return render_template("index.html", authorization=False, login="anonimus", login_false=False)

@app.route('/', methods=['POST', 'GET'])
def hello_world():
    if request.method == 'GET':
        login: str
        if flask_login.current_user.is_anonymous:
            login = "anonymus"
        else:
            login = flask_login.current_user.login
        return render_template("index.html", authorization=not flask_login.current_user.is_anonymous, login=login)
    elif request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")
        password_hash = hashlib.sha224(password.encode()).hexdigest()
        if username and password:
            cursor = db.db.cursor(named_tuple=True, buffered=True)
            try:
                cursor.execute(
                    "SELECT id,login FROM users WHERE `login` = '%s' and `password_hash` = '%s'" % (
                        username, password_hash))
                user = cursor.fetchone()
            except Exception:
                cursor.close()
                return render_template("index.html", authorization=False,
                                       login="anonimus", login_false=True)
            cursor.close()
            if user is not None:
                flask_user = User()
                flask_user.id = user.id
                flask_user.login = user.login
                flask_login.login_user(flask_user, remember=True)
                return render_template("index.html", authorization=not flask_login.current_user.is_anonymous,
                                       login=user.login, login_false=False)
            else:
                flash("Не правильный логин или пароль")
                return render_template("index.html", authorization=False,
                                       login="anonimus", login_false=True)
        else:
            flash("Не правильный логин или пароль")
            return render_template("index.html", authorization=False,
                                   login="anonimus", login_false=True)


@app.route('/logout', methods=['GET'])
def logout():
    flask_login.logout_user()
    return render_template("index.html", authorization=not flask_login.current_user.is_anonymous, login="anonimus",
                           login_false=False)

@app.route('/booking', methods=['GET'])
@login_required
def req():
    booking = db.select(None, "booking")
    date = db.select("date", "booking")
    login = dict(db.select(["id","login"], "users"))
    clothes = dict(db.select(["id", "title"], "clothes"))
    shop = dict(db.select(["id", "title"], "shop"))
    status = dict(db.select(["id","title"], "status"))
    return render_template("booking.html", booking=booking, date=date, login=login, clothes=clothes, shop=shop, status=status)

@app.route('/booking/delete', methods=['POST'])
@login_required
def book():
    id = request.form.get("id")
    cursor = db.db.cursor()
    cursor.execute("DELETE FROM `booking` WHERE `booking`.`id` = '%s'" % id)
    db.db.commit()
    cursor.close()
    return redirect("/booking")

@app.route('/book/new', methods=['POST', 'GET'])
@login_required
def sub_new():
    if request.method == 'GET':
        clothes = db.select(["id", "title"], "clothes")
        shop = db.select(["id", "title"], "shop")
        status = db.select(["id", "title"], "status")
        return render_template("new.html",  status=status, clothes=clothes, shop=shop)
    elif request.method == 'POST':
        date = request.form.get("date")
        clothes_id = request.form.get("id_clothes")
        shop_id = request.form.get("id_shop")
        status_id = request.form.get("id_status")

        if date and clothes_id and shop_id and status_id:
            cursor = db.db.cursor(named_tuple=True)
            try:
                cursor.execute(
                    "INSERT INTO `booking` (`date`,`id_login`, `id_clothes`, `id_shop`, `id_status`) VALUES ('%s','%s','%s','%s','%s')" % (
                       date, flask_login.current_user.id, clothes_id, shop_id, status_id))
                db.db.commit()
                cursor.close()
                return redirect("/booking")
            except Exception:
                clothes = db.select(["id", "title"], "clothes")
                shop = db.select(["id", "title"], "shop")
                status = db.select(["id", "title"], "status")
                return render_template("new.html", login=flask_login.current_user.login, insert_false=True, clothes=clothes, shop=shop,
                                       status=status)
        else:
            clothes = db.select(["id", "title"], "clothes")
            shop = db.select(["id", "title"], "shop")
            status = db.select(["id", "title"], "status")
            return render_template("new.html", login=flask_login.current_user.login, insert_false=True, clothes=clothes, shop=shop,
                                   status=status)

@app.route('/book/edit', methods=['POST'])
@login_required
def list_edit():
    try:
        booking_id = request.form.get("id")
        date = request.form.get("date")
        login = request.form.get("login_users")
        clothes_id = request.form.get("id_clothes")
        shop_id = request.form.get("id_shop")
        status_id = request.form.get("id_status")
        statuss = dict(db.select(["id", "title"],"status"))
        clothess = dict(db.select(["id", "title"],"clothes"))
        shops = dict(db.select(["id","title"], "shop"))

        sub = {
            'booking_id': int(booking_id),
            'date': date,
            'login_users': login,
            'clothes_id': int(clothes_id),
            'shop_id': int(shop_id),
            'status_id': int(status_id),
        }
        return render_template("book_edit.html", sub=sub, clothess=clothess, shops=shops, statuss=statuss,
                               login=flask_login.current_user.login, booking_id=booking_id)

    except Exception:
        return redirect(url_for("booking"))


@app.route('/book/edit/submit', methods=['POST'])
@login_required
def sub_edit_submit():
    list_id = request.form.get("list_id")
    date = request.form.get("date")
    login = request.form.get("login_users")
    clothes_id = request.form.get("id_clothes")
    shop_id = request.form.get("id_shop")
    status_id = request.form.get("id_status")

    if date and clothes_id and shop_id and status_id:
        cursor = db.db.cursor(named_tuple=True)
        try:
            cursor.execute(
                "UPDATE `booking` SET  `date` = '%s', `id_clothes` = '%s', `id_shop` = '%s',`id_status` = '%s' WHERE `booking`.`id` = '%s'" % (
                    date, clothes_id, shop_id, status_id, list_id))
            db.db.commit()
            cursor.close()
            return redirect("/booking")
        except Exception:
            return redirect("/booking")
    else:
        return redirect("/booking")

if __name__ == '__main__':
    app.run()