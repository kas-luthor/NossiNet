import os
import sqlite3
from contextlib import closing
from pathlib import Path
import random

from flask import g

from NossiSite import app


class DescriptiveError(Exception):
    pass


def init_db():
    print("initializing DB")
    with closing(connect_db("initialization")) as db:
        with app.open_resource("../schema.sql", mode="r") as f:
            db.cursor().executescript(f.read())
        db.commit()


def connect_db(source):
    """db connection singleton"""
    db = getattr(g, "db", None)
    if db:
        return db
    if source != "before request":
        print("connecting to", app.config["DATABASE"], "from", source)
    if not Path(app.config["DATABASE"]).exists():
        Path(app.config["DATABASE"]).touch()
        init_db()
    g.db = sqlite3.connect(app.config["DATABASE"])
    return g.db


def write_nonblocking(path, data):
    path = Path(path)
    if path.is_dir():
        path = path / "_"
    i = 0
    while (path.with_suffix(f".{i}")).exists():
        i += 1
    with path.with_suffix(f".{i}").open(mode="x") as x:
        x.write(data + "\n")
        x.write("DONE")  # mark file as ready


def read_nonblocking(path):
    path = Path(path)
    if path.is_dir():
        path = path / "_"
    result = []
    file: Path
    for file in sorted(path.parent.glob(str(path.stem) + "*")):
        with file.open(mode="r") as f:
            lines = f.readlines()
            if lines[-1] != "DONE":
                break  # file not read yet or fragmented
            result += lines[:-1]
        os.remove(str(file.absolute()))
    return result


def is_int(s: str) -> bool:
    try:
        int(s)
        return True
    except ValueError:
        return False


def sumdict(inp):
    result = 0
    try:
        for e in inp.keys():
            result += int(inp[e])
    except:
        result = sum(inp)
    return result


def d10(amt, diff, ones=True):  # faster than the WoDDice
    succ = 0
    anti = 0
    for i in range(amt):
        x = random.randint(1, 10)
        if x >= diff:
            succ += 1
        if ones and x == 1:
            anti += 1
    if anti > 0:
        if succ > anti:
            return succ - anti
        else:
            if succ > 0:
                return 0
            else:
                return 0 - anti
    else:
        return succ
