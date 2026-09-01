import time
import uuid
import json
import hashlib
import MySQLdb
import MySQLdb.cursors
from config import Config as config
from modules.repository import Repository
from datetime import datetime
from flask import Flask, request, jsonify, render_template, abort, g

class MsgURWebServer:
    def __init__(self):
        self.config = config

        self.app = Flask(__name__, static_url_path='/static')
        self.app.url_map.strict_slashes = False

        if self.config.debug:
            print("[+] debug instance enabled")
            self.app.config['TEMPLATES_AUTO_RELOAD'] = True

        self.repository = Repository(self.config.gitinfo)
        if self.repository.revision:
            print(f"[+] repository revision: {self.repository.revision}")
            print(f"[+] repository committed: {self.repository.created}")

    def database(self):
        db = MySQLdb.connect(
            host=config.db.hostname,
            unix_socket=config.db.socket,
            user=config.db.username,
            password=config.db.password,
            database=config.db.database,
            autocommit=True,
            cursorclass=MySQLdb.cursors.DictCursor
        )

        return db

    def identifier_generate(self):
        uid = uuid.uuid4().bytes

        ctx = hashlib.blake2b(digest_size=6)
        ctx.update(uid)
        digest = ctx.digest()

        return digest.hex()

    def routes(self):
        @self.app.context_processor
        def inject_context():
            return {
                "now": datetime.utcnow(),
                "git": self.repository,
            }

        @self.app.before_request
        def before_request_handler():
            # shortcut static files
            if request.path.startswith("/static"):
                return None

            g.db = self.database()
            return None

        @self.app.after_request
        def after_request_handler(response):
            # shortcut static files
            if request.path.startswith("/static"):
                return response

            if "db" in g:
                g.db.close()

            response.headers["Access-Control-Allow-Origin"] = "*"
            return response

        @self.app.get('/api/fetch/<id>')
        def fetch(id):
            cursor = g.db.cursor()
            cursor.execute("""
               SELECT ciphertext, UNIX_TIMESTAMP(created) created, iv
                FROM messages WHERE id = %(id)s
                  AND seen IS NULL

            """, {"id": id})

            row = cursor.fetchone()
            if row is None:
                abort(404)

            cursor.execute("""
                UPDATE messages SET ciphertext = NULL, seen = CURRENT_TIMESTAMP
                WHERE id = %(id)s
                AND seen IS NULL

            """, {"id": id})

            # FIXME
            # cursor.execute("DELETE FROM messages WHERE id = %(id)s", {"id": id})

            return jsonify(row)

        @self.app.post('/api/create')
        def create():
            cursor = g.db.cursor()
            payload = request.json

            data = {
                "id": self.identifier_generate(),
                "data": payload.get("message"),
                "iv": payload.get("iv")
            }

            cursor.execute("""
                INSERT INTO messages (id, ciphertext, iv)
                VALUES (%(id)s, %(data)s, %(iv)s)

            """, data)

            return jsonify({"id": data["id"]})

        #
        # Static Templates
        #
        @self.app.get('/about')
        def about():
            return render_template("about.html")

        @self.app.get('/<hash>')
        def index_hash(hash):
            return render_template("fetch.html")

        @self.app.get('/')
        def index():
            return render_template("create.html")

if __name__ == "msgursrv":
    print("[+] wsgi: initializing msgur application")

    root = MsgURWebServer()
    root.routes()
    app = root.app
