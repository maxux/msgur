import os
import sys
import time
import datetime
import uuid
import sqlite3
import json
import base64
from config import config
from flask import Flask, request, jsonify, render_template, abort

app = Flask(__name__, static_url_path='/static')
app.url_map.strict_slashes = False

@app.route('/fetch/<id>', methods=['GET'])
def fetch(id):
    db = sqlite3.connect("db/msgur.sqlite3")

    c = db.cursor()
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

    mid = str(uuid.uuid4())
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
    return render_template("about.html")

@app.route('/<hash>', methods=['GET'])
def index_hash(hash):
    return render_template("fetch.html")

@app.route('/', methods=['GET'])
def index():
    return render_template("create.html")

print("[+] listening")
app.run(host=config['listen'], port=config['port'], debug=config['debug'], threaded=True)

