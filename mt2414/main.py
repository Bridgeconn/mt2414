import os
import uuid
import sqlite3
import json
import psycopg2
from functools import wraps
from datetime import datetime, timedelta

import scrypt
import requests
import jwt
from flask import Flask, request, session
from flask import g
from flask_cors import CORS, cross_origin
import nltk
import polib


PO_METADATA = {
    'Project-Id-Version': '1.0',
    'Report-Msgid-Bugs-To': 'tfbfgroup@googlegroups.com',
    'POT-Creation-Date': '2007-10-18 14:00+0100',
    'PO-Revision-Date': '2007-10-18 14:00+0100',
    'Last-Translator': 'you <you@example.com>',
    'Language-Team': 'English <yourteam@example.com>',
    'MIME-Version': '1.0',
    'Content-Type': 'text/plain; charset=utf-8',
    'Content-Transfer-Encoding': '8bit',
}


app = Flask(__name__)
CORS(app)

sendinblue_key = os.environ.get("MT2414_SENDINBLUE_KEY")
jwt_hs256_secret = os.environ.get("MT2414_HS256_SECRET")
postgres_host = os.environ.get("MT2414_POSTGRES_HOST", "localhost")
postgres_port = os.environ.get("MT2414_POSTGRES_PORT", "5432")
postgres_user = os.environ.get("MT2414_POSTGRES_USER", "postgres")
postgres_password = os.environ.get("MT2414_POSTGRES_PASSWORD", "secret")
postgres_database = os.environ.get("MT2414_POSTGRES_DATABASE", "postgres")

def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'db'):
        g.db = psycopg2.connect(dbname=postgres_database, user=postgres_user, password=postgres_password, host=postgres_host, port=postgres_port)
    return g.db


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'db'):
        g.db.close()


@app.route("/v1/auth", methods=["POST"])
def auth():
    username = request.form["username"]
    password = request.form["password"]
    connection = get_db()
    cursor = connection.cursor()
    cursor.execute("SELECT password_hash, password_salt FROM users WHERE email = %s AND email_verified = True", (username,))
    rst = cursor.fetchone()
    if not rst:
        return '{}'
    password_hash = rst[0].hex()
    password_salt = bytes.fromhex(rst[1].hex())
    password_hash_new = scrypt.hash(password, password_salt).hex()
    if password_hash == password_hash_new:
        access_token = jwt.encode({'sub': username}, jwt_hs256_secret, algorithm='HS256')
        return '{"access_token": "%s"}\n' % access_token.decode('utf-8')
    return '{}'


@app.route("/v1/registrations", methods=["POST"])
def new_registration():
    email = request.form['email']
    password = request.form['password']
    headers = {"api-key": sendinblue_key}
    url = "https://api.sendinblue.com/v2.0/email"
    verification_code = str(uuid.uuid4()).replace("-","")
    body = '''Hi,<br/><br/>Thanks for your interest to use the MT2414 web service. <br/>
    You need to confirm your email by opening this link:

    <a href="https://api.mt2414.in/v1/verifications/%s">https://api.mt2414.in/v1/verifications/%s</a>

    <br/><br/>The documentation for accessing the API is available at <a href="http://docs.mt2414.in">docs.mt2414.in</a>''' % (verification_code, verification_code)
    payload = {
        "to": {email: ""},
        "from": ["noreply@mt2414.in","Mt. 24:14"],
        "subject": "MT2414 - Please verify your email address",
        "html": body,
        }
    connection = get_db()
    password_salt = str(uuid.uuid4()).replace("-","")
    password_hash = scrypt.hash(password, password_salt)


    cursor = connection.cursor()
    cursor.execute("SELECT email FROM users WHERE email = %s", (email,))
    if cursor.fetchone():
        return "{}\n"
    else:
        cursor.execute("INSERT INTO users (email, verification_code, password_hash, password_salt, created_at) VALUES (%s, %s, %s, %s, current_timestamp)",
                (email, verification_code, password_hash, password_salt))
    cursor.close()
    connection.commit()
    resp = requests.post(url, data=json.dumps(payload), headers=headers)
    return '{}\n'

@app.route("/v1/forgotpassword", methods = ["POST"])
def forgot_password():
    email = request.form['email']
    password = request.form['password']
    connection = get_db()
    cursor = connection.cursor()
    cursor.execute("SELECT email from users WHERE email = %s", (email,))
    if cursor.fetchone():
        headers = {"api-key": sendinblue_key}
        url = "https://api.sendinblue.com/v2.0/email"
        verification_code = str(uuid.uuid4()).replace("-","")
        body = '''Hi,<br/><br/>your request for changing the password has been recieved. <br/>
        Your new password would be activated upon opening this link:

        <a href="https://api.mt2414.in/v1/verifications/%s">https://api.mt2414.in/v1/verifications/%s</a>

        <br/><br/>The documentation for accessing the API is available at <a href="http://docs.mt2414.in">docs.mt2414.in</a>''' % (verification_code, verification_code)
        payload = {
            "to": {email: ""},
            "from": ["noreply@mt2414.in","Mt. 24:14"],
            "subject": "MT2414 - Password change verification mail",
            "html": body,
            }
        password_salt = str(uuid.uuid4()).replace("-","")
        password_hash = scrypt.hash(password, password_salt)
        cursor.execute("UPDATE users SET email_verified = False, verification_code = %s, password_hash = %s, password_salt = %s, created_at = current_timestamp WHERE email = %s", (verification_code, password_hash, password_salt, email))
        connection.commit()
        resp = requests.post(url, data=json.dumps(payload), headers=headers)
        return '{}\n'
    else:
        return 'email has not yet been registered'
    return '{}\n'

class TokenError(Exception):

    def __init__(self, error, description, status_code=401, headers=None):
        self.error = error
        self.description = description
        self.status_code = status_code
        self.headers = headers

    def __repr__(self):
        return 'TokenError: %s' % self.error

    def __str__(self):
        return '%s. %s' % (self.error, self.description)

@app.errorhandler(TokenError)
def auth_exception_handler(error):
    return 'Authentication failed\n', 401

def check_token(f):
    @wraps(f)
    def wrapper(*args, **kwds):
        auth_header_value = request.headers.get('Authorization', None)
        if not auth_header_value:
            raise TokenError('No Authorization header', 'Token missing')

        parts = auth_header_value.split()

        if (len(parts) == 1) and (parts[0].lower() != 'bearer'):
            access_id, key = parts[0].split(":")
            connection = get_db()
            cursor = connection.cursor()
            cursor.execute("SELECT keys.key_hash, keys.key_salt, users.email FROM keys LEFT JOIN users ON keys.user_id = users.id WHERE keys.access_id = %s AND users.email_verified = True", (access_id,))
            rst = cursor.fetchone()
            if not rst:
                raise TokenError('Invalid token', 'Invalid token')
            key_hash = rst[0].hex()
            key_salt = bytes.fromhex(rst[1].hex())

            key_hash_new = scrypt.hash(key, key_salt).hex()
            if key_hash == key_hash_new:
                request.email = rst[2]
            else:
                raise TokenError('Invalid token', 'Invalid token')
        elif (len(parts) == 2) and (parts[0].lower() == 'bearer'):
            # check for JWT token
            token = parts[1]
            options = {
                'verify_sub': True
            }
            algorithm = 'HS256'
            leeway = timedelta(seconds=10)

            try:
                decoded = jwt.decode(token, jwt_hs256_secret, options=options, algorithms=[algorithm], leeway=leeway)
                request.email = decoded['sub']
            except jwt.exceptions.DecodeError as e:
                raise TokenError('Invalid token', str(e))
        else:
            raise TokenError('Invalid header', 'Token contains spaces')

        #raise TokenError('Invalid JWT header', 'Token missing')
        return f(*args, **kwds)
    return wrapper

@app.route("/v1/keys", methods=["POST"])
@check_token
def new_key():
    key = str(uuid.uuid4()).replace("-","")
    access_id = str(uuid.uuid4()).replace("-","")
    key_salt = str(uuid.uuid4()).replace("-","")
    key_hash = scrypt.hash(key, key_salt)

    connection = get_db()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM keys LEFT JOIN users ON keys.user_id = users.id WHERE users.email = %s AND users.email_verified = True", (request.email,))
    rst = cursor.fetchone()
    cursor.execute("SELECT id FROM users WHERE email = %s", (request.email,))
    rst2 = cursor.fetchone()
    user_id = rst2[0]
    if rst:
        cursor.execute("UPDATE keys SET access_id=%s, key_hash=%s, key_salt=%s WHERE user_id=%s", (access_id, key_hash, key_salt, user_id))
    else:
        cursor.execute("INSERT INTO keys (access_id, key_hash, key_salt, user_id) VALUES (%s, %s, %s, %s)", (access_id, key_hash, key_salt, user_id))
    cursor.close()
    connection.commit()
    return '{"id": "%s", "key": "%s"}\n' % (access_id, key)

@app.route("/v1/verifications/<string:code>", methods=["GET"])
def new_registration2(code):
    connection = get_db()
    cursor = connection.cursor()
    cursor.execute("SELECT email FROM users WHERE verification_code = %s AND email_verified = False", (code,))
    if cursor.fetchone():
        cursor.execute("UPDATE users SET email_verified = True WHERE verification_code = %s", (code,))
    cursor.close()
    connection.commit()
    return '{}\n'


@app.route("/v1/sources", methods=["POST"])
@check_token
def sources():
    req = request.get_json(True)
    language = req["language"]
    content = req["content"]

    connection = get_db()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO sources (language) VALUES (%s) RETURNING id", (language,))
    source_id = cursor.fetchone()[0]
    cursor.close()
    cursor = connection.cursor()
    for k, v in content.items():
        cursor.execute("INSERT INTO sourcetexts (name, content, source_id) VALUES (%s, %s, %s)", (k, v, source_id))

    cursor.close()
    connection.commit()
    return '{}\n'


@app.route("/v1/tokenwords/<string:sourcelang>", methods=["GET"])
@check_token
def tokenwords(sourcelang):
    connection = get_db()
    cursor = connection.cursor()
    cursor.execute("select st.name, st.content from sourcetexts st left join sources s on st.source_id = s.id WHERE s.language = %s", (sourcelang,))
    out = []
    for rst in cursor.fetchall():
        out.append(rst[1])
    cursor.close()
    connection.commit()
    token_list = nltk.word_tokenize(" ".join(out))
    token_set = set([x.encode('utf-8') for x in token_list])
    words = []
    for t in token_set:
        entry = {
                "msgid": t.decode("utf-8"),
                "msgstr": '',
                }
        po.append(entry)
    tw = {}
    tw["tokenwords"] = str(po)
    return json.dumps(tw)


@app.route("/v1/translations", methods=["POST"])
#@check_token
def translations():
    req = request.get_json(True)
    sourcelang = req["sourcelang"]
    #targetlang = req["targetlang"]
    tokens = req["tokenwords"]
    connection = get_db()
    cursor = connection.cursor()
    cursor.execute("select st.name, st.content, st.source_id from sourcetexts st left join sources s on st.source_id = s.id WHERE s.language = %s", (sourcelang,))
    out = []
    for rst in cursor.fetchall():
        out.append((rst[0], rst[1]))
    source_id = rst[2]
    tr = {}
    for name, book in out:
        out_text_lines = []
        for line in book.split("\n"):
            line_words = nltk.word_tokenize(line.decode('utf8'))
            new_line_words = []
            for word in line_words:
                new_line_words.append(tokens.get(word, word))
            out_line = " ".join(new_line_words)
            out_text_lines.append(out_line)

        out_text = "\n".join(out_text_lines)
        tr[name] = out_text
        cr.execute("INSERT INTO translationtexts (name, content, language, source_id) VALUES (%s, %s, %s, %s)", (name, out_text, sourcelang, source_id))
    return json.dumps(tr)

@app.route("/v1/corrections", methods=["POST"])
@check_token
def corrections():
    return '{}\n'


@app.route("/v1/suggestions", methods=["GET"])
@check_token
def suggestions():
    return '{}\n'
