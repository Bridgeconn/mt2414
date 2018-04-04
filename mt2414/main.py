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
from flask import Flask, request, session, redirect
from flask import g
from flask_cors import CORS, cross_origin
import jwt
import requests
import scrypt
import psycopg2


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

def get_db():                                                                      #--------------To open database connection-------------------#
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'db'):
        g.db = psycopg2.connect(dbname=postgres_database, user=postgres_user, password=postgres_password, host=postgres_host, port=postgres_port)
    return g.db

@app.teardown_appcontext                                              #-----------------Close database connection----------------#
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'db'):
        g.db.close()

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
        access_token = jwt.encode({'sub': email, 'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1), 'role': role}, jwt_hs256_secret, algorithm='HS256')
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
                'verify_exp': True
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
        # raise TokenError('Invalid JWT header', 'Token missing')
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
            if "IN" in item["cc"]:
                tr[item["ang"]] = item["lc"]
        db_item = pickle.dumps(tr)
        connection = get_db()
        cursor = connection.cursor()
        cursor.execute("SELECT picklelist FROM targetlanglist")
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
