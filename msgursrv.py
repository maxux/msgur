import os
import sys
import time
import datetime
import uuid
import sqlite3
import json
import base64
import hashlib
from datetime import datetime
from flask import Flask, request, jsonify, render_template, abort

class Msgur:
    def __init__(self):
        self.app = Flask(__name__, static_url_path='/static')
        self.app.url_map.strict_slashes = False

        self.gitsha = self.gitsharoot()
        print(f"[+] running code revision: {self.gitsha}")

    def gitsharoot(self):
        try:
            ref = ""

            with open(".git/HEAD", "r") as f:
                head = f.read()
                if not head.startswith("ref:"):
                    return None

                ref = head[5:].strip()

            with open(f".git/{ref}", "r") as f:
                sha = f.read()
                return sha[:8]

        except Exception as e:
            print(e)
            return None

    def idgen(self):
        uid = uuid.uuid4().bytes

        h = hashlib.blake2b(digest_size=9)
        h.update(uid)

        digest = h.digest()

        # use base64 url safe
        encoded = base64.b64encode(digest, altchars=b'-_')

        return encoded.decode('utf-8')


    def routes(self):
        @self.app.context_processor
        def inject_now():
            return {'now': datetime.utcnow()}

        @self.app.route('/fetch/<id>', methods=['GET'])
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

        @self.app.route('/create', methods=['POST'])
        def create():
            db = sqlite3.connect("db/msgur.sqlite3")

            mid = self.idgen()
            payload = request.get_json()
            message = payload["message"]

            c = db.cursor()
            fields = (mid, message,)
            c.execute('INSERT INTO messages (id, message) VALUES (?, ?)', fields)
            db.commit()
            db.close()

            return jsonify({"id": mid})

        @self.app.route('/about', methods=['GET'])
        def about():
            content = {"revision": self.gitsha}
            return render_template("about.html", **content)

        @self.app.route('/<hash>', methods=['GET'])
        def index_hash(hash):
            content = {"revision": self.gitsha}
            return render_template("fetch.html", **content)

        @self.app.route('/', methods=['GET'])
        def index():
            content = {"revision": self.gitsha}
            return render_template("create.html", **content)

if __name__ == "msgursrv":
    print("[+] wsgi: initializing msgur application")

    root = Msgur()
    root.routes()
    app = root.app

