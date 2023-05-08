import os
import sys
import time
import datetime
import uuid
import sqlite3
import json
import base64
import git
import hashlib
from config import config
from flask import Flask, request, jsonify, render_template, abort

app = Flask(__name__, static_url_path='/static')
app.url_map.strict_slashes = False

repo = git.Repo(search_parent_directories=True)
sha = repo.head.object.hexsha
gitsha = sha[0:8]

def idgen():
    uid = uuid.uuid4().bytes

    h = hashlib.blake2b(digest_size=9)
    h.update(uid)

    digest = h.digest()

    # use base64 url safe
    encoded = base64.b64encode(digest, altchars=b'-_')

    return encoded.decode('utf-8')


@app.route('/fetch/<id>', methods=['GET'])
def fetch(id):
    db = sqlite3.connect("db/msgur.sqlite3")

    c = db.cursor()

    # ensure data are overwritten when deleting entry
    c.execute("PRAGMA secure_delete = ON")
    c.fetchone()

    fields = (id,)
    c.execute('SELECT message FROM messages WHERE id = ?', fields)
    data = c.fetchone()

    if data is None:
        db.close()
        return abort(404)

    c.execute('DELETE FROM messages WHERE id = ?', fields)
    db.commit()
    db.close()

    return jsonify({"message": data[0]})

@app.route('/create', methods=['POST'])
def create():
    db = sqlite3.connect("db/msgur.sqlite3")

    mid = idgen()
    payload = request.get_json()
    message = payload["message"]

    c = db.cursor()
    fields = (mid, message,)
    c.execute('INSERT INTO messages (id, message) VALUES (?, ?)', fields)
    db.commit()
    db.close()

    return jsonify({"id": mid})

@app.route('/about', methods=['GET'])
def about():
    content = {"revision": gitsha}
    return render_template("about.html", **content)

@app.route('/<hash>', methods=['GET'])
def index_hash(hash):
    content = {"revision": gitsha}
    return render_template("fetch.html", **content)

@app.route('/', methods=['GET'])
def index():
    content = {"revision": gitsha}
    return render_template("create.html", **content)

def production():
    return app

if __name__ == "__main__":
    print("[+] listening in debug mode")
    app.run(host=config['listen'], port=config['port'], debug=config['debug'], threaded=True)

