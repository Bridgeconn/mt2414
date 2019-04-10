##### Pylint Configurations #################
# For the complete list of pylint error messages, http://pylint-messages.wikidot.com/all-codes
# To disable pylint "Line too long (%s/%s)" error message.
# pylint: disable=C0301
# To disable too many modules error message.
# pylint: disable=C0302
# To disable Anomalous backslash in string: \'%s\'. String constant might be missing an r prefix.
# pylint: disable=W1401
# To disable missing module docstring error message.
# pylint: disable=C0111
# ##### Pylint Configurations ends here########

import os
import uuid
import urllib.request
from functools import wraps
import datetime
from datetime import timedelta
import re
from xlrd import open_workbook
import json
import ast
import logging
import pickle
import pyotp
import pyexcel
import nltk
import flask
from flask import Flask, request, session, redirect, jsonify
from flask import g
from flask_cors import CORS, cross_origin
import jwt
import requests
import scrypt
import psycopg2
import pymysql
from .FeedbackAligner import FeedbackAligner
from .JsonExporter import JsonExporter
from operator import itemgetter
from itertools import *

logging.basicConfig(filename='API_logs.log', format='%(asctime)s: %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

app = Flask(__name__)
CORS(app)

sendinblue_key = os.environ.get("MT2414_SENDINBLUE_KEY")
jwt_hs256_secret = os.environ.get("MT2414_HS256_SECRET")
postgres_host = os.environ.get("MT2414_POSTGRES_HOST", "localhost")
postgres_port = os.environ.get("MT2414_POSTGRES_PORT", "5432")
postgres_user = os.environ.get("MT2414_POSTGRES_USER", "postgres")
postgres_password = os.environ.get("MT2414_POSTGRES_PASSWORD", "secret")
postgres_database = os.environ.get("MT2414_POSTGRES_DATABASE", "postgres")
host_api_url = os.environ.get("MT2414_HOST_API_URL")
host_ui_url = os.environ.get("MT2414_HOST_UI_URL")
host_aligner_ui_url = os.environ.get("MTV2_HOST_ALIGNER_UI_URL")
mysql_host = os.environ.get("MTV2_HOST", "localhost")
mysql_port = int(os.environ.get("MTV2_PORT", '3306'))
mysql_user = os.environ.get("MTV2_USER", "mysql")
mysql_password = os.environ.get("MTV2_PASSWORD", "secret")
mysql_database = os.environ.get("MTV2_DATABASE", "postgres")
system_email = os.environ.get("MTV2_EMAIL_ID", "autographamt@gmail.com")


def connect_db():
    """
    Opens a connection with MySQL Database
    """
    if not hasattr(g, 'db'):
        g.db = pymysql.connect(host=mysql_host,database=mysql_database, user=mysql_user, password=mysql_password, charset='utf8mb4')
    return g.db


def get_db():                                                                      #--------------To open database connection-------------------#
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'db1'):
        g.db1 = psycopg2.connect(dbname=postgres_database, user=postgres_user, password=postgres_password, host=postgres_host, port=postgres_port)
    return g.db1


def getBibleBookIds():
    '''
    Returns a tuple of two dictionarys of the books of the Bible, bookcode has bible book codes
    as the key and bookname has bible book names as the key.
    '''
    bookcode = {}
    bookname = {}
    connection  = connect_db()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM Bible_Book_Lookup Order by ID")
    rst = cursor.fetchall()
    for item in rst:
        bookname[item[1]] = str(item[0])
        bookcode[item[2]] = str(item[0])
    cursor.close()
    return (bookcode, bookname)

@app.teardown_appcontext                                              #-----------------Close database connection----------------#
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'db'):
        g.db.close()
    if hasattr(g, 'db1'):
        g.db1.close()

@app.route("/v1/auth", methods=["POST"])                    #-------------------For login---------------------#
def auth():
    email = request.form["email"]
    password = request.form["password"]
    connection = get_db()
    cursor = connection.cursor()
    cursor.execute("SELECT email FROM users WHERE  email = %s", (email,))
    est = cursor.fetchone()
    if not est:
        logging.warning('Unregistered user \'%s\' login attempt unsuccessful' % email)
        return '{"success":false, "message":"Invalid email"}'
    cursor.execute("SELECT u.password_hash, u.password_salt, r.name FROM users u LEFT JOIN roles r ON u.role_id = r.id WHERE u.email = %s and u.email_verified is True", (email,))
    rst = cursor.fetchone()
    if not rst:
        return '{"success":false, "message":"Email is not Verified"}'
    password_hash = rst[0].hex()
    password_salt = bytes.fromhex(rst[1].hex())
    password_hash_new = scrypt.hash(password, password_salt).hex()
    role = rst[2]
    if password_hash == password_hash_new:
        access_token = jwt.encode({'sub': email, 'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1), 'role': role, 'app':'mt'}, jwt_hs256_secret, algorithm='HS256')
        logging.warning('User: \'' + str(email) + '\' logged in successfully')
        return '{"access_token": "%s"}\n' % (access_token.decode('utf-8'),)
    logging.warning('User: \'' + str(email) + '\' login attempt unsuccessful: Incorrect Password')
    return '{"success":false, "message":"Incorrect Password"}'

@app.route("/v1/registrations", methods=["POST"])       #-----------------For user registrations-----------------#
def new_registration():
    email = request.form['email']
    password = request.form['password']
    headers = {"api-key": sendinblue_key}
    url = "https://api.sendinblue.com/v2.0/email"
    verification_code = str(uuid.uuid4()).replace("-", "")
    body = '''Hi,<br/><br/>Thanks for your interest to use the AutographaMT web service. <br/>
    You need to confirm your email by opening this link:

    <a href="https://%s/v1/verifications/%s">https://%s/v1/verifications/%s</a>

    <br/><br/>The documentation for accessing the API is available at <a href="https://docs.autographamt.com">https://docs.autographamt.com</a>''' % (host_api_url, verification_code, host_api_url, verification_code)
    payload = {
        "to": {email: ""},
        "from": ["noreply@autographamt.in", "Autographa MT"],
        "subject": "AutographaMT - Please verify your email address",
        "html": body,
        }
    connection = get_db()
    password_salt = str(uuid.uuid4()).replace("-", "")
    password_hash = scrypt.hash(password, password_salt)
    cursor = connection.cursor()
    cursor.execute("SELECT email FROM users WHERE email = %s", (email,))
    rst = cursor.fetchone()
    if not rst:
        cursor.execute("INSERT INTO users (email, verification_code, password_hash, password_salt, created_at) VALUES (%s, %s, %s, %s, current_timestamp)", (email, verification_code, password_hash, password_salt))
        cursor.close()
        connection.commit()
        resp = requests.post(url, data=json.dumps(payload), headers=headers)
        return '{"success":true, "message":"Verification Email Sent"}'
    else:
        return '{"success":false, "message":"Email Already Exists"}'

@app.route("/v1/resetpassword", methods=["POST"])    #-----------------For resetting the password------------------#
def reset_password():
    email = request.form['email']
    connection = get_db()
    cursor = connection.cursor()
    cursor.execute("SELECT email from users WHERE email = %s", (email,))
    if not cursor.fetchone():
        return '{"success":false, "message":"Email has not yet been registered"}'
    else:
        headers = {"api-key": sendinblue_key}
        url = "https://api.sendinblue.com/v2.0/email"
        totp = pyotp.TOTP('base32secret3232')       # python otp module
        verification_code = totp.now()
        body = '''Hi,<br/><br/>your request for resetting the password has been recieved. <br/>
        Your temporary password is %s. Enter your new password by opening this link:

        <a href="https://%s/forgotpassword">https://%s/forgotpassword</a>

        <br/><br/>The documentation for accessing the API is available at <a href="https://docs.autographamt.com">https://docs.autographamt.com</a>''' % (verification_code, host_ui_url, host_ui_url)
        payload = {
            "to": {email: ""},
            "from": ["noreply@autographamt.in", "AutographaMT"],
            "subject": "AutographaMT - Password reset verification mail",
            "html": body,
            }
        cursor.execute("UPDATE users SET verification_code= %s WHERE email = %s", (verification_code, email))
        cursor.close()
        connection.commit()
        resp = requests.post(url, data=json.dumps(payload), headers=headers)
        return '{"success":true, "message":"Link to reset password has been sent to the registered mail ID"}\n'

@app.route("/v1/forgotpassword", methods=["POST"])    #--------------To set the new password-------------------#
def reset_password2():
    temp_password = request.form['temp_password']
    password = request.form['password']
    connection = get_db()
    cursor = connection.cursor()
    cursor.execute("SELECT email FROM users WHERE verification_code = %s AND email_verified = True", (temp_password,))
    rst = cursor.fetchone()
    if not rst:
        return '{"success":false, "message":"Invalid temporary password."}'
    else:
        email = rst[0]
        password_salt = str(uuid.uuid4()).replace("-", "")
        password_hash = scrypt.hash(password, password_salt)
        cursor.execute("UPDATE users SET verification_code = %s, password_hash = %s, password_salt = %s, updated_at = current_timestamp WHERE email = %s", (None, password_hash, password_salt, email))
        cursor.close()
        connection.commit()
        return '{"success":true, "message":"Password has been reset. Login with the new password."}'

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
    return 'Authentication Failed\n', 401

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
                'verify_sub': True,
                'verify_exp': True,
                'verify_role': True
            }
            algorithm = 'HS256'
            leeway = timedelta(seconds=10)
            try:
                decoded = jwt.decode(token, jwt_hs256_secret, options=options, algorithms=[algorithm], leeway=leeway)
                request.email = decoded['sub']
                request.role = decoded['role']
                request.app = decoded['app']
            except jwt.exceptions.DecodeError as e:
                raise TokenError('Invalid token', str(e))
            if request.app == 'aligner':
                connection = connect_db()
                cursor = connection.cursor()
                cursor.execute("SELECT Token FROM Users WHERE Email=%s", (request.email,))
                savedToken = cursor.fetchone()[0]
                if token != savedToken:
                    raise TokenError('Invalid Token', 'Non ITL Token')
        else:
            raise TokenError('Invalid header', 'Token contains spaces')
        return f(*args, **kwds)
    return wrapper



@app.route("/v1/keys", methods=["POST"])
@check_token
def new_key():
    key = str(uuid.uuid4()).replace("-", "")
    access_id = str(uuid.uuid4()).replace("-", "")
    key_salt = str(uuid.uuid4()).replace("-", "")
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
    return redirect("https://%s/" % (host_ui_url))


@app.route("/v1/createsources", methods=["POST"])                     #--------------For creating new source (admin) -------------------#
@check_token
def create_sources():
    req = request.get_json(True)
    language = req["language"]
    version = req["version"]
    connection = get_db()
    cursor = connection.cursor()
    auth = request.headers.get('Authorization', None)
    parts = auth.split()
    if len(parts) == 2:
        token = parts[1]
        options = {
            'verify_sub': True,
            'verify_exp': True
        }
        algorithm = 'HS256'
        leeway = timedelta(seconds=10)
        decoded = jwt.decode(token, jwt_hs256_secret, options=options, algorithms=[algorithm], leeway=leeway)
        user_role = decoded['role']
        if user_role == 'admin' or user_role == 'superadmin':
            cursor.execute("SELECT id FROM sources WHERE language = %s AND version = %s", (language, version))
            rst = cursor.fetchone()
            if not rst:
                cursor.execute("INSERT INTO sources (language, version) VALUES (%s, %s)", (language, version))
            else:
                return '{"success":false, "message":"Source already exists."}'
            cursor.close()
            connection.commit()
            return '{"success":true, "message":"New source has been created"}'
        else:
            return '{"success":false, "message":"You don\'t have permission to access this page"}'


def tokenise(content):                                                  #--------------To generate tokens -------------------#
    remove_punct = re.sub(r'([!"#$%&\\\'\(\)\*\+,\.\/:;<=>\?\@\[\]^_`{|\}~\”\“\‘\’।0123456789cvpsSAQqCHPETIidmJNa])', '', content)
    token_list = nltk.word_tokenize(remove_punct)
    token_set = set([x.encode('utf-8') for x in token_list])
    return token_set


@app.route("/v1/sourceid", methods=["POST"])      #--------------For return source_id -------------------#
@check_token
def sourceid():
    req = request.get_json(True)
    language = req["language"]
    version = req["version"]
    connection = get_db()
    cursor = connection.cursor()
    cursor.execute("SELECT id FROM sources WHERE language = %s AND version = %s", (language, version))
    rst = cursor.fetchone()
    cursor.close()
    if rst:
        source_id = rst[0]
        return str(source_id)


@app.route("/v1/sources", methods=["POST"])           #--------------To upload source file in database, generate bookwise token and save the tokens in database-------------------#
@check_token
def sources():
    files = request.files['content']
    read_file = files.read()
    source_id = request.form["source_id"]
    auth = request.headers.get('Authorization', None)
    parts = auth.split()
    email_id = request.email
    if len(parts) == 2:
        token = parts[1]
        options = {
            'verify_sub': True,
            'verify_exp': True
        }
        algorithm = 'HS256'
        leeway = timedelta(seconds=10)
        decoded = jwt.decode(token, jwt_hs256_secret, options=options, algorithms=[algorithm], leeway=leeway)
        user_role = decoded['role']
        if user_role == 'admin' or user_role == 'superadmin':
            if not source_id:
                return '{"success":false, "message":"Select language and version"}'
            connection = get_db()
            cursor = connection.cursor()
            changes = []
            books = []
            cursor.execute("SELECT book_name, content, revision_num from sourcetexts WHERE source_id = %s", (source_id,))
            all_books = cursor.fetchall()
            for i in range(0, len(all_books)):
                books.append(all_books[i][0])
            convert_file = (read_file.decode('utf-8').replace('\r', ''))
            book_name_check = re.search('(?<=\id )\w{3}', convert_file)
            if not book_name_check:
                logging.warning('User: \'' + str(email_id) + '(' + str(user_role) + ')\'. File content \'' + str(content) + '\' in incorrect format.')
                return '{"success":false, "message":"Upload Failed. File content in incorrect format."}'
            book_name = book_name_check.group(0)
            text_file = re.sub(r'(\\rem.*)', '', convert_file)
            text_file = re.sub('(\\\\id .*)', '\\id ' + str(book_name), text_file)
            if book_name in books:
                count = 0
                count1 = 0
                for i in range(0, len(all_books)):
                    if all_books[i][1] != text_file and book_name == all_books[i][0]:
                        count = count + 1
                    elif all_books[i][1] == text_file and book_name == all_books[i][0]:
                        count1 = all_books[i][2]
                if count1 == 0 and count != 0:
                    revision_num = count + 1
                    cursor.execute("INSERT INTO sourcetexts (book_name, content, source_id, revision_num) VALUES (%s, %s, %s, %s)", (book_name, text_file, source_id, revision_num))
                    changes.append(book_name)
                    logging.warning('User: \'' + str(email_id) + '(' + str(user_role) + ')\' uploaded revised version of \'' + str(book_name) + '\'. Source Id: ' + str(source_id))
                    token_set = tokenise(text_file)
                    for t in token_set:
                        cursor.execute("INSERT INTO cluster (token, book_name, revision_num, source_id) VALUES (%s, %s, %s, %s)", (t.decode("utf-8"), book_name, revision_num, source_id))
            elif book_name not in books:
                revision_num = 1
                cursor.execute("INSERT INTO sourcetexts (book_name, content, source_id, revision_num) VALUES (%s, %s, %s, %s)", (book_name, text_file, source_id, revision_num))
                logging.warning('User: \'' + str(email_id) + '(' + str(user_role) + ')\' uploaded new book \'' + str(book_name) + '\'. Source Id: ' + str(source_id))
                changes.append(book_name)
                token_set = tokenise(text_file)
                for t in token_set:
                    cursor.execute("INSERT INTO cluster (token, book_name, revision_num, source_id) VALUES (%s, %s, %s, %s)", (t.decode("utf-8"), book_name, revision_num, source_id))
        else:
            return '{"success":false, "message":"You are not authorized to view this page. Contact Administrator"}'
    else:
        raise TokenError('Invalid header', 'Access token required')
    cursor.close()
    connection.commit()
    if changes:
        return '{"success":true, "message":"Source has been uploaded successfully."}'
    else:
        logging.warning('User:' + str(email_id) + ', Source content upload failed as files already exists.')
        return '{"success":false, "message":"No Changes. Existing source is already up-to-date."}'


@app.route("/v1/languagelist", methods=["GET"])       #--------------To fetch the list of languages from the database -------------------#
@check_token
def languagelist():
    connection = get_db()
    cursor = connection.cursor()
    cursor.execute("SELECT picklelist FROM targetlanglist")
    rst = cursor.fetchone()
    if not rst:
        return '{"success":false, "message":"No List available. Generate new list."}'
    else:
        db_item = pickle.loads(rst[0])
        return json.dumps(db_item)


@app.route("/v1/updatelanguagelist", methods=["GET"])                #--------------To update the database with languages from unfoldingword.org------------------#
@check_token
def updatelanguagelist():
    with urllib.request.urlopen("http://td.unfoldingword.org/exports/langnames.json") as url:
        data = json.loads(url.read().decode())
        tr = {}
        for item in data:
            # if "IN" in item["cc"]:
            tr[item["ang"]] = item["lc"]
        db_item = pickle.dumps(tr)
        connection = get_db()
        cursor = connection.cursor()
        cursor.execute("DELETE FROM targetlanglist")
        cursor.execute("INSERT INTO targetlanglist (picklelist) VALUES (%s)", (db_item,))
        cursor.close()
        connection.commit()
        return '{"success":true, "message":"Language List updated."}'


@app.route("/v1/get_languages", methods=["POST"])        #-------------------------To find available language and version----------------------#
@check_token
def available_languages():
    connection = get_db()
    cursor = connection.cursor()
    cursor.execute("SELECT s.language, s.version FROM sources s  LEFT JOIN sourcetexts st ON st.source_id = s.id")
    rst = cursor.fetchall()
    languages = set()
    if not rst:
        return '{"success":false, "message":"No sources"}'
    else:
        for lan in range(0, len(rst)):
            languages.add(rst[lan])
        language_list = list(languages)
        cursor.close()
        return json.dumps(language_list)


@app.route("/v1/get_books", methods=["POST"])           #-------------------------To find available books and revision number----------------------#
@check_token
def available_books():
    req = request.get_json(True)
    language = req["language"]
    version = req["version"]
    connection = get_db()
    cursor = connection.cursor()
    cursor.execute("SELECT st.book_name, st.revision_num FROM sources s LEFT JOIN sourcetexts st ON st.source_id = s.id WHERE s.language = %s AND s.version = %s", (language, version))
    rst = cursor.fetchall()
    book_list = []
    if not rst:
        return '{"success":false, "message":"No books available"}'
    else:
        for book in range(0, len(rst)):
            book_list.append(rst[book])
        cursor.close()
        return json.dumps(book_list)

@app.route("/v1/language", methods=["POST"])                 #-------------------------To find available source language list----------------------#
@check_token
def language():
    connection = get_db()
    cursor = connection.cursor()
    cursor.execute("SELECT language FROM sources")
    language = cursor.fetchall()
    language_list = set()
    if not language:
        return '{"success":false, "message":"No Languages"}'
    else:
        for rst in language:
            language_list.add(rst[0])
        cursor.close()
        return json.dumps(list(language_list))

@app.route("/v1/targetlang", methods=["POST"])                       #-------------------------To find available target_language list----------------------#
@check_token
def targetlang():
    req = request.get_json(True)
    language = req["language"]
    version = req["version"]
    revision = req["revision"]
    connection = get_db()
    cursor = connection.cursor()
    cursor.execute("SELECT at.targetlang FROM autotokentranslations at LEFT JOIN sources s ON at.source_id = s.id WHERE s.language = %s AND s.version = %s AND at.revision_num = %s", (language, version, revision))
    targetlang = cursor.fetchall()
    targetlang_list = set()
    if not targetlang:
        return '{"success":false, "message":"No Languages"}'
    else:
        for rst in targetlang:
            targetlang_list.add(rst[0])
        cursor.close()
        return json.dumps(list(targetlang_list))

@app.route("/v1/version", methods=["POST"])                       #-------------------------To find available versions----------------------#
@check_token
def version():
    req = request.get_json(True)
    language = req["language"]
    connection = get_db()
    cursor = connection.cursor()
    cursor.execute("SELECT version FROM sources WHERE language = %s", (language,))
    version = cursor.fetchall()
    version_list = set()
    if not version:
        return '{"success":false, "message":"No version"}'
    else:
        for rst in version:
            version_list.add(rst[0])
        cursor.close()
        return json.dumps(list(version_list))

@app.route("/v1/revision", methods=["POST"])                            #-------------------------To find revision number----------------------#
@check_token
def revision():
    req = request.get_json(True)
    language = req["language"]
    version = req["version"]
    connection = get_db()
    cursor = connection.cursor()
    cursor.execute("SELECT st.revision_num FROM sources s LEFT JOIN sourcetexts st ON st.source_id = s.id WHERE s.language = %s AND s.version = %s", (language, version))
    revision = cursor.fetchall()
    revision_list = set()
    if not revision:
        return '{"success":false, "message":"No books available"}'
    else:
        for rst in revision:
            revision_list.add(rst[0])
        cursor.close()
        return json.dumps(list(set(revision_list)))

@app.route("/v1/book", methods=["POST"])                          #-------------------------To find available books----------------------#
@check_token
def book():
    req = request.get_json(True)
    language = req["language"]
    version = req["version"]
    revision = req["revision"]
    connection = get_db()
    cursor = connection.cursor()
    cursor.execute("SELECT st.book_name FROM sources s LEFT JOIN sourcetexts st ON st.source_id = s.id WHERE s.language = %s AND s.version = %s AND revision_num = %s", (language, version, revision))
    books = cursor.fetchall()
    book_list = []
    if not books:
        return '{"success":false, "message":"No books available"}'
    else:
        for rst in books:
            book_list.append(rst[0])
        cursor.close()
        return json.dumps(list(book_list))

@app.route("/v1/getbookwiseautotokens", methods=["POST", "GET"], defaults={'excel_status':'true'})
@app.route("/v1/getbookwiseautotokens/<excel_status>", methods=["POST", "GET"])      #--------------To download tokenwords in an Excel file (bookwise)---------------#
@check_token
def bookwiseagt(excel_status):
    req = request.get_json(True)
    sourcelang = req["sourcelang"]
    version = req["version"]
    revision = req["revision"]
    include_books = req["books"]
    exclude_books = req["nbooks"]
    targetlang = req["targetlang"]
    connection = get_db()
    cursor = connection.cursor()
    cursor.execute("SELECT id FROM sources WHERE language = %s AND version = %s", (sourcelang, version))
    source_id = cursor.fetchone()
    email_id = request.email
    if not source_id:
        return '{"success":false, "message":"Source is not available. Upload source."}'
    else:
        if not include_books and not exclude_books:
            return '{"success":false, "message":"Select any books from include books"}'
        elif not include_books and exclude_books:
            return '{"success":false, "message":"Select any books from include books"}'

        book_name = []
        cursor.execute("SELECT book_name FROM cluster WHERE source_id =%s AND revision_num = %s", (source_id[0], revision))
        rst = cursor.fetchall()
        for bkn in rst:
            book_name.append(bkn[0])
        b = set(include_books) - set(book_name)                 # to check include_books in book_name (book_name contains books that fetch from database)
        c = set(exclude_books) - set(book_name)                 # to check exclude_books in book_name (book_name contains books that fetch from database)
        translated_tokens = []
        cursor.execute("SELECT  token FROM autotokentranslations WHERE translated_token IS NOT NULL AND revision_num = %s AND targetlang = %s AND source_id = %s", (revision, targetlang, source_id[0]))
        rst1 = cursor.fetchall()
        for tk in rst1:
            translated_tokens.append(tk[0])
        token_list = []
        if not b and not c:
            if include_books and not exclude_books:
                for bkn in include_books:
                    cursor.execute("SELECT token FROM cluster WHERE source_id =%s AND revision_num = %s AND book_name = %s", (source_id[0], revision, bkn,))
                    tokens = cursor.fetchall()
                    for t in tokens:
                        token_list.append(t[0])
                token_set = set(token_list) - set(translated_tokens)
                cursor.close()
                result = [['TOKEN', 'TRANSLATION']]
                for i in list(token_set):
                    result.append([i])
                sheet = pyexcel.Sheet(result)
                output = flask.make_response(sheet.xlsx)
                output.headers["Content-Disposition"] = "attachment; filename = %s.xlsx" % (bkn)
                output.headers["Content-type"] = "xlsx"
                logging.warning('User:\'' + str(email_id) + '\'. Downloaded tokens from book/books ' + ", ".join(include_books) + '. Source ID:' + str(source_id[0]) + '. Revision:' + str(revision))
                if excel_status == "true":
                    return output
                else:
                    return json.dumps(list(token_set))
            elif include_books and exclude_books:
                for bkn in include_books:
                    cursor.execute("SELECT token FROM cluster WHERE source_id = %s AND revision_num = %s AND book_name = %s", (source_id[0], revision, bkn,))
                    tokens = cursor.fetchall()
                    for t in tokens:
                        token_list.append(t[0])
                exclude_tokens = []
                for bkn in exclude_books:
                    cursor.execute("SELECT token FROM cluster WHERE source_id = %s AND revision_num = %s AND book_name = %s", (source_id[0], revision, bkn,))
                    ntokens = cursor.fetchall()
                    for t in ntokens:
                        exclude_tokens.append(t[0])
                set_toknwords = set(token_list) - set(exclude_tokens)
                token_set = set(set_toknwords) - set(translated_tokens)
                cursor.close()
                result = [['TOKEN', 'TRANSLATION']]
                for i in list(token_set):
                    result.append([i])
                sheet = pyexcel.Sheet(result)
                output = flask.make_response(sheet.xlsx)
                output.headers["Content-Disposition"] = "attachment; filename = %s.xlsx" % (bkn)
                output.headers["Content-type"] = "xlsx"
                logging.warning('User:\'' + str(email_id) + '\'. Downloaded tokens from book/books ' + ", ".join(include_books) + ' excluding from ' + ', '.join(exclude_books) + '. Source ID:' + str(source_id[0]) + '. Revision:' + str(revision))
                if excel_status == "true":
                    return output
                else:
                    return json.dumps(list(token_set))
        elif b and c:
            logging.warning('User: \'' + str(email_id) + '\'. Token download failed, Source books:\'' + str(", ".join(list(b) + list(c))) + '\' not available')
            return '{"success":false, "message":" %s and %s is not available. Upload it."}' % ((list(b)), list(c))
        elif not b and c:
            logging.warning('User: \'' + str(email_id) + '\'. Token download failed, Source books:\'' + str(", ".join(list(c))) + '\' not available')
            return '{"success":false, "message":" %s is not available. Upload it."}' % (list(c))
        elif not c and b:
            logging.warning('User: \'' + str(email_id) + '\'. Token download failed, Source books:\'' + str(", ".join(list(b))) + '\' not available')
            return '{"success":false, "message":" %s is not available. Upload it."}' % ((list(b)))

@app.route("/v1/autotokens", methods=["GET", "POST"])
@check_token
def autotokens():
    req = request.get_json(True)
    language = req["language"]
    version = req["version"]
    revision = req["revision"]
    connection = get_db()
    cursor = connection.cursor()
    cursor.execute("SELECT id FROM sources WHERE language = %s AND version = %s", (language, version))
    source_id = cursor.fetchone()
    if not source_id:
        return '{"success":false, "message":"Source not available. Upload source"}'
    else:
        cursor.execute("SELECT token FROM cluster WHERE source_id = %s AND revision_num = %s", (source_id[0], revision))
        token_set = cursor.fetchall()
        if not token_set:
            return '{"success":false, "message":"Not a valid revision number"}'
        token_set1 = set([token_set[i] for i in range(0, len(token_set))])
        tr = {}
        for t in token_set1:
            tr[str(t)] = "concord"
        cursor.close()
        return json.dumps(tr)

@app.route("/v1/tokenlist", methods=["POST", "GET"])               #------------------To download remaining tokenwords in an Excel file (bookwise)---------------#
@check_token
def tokenlist():
    req = request.get_json(True)
    sourcelang = req["sourcelang"]
    version = req["version"]
    revision = req["revision"]
    targetlang = req["targetlang"]
    book_list = req["book_list"]
    connection = get_db()
    cursor = connection.cursor()
    cursor.execute("SELECT id FROM sources WHERE language = %s AND version = %s", (sourcelang, version))
    source_id = cursor.fetchone()
    if not source_id:
        return '{"success":false, "message":"Source is not available. Upload source."}'
    else:
        cursor.execute("SELECT  token FROM autotokentranslations WHERE translated_token IS NOT NULL AND revision_num = %s AND targetlang = %s AND source_id = %s", (revision, targetlang, source_id[0]))
        translated_token = cursor.fetchall()
        if not translated_token:
            return '{"success":false, "message":"Translated tokens are not available. Upload token translation ."}'
        token = []
        for tk in translated_token:
            token.append(tk[0])
        token_list = []
        for bk in book_list:
            cursor.execute("SELECT  token FROM cluster WHERE revision_num = %s AND source_id = %s AND book_name = %s", (revision, source_id[0], bk))
            cluster_token = cursor.fetchall()
            for ct in cluster_token:
                token_list.append(ct[0])
        output = set(token_list) - set(token)
        if not list(output):
            return '{"success":false, "message":"No remaining tokens."}'
        result = [['TOKEN', 'TRANSLATION']]
        for i in list(output):
            result.append([i])
        sheet = pyexcel.Sheet(result)
        output = flask.make_response(sheet.xlsx)
        output.headers["Content-Disposition"] = "attachment; filename=%s.xlsx" % (bk)
        output.headers["Content-type"] = "xlsx"
        return output

@app.route("/v1/tokencount", methods=["POST"])                       #----------------To check total_token count (bookwise)-----------------#
@check_token
def tokencount():
    req = request.get_json(True)
    sourcelang = req["sourcelang"]
    version = req["version"]
    revision = req["revision"]
    targetlang = req["targetlang"]
    connection = get_db()
    cursor = connection.cursor()
    cursor.execute("SELECT id FROM sources WHERE language = %s AND version = %s", (sourcelang, version))
    source_id = cursor.fetchone()
    if not source_id:
        return '{"success":false, "message":"Source is not available. Upload source."}'
    else:
        cursor.execute("SELECT st.book_name FROM sources s LEFT JOIN sourcetexts st ON st.source_id = s.id WHERE s.language = %s AND s.version = %s AND st.revision_num = %s", (sourcelang, version, revision))
        books = cursor.fetchall()
        cursor.execute("SELECT  token FROM autotokentranslations WHERE translated_token IS NOT NULL AND revision_num = %s AND targetlang = %s AND source_id = %s", (revision, targetlang, source_id[0]))
        translated_token = cursor.fetchall()
        if not translated_token:
            return '{"success":false, "message":"Tokens is not available. Upload token translation."}'
        else:
            token = []
            for tk in translated_token:
                token.append(tk[0])
            result = {}
            for bk in books:
                token_list = []
                cursor.execute("SELECT token FROM cluster WHERE revision_num = %s AND source_id = %s AND book_name = %s", (revision, source_id[0], bk[0]))
                cluster_token = cursor.fetchall()
                for ct in cluster_token:
                    token_list.append(ct[0])
                    total_token = len(token_list)
                output = set(token_list) - set(token)
                count = len(list(output))
                result[bk[0]] = count, total_token
            cursor.close()
            return json.dumps(result)

@app.route("/v1/uploadtokentranslation", methods=["POST"])    #-------------To upload token translation to database (excel file)--------------#
@check_token
def upload_tokens_translation():
    language = request.form["language"]
    version = request.form["version"]
    revision = request.form["revision"]
    tokenwords = request.files['tokenwords']
    targetlang = request.form["targetlang"]
    email_id = request.email
    changes = []
    connection = get_db()
    cursor = connection.cursor()
    cursor.execute("SELECT id FROM sources WHERE language = %s AND version = %s ", (language, version))
    source_id = cursor.fetchone()
    if not source_id:
        return '{"success":false, "message":"Unable to locate the language, version and revision number specified"}'
    exl = tokenwords.read()
    with open("tokn.xlsx", "wb") as o:
        o.write(exl)
    try:
        tokenwords = open_workbook('tokn.xlsx')
    except:
        logging.warning('User: \'' + str(email_id) + '\'. Token translation upload failed. Invalid file format.')
        return '{"success":false, "message":"Invalid file format. Upload correct format of xls/xlsx files."}'
    book = tokenwords
    p = book.sheet_by_index(0)
    count = 0
    for c in range(p.nrows):                                   # to find an empty cell
        cell = p.cell(c, 1).value
        if cell:
            count = count + 1
    if count > 1:
        token_c = (token_c.value for token_c in p.col(0, 1))
        tran = (tran.value for tran in p.col(1, 1))
        data = dict(zip(token_c, tran))
        dic = ast.literal_eval(json.dumps(data))
        cursor.execute("SELECT token FROM autotokentranslations WHERE source_id = %s AND revision_num = %s AND targetlang = %s", (source_id[0], revision, targetlang))
        transtokens = cursor.fetchall()
        if transtokens:
            token_list = []
            for i in transtokens:
                token_list.append(i[0])
            for k, v in dic.items():             # key(k) and value(v)
                if v:
                    if k not in token_list:
                        cursor.execute("INSERT INTO autotokentranslations (token, translated_token, targetlang, revision_num, source_id) VALUES (%s, %s, %s, %s, %s)", (k, v, targetlang, revision, source_id[0]))
                        changes.append(v)
            cursor.close()
            connection.commit()
            filename = "tokn.xlsx"
            if os.path.exists(filename):
                os.remove(filename)
        else:
            for k, v in dic.items():
                if v:
                    cursor.execute("INSERT INTO autotokentranslations (token, translated_token, targetlang, revision_num, source_id) VALUES (%s, %s, %s, %s, %s)", (k, v, targetlang, revision, source_id[0]))
                    changes.append(v)
            cursor.close()
            connection.commit()
            filename = "tokn.xlsx"
            if os.path.exists(filename):
                os.remove(filename)
        if changes:
            logging.warning('User: \'' + str(email_id) + '\' uploaded translation of tokens successfully')
            return '{"success":true, "message":"Token translation have been uploaded successfully"}'
        else:
            logging.warning('User: \'' + str(email_id) + '\' upload of token translation unsuccessfully')
            return '{"success":false, "message":"No Changes. Existing token is already up-to-date."}'
    else:
        return '{"success":false, "message":"Tokens have no translation"}'

def pickle_for_translation_update(translation, p_data = None):
    tr = {'translation': translation, 'user': request.email, 'date': str(datetime.datetime.utcnow())}
    if not p_data:
        translation_details = list(tr)
    else:
        translation_details = pickle.loads(p_data)
        translation_details.append(tr)
    pickledata = pickle.dumps(translation_details)
    return pickledata

@app.route("/v1/updatetranslation", methods=["POST"])
@check_token
def update_translation():
    req = request.get_json(True)
    sourcelang = req["sourcelang"]
    version = req["version"]
    revision = req["revision"]
    token = req["token"]
    translation = req["translation"]
    targetlang = req["targetlang"]
    connection = get_db()
    cursor = connection.cursor()
    cursor.execute("SELECT id FROM sources WHERE language = %s AND version = %s", (sourcelang, version))
    source_id = cursor.fetchone()[0]
    cursor.execute("SELECT token FROM autotokentranslations WHERE token = %s AND source_id = %s AND revision_num = %s AND targetlang = %s", (token, source_id, revision, targetlang))
    if not cursor.fetchone():
        cursor.execute("SELECT token FROM cluster WHERE token = %s AND source_id = %s AND revision_num = %s", (token, source_id, revision))
        if not cursor.fetchone():
            return '{"success":false, "message":"The selected token is not a token from the selected source"}'
        else:
            pickledata = pickle_for_translation_update(translation)
            cursor.execute("INSERT INTO autotokentranslations (token, translated_token, pickledata, targetlang, revision_num, source_id) VALUES (%s, %s, %s, %s, %s, %s)", (token, translation, pickledata, targetlang, revision, source_id))
            cursor.close()
            connection.commit()
            return '{"success":true, "message":"Token has been updated"}'
    else:
        cursor.execute("SELECT pickledata FROM autotokentranslations WHERE token = %s AND source_id = %s AND revision_num = %s AND targetlang = %s", (token, source_id, revision, targetlang))
        rst = cursor.fetchone()
        if not rst:
            pickledata = pickle_for_translation_update(translation)
        else:
            pickledata = pickle_for_translation_update(translation, rst[0])
        cursor.execute("UPDATE autotokentranslations SET translated_token = %s, pickledata = %s WHERE token = %s AND source_id = %s AND revision_num = %s AND targetlang = %s", (translation, pickledata, token, source_id, revision, targetlang))
        cursor.close()
        connection.commit()
        return '{"success":true, "message":"Token has been updated"}'

@app.route("/v1/updatetokentranslation", methods=["POST"])     #-------------To update token translation (only for admin)-----------------#
@check_token
def update_tokens_translation():
    language = request.form["language"]
    version = request.form["version"]
    revision = request.form["revision"]
    tokenwords = request.files['tokenwords']
    targetlang = request.form["targetlang"]
    auth = request.headers.get('Authorization', None)
    parts = auth.split()
    email_id = request.email
    if len(parts) == 2:
        token = parts[1]
        options = {
            'verify_sub': True,
            'verify_exp': True
        }
        algorithm = 'HS256'
        leeway = timedelta(seconds=10)
        decoded = jwt.decode(token, jwt_hs256_secret, options=options, algorithms=[algorithm], leeway=leeway)
        user_role = decoded['role']
        if user_role == 'admin' or user_role == 'superadmin':
            changes = []
            connection = get_db()
            cursor = connection.cursor()
            cursor.execute("SELECT id FROM sources WHERE language = %s AND version = %s ", (language, version))
            source_id = cursor.fetchone()
            if not source_id:
                return '{"success":false, "message":"Unable to locate the language, version and revision number specified"}'
            exl = tokenwords.read()
            with open("tokn.xlsx", "wb") as o:
                o.write(exl)
            tokenwords = open_workbook('tokn.xlsx')
            book = tokenwords
            p = book.sheet_by_index(0)
            count = 0
            for c in range(p.nrows):                                   # to find an empty cell
                cell = p.cell(c, 1).value
                if cell:
                    count = count + 1
            if count > 1:
                token_c = (token_c.value for token_c in p.col(0, 1))
                tran = (tran.value for tran in p.col(1, 1))
                data = dict(zip(token_c, tran))             # coverting into dict format
                dic = ast.literal_eval(json.dumps(data))
                cursor.execute("SELECT token FROM autotokentranslations WHERE source_id = %s AND revision_num = %s AND targetlang = %s", (source_id[0], revision, targetlang))
                transtokens = cursor.fetchall()
                if transtokens:
                    token_list = []
                    for i in transtokens:
                        token_list.append(i[0])
                    for k, v in dic.items():
                        if v:
                            if k in token_list:
                                cursor.execute("UPDATE autotokentranslations SET translated_token = %s WHERE token = %s AND source_id = %s AND targetlang = %s AND revision_num = %s", (v, k, source_id[0], targetlang, revision))
                                changes.append(k)
                            else:
                                cursor.execute("INSERT INTO autotokentranslations (token, translated_token, targetlang, revision_num, source_id) VALUES (%s, %s, %s, %s, %s)", (k, v, targetlang, revision, source_id[0]))
                                changes.append(k)
                    cursor.close()
                    connection.commit()
                    filename = "tokn.xlsx"
                    if os.path.exists(filename):
                        os.remove(filename)
                else:
                    for k, v in dic.items():
                        if v:
                            cursor.execute("INSERT INTO autotokentranslations (token, translated_token, targetlang, revision_num, source_id) VALUES (%s, %s, %s, %s, %s)", (k, v, targetlang, revision, source_id[0]))
                            changes.append(k)
                    cursor.close()
                    connection.commit()
                    filename = "tokn.xlsx"
                    if os.path.exists(filename):
                        os.remove(filename)
                    return '{"success":true, "message":"Token translation have been uploaded successfully"}'
                if changes:
                    logging.warning('User: \'' + str(request.email) + '\' uploaded translation of tokens successfully')
                    return '{"success":true, "message":"Token translation have been updated"}'
                else:
                    logging.warning('User: \'' + str(request.email) + '\' upload of token translation unsuccessfully')
                    return '{"success":false, "message":"No Changes. Existing token is already up-to-date."}'
            else:
                return '{"success":false, "message":"Tokens have no translation"}'
        else:
            return '{"success":false, "message":"You are not authorized to view this page. Contact Administrator"}'
    else:
        raise TokenError('Invalid header', 'Access token required')

@app.route("/v1/uploadtaggedtokentranslation", methods=["POST"])    #-------------To upload tagged token translation-----------------#
@check_token
def upload_taggedtokens_translation():
    req = request.get_json(True)
    language = req["language"]
    tokenwords = req["tokenwords"]
    targetlang = req["targetlang"]
    version = req["version"]
    revision = req["revision"]
    connection = get_db()
    cursor = connection.cursor()
    for k, v in tokenwords.items():
        cursor.execute("INSERT INTO taggedtokens (token, strongs_num, language, version, revision_num) VALUES (%s, %s, %s, %s, %s)", (v, k, language, version, revision))
    cursor.close()
    connection.commit()
    return '{success:true, message:"Tagged token have been updated."}'

@app.route("/v1/emailslist", methods=["GET"])
@check_token
def emails_list():
    connection = get_db()
    cursor = connection.cursor()
    user_email = request.email
    auth = request.headers.get('Authorization', None)
    parts = auth.split()
    if len(parts) == 2:
        token = parts[1]
        options = {
            'verify_sub': True,
            'verify_exp': True
        }
        algorithm = 'HS256'
        leeway = timedelta(seconds=10)
        decoded = jwt.decode(token, jwt_hs256_secret, options=options, algorithms=[algorithm], leeway=leeway)
        user_role = decoded['role']
        if user_role == 'superadmin':
            cursor.execute("SELECT u.email, r.name FROM users u LEFT JOIN roles r ON u.role_id = r.id")
            email_list = {}
            for e in cursor.fetchall():
                if str(e[0]) != str(user_email):
                    email_list[str(e[0])] = str(e[1])
            return json.dumps(email_list)
        else:
            return '{success:false, message:"You are not authorized to view this page. Contact Administrator"}'
    else:
        raise TokenError('Invalid Token', 'Works only on autographamt.com')

@app.route("/v1/superadminapproval", methods=["POST"])
@check_token
def super_admin_approval():
    req = request.get_json(True)
    connection = get_db()
    cursor = connection.cursor()
    admin = req["admin"]
    email = req["email"]
    auth = request.headers.get('Authorization', None)
    parts = auth.split()
    if len(parts) == 2:
        token = parts[1]
        options = {
            'verify_sub': True,
            'verify_exp': True
        }
        algorithm = 'HS256'
        leeway = timedelta(seconds=10)
        decoded = jwt.decode(token, jwt_hs256_secret, options=options, algorithms=[algorithm], leeway=leeway)
        user_role = decoded['role']
        if user_role == 'superadmin' and admin == "True":
            cursor.execute("UPDATE users SET role_id = 2 WHERE email = %s", (email,))
            cursor.close()
            connection.commit()
            return '{"success":true, "message":" ' + str(email) + ' has been provided with Administrator privilege."}'
        elif user_role == 'superadmin' and admin == "False":
            cursor.execute("UPDATE users SET role_id = 3 WHERE email = %s", (email,))
            cursor.close()
            connection.commit()
            return '{"success":true, "message":"Administrator privileges has been removed of user: ' + str(email) + '."}'
        elif user_role != 'superadmin':
            return '{"success":false, "message":"You are not authorized to edit this page. Contact Administrator"}'
    return '{}\n'

@app.route("/v1/generateconcordance", methods=["POST", "GET"])       #-----------------To generate concordance-------------------#
@check_token
def generate_concordance():
    req = request.get_json(True)
    language = req["language"]
    version = req["version"]
    revision = req["revision"]
    connection = get_db()
    cursor = connection.cursor()
    cursor.execute("SELECT id FROM sources WHERE language = %s AND version = %s", (language, version))
    rst = cursor.fetchone()
    if not rst:
        return '{"success":false, "message":"Source does not exist"}'
    source_id = rst[0]
    cursor.execute("SELECT content FROM sourcetexts WHERE source_id = %s AND revision_num = %s", (source_id, revision))
    rst1 = cursor.fetchall()
    full_list = []
    for item in rst1:
        book_name = re.search('(?<=\id )\w+', item[0]).group(0)
        split_content = item[0].split('\c ')
        split_content.pop(0)
        for i in split_content:
            chapter_no = i.split('\n', 1)[0]
            full_list.append(re.sub(r'\\v ', str(book_name) + ' ' + str(chapter_no) + ':', i))
    full_text = "\n".join(full_list)
    db_item = pickle.dumps(full_text)
    cursor.execute("SELECT pickledata FROM concordance WHERE source_id = %s AND revision_num = %s", (source_id, revision))
    rst2 = cursor.fetchone()
    if not rst2:
        cursor.execute("INSERT into concordance (pickledata, source_id, revision_num) VALUES (%s, %s, %s)", (db_item, source_id, revision))
    else:
        cursor.execute("UPDATE concordance SET pickledata = %s WHERE source_id = %s AND revision_num = %s", (db_item, source_id, revision))
    cursor.close()
    connection.commit()
    return '{"success":true, "message":"Concordance list has been updated"}'

@app.route("/v1/getconcordance", methods=["POST", "GET"])               #-----------------To download concordance-------------------#
@check_token
def get_concordance():
    req = request.get_json(True)
    language = req["language"]
    version = req["version"]
    revision = req["revision"]
    token = req["token"]
    connection = get_db()
    cursor = connection.cursor()
    cursor.execute("SELECT id from sources WHERE language = %s AND version = %s", (language, version))
    source_id = cursor.fetchone()
    if not source_id:
        return '{"success":false, "message":"Source is not available. Upload it"}'
    else:
        cursor.execute("SELECT pickledata FROM concordance WHERE source_id = %s AND revision_num = %s", (source_id[0], revision))
        concord = cursor.fetchone()
        if not concord:
            return '{"success":false, "message":"Concordance list has not been generated yet. Please select the referesh button to generate it."}'
        con = {}
        full_text = pickle.loads(concord[0])
        concordance_list = re.findall('(.*' + str(token) + '.*)', full_text)
        if not concordance_list:
            return '{"success":false, "message":"The selected token is not available for the source langauage and version selected. Please select the referesh button and try again"}'
        concordance = "\n".join(concordance_list)
        cursor.close()
        return json.dumps(concordance)

@app.route("/v1/translations", methods=["POST"])                   #---------------To download translation draft-------------------#
@check_token
def translations():
    req = request.get_json(True)
    sourcelang = req["sourcelang"]
    targetlang = req["targetlang"]
    version = req["version"]
    revision = req["revision"]
    books = req["books"]
    changes = []
    changes1 = []
    if len(books) == 0:
        logging.warning('User: \'' + str(request.email) + '\'. Translation draft generation unsuccessful as no books were selected by user')
        return '{"success":false, "message":"Select the books to be Translated."}'
    connection = get_db()
    cursor = connection.cursor()
    tokens = {}
    cursor.execute("SELECT id FROM sources WHERE language = %s AND version = %s", (sourcelang, version))
    rst = cursor.fetchone()
    if not rst:
        logging.warning('User: \'' + str(request.email) + '\'. Source selected by the user is not available.')
        return '{"success":false, "message":"Source is not available. Upload it"}'
    else:
        source_id = rst[0]
        cursor.execute("SELECT token, translated_token FROM autotokentranslations WHERE targetlang = %s AND source_id = %s AND translated_token IS NOT NULL", (targetlang, source_id))
        for t, tt in cursor.fetchall():
            if tt:
                tokens[t] = tt
        tr = {} # To store untranslated tokens
        punctuations = ['!', '#', '$', '%', '"', '—', "'", "``", '&', '(', ')', '*', '+', ',', '-', '.', '/', ':', '।', ';', '<', '=', '>', '?', '@', '[', '\\', ']', '^', '_', '`', '{', '|', '}', '~'] # Can be replaced with string.punctuation. But an extra character '``' is added here
        untranslated = []
        single_quote = ["'"]
        double_quotes = ['"', "``"]
        pattern_match = re.compile(r'\\[a-z]{1,3}\d?') # To find any usfm markers in the text. 
        for book in books:
            cursor.execute("SELECT content FROM sourcetexts WHERE source_id = %s AND revision_num = %s and book_name = %s", (source_id, revision, book))
            source_content = cursor.fetchone()
            if source_content:
                out_text_lines = []
                book_name = (re.search('(?<=\id )\w+', source_content[0])).group(0)
                changes.append(book_name)
                hyphenated_words = re.findall(r'\w+-\w+', source_content[0])
                content = re.sub(r'([!"#$%&\'\(\)\*\+,\.\/:;<=>\?\@\[\]^_`{|\}~।\”\“\‘\’])', r' \1 ', source_content[0])
                single_quote_count = 0
                double_quotes_count = 0
                for line in content.split("\n"):
                    line_words = nltk.word_tokenize(line)
                    new_line_words = []
                    for word in line_words:
                        if word in punctuations:
                            last_word = new_line_words.pop(-1)
                            if word in single_quote:
                                if single_quote_count % 2 == 0:
                                    word = " " + word + " "
                                single_quote_count += 1
                            elif word in double_quotes:
                                if double_quotes_count % 2 == 0:
                                    word = " " + word + " "
                                double_quotes_count += 1
                            elif word is ':' and last_word.isdigit():
                                word = word + " "
                            word_with_punct = last_word + word
                            new_line_words.append(word_with_punct)
                        elif word.isdigit():
                            new_line_words.append(tokens.get(word, word))
                        elif not pattern_match.match(word): # TODO: Delete tag_check
                            new_line_words.append(tokens.get(word, ">>>"+str(word)+"<<<"))
                            if word not in tokens:
                                untranslated.append(word)
                        else:
                            new_line_words.append(tokens.get(word, word))
                    out_line = " ".join(new_line_words)
                    out_line = re.sub("  ", "", out_line)
                    out_text_lines.append(out_line)
                out_text = "\n".join(out_text_lines)
                for w in hyphenated_words:
                    word = ">>>"+str(w)+"<<<"
                    replace = tokens.get(w, ">>>"+str(w)+"<<<")
                    out_text = re.sub(r'' + str(word), str(replace), out_text)
                out_final = re.sub(r'>>>(\d+)-(\d+)<<<', r'\1-\2', out_text)
                out_final = re.sub(r'>>>(\d+)—(\d+)<<<', r'\1—\2', out_final)
                out_final = re.sub(r'\[ ', r' [', out_final)
                out_final = re.sub(r'\( ', r' (', out_final)
                out_final = re.sub('  ', '', out_final)
                out_final = re.sub("``", '"', out_final)
                out_final = re.sub(r"(\\v) (\d+)(')", r'\1 \2 \3', out_final)
                out_final = re.sub(r'(\\v) (\d+)(")', r'\1 \2 \3', out_final)
                out_final = re.sub(r'\\ide .*', '\\\\ide UTF-8', out_final)
                out_final = re.sub('(\\\\id .*)', '\\id ' + str(book_name), out_final)
                out_final = re.sub(r'\\rem.*', '', out_final)
                tr["untranslated"] = "\n".join(list(set(untranslated)))
                tr[book_name] = out_final
            else:
                changes1.append(book)
        cursor.close()
        connection.commit()
        if changes:
            logging.warning('User: \'' + str(request.email) + '\'. Translation draft successfully generated for book/books ' + ", ".join(changes) + '. Source ID:' + str(source_id) + '. Revision:' + str(revision) + '. Target Language:' + str(targetlang))
            return json.dumps(tr)
        else:
            logging.warning('User: \'' + str(request.email) + '\'. Translation draft generation unsuccessful')
            return '{"success":false, "message":"' + ", ".join(changes1) + ' not available. Upload it to generate draft"}'

@app.route("/v1/corrections", methods=["POST"])
@check_token
def corrections():
    return '{}\n'

@app.route("/v1/suggestions", methods=["GET"])
@check_token
def suggestions():
    return '{}\n'

def getLid(bcv):
    connection = connect_db()
    cursor = connection.cursor()
    bcv = str(bcv)
    length = len(bcv)
    book = int(bcv[-length:-6])
    chapter = int(bcv[-6:-3])
    verse = int(bcv[-3:])
    cursor.execute("SELECT ID FROM Bcv_LidMap WHERE Book = %s AND Chapter \
    = %s AND Verse = %s", (book, chapter, verse))
    lid_rst = cursor.fetchone()
    if lid_rst:
        lid = int(lid_rst[0])
    else:
        return 'Invalid BCV'
    cursor.close()
    return lid

def generatePositionalTextList(value):
    if not value:
        textObj = {
            "text":[]
        }
        return textObj
    text_list = ['' for i in range(len(value))]
    strongsList = ["" for i in range(len(value))]
    textObj = {}
    if type(value) == dict:
        for ky in value.keys():
            if ky:
                text_list[int(ky) - 1] = value[ky]
    else:
        if len(value[0]) > 2:
            for item in value:
                index = int(item[0]) - 1
                text_list[index] = item[1]
                strongsList[index] = item[2]
        else:
            for item in value:
                index = item[0]
                if index:
                    text_list[int(index) - 1] = item[1]
    textObj = {
        "text": text_list
    }
    if list(set(strongsList))[0] != "":
        textObj["strongs"] = strongsList
    return textObj

def getLexiconTable(trg, tVer):
    connection = connect_db()
    cursor = connection.cursor()
    target = "%s_%s" %(trg.capitalize(), tVer.upper())
    cursor.execute("SHOW TABLES LIKE '" + target + "_Eng_Aligned_Lexicon%'")
    lexicon_table = cursor.fetchone()[0]
    cursor.close()
    return lexicon_table


def getTableNames(srclang, trglang):
    """
    Returns alignment table name, source Bible word table name and target Bible word table name
    """
    src, sVer = srclang.split('-')
    trg, tVer = trglang.split('-')
    if trg.lower() == 'heb':
        srcBibleWord = "%s_%s_OT_BibleWord" %(src.capitalize(), sVer.upper())
        trgBibleWord = "%s_%s_BibleWord" %(trg.capitalize(), tVer.upper())
        tablename = '%s_%s_%s_%s_Alignment' %(src.capitalize(), sVer.upper(), trg.capitalize(), tVer.upper())
    else:
        srcBibleWord = "%s_%s_BibleWord" %(src.capitalize(), sVer.upper())
        trgBibleWord = "%s_%s_BibleWord" %(trg.capitalize(), tVer.upper())
        tablename = '%s_%s_%s_%s_Alignment' %(src.capitalize(), sVer.upper(), trg.capitalize(), tVer.upper())
    return tablename, srcBibleWord, trgBibleWord


def getFromBibleWords(field, lid, tablename):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("SELECT Position, " + field + " FROM " + tablename + " WHERE LID=%s", (lid,))
    bibleWordsRst = cursor.fetchall()
    bibleWordsList = ["" for i in range(len(bibleWordsRst))]
    for p, f in bibleWordsRst:
        bibleWordsList[int(p) - 1] = f
    cursor.close()
    return bibleWordsList


def generateLexicanData(lidList):
    connection = connect_db()
    cursor = connection.cursor()
    lid = lidList[0]
    if lid < 23146:
        command = "SELECT LID, Position, Strongs, HebrewWord, Transliteration, EnglishKJV, Pronounciation, \
        Definition FROM Heb_UHB_Eng_KJV_Aligned_Lexicon WHERE LID in (" + str(lidList)[1:-1] + ")"
    else:
        command = "SELECT LID, Position, Strongs, GreekWord, Transliteration, \
    EnglishULB_NASB_Lex_Combined, Pronounciation, Definition FROM \
    Grk_Eng_Aligned_Lexicon WHERE LID in (" + str(lidList)[1:-1] + ")"
    cursor.execute(command)
    lexicanData = {}
    englishPosDict = {}
    for ld, pos, srn, grkwd, translit, eng, pron, defn in cursor.fetchall():
        if pos:
            pattern = {
                        "strongs": srn,
                        "pronunciation": pron,
                        "sourceword": grkwd,
                        "transliteration": translit,
                        "definition": defn,
                        "targetword": eng
                        }
            lexicanData[srn] = pattern
            if ld in englishPosDict:
                temp = englishPosDict[ld]
                temp[pos] = eng
                englishPosDict[ld] = temp
            else:
                englishPosDict[ld] = {
                    pos:eng
                }
    cursor.close()
    return (lexicanData, englishPosDict)

def generatePositionalPairsAndColorCode(lidList, tablename):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("SELECT LidTrg, PositionSrc, PositionTrg, Stage FROM \
    " + tablename + " WHERE LidSrc in (" + str(lidList)[1:-1] + ")")
    positionalPairs = {}
    for lt, pSrc, pTrg, st in cursor.fetchall():
        if lt in positionalPairs:
            temp = positionalPairs[lt]
            temp["pairs"] = temp["pairs"] + [str(pSrc) + "-" + str(pTrg)]
            temp["colorCode"] = temp["colorCode"] + [st]
            positionalPairs[lt] = temp
        else:
            positionalPairs[lt] = {
                "pairs":[str(pSrc) + "-" + str(pTrg)],
                "colorCode": [st]
            }
    cursor.close()
    return (positionalPairs)
    
def parsePositionDictToArray(array):
    CompleteList = []
    for key in sorted(list(array)):
        List = generatePositionalTextList(array[key])
        CompleteList.append(List["text"])
    return CompleteList

def parsePositionTupleToList(data):
    lexiconData = {}
    srcData = [(j,i) for i, j in data[0]]
    strongsData = [(item[1], item[0]) for item in data[1]]
    sourceList = generatePositionalTextList(srcData)
    strongsList = generatePositionalTextList(strongsData)
    engData = []
    targetList = []

    for item in data[1]:
        targetList.append(item[3]["OriginalWord"])
        strongs = item[0]
        pronunciation = item[3]["Pronounciation"]
        transliteration = item[2]
        targetword = item[3]["English"]
        definition = item[3]["Definition"]
        sourceword = item[3]["OriginalWord"]
        engData.append((item[1], item[3]["English"]))
        if strongs:
            lexiconData[strongs] = {
                "strongs": strongs,
                "pronunciation": pronunciation,
                "sourceword": sourceword,
                "transliteration": transliteration,
                "definition": definition,
                "targetword": targetword
                }
    englishList = generatePositionalTextList(engData)
    return (sourceList, strongsList, targetList, englishList, lexiconData)

def generatePositionalPairDict(positionalPairs, content, col, lid):
    if not content:
        if lid not in positionalPairs:
            positionalPairs[lid] = {
                "pairs":[],
                "colorCode":[]
            }
    else:
        for item in content:
            trgLid = item[1][0]
            pair = str(item[0][1]) + "-" + str(item[1][1])
            if trgLid in positionalPairs:
                temp = positionalPairs[trgLid]
                temp["pairs"] = temp["pairs"] + [pair]
                temp["colorCode"] = temp["colorCode"] + [col]
                positionalPairs[trgLid] = temp
            else:
                positionalPairs[trgLid] = {
                    "pairs": [pair],
                    "colorCode":[col]
                }
    return positionalPairs


def parsePositionalPairs(auto, corrected, replacement, lid):
    positionalPairs = {}
    positionalPairs = generatePositionalPairDict(positionalPairs, auto, 0, lid)
    positionalPairs = generatePositionalPairDict(positionalPairs, corrected, 1, lid)
    positionalPairs = generatePositionalPairDict(positionalPairs, replacement, 2, lid)
    return positionalPairs


@app.route('/v2/alignments/<bcv>/<srclang>/<trglang>', methods=["GET"])
def getalignments(bcv, srclang, trglang):
    '''
    Returns list of positional pairs, list of Hindi words, list of strong numbers for the bcv queried. 
    '''
    connection = connect_db()
    
    src = srclang.split('-')[0]
    trg, tVer = trglang.split('-')

    lid = getLid(bcv)

    startLid = lid - 4
    if lid < 23146:
        OT = True
        lidList = [startLid + i for i in range(9) if (startLid + i) > 0 and (startLid + i) < 23146]
    else:
        OT = False
        lidList = [startLid + i for i in range(9) if (startLid + i) > 23145 and (startLid + i) < 31102]
    tablenames = getTableNames(srclang, trglang)
    alignmentTableName, src_bible_words_table, trg_bible_words_table = tablenames
    lexicon_table = getLexiconTable(trg, tVer)
    fb = FeedbackAligner(connection, src, src_bible_words_table, trg, trg_bible_words_table, alignmentTableName, lexicon_table)
    lexiconData = {}
    sourceObj = {}
    targetObj = {}
    positionalPairs = {}
    for l in lidList:
        res = fb.fetch_alignment(l, OT)
        verseData = parsePositionTupleToList(res)
        sourceObj[l] = {
            src + "_text": verseData[0]["text"]
        }
        targetObj[l] = {
            trg + "_text": verseData[2],
            "strongs": verseData[1]["text"],
            "english": verseData[3]["text"]
        }
        for key in verseData[4].keys():
            lexiconData[key] = verseData[4][key]
        if l == lid:
            positionalPairs = parsePositionalPairs(res[2], res[3], res[4], lid)
    lidDict = getLidDict()
    bcvList = [lidDict[x] for x in lidList]
    jsonElement = {
        "lid": lid,
        "LidList": lidList,
        "bcvList": bcvList,
        "sourceContent": sourceObj,
        "targetContent": targetObj,
        "lexicanData": lexiconData,
        "positionalPairs": positionalPairs
    }
    return jsonify(jsonElement)


def getLidDict():
    '''
    Generates a Dictionary with lid as key and bcv as value
    '''
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("SELECT ID, Book, Chapter, Verse FROM Bcv_LidMap")
    rst_num = cursor.fetchall()
    lid_dict = {}
    for l,b,c,v in rst_num:
        lid_dict[l] = str(b) + str(c).zfill(3) + str(v).zfill(3)
    cursor.close()
    return lid_dict


def lid_to_bcv(num_list):
    '''
    Recieves a list of Lid's and returns a BCV list.
    '''
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("SELECT ID, Book, Chapter, Verse FROM Bcv_LidMap")
    rst = cursor.fetchall()
    lid_dict = {}
    bcv_list = []
    for l,b,c,v in rst:
        lid_dict[l] = str(b) + str(c).zfill(3) + str(v).zfill(3)
    for n in num_list:
        bcv = lid_dict[n]
        bcv_list.append(bcv)
    cursor.close()
    return bcv_list


@app.route('/v2/alignments/books/<srclang>/<trglang>', methods=["GET"])
def getbooks(srclang, trglang):
    '''
    Returns a list of books whose alignments are available
    '''
    connection = connect_db()
    cursor = connection.cursor()
    tablename = getTableNames(srclang, trglang)[1]
    bible_code_dict = {}
    cursor.execute("SELECT ID, Code FROM Bible_Book_Lookup ORDER BY ID")
    for i, c in cursor.fetchall():
        bible_code_dict[i] = c

    lid_dict = getLidDict()
    cursor.execute("SELECT DISTINCT(LID) FROM " + tablename)
    lid_list = [x[0] for x in cursor.fetchall()]
    book_code_list = sorted(list(set([int(lid_dict[l])//1000000 for l in lid_list])))
    books = [bible_code_dict[bc] for bc in book_code_list]
    cursor.close()
    return jsonify({"books":books})


@app.route('/v2/alignments/chapternumbers/<bookname>', methods=["GET"])
def getchapternumbers(bookname):
    '''
    Returns a list of chapter number of the book queried.
    '''
    connection = connect_db()
    cursor = connection.cursor()
    bookname = bookname.upper()
    bookcode = getBibleBookIds()[0]
    if bookname not in bookcode:
        return '{"success":false, "message":"Invalid book name"}'
    else:
        bc = bookcode[bookname]
    
    cursor.execute("SELECT DISTINCT(Chapter) FROM Bcv_LidMap WHERE Book = %s", (int(bc),))
    rst = cursor.fetchall()
    temp_list = []
    if rst != []:
        for c in rst:
            temp_list.append(c[0])
    cursor.close()
    return jsonify({"chapter_numbers": sorted(temp_list)})


@app.route('/v2/alignments/versenumbers/<bookname>/<chapternumber>', methods=["GET"])
def getversenumbers(bookname, chapternumber):
    '''
    Returns a list containing the verse numbers for the particular chapter number of a book.
    '''
    connection = connect_db()
    cursor = connection.cursor()
    bookname = bookname.upper()
    bc = getBibleBookIds()[0]
    if bookname not in bc:
        return '{"success":false, "message":"Invalid book name"}'
    else:
        bookcode = bc[bookname]
    cursor.execute("SELECT Verse FROM Bcv_LidMap WHERE Book = %s and \
                            Chapter = %s", (int(bookcode), int(chapternumber)))
    rst = cursor.fetchall()
    temp_list = []
    if rst != []:
        for v in rst:
            temp_list.append(v[0])
    cursor.close()
    return jsonify({"verse_numbers": sorted(temp_list)})

def getSuccessStatus(message, status):
    status_check = {
        "success":status,
        "message":message
    }
    return status_check

def checkUserEditAccess(bcv, srclang, trglang, userId, organisation_id):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("SELECT TranslatorRole_id, Books FROM Assignments WHERE Source_language=%s AND Target_language=%s \
    AND User_id=%s AND Organisation_id=%s AND TranslatorRole_id != 2", (srclang.lower(), trglang.lower(), int(userId), int(organisation_id)))
    userAssignedData = cursor.fetchall()
    cursor.close()
    if not userAssignedData:
        return getSuccessStatus("No task has been assigned to you yet.", False)
    books = []
    for r, b in userAssignedData:
        if r == 1:
            books = books + b.split(",")
            bcvLength = len(str(bcv))
            bookId = int(str(bcv)[-bcvLength:-6])
            bibleBookCodesDict = {int(v):k for k,v in getBibleBookIds()[0].items()}
            bookCode = bibleBookCodesDict[bookId].lower()
            if bookCode not in books:
                return getSuccessStatus("You don\'t have permission to edit this book", False)
    return getSuccessStatus("Successful", True)


@app.route('/v2/alignments', methods=["POST"])
@check_token
def editalignments():
    '''
    Recieves BCV and list of positional pairs as input. The old positional pairs
    are deleted and the new ones are inserted into the database.
    '''
    req = request.get_json(True)
    bcv = req["bcv"]
    srclang = req["srclang"]
    trglang = req["trglang"]
    organisation = req["organisation"]
    position_pairs = req["positional_pairs"]
    email = request.email
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("SELECT ID FROM Users WHERE Email=%s", (email,))
    userId = cursor.fetchone()[0]
    cursor.execute("SELECT ID FROM Organisations WHERE Name=%s", (organisation,))
    organisation_id = cursor.fetchone()[0]
    tablenames = getTableNames(srclang, trglang)
    alignmentTableName, src_bible_words_table, trg_bible_words_table = tablenames    
    access_check = checkUserEditAccess(bcv, srclang, trglang, userId, organisation_id)
    if access_check["success"]:
        srclid = getLid(bcv)
        src, sVer = srclang.split('-')
        trg, tVer = trglang.split('-')
        cursor.execute("SELECT Position, Word FROM " + src_bible_words_table + " WHERE LID=%s", (srclid,))
        src_text_list = generatePositionalTextList(cursor.fetchall())["text"]
        final_position_pairs = []
        for key in position_pairs.keys():
            cursor.execute("SELECT Position, Strongs FROM " + trg_bible_words_table + " WHERE LID=%s", (key,))
            trg_text_list = generatePositionalTextList(cursor.fetchall())["text"]
            for item in position_pairs[key]:
                sPos, tPos = item.split("-")
                if sPos != "255":
                    sourceWord = src_text_list[int(sPos) - 1]
                else:
                    sourceWord = None
                if tPos != "255":
                    targetWord = trg_text_list[int(tPos) - 1]
                else:
                    targetWord = None
                final_position_pairs.append(((srclid, sPos, sourceWord), (key, tPos, targetWord)))

        fb = FeedbackAligner(connection, src, src_bible_words_table, trg, trg_bible_words_table, alignmentTableName)
        fb.save_alignment_full_verse(srclid, final_position_pairs, userId, None, 1)
        connection.commit()
        cursor.close()
        return '{"success":true, "message":"Alignment saved successfully"}'
    else:
        return '{"success":false, "message":"%s"}' %(access_check["message"])


@app.route("/v2/lexicons/<strong>", methods=["GET"])
def getlexicons(strong):
    """
    Fetches Lexicon data for the specified strongs.
    """
    connection = connect_db()
    cursor = connection.cursor()
    if not strong.isdigit():
        return 'Invalid Strong Number\n'
    else:
        strong = int(strong)
    cursor.execute("SELECT Strongs, Pronounciation, GreekWord, Transliteration, \
    Definition, EnglishULB_NASB_Lex_Combined, EnglishULB \
     FROM Grk_Eng_Aligned_Lexicon WHERE Strongs = %s", (strong,))
    rst = cursor.fetchone()
    if rst:
        strongs = rst[0]
        pronunciation = rst[1]
        greek_word = rst[2]
        transliteration = rst[3]
        definition = rst[4]
        if rst[5].strip() != '':
            englishword = rst[5].strip()
        else:
            englishword = rst[6].strip()
    else:
        return '{"success":false, "message":"No information available"}'
    cursor.close()
    return jsonify({"strongs":strongs, "pronunciation":pronunciation, "sourceword":greek_word, \
                "transliteration":transliteration, "definition":definition, "targetword":englishword})


@app.route("/v2/alignments/export/<srclang>/<trglang>/<book>", methods=["GET"], defaults={'usfm_status':None})
@app.route("/v2/alignments/export/<srclang>/<trglang>/<book>/<usfm_status>", methods=["GET"])
def jsonexporter(srclang, trglang, book, usfm_status):
    connection  = connect_db()
    bc = getBibleBookIds()[0][book.upper()]
    tables = getTableNames(srclang, trglang)
    alignment_table, source_word_table, target_word_table = tables
    je = JsonExporter(connection, source_word_table, target_word_table, bc, book, \
    alignment_table, usfm_status)
    var = je.exportAlignments()
    return var


@app.route("/v2/searchreferences", methods=["POST"])
def searchreference():
    reference = request.form["reference"]
    pattern = re.compile('(?:\s+)?((?:\d+)?\s?[a-zA-Z]+)(?:\s+)?(\d+)(?:\s+)?:(?:\s+)?(\d+)')
    bookcode, bookname = getBibleBookIds()
    if re.search(pattern, reference):
        s = re.search(pattern, reference)
        book = s.group(1)
        book = book.strip()
        try:
            if len(book) > 3:
                book = bookname[book.capitalize()]
            else:
                book = bookcode[s.group(1).upper()]
        except:
            return '{"success":false, "message":"Invalid Book Name or Book Code"}'
        chap = s.group(2).zfill(3)
        ver = s.group(3).zfill(3)
        bc = book + chap + ver
        return bc
    else:
        return '{"success":false, "message":"Incorrect Format"}'


def getLanguageList():
    languageList = {
        'grk': 'Greek',
        'hin': 'Hindi',
        'mar': 'Marathi',
        'guj': 'Gujarati',
        'mal': 'Malayalam',
        'odi': 'Odiya',
        'pun': 'Punjabi',
        'asm': 'Assamese',
        'ben': 'Bengali',
        'tam': 'Tamil',
        'urd': 'Urdu',
        'tel': 'Telugu',
        'kan': 'Kannada',
        'heb': 'Hebrew'
    }
    return languageList


@app.route("/v2/alignments/languages", methods=["GET"])
def getlanguages():
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("SHOW TABLES LIKE '%_Alignment'")
    rst = cursor.fetchall()
    languageList = getLanguageList()
    languageDict = {}
    tablesList = list(set([x[0].replace('_History', '') for x in rst]))
    tablesList = [y.replace('_Alignment', '') for y in tablesList]
    for item in tablesList:
        src, sVer = item.split('_')[0:2]
        src = src.lower()
        key = (src + '-' + sVer).lower()
        languageDict[key] = languageList[src] + " (Version: " + sVer + ")"
    return jsonify(languageDict)


@app.route("/v2/alignments/targetlanguages/<srclang>", methods=["GET"])
def getTargetLanguagesList(srclang):
    connection = connect_db()
    cursor = connection.cursor()
    src, sVer = srclang.split("-")
    source_language = "%s_%s" %(src.capitalize(), sVer.upper())
    cursor.execute("SHOW TABLES LIKE '%" + source_language + "%_Alignment'")
    rst = cursor.fetchall()
    languageList = getLanguageList()
    languageDict = {}
    for item in rst:
        tables_split = item[0].split("_")
        trg = tables_split[2]
        tVer = tables_split[3].lower()
        trg = trg.lower()
        key = (trg + "-" + tVer).lower()
        languageDict[key] = languageList[trg] + " (Version: " + tVer +")"
    return jsonify(languageDict)


@app.route("/v2/alignments/translationwords/<srclang>/<trglang>/<index>", methods=["GET"])
def getTranslationWords(srclang, trglang, index):
    connection = connect_db()
    src, sVer = srclang.split('-')
    trg, tVer = trglang.split('-')
    first = int(index.split('-')[0])
    last = int(index.split('-')[1]) + 1
    fb = FeedbackAligner(connection, src.capitalize(), sVer.upper(), trg.capitalize(), tVer.upper())
    TW = fb.fetch_seleted_TW_alignments(range(first, last))
    return jsonify(TW)


@app.route("/v2/alignments/strongs/<srclang>/<trglang>", methods=["GET"])
def getStrongsList(srclang, trglang):
    connection = connect_db()
    tables = getTableNames(srclang, trglang)

    bible_word_table = tables[2]
    alignment_table = tables[0]
    cursor = connection.cursor()
    cursor.execute("SELECT Distinct(Strongs) From " + bible_word_table)
    strongsList = []
    for item in cursor.fetchall():
        strongs = item[0]
        if strongs:
            strongsList.append(item[0])
    cursor.execute("SELECT Strongs, Stage FROM " + alignment_table + " WHERE Strongs IN (" + str(strongsList)[1:-1] + ")")
    stageDict = {}
    for it in cursor.fetchall():
        if it[1] == 2:
            checked = 1
            unchecked = 0
        else:
            checked = 0
            unchecked = 1
        if it[0] in stageDict:
            stageDict[it[0]] = {
                "checked":stageDict[it[0]]["checked"] + checked,
                "unchecked":stageDict[it[0]]["unchecked"] + unchecked
            }
        else:
            stageDict[it[0]] = {
                "checked":0 + checked,
                "unchecked":0 + unchecked
            }
    cursor.close()
    return jsonify(stageDict)


@app.route("/v2/alignments/strongs/<srclang>/<trglang>/<strongsnumber>", methods=["GET"])
def getStrongsInfo(srclang, trglang, strongsnumber):
    '''
    Returns Checked and Unchecked status of a Strongs Number.
    '''
    connection = connect_db()
    cursor = connection.cursor()
    tablename = getTableNames(srclang, trglang)[0]
    cursor.execute("SELECT ID, Book, Chapter, Verse FROM Bcv_LidMap")
    lidDict = {}
    for l,b,c,v in cursor.fetchall():
        bc = str(b).zfill(2)
        chap = str(c).zfill(3)
        ver = str(v).zfill(3)
        bcv = int(bc + chap + ver)
        lidDict[l] = bcv
    cursor.execute("SELECT WordSrc, LidSrc, PositionSrc, PositionTrg, Stage FROM " + tablename + " WHERE Strongs=%s", (strongsnumber))
    rst = cursor.fetchall()
    temp = {}
    posDict = {}

    #Create positional dict with lids as key and dict of with key as \
    # source position and value as word as value of posDict.
    for item in rst:
        if item[4] != 2:
            stage = 0
        else:
            stage = 2
        if item[1] in posDict:
            temp = posDict[item[1]]
            temp[item[2]] = {
                'word':item[0],
                'stage':stage,
                'positionalPair':str(item[2]) + '-' + str(item[3])
            }
            posDict[item[1]] = temp
        else:
            posDict[item[1]] = {
                item[2] : {
                    'word':item[0],
                    'stage':stage,
                    'positionalPair':str(item[2]) + '-' + str(item[3])
            }
            }

    mainPhraseData = {}

    for key in posDict.keys():
        bCV = lidDict[key]
        phraseCheckList = sorted(list(posDict[key].keys()))
        phraseList = []
        for k,g in groupby(enumerate(phraseCheckList), lambda x:x[0] - x[1]):   #Checks for sequence to 
            phraseList.append(list(map(itemgetter(1), g)))                      #point to a phrase
        for item in phraseList:
            joinWords = ' '.join(posDict[key][x]['word'] for x in item)     # Joins all words according to
                                                                            # to the positions returned above
            joinStage = [posDict[key][y]['stage'] for y in item]
            trg = posDict[key][item[0]]['positionalPair'].split('-')[1]
            posPairsList = [str(z) + '-' + trg for z in item]
            setOfStage = list(set(joinStage))
            if len(setOfStage) == 1 and setOfStage[0] == 2: # Checks if all words are checked
                checkedStatus = "checked"
            else:
                checkedStatus = "unchecked"
            if joinWords in mainPhraseData:
                temp = mainPhraseData[joinWords]
                if checkedStatus in temp:
                    temp[checkedStatus] = {
                        'bcv': temp[checkedStatus]['bcv'] + [bCV],
                        'positionalPairs': temp[checkedStatus]['positionalPairs'] + [posPairsList]
                    }
                else:
                    temp[checkedStatus] = {
                        'bcv':[bCV],
                        'positionalPairs': [posPairsList]
                    }
                mainPhraseData[joinWords] = temp
            else:
                mainPhraseData[joinWords] = {
                    checkedStatus:{
                        'bcv':[bCV],
                        'positionalPairs':[posPairsList]
                    }
                }
    strongsInfoDict = {}
    for k,v in mainPhraseData.items():
        checkedCount = 0
        uncheckedCount = 0
        if "checked" in v:
            checkedCount = len(v["checked"]["bcv"])
        if "unchecked" in v:
            uncheckedCount = len(v["unchecked"]["bcv"])
        strongsInfoDict[k] = {
            "references": v,
            "checkedCount":checkedCount,
            "uncheckedCount":uncheckedCount,
            "count": checkedCount + uncheckedCount
        }
    cursor.close()
    return jsonify(strongsInfoDict)


@app.route("/v2/alignments/strongs", methods=["POST"])
@check_token
def updateCheckedStrongs():
    req = request.get_json(True)
    srclang = req["srclang"]
    trglang = req["trglang"]
    strongs = int(req["strongs"])
    word = req["word"]
    positionData = req["positionData"]
    status = int(req["status"])
    tablename = getTableNames(srclang, trglang)[0]
    connection = connect_db()
    cursor = connection.cursor()
    lidDict = getLidDict()
    bcvDict = {v:k for k,v in lidDict.items()}
    if status == 0:
        stage = 2
    else:
        stage = 1
    for k,v in positionData.items():
        posList = []
        lid = int(bcvDict[k])
        for item in v:
            posList.append(item.split('-')[0])
        cursor.execute("UPDATE " + tablename + " SET Stage=%s WHERE Strongs=%s AND\
         LidSrc=%s AND PositionSrc in (" + str(posList)[1:-1] + ")", (stage, strongs, lid))
    connection.commit()
    cursor.close()
    return '{"success":true, "message":"Done"}'


@app.route("/v2/registrations", methods=["POST"])
def registrations():
    '''
    Registration for a user in the alignment tool.
    '''
    req = request.get_json(True)
    email = req["email"]
    fname = req["firstName"]
    lname = req["lastName"]
    password = req["password"]
    headers = {"api-key": sendinblue_key}
    url = "https://api.sendinblue.com/v2.0/email"
    verification_code = str(uuid.uuid4()).replace("-", "")
    body = '''Hi,<br/><br/>Thanks for your interest to use the AutographaMT Interlinear web service. <br/>
    You need to confirm your email by opening this link:

    <a href="https://%s/v2/verifications/%s">https://%s/v2/verifications/%s</a>

    <br/><br/>The documentation for accessing the API is available at <a href="https://docs.autographamt.com">https://docs.autographamt.com</a>''' % (host_api_url, verification_code, host_api_url, verification_code)
    payload = {
        "to": {email: ""},
        "from": ["noreply@autographamt.in", "Autographa MT"],
        "subject": "AutographaMT - Please verify your email address",
        "html": body,
        }
    connection = connect_db()
    password_salt = str(uuid.uuid4()).replace("-", "")
    password_hash = scrypt.hash(password, password_salt)
    cursor = connection.cursor()
    cursor.execute("SELECT Email FROM Users WHERE Email = %s", (email,))
    rst = cursor.fetchone()
    if not rst:
        cursor.execute("INSERT INTO Users (Email, Fname, Lname, Verification_code, Password_hash, Password_salt \
        ) VALUES (%s, %s, %s, %s, %s, %s)", (email, fname, lname, verification_code, password_hash, password_salt))
        cursor.close()
        connection.commit()
        resp = requests.post(url, data=json.dumps(payload), headers=headers)
        return '{"success":true, "message":"Verification Email Sent"}'
    else:
        return '{"success":false, "message":"Email Already Exists"}'


@app.route("/v2/resetpassword", methods=["POST"])    #-----------------For resetting the password------------------#
def resetPassword():
    email = request.form['email']
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("SELECT Email, Email_verified from Users WHERE Email = %s", (email,))
    emailData = cursor.fetchone()
    if not emailData:
        return '{"success":false, "message":"Email has not yet been registered"}'
    else:
        headers = {"api-key": sendinblue_key}
        url = "https://api.sendinblue.com/v2.0/email"
        totp = pyotp.TOTP('base32secret3232')       # python otp module
        verification_code = totp.now()
        body = '''Hi,<br/><br/>your request for resetting the password has been recieved. <br/>
        Your temporary password is %s. Enter your new password by opening this link:

        <a href="https://%s/resetpassword">https://%s/resetpassword</a>

        <br/><br/>The documentation for accessing the API is available at <a href="https://docs.autographamt.com">https://docs.autographamt.com</a>''' % (verification_code, host_ui_url, host_ui_url)
        payload = {
            "to": {email: ""},
            "from": ["noreply@autographamt.in", "AutographaMT"],
            "subject": "AutographaMT - Reset Password",
            "html": body,
            }
        cursor.execute("UPDATE Users SET Verification_code=%s WHERE Email = %s", (verification_code, email))
        cursor.close()
        connection.commit()
        resp = requests.post(url, data=json.dumps(payload), headers=headers)
        return '{"success":true, "message":"Link to reset password has been sent to the registered mail ID"}\n'


@app.route("/v2/forgotpassword", methods=["POST"])    #--------------To set the new password-------------------#
def changePassword():
    temp_password = request.form['temp_password']
    password = request.form['password']
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("SELECT Email FROM Users WHERE Verification_code = %s AND Email_verified = 1", (temp_password,))
    rst = cursor.fetchone()
    if not rst:
        return '{"success":false, "message":"Invalid temporary password."}'
    else:
        email = rst[0]
        password_salt = str(uuid.uuid4()).replace("-", "")
        password_hash = scrypt.hash(password, password_salt)
        cursor.execute("UPDATE Users SET Password_hash = %s, Password_salt = %s WHERE Email = %s", (password_hash, password_salt, email))
        cursor.close()
        connection.commit()
        return '{"success":true, "message":"Password has been reset. Login with the new password."}'


@app.route("/v2/verifications/<code>", methods=["GET"])
def verifications(code):
    '''
    Checks the validation link sent to the users email.
    '''
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("SELECT Email FROM Users WHERE Verification_code=%s", (code,))
    email = cursor.fetchone()
    if not email:
        return '{"success":false, "message":"Invalid Link"}'
    else:
        cursor.execute("UPDATE Users SET Email_verified=true WHERE Email=%s", (email[0],))
        connection.commit()
        cursor.close
        return redirect("https://%s/" % (host_aligner_ui_url))


@app.route("/v2/auth", methods=["POST"])
def authenticate():
    '''
    Authentication for version 2 users.
    '''
    req = request.get_json(True)
    email = req["email"]
    password = req["password"]
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("SELECT ID, Password_hash, Password_salt, Email_verified, Role_id, Fname FROM Users WHERE Email=%s", (email,))
    rst = cursor.fetchone()
    if not rst:
        return '{"success":false, "message":"Email is not registered"}'
    else:
        if rst[3] == 0:
            return '{"success":false, "message":"Email is not verified"}'
        else:
            password_hash = rst[1]
            password_salt = rst[2]
            new_password_hash = scrypt.hash(password, password_salt)
            if password_hash == new_password_hash:

                access_token = jwt.encode(
                    {
                        'sub': email,
                        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1),
                        'role': rst[4],
                        'firstName':rst[5],
                        'app':'aligner'
                    },
                    jwt_hs256_secret,
                    algorithm='HS256'
                ).decode('utf-8')
                cursor.execute("UPDATE Users SET Token=%s WHERE Email=%s", (access_token, email,))
                connection.commit()
                cursor.close
                return '{"access_token":"%s"}' %(access_token)
            else:
                return '{"success":false, "message":"Incorrect Password"}'


@app.route("/v2/users", methods=["GET"])
@check_token
def listUsers():
    '''
    Lists user to an admin
    '''
    role = request.role
    if role != 1:
        connection = connect_db()
        cursor = connection.cursor()
        roleDict = {}
        cursor.execute("SELECT ID, Role FROM Roles")
        roleDict = {i:n for i,n in cursor.fetchall()}
        cursor.execute("SELECT Email, Role_id FROM Users")
        emailList = {e:roleDict[r] for e,r in cursor.fetchall() if r !=3}
        return jsonify(emailList)
    else:
        return '{"success":false, "message":"You don\'t have permission to access this resource"}'


@app.route("/v2/users/organisations", methods=["POST"])
@check_token
def requestOrganisationAcess():
    '''
    User sends request for creation of an organisation
    '''
    req = request.get_json(True)
    name = req["organisation_name"]
    address = req["address"]
    organisationEmail = req["email"]
    countryCode = req["country_code"]
    phone = req["phone"]
    userEmail = request.email
    email = system_email
    headers = {"api-key": sendinblue_key}
    url = "https://api.sendinblue.com/v2.0/email"
    body = '''Hi,<br/><br/>Request to create Orgaisation<br/>
    <p><h2>Organisation Details:</h2></p>
    <p>Name: %s</p>
    <p>Address: %s</p>
    <p>Email: %s</p>
    <p>Country Code: %s</p>
    <p>Phone: %s</p>
    <p>User Email: %s</p>


    <br/><br/>The documentation for accessing the API is available at \
    <a href="https://docs.autographamt.com">https://docs.autographamt.com</a>
    <p> Do Not reply to this mail </p>
    '''\
     % (name, address, organisationEmail, countryCode, phone, userEmail)
    payload = {
        "to": {email: ""},
        "from": ["noreply@autographamt.in", "Autographa MT"],
        "subject": "AutographaMT - Organisation Creation Request for %s" %(name),
        "html": body,
        }

    resp = requests.post(url, data=json.dumps(payload), headers=headers)
    return '{"success":true, "message":"Request sent to Admin"}'


@app.route("/v2/users/assignments/<email>", methods=["GET"])
@check_token
def getUserAssignedTasks(email):
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("SELECT ID FROM Users WHERE Email=%s", (email,))
    user_id = cursor.fetchone()[0]
    cursor.execute("SELECT t.RoleName, a.Books, a.Source_language, a.Target_language, o.Name From Assignments a \
    INNER JOIN TranslatorRoles t ON t.ID=a.TranslatorRole_id \
    INNER JOIN Organisations o ON o.ID=a.Organisation_id \
    WHERE a.User_id=%s", (user_id,))
    workAssignedToUser = cursor.fetchall()
    WATU = []
    for role, books, srclang, trglang, organisation in workAssignedToUser:
        WATU.append(
            {
                "role":role.lower(),
                "books":books,
                "source_language":srclang,
                "target_language":trglang,
                "organisation":organisation
            }
        )
    return jsonify(WATU)


@app.route("/v2/organisations", methods=["POST"])
@check_token
def createOrganisation():
    role = request.role
    if role == 3:
        req = request.get_json(True)
        name = req["organisation_name"]
        address = req["address"]
        email = req["email"]
        countryCode = req["country_code"]
        phone = req["phone"]
        organisationOwner = req["organisation_owner_email"]
        connection = connect_db()
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM Organisations WHERE Name=%s AND Email=%s", (name, email))
        rst = cursor.fetchone()
        if not rst:
            cursor.execute("SELECT Organisation_id FROM Users WHERE Email=%s", (organisationOwner,))
            orgOwnerId = cursor.fetchone()[0]
            if orgOwnerId != 1:
                return '{"success":false, "message":"Already Assigned to another organisation"}'
            else:
                cursor.execute("INSERT INTO Organisations (Name, Address, Email, Country_code, Phone)\
                VALUES (%s, %s, %s, %s, %s)", (name, address, email, countryCode, phone))
                ID = cursor.lastrowid
                cursor.execute("UPDATE Users SET Organisation_id=%s, Role_id=%s WHERE Email=%s", (ID, 2, organisationOwner))
            connection.commit()
            cursor.close()
            return '{"success":true, "message":"Organisation Created"}'
        else:
            cursor.close()
            return '{"success":false, "message":"Already exists"}'
    else:
        return '{"success":false, "message":"You don\'t have permission to access this resource"}'


@app.route("/v2/projects", methods=["GET"])
@check_token
def getProjects():
    '''
    Loads the active projects of an admin
    '''
    role = request.role
    if role != 1:
        connection = connect_db()
        cursor = connection.cursor()
        email = request.email
        cursor.execute("SELECT a.Source_language, a.Target_language, o.Name FROM Assignments a \
        INNER JOIN Organisations o ON a.Organisation_id=o.ID \
        INNER JOIN Users u ON o.ID=u.Organisation_id WHERE u.Email=%s", (email,))
        languages = cursor.fetchall()
        projectsList = {}
        for srclang, trglang, organisation in languages:
            language = srclang + ":" + trglang
            if organisation in projectsList:
                if language not in projectsList[organisation]:
                    projectsList[organisation] = projectsList[organisation] + [language]
            else:
                projectsList[organisation] = [language]
        cursor.close()
        return jsonify(projectsList)
    else:
        return '{"success":false, "message":"You don\'t have permission to access this resource"}'


@app.route("/v2/projects", methods=["POST"])
@check_token
def createProjects():
    '''
    Creates a Project under the admin's organisation.
    '''
    role = request.role
    req = request.get_json(True)
    lang = req["language"]
    email = request.email
    if role == 2:
        connection = connect_db()
        cursor = connection.cursor()
        cursor.execute("SELECT Organisation_id FROM Users WHERE Email=%s", (email,))
        organisation_id = cursor.fetchone()[0]
        cursor.execute("SELECT Language FROM Projects WHERE Language=%s AND Organisation_id=%s", (lang, organisation_id))
        lang_rst = cursor.fetchone()
        if not lang_rst:
            cursor.execute("INSERT INTO Projects (Language, Organisation_id) VALUES (%s, %s)", (lang.lower(), organisation_id))
            connection.commit()
            cursor.close()
            return '{"success":true, "message":"Project created"}'
        else:
            return '{"success":false, "message":"Language Project already exists for this organization"}'
    else:
        return '{"success":false, "message":"You don\'t have permission to access this resource"}'


@app.route("/v2/projects/users/<srclang>/<trglang>", methods=["GET"])
@check_token
def getUsersUnderProject(srclang, trglang):
    '''
    To view users assigned to a specific project
    '''
    role = request.role
    if role != 1:
        connection = connect_db()
        cursor = connection.cursor()
        email = request.email
        cursor.execute("SELECT Organisation_id FROM Users WHERE Email=%s", (email,))
        organisation_id = cursor.fetchone()[0]
        cursor.execute("SELECT u.Email, t.RoleName, a.Books FROM Assignments a \
        INNER JOIN Users u ON u.ID=a.User_id \
        INNER JOIN TranslatorRoles t ON t.ID=a.TranslatorRole_id \
        WHERE a.Source_language=%s AND a.Target_language=%s AND a.Organisation_id=%s", \
        (srclang, trglang, organisation_id))
        userRoles = cursor.fetchall()
        projectUsersRole = []
        cursor.close()
        if userRoles:
            for eMail, role, book in userRoles:
                if book.strip() != "":
                    projectUsersRole.append(
                        {
                            "user":eMail,
                            "role":role,
                            "books":book
                        }
                    )
            return jsonify(projectUsersRole)
        else:
            return '{"success":false, "message":"No Users assigned under this project"}'
    else:
        return '{"success":false, "message":"Not authorized to view this resource"}'


@app.route("/v2/assignments/<status>", methods=["POST"])
@check_token
def assignTasks(status):
    '''
    Assigns a task to the specified user.
    '''
    user_role = request.role
    req = request.get_json(True)
    user_email = req["email"]
    srclang = req["srclang"].lower()
    trglang = req["trglang"].lower()
    role = req["role"]
    bookList = req["books"]
    bookList = [bk.lower() for bk in bookList]
    email = request.email
    if user_role != 1:
        connection = connect_db()
        cursor = connection.cursor()
        cursor.execute("SELECT ID FROM Users WHERE Email=%s", (user_email,))
        user_id = cursor.fetchone()[0]
        cursor.execute("SELECT Organisation_id FROM Users WHERE Email=%s", (email,))
        organisation_id = cursor.fetchone()
        cursor.execute("SELECT ID FROM TranslatorRoles WHERE RoleName=%s", (role.lower(),))
        role_id = cursor.fetchone()[0]
        cursor.close()
        if role_id == 3:
            cursor = connection.cursor()
            books = "all books assigned"
            cursor.execute("DELETE FROM Assignments WHERE User_id=%s AND Source_language=%s AND Target_language=%s \
            AND TranslatorRole_id=%s AND Organisation_id=%s", (user_id, srclang, trglang, role_id, organisation_id))
            if status == 'add':
                cursor.execute("INSERT INTO Assignments (User_id, Source_language, Target_language, TranslatorRole_id, Books, Organisation_id) VALUES \
            (%s, %s, %s, %s, %s)", (user_id, srclang, trglang, role_id, books, organisation_id))
            connection.commit()
            cursor.close()
            return '{"success":true, "message":"Updated Checker task successful"}'
        else:
            cursor = connection.cursor()
            cursor.execute("SELECT Books FROM Assignments WHERE User_id=%s AND Source_language=%s AND Target_language=%s AND \
            TranslatorRole_id=%s AND Organisation_id = %s", (user_id, srclang, trglang, role_id, organisation_id))
            books_rst = cursor.fetchone()
            if not books_rst:
                books = ','.join(bookList)
                cursor.execute("INSERT INTO Assignments (User_id, Source_language, Target_language, TranslatorRole_id, Books, Organisation_id) VALUES \
                (%s, %s, %s, %s, %s, %s)", (user_id, srclang, trglang, role_id, books, organisation_id))
                if status == 'delete':
                    return '{"success":false, "message":"Book not assigned yet"}'
            else:
                if status == 'add':
                    newBooksList = bookList + books_rst[0].split(',')
                    newBooksList = list(set(newBooksList))
                else:
                    newBooksList = books_rst[0].split(',')
                    for book in bookList:
                        if book in newBooksList:
                            newBooksList.remove(book)
                newBooksList = [x for x in newBooksList if x != ""]
                books = ','.join(newBooksList)
                cursor.execute("UPDATE Assignments SET Books=%s WHERE User_id=%s AND Organisation_id=%s AND TranslatorRole_id=%s\
                AND Source_language=%s AND Target_language=%s", (books, user_id, organisation_id, role_id, srclang, trglang))
            connection.commit()
            cursor.close()
            return '{"success":true, "message":"Updated ' + ", ".join(books) +  ' Successful"}'
    else:
        return '{"success":false, "message":"You don\'t have permission to access this resource"}'

@app.route("/v2/alignments/reports/<srclang>/<trglang>", methods=["GET"])
def generateReport(srclang, trglang):
    connection = connect_db()
    cursor = connection.cursor()
    languageList = getLanguageList()
    reportDict = {}
    src = srclang.split('-')[0]
    tablename = getTableNames(srclang, trglang)[0]
    autoLids = []
    manualLids = []
    checkedLids = []
    cursor.execute("SELECT LidSrc, Stage FROM " + tablename)
    rst = set(list(cursor.fetchall()))
    for l,s in rst:
        if s == 1:
            manualLids.append(l)
        elif s == 0:
            autoLids.append(l)
        else:
            checkedLids.append(l)
    autoLids = set(autoLids)
    manualLids = set(manualLids)
    checkedLids = set(checkedLids)
    autoLids = set(list(autoLids) + list(checkedLids))
    manualLids = manualLids - checkedLids
    reportDict[src] = {
                "total":len(rst),
                "language":languageList[src.lower()],
                "autoAlignedCount":len(autoLids),
                "manualAlignedCount":len(manualLids),
                "Checked":len(checkedLids)
            }
    return jsonify(reportDict)


@app.route("/v2/feedbacks", methods=["POST"])
def feedbacks():
    req = request.get_json(True)
    useremail = req["email"]
    subject = req["subject"]
    message = req["feedback"]
    mainEmail = system_email
    headers = {"api-key": sendinblue_key}
    url = "https://api.sendinblue.com/v2.0/email"
    body = '''
    %s
    ''' %(message)
    payload = {
        "to": {mainEmail: ""},
        "from": [useremail, "Autographa MT"],
        "subject": "AutographaMT - Feedback: %s" %(subject),
        "html": body,
        }

    resp = requests.post(url, data=json.dumps(payload), headers=headers)
    return '{"success":true, "message":"Feedback sent to admin"}'

@app.route("/v2/users/resetpassword", methods=["POST"])
@check_token
def resetuserPassword():
    email = request.form["email"]
    role = request.role
    if role != 1:
        connection = connect_db()
        cursor = connection.cursor()
        cursor.execute("SELECT Role_id FROM Users WHERE Email=%s", (email,))
        rst = cursor.fetchone()
        if not rst:
            return '{"success":false, "message":"User does not exist"}'
        else:
            userRole = rst[0]
            if (role == 2 and userRole == 1) or (role == 3 and userRole < 3):
                headers = {"api-key": sendinblue_key}
                url = "https://api.sendinblue.com/v2.0/email"
                totp = pyotp.TOTP('base32secret3232')       # python otp module
                verification_code = totp.now()
                body = '''Hi,<br/><br/>your request for resetting the password has been recieved. <br/>
                Your temporary password is %s. Enter your new password by opening this link:

                <a href="https://%s/resetpassword">https://%s/resetpassword</a>

                <br/><br/>The documentation for accessing the API is available at <a href="https://docs.autographamt.com">https://docs.autographamt.com</a>''' % (verification_code, host_ui_url, host_ui_url)
                payload = {
                    "to": {email: ""},
                    "from": ["noreply@autographamt.in", "AutographaMT"],
                    "subject": "AutographaMT - Reset Password",
                    "html": body,
                    }
                cursor.execute("UPDATE Users SET Verification_code=%s WHERE Email = %s", (verification_code, email))
                cursor.close()
                resp = requests.post(url, data=json.dumps(payload), headers=headers)
                return '{"success":true, "message":"Reset Link sent to email"}'
            else:
                return '{"success":false, "message":"You don\'t have permission to edit this user"}'
    else:
        return '{"success":false, "message":"You don\'t have permission to access this resource"}'

    