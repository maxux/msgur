import sqlite3
import MySQLdb
import MySQLdb.cursors
import time
from typing import NamedTuple

#
# Database Engines
#
class Engines:
    class MariaDB(NamedTuple):
        username: str
        password: str
        database: str
        hostname: str = "127.0.0.1"
        socket: str = ""

    class SQLite(NamedTuple):
        dbfile: str

engines = Engines


#
# Database Backends
#
class _mariadb:
    """
    CREATE TABLE messages (
      id VARCHAR(12) CHARACTER SET ascii COLLATE ascii_general_ci NOT NULL,
      ciphertext TEXT CHARACTER SET ascii COLLATE ascii_bin DEFAULT NULL,
      created TIMESTAMP NOT NULL DEFAULT current_timestamp(),
      seen TIMESTAMP NULL DEFAULT NULL,
      iv VARCHAR(24) CHARACTER SET ascii COLLATE ascii_general_ci NOT NULL

    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

    ALTER TABLE messages ADD PRIMARY KEY (id), ADD KEY seen (seen);
    """
    def __init__(self, cfg):
        self.cfg = cfg
        self.ctx = MySQLdb.connect(
            host=self.cfg.hostname,
            unix_socket=self.cfg.socket,
            user=self.cfg.username,
            password=self.cfg.password,
            database=self.cfg.database,
            autocommit=False,
            cursorclass=MySQLdb.cursors.DictCursor
        )

    def close(self):
        self.ctx.close()

    def create(self, id, data, iv):
        cursor = self.ctx.cursor()
        params = {"id": id, "data": data, "iv": iv}

        cursor.execute("""
            INSERT INTO messages (id, ciphertext, iv)
            VALUES (%(id)s, %(data)s, %(iv)s)

        """, params)

        self.ctx.commit()

        return {"id": id}

    def fetch(self, id):
        cursor = self.ctx.cursor()
        cursor.execute("""
           SELECT ciphertext, UNIX_TIMESTAMP(created) created, iv
            FROM messages WHERE id = %(id)s
             AND seen IS NULL
           FOR UPDATE

        """, {"id": id})

        row = cursor.fetchone()
        if row is None:
            return None

        cursor.execute("""
            UPDATE messages SET ciphertext = NULL, seen = CURRENT_TIMESTAMP
            WHERE id = %(id)s
            AND seen IS NULL

        """, {"id": id})

        self.ctx.commit()

        return row

    def statistics(self):
        cursor = self.ctx.cursor()
        cursor.execute("SELECT COUNT(*) `rows` FROM messages");
        return cursor.fetchone()


class _sqlite:
    """
    CREATE TABLE messages (
        id varchar(12) primary key,
        ciphertext text default null,
        created timestamp default current_timestamp,
        seen timestamp default null,
        iv varchar(24)
    );
    CREATE INDEX seen ON messages (seen);
    """
    def __init__(self, cfg):
        self.cfg = cfg
        self.ctx = sqlite3.connect(self.cfg.dbfile)

    def close(self):
        self.ctx.close()

    def create(self, id, data, iv):
        cursor = self.ctx.cursor()
        params = (id, data, iv,)

        cursor.execute("""
            INSERT INTO messages (id, ciphertext, iv)
            VALUES (?, ?, ?)

        """, params)

        self.ctx.commit()

        return {"id": id}

    def fetch(self, id):
        cursor = self.ctx.cursor()
        cursor.execute("PRAGMA secure_delete = ON")
        cursor.fetchone()

        cursor.execute("""
           SELECT ciphertext, unixepoch(created), iv
            FROM messages WHERE id = ?
             AND seen IS NULL

        """, (id,))

        xrow = cursor.fetchone()
        if xrow is None:
            return None

        cursor.execute("""
            UPDATE messages SET ciphertext = NULL, seen = CURRENT_TIMESTAMP
            WHERE id = ?
            AND seen IS NULL

        """, (id,))

        self.ctx.commit()

        return {"ciphertext": xrow[0], "created": xrow[1], "iv": xrow[2]}

    def statistics(self):
        cursor = self.ctx.cursor()
        cursor.execute("SELECT COUNT(*) FROM messages");
        data = cursor.fetchone()

        return {"rows": data[0]}


#
# Instances Manager
#
class InvalidBackend(Exception):
    pass

class Database:
    def __init__(self, cfg):
        self.cfg = cfg
        self.backend = None

        if isinstance(self.cfg, Engines.MariaDB):
            print("[+] database backend active: mariadb")
            self.backend = _mariadb

        elif isinstance(self.cfg, Engines.SQLite):
            print("[+] database backend active: sqlite3")
            self.backend = _sqlite

        else:
            raise InvalidBackend("No backend available for supplied settings")

        # Check database schema and contents
        self.basecheck()

    def basecheck(self):
        try:
            check = self.instance()
            info = check.statistics()
            print(f"[+] database loaded, {info['rows']} messages found")

        except Exception as error:
            print(f"[-] database unavailable: {error}")
            exit(1)

    def instance(self):
        return self.backend(self.cfg)
