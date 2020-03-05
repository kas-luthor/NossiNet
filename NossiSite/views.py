import json
import subprocess
import time

import bleach
from flask import abort, session, render_template, request, flash, redirect, url_for
from werkzeug.security import gen_salt, generate_password_hash

from NossiPack.FenCharacter import FenCharacter
from NossiPack.User import Userlist, User, Config
from NossiPack.VampireCharacter import VampireCharacter
from NossiSite.base import app
from NossiSite.helpers import (
    checktoken,
    wikiload,
    wikisave,
    checklogin,
    log,
    update_discord_bindings,
    connect_db,
)

bleach.ALLOWED_TAGS += [
    "br",
    "u",
    "p",
    "table",
    "th",
    "tr",
    "td",
    "tbody",
    "thead",
    "tfoot",
]


@app.route("/version")
def getversion():
    res = subprocess.run(
        ["git", "log", "-n 1"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )
    result = res.stdout
    return result, 200, {"Content-Type": "text/plain; charset=utf-8"}


@app.route("/")
def show_entries():
    db = connect_db("main")
    cur = db.execute(
        "SELECT author, title, text, id, tags FROM entries ORDER BY id DESC"
    )
    entries = [
        dict(author=row[0], title=row[1], text=row[2], id=row[3], tags=row[4])
        for row in cur.fetchall()
    ]
    for e in entries:
        skip = True
        if session.get("logged_in") and session.get("tags"):
            for t in session.get("tags").split(" "):
                if t in e.get("tags", "").split(" "):
                    skip = False
        else:
            if "default" in (e.get("tags") if e.get("tags") else "").split(" "):
                skip = False
        if skip:
            e["author"] = e.get("author").lower()  # "delete" nonmatching tags
        e["text"] = bleach.clean(e["text"].replace("\n", "<br>"))
        e["own"] = (session.get("logged_in")) and (session.get("user") == e["author"])
    entries = [
        e for e in entries if e.get("author", "none")[0].isupper()
    ]  # dont send out lowercase authors (deleted)

    return render_template("show_entries.html", entries=entries)


@app.route("/edit/<path:x>", methods=["GET", "POST"])
def editentries(x=None):
    checklogin()
    db = connect_db("editentries")
    if request.method == "GET":
        if x == "all":
            cur = db.execute(
                "SELECT author, title, text, id, tags "
                "FROM entries WHERE UPPER(author) LIKE UPPER(?)",
                [session.get("user")],
            )
            entries = [
                dict(author=row[0], title=row[1], text=row[2], id=row[3], tags=row[4])
                for row in cur.fetchall()
            ]

            return render_template("show_entries.html", entries=entries, edit=True)
        try:
            x = int(x)
            cur = db.execute(
                "SELECT author, title, text, id, tags " "FROM entries WHERE id == ?",
                [x],
            )
            entry = [
                dict(author=row[0], title=row[1], text=row[2], id=row[3], tags=row[4])
                for row in cur.fetchall()
            ][0]
            if (session.get("user").upper() == entry["author"].upper()) or session.get(
                "admin"
            ):
                return render_template("edit_entry.html", mode="blog", entry=entry)
            flash("not authorized to edit id" + str(x))
        except ValueError:
            try:
                author = ""
                ident = (x,)
                retrieve = session.get("retrieve", None)
                if retrieve:
                    title = retrieve["title"]
                    text = retrieve["text"]
                    tags = retrieve["tags"].split(" ")
                else:
                    title, tags, text = wikiload(x)
                entry = dict(
                    author=author, id=ident, title=title, tags=" ".join(tags), text=text
                )
                return render_template(
                    "edit_entry.html", mode="wiki", wiki=x, entry=entry
                )
            except FileNotFoundError:
                flash("entry " + str(x) + " not found.")
        return redirect(url_for("editentries", x="all"))
    if request.method == "POST":
        if request.form["id"] == "new":
            add_entry()
        if checktoken():
            if request.form.get("wiki", None) is not None:
                log.info(f"saving wiki file {request.form['wiki']}")
                wikisave(
                    x,
                    session.get("user"),
                    request.form["title"],
                    request.form["tags"].split(" "),
                    request.form["text"],
                )
                update_discord_bindings(session["user"], x)
                session["retrieve"] = None
                return redirect(url_for("wikipage", page=request.form["wiki"]))

            cur = db.execute(
                "SELECT author, title, text, id, tags " "FROM entries WHERE id == ?",
                [int(request.form["id"])],
            )
            entry = [
                dict(author=row[0], title=row[1], text=row[2], id=row[3], tags=row[4])
                for row in cur.fetchall()
            ][0]
            if (session.get("user").upper() == entry["author"].upper()) or session.get(
                "admin"
            ):
                db.execute(
                    "UPDATE entries SET title=?, text=?, tags=? WHERE id == ?",
                    [
                        request.form["title"],
                        request.form["text"],
                        request.form["tags"],
                        request.form["id"],
                    ],
                )
                session["retrieve"] = None
                db.commit()
                flash("entry was successfully edited")
            else:
                flash(
                    "not authorized: "
                    + session.get("user").upper()
                    + "!="
                    + entry["author"].upper()
                )
        else:
            flash("go back and try again")
        return redirect(url_for("show_entries"))
    return abort(405)


@app.route("/update_filter/", methods=["POST"])
def update_filter():
    if checktoken() and session.get("logged_in"):
        session["tags"] = request.form["tags"]
    return redirect(url_for("show_entries"))


@app.route("/config/", methods=["POST"])
@app.route("/config/<path:x>", methods=["GET", "POST"])
def config(x=None):
    checklogin()
    if request.method == "GET":
        c = Config.load(session["user"], x) or ""
        heading = "Change " + x.title()
        if x == "discord":
            desc = (
                "Your Discord account (name#number) that will be able to "
                "remote control your Nosferatunet Account:"
            )
        else:
            desc = f"What would you like {x.title()} to be?"
        return render_template(
            "config.html", heading=heading, description=desc, config=x, curval=c
        )
    if request.method == "POST":
        if not x:
            return redirect(url_for("config", x=request.form["configuration"]))
        if request.form.get("delete", None):
            log.info(f"Deleting {x} of user {session['user']}.")
            Config.delete(session["user"], x.lower())
            flash(f"Deleted {x}!")
        else:
            Config.save(session["user"], x.lower(), request.form["configuration"])
            flash(f"Saved {x}!")
        return redirect(url_for("show_user_profile", username=session["user"]))
    return abort(405)


@app.route("/charactersheet/")
def charsheet():
    checklogin()
    ul = Userlist()
    u = ul.loaduserbyname(session.get("user"))
    configchar = u.config("character_sheet", None)
    if configchar:
        redirect(url_for("fensheet", c=configchar))
    sheet = u.sheet.getdictrepr()
    if sheet["Type"] == "OWOD":
        return render_template("vampsheet.html", character=sheet, own=True)
    error = "unrecognized sheet format"
    return render_template("vampsheet.html", character=sheet, error=error, own=True)


@app.route("/showsheet/<name>")
def showsheet(name="None"):
    checklogin()
    if name == "None":
        return "error"
    name = name.upper()
    ul = Userlist()
    u = ul.loaduserbyname(name)
    if u:
        if u.sheetpublic or session.get("admin", False):
            return render_template(
                "vampsheet.html", character=u.sheet.getdictrepr(), own=False
            )
    flash("you do not have permission to see this")
    return render_template(
        "vampsheet.html", character=VampireCharacter().getdictrepr(), own=False
    )


@app.route("/deletesheet/", methods=["POST"])
def del_sheet():
    checklogin()
    x = int(request.form["sheetnum"])
    ul = Userlist()
    u = ul.loaduserbyname(session.get("user"))
    u.oldsheets.pop(x)
    ul.saveuserlist()
    flash("Sheet deleted from history!")
    return redirect(url_for("menu_oldsheets"))


@app.route("/restoresheet/", methods=["POST"])
def res_sheet():
    checklogin()
    x = int(request.form["sheetnum"])
    ul = Userlist()
    u = ul.loaduserbyname(session.get("user"))
    newactive = u.oldsheets.pop(x)
    u.oldsheets.append(u.sheet)
    u.sheet = newactive
    ul.saveuserlist()
    flash("Sheet deleted from history!")
    return redirect(url_for("menu_oldsheets"))


@app.route("/berlinmap")
def berlinmap():
    return render_template("map.html")
    # return redirect(
    # "https://www.google.com/maps/d/viewer?mid=1TH6vryHyVxv_xFjFJDXgXQegZO4")


@app.route("/berlinmap/data.dat")
def mapdata():
    db = connect_db("mapdata")
    log.debug("generating mapdata")
    time0 = time.time()
    cur = db.execute("SELECT name, owner,tags,data FROM property")
    plzs = {}
    for row in cur.fetchall():
        plzs[row[0]] = {
            "owner": row[1] or "",
            "tags": row[2] or "",
            "data": row[3] or "",
        }
    cur = db.execute("SELECT name, faction, allegiance, clan, tags FROM actors")
    for row in cur.fetchall():
        for plzdat in plzs.values():
            if plzdat["owner"].upper() == row[0]:
                plzdat["tags"] += " ".join(x for x in row[1:] if x)
                if row[1]:
                    plzdat["faction"] = row[1]
    log.debug(f"took: {time.time() - time0} seconds.")
    return json.dumps(plzs)


@app.route("/oldsheets/")
def menu_oldsheets():
    checklogin()
    ul = Userlist()
    u = ul.loaduserbyname(session.get("user"))
    oldsheets = []
    xpdiffs = []
    for i in range(len(u.oldsheets)):
        oldsheets.append(u.oldsheets[i].timestamp)
        if i > 0:
            xpdiffs.append(u.oldsheets[i].get_diff(u.oldsheets[i - 1]))
        else:
            xpdiffs.append(u.oldsheets[i].get_diff(None))
    return render_template("oldsheets.html", oldsheets=oldsheets, xpdiffs=xpdiffs)


@app.route("/showoldsheets/<x>")
def showoldsheets(x):
    checklogin()
    ul = Userlist()
    u = ul.loaduserbyname(session.get("user"))
    try:
        sheetnum = int(x)
    except:
        return redirect(url_for("/oldsheets/"))
    return render_template(
        "vampsheet.html", character=u.oldsheets[sheetnum].getdictrepr(), oldsheet=x
    )


@app.route("/new_vamp_sheet/", methods=["GET"])
def new_vamp_sheet():
    checklogin()
    return render_template("vampsheet_editor.html", character=VampireCharacter())


@app.route("/modify_sheet/", methods=["GET", "POST"])
@app.route("/modify_sheet/<t>", methods=["GET", "POST"])
def modify_sheet(t=None):
    checklogin()
    ul = Userlist()
    u = ul.loaduserbyname(session.get("user"))
    if t is not None:
        if t == "FEN":
            u.sheet = FenCharacter()
        if t == "OWOD":
            u.sheet = VampireCharacter()
    if request.method == "POST":
        log.info(f"incoming modify: {request.form}")
        u.update_sheet(request.form)
        ul.saveuserlist()

        return redirect("/charactersheet/")
    a = "NOPE"
    sheet = u.sheet.getdictrepr()
    if sheet["Type"] == "OWOD":
        a = render_template(
            "vampsheet_editor.html",
            character=sheet,
            Clans=u.sheet.get_clans(),
            Backgrounds=u.sheet.get_backgrounds(),
        )
    elif sheet["Type"] == "FEN":
        a = render_template("fensheet_editor.html", character=u.sheet)
    return a


@app.route("/delete_entry/<ident>", methods=["POST"])
def delete_entry(ident):
    if checktoken():
        checklogin()
        db = connect_db("deleteentry")
        entry = {}
        cur = db.execute(
            "SELECT author, title, text, id FROM entries WHERE id = ?", [ident]
        )
        for row in cur.fetchall():  # SHOULD only run once
            entry = dict(author=row[0], title=row[1], text=row[2], id=row[3])
        if (not session.get("admin")) and (
            entry.get("author").upper() != session.get("user")
        ):
            flash("This is not your Post!")
        else:
            if entry.get("author")[0].islower():
                db.execute(
                    "UPDATE entries SET author = ? WHERE id = ?",
                    [entry.get("author").upper(), entry.get("id")],
                )
                flash('Entry: "' + entry.get("title") + '" has been restored.')

            else:
                db.execute(
                    "UPDATE entries SET author = ? WHERE id = ?",
                    [entry.get("author").lower(), entry.get("id")],
                )
                flash('Entry: "' + entry.get("title") + '" has been deleted.')
            db.commit()
        return redirect(url_for("show_entries"))
    return abort(404)


@app.route("/add", methods=["POST"])
def add_entry():
    checklogin()
    log.info(f"{session.get('user', '?')} adding {request.form}")
    if checktoken():
        db = connect_db("mapdata")
        db.execute(
            "INSERT INTO entries (author, title, text, tags) VALUES (?, ?, ?, ?)",
            [
                session.get("user"),
                request.form["title"],
                request.form["text"],
                request.form["tags"],
            ],
        )
        db.commit()
        flash("New entry was successfully posted")

    return redirect(url_for("show_entries"))


@app.route("/buy_funds/", methods=["GET", "POST"])
def add_funds():
    ul = Userlist()
    u = ul.loaduserbyname(session.get("user"))
    error = None
    keyprovided = session.get("amount") is not None
    if not keyprovided:
        keyprovided = None
    if request.method == "POST":
        if checktoken():
            try:
                amount = int(request.form["amount"])
                if amount > 0:
                    key = int(time.time())
                    key = generate_password_hash(str(key))
                    log.info(
                        f"REQUEST BY {u.username} FOR {amount} CREDITS. KEY: {key}."
                    )
                    session["key"] = key[-10:]
                    session["amount"] = amount
                    keyprovided = True
                else:
                    error = "need positive amount"
            except Exception:
                try:
                    key = request.form["key"][-10:]
                    if key == session.pop("key"):
                        flash(
                            "Transfer of "
                            + str(session.get("amount"))
                            + " Credits was successfull!"
                        )
                        u.funds += int(session.pop("amount"))
                    else:
                        error = "wrong key, transaction invalidated."
                        session.pop("amount")
                        session.pop("key")
                except Exception:
                    error = "invalid transaction"

    ul.saveuserlist()

    return render_template("funds.html", user=u, error=error, keyprovided=keyprovided)


@app.route("/register", methods=["GET", "POST"])
def register():  # this is not clrs secure because it does not need to be
    error = None
    if request.method == "POST":
        username = request.form["username"].strip().upper()
        if len(username) > 2:
            if request.form["password"] == request.form["passwordcheck"]:
                password = request.form["password"]
                if len(password) > 0:
                    log.info(f"creating user {username}")
                    error = Userlist.adduser(username, password)
                    if error is None:
                        flash("User successfully created.")
                        return redirect(url_for("start"))
                else:
                    error = "Password has to be not empty!"
            else:
                error = "Passwords do not match!"
        else:
            error = "Username is too short!"
    if error:
        flash(error, category="error")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
@app.route("/login/<path:r>", methods=["GET", "POST"])
def login(r=None):
    error = None
    returnto = r
    if request.method == "POST":
        ul = Userlist()
        user = request.form["username"]
        user = user.upper()
        if not ul.valid(user, request.form.get("password", None)):
            error = "invalid username/password combination"
        else:
            session["logged_in"] = True
            session["print"] = gen_salt(32)
            session["user"] = user
            session["admin"] = (
                ul.loaduserbyname(session.get("user")).admin == "Administrator"
            )
            flash("You were logged in")
            log.info(f"logged in as {user}")
            returnto = request.form.get("returnto", None)
            if returnto is None:
                return redirect(url_for("show_entries"))
            return redirect(returnto)
    return render_template("login.html", returnto=returnto, error=error)


@app.route("/logout")
def logout():
    session.clear()
    flash("You were logged out")
    return redirect(url_for("show_entries"))


@app.route("/nn")
def start():
    return render_template(
        "show_entries.html",
        entries=[
            dict(
                author="the NOSFERATU NETWORK",
                title="WeLcOmE tO tHe NoSfErAtU nEtWoRk",
                text="",
            )
        ],
        heads=['<META HTTP-EQUIV="refresh" CONTENT="5;url=/">'],
    )


@app.route("/user/<username>")
def show_user_profile(username):
    msgs = []

    if username == session.get("user"):
        db = connect_db("mapdata")
        # get messages for this user if looking at own page
        cur = db.execute(
            "SELECT author,recipient,title,text,value,lock, id FROM messages "
            "WHERE ? IN (recipient, author) " + " ORDER BY id DESC",
            (session.get("user"),),
        )
        for row in cur.fetchall():
            msg = dict(
                author=row[0],
                recipient=row[1],
                title=row[2],
                text=row[3],
                value=row[4],
                lock=row[5],
                id=row[6],
            )
            if msg["lock"]:
                if msg["author"] == username:
                    msg["text"] = (
                        "[not yet paid for by "
                        + msg["recipient"]
                        + "]<br><br>"
                        + msg["text"]
                    )
                    msg.pop("lock")
                else:
                    msg["text"] = "[locked until you pay]"
            msgs.append(msg)

    ul = Userlist()
    u = ul.loaduserbyname(username)
    if u is None:
        u = User(username, "")
    site = render_template("userinfo.html", user=u, msgs=msgs, configs=u.configs())
    return site


@app.route("/test/<x>")
def test_migrate(x):
    ul = Userlist()
    for c in x.split(" "):
        ul.loaduserbyname(c)
    ul.saveuserlist()


@app.route("/impressum/")
def impressum():
    return render_template("Impressum.html")


@app.route("/sendmsg/<username>", methods=["POST"])
def send_msg(username):
    def check0(a):
        return int(a) == 0

    error = None
    if checktoken():
        checklogin()
        db = connect_db("mapdata")
        db.execute(
            "INSERT INTO messages (author,recipient,title,text,value,lock)"
            " VALUES (?, ?, ?, ?, ?, ?)",  # 6
            [
                session.get("user"),  # 1 -author
                username,  # 2 -recipient
                request.form["title"],  # 3 title
                request.form["text"],  # 4 text
                request.form["price"],  # 5 value
                not check0(request.form["price"]),  # 6 lock
            ],
        )
        db.commit()
        flash("Message sent")
    return redirect(url_for("show_entries", error=error))


@app.route("/unlock/<ident>")
def unlock(ident):
    ul = Userlist()
    error = None
    u = None
    lock = 0
    author = ""
    value = 0
    if checktoken():
        db = connect_db("mapdata")
        u = ul.loaduserbyname(session.get("user"))
        cur = db.execute(
            "SELECT author, value, lock FROM messages WHERE id = ?", [ident]
        )
        for row in cur.fetchall():
            author = row[0]
            value = row[1]
            lock = row[2]
        n = ul.loaduserbyname(
            author
        )  # n because n = u seen from the other side of the table
        if lock == 1:
            if u.funds < value:
                error = "Not enough funds."
            else:
                u.funds -= value
                aftertax = int(value * 0.99)  # 1% Tax
                n.funds = int((n.funds + aftertax))
                db.execute("UPDATE messages SET lock = 0 WHERE id = ?", [ident])
                flash("Transfer complete. Check the received message.")
                db.commit()
                ul.saveuserlist()
        else:
            flash("already unlocked!")

    return render_template(
        "userinfo.html",
        user=u,
        error=error,
        heads=[
            '<META HTTP-EQUIV="refresh" CONTENT="5;url='
            + url_for("show_user_profile", username=u.username)
            + '">'
        ],
    )


@app.route("/resetpassword/", methods=["GET", "POST"])
def resetpassword():
    checklogin()
    ul = Userlist()
    u = ul.loaduserbyname(session.get("user"))
    if request.method == "POST":
        if checktoken():
            try:
                username = request.form["username"].strip().upper()
                password = request.form["password"]
                newpassword = request.form["newpassword"]
                if session.get("admin", False):
                    u = ul.loaduserbyname(username)
                if u.username == username:
                    if u.check_password(password) or session.get("admin", False):
                        u.set_password(newpassword)
                        flash("Password change successfull!")
                    else:
                        flash("Wrong password!")
                else:
                    flash("You are not " + username)
            except:
                flash("You seem to not exist. Huh...")
                return render_template("resetpassword.html")
    ul.saveuserlist()

    return render_template("resetpassword.html")


@app.route("/payout/", methods=["GET", "POST"])
def payout():
    checklogin()
    ul = Userlist()
    u = ul.loaduserbyname(session.get("user"))
    error = None
    if request.method == "POST":
        if checktoken():
            try:
                amount = int(request.form["amount"])

                u.funds += -amount
                log.info(f"DEDUCT BY {session.get('user')}: {amount}")
                if u.funds < 0:
                    flash("not enough funds")
                    raise Exception()
                flash("Deduct successfull")
                ul.saveuserlist()
            except:
                error = (
                    'Error deducting "' + request.form.get("amount", "nothing") + '".'
                )

    return render_template("payout.html", user=u, error=error)


@app.route("/lightswitch/")
def lightswitch():
    if session.get("light", False):
        session.pop("light")
    else:
        session["light"] = "ON"
    return redirect(request.referrer)


@app.route("/favicon.ico")
def favicon():
    return redirect("/static/favicon.ico")
