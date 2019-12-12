import sys,re,pymysql


src = sys.argv[1]
trg = sys.argv[2]
path = sys.argv[3]

in_file = open(path,"r")

title = in_file.readline()

host="localhost"
user="root"
password="password"
database="itl_db"
db = pymysql.connect(host=host,    # your host, usually localhost
                     user=user,         # your username
                     password=password,  # your password
                     database=database,
                     charset='utf8mb4')
cur = db.cursor()

# table_name = src_lang+"_"+trg_lang+"_alignment"
table_name = src+"_"+trg+"_alignment"
# sys.exit(0)

cur.execute("SHOW TABLES LIKE '"+table_name+"'")

if cur.rowcount>0:
	cur.execute("DROP TABLE "+table_name)

cur.execute('''CREATE TABLE '''+table_name+''' (
	lid INTEGER NOT NULL,
	source_wordID VARCHAR(50) CHARACTER SET utf8mb4 NOT NULL,
	target_wordID VARCHAR(50) CHARACTER SET utf8mb4 NOT NULL,
	user VARCHAR(10)
	)''')
cur.execute("ALTER TABLE "+table_name+ " ADD INDEX source_wordID_index(source_wordID)")
cur.execute("ALTER TABLE "+table_name+ " ADD INDEX target_wordID_index(target_wordID)")
db.commit()

for line in in_file.readlines():
	cells = re.split("\t",line[:-1])
	source_wordID =cells[0]+"_"+cells[1]
	target_wordID =cells[2]+"_"+cells[3]
	user = 'default'

	cur.execute("INSERT INTO "+table_name+" (lid,source_wordID,target_wordID,user) VALUES (%s,%s,%s,%s)",(cells[0],source_wordID,target_wordID,user))

db.commit()

db.close()