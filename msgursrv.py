import time
import uuid
import json
import hashlib
from config import Config as config
from modules.repository import Repository
from modules.database import Database
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

        self.database = Database(self.config.db)

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

            g.db = self.database.instance()
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
            data = g.db.fetch(id)
            if data is None:
                abort(404)

            return jsonify(data)

        @self.app.post('/api/create')
        def create():
            payload = request.json

            id = self.identifier_generate()
            data = payload.get("message")
            iv = payload.get("iv")

            info = g.db.create(id, data, iv)
            return jsonify(info)

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
