

import sys,codecs,re,string,pickle
import pymysql


host="localhost"
user="root"
password="password"
database="itl_db"


def create_concordance_table(lang):
	db = pymysql.connect(host=host,    # your host, usually localhost
	                     user=user,         # your username
	                     password=password,  # your password
	                     database=database,
	                     charset='utf8mb4')
	cur = db.cursor()
	
	table_name = lang+"_bible_concordance"

	cur.execute("SHOW TABLES LIKE '"+table_name+"'")

	if cur.rowcount>0:
		cur.execute("DROP TABLE "+table_name)

	db.commit()
	
	cur.execute('''CREATE TABLE '''+table_name+''' (
		word VARCHAR(50) CHARACTER SET utf8mb4 NOT NULL,
		occurences VARCHAR(10) NOT NULL)''')
	db.commit()
	
	cur.execute("ALTER TABLE "+table_name+ " ADD INDEX word_index(word)")
	cur.execute("ALTER TABLE "+table_name+ " ADD UNIQUE INDEX occurences_index(occurences)")
	db.commit()
	db.close()

	

def insert_concordance_into_table(lang,path):
	db = pymysql.connect(host=host,    # your host, usually localhost
	                     user=user,         # your username
	                     password=password,  # your password
	                     database=database,
	                     charset='utf8mb4')
	# db = pymysql.connect(host="localhost",database="vachan_engine", user="root", password="11111111", charset='utf8mb4')
	bible_text = open(path,"r")

	cur = db.cursor()

	lid_start = 23146

	table_name = lang+"_bible_concordance"
	lid = lid_start
	verse=bible_text.readline()
	while(verse):
		clean_verse = ""

		for char in verse:
			if char not in string.punctuation and (char not in ["0","1","2","3","4","5","6","7","8","9"] or lang == "grk"):
				clean_verse  = clean_verse+char
		verse_words = re.split("\s+",clean_verse.strip())
		# print(verse_words)

		for pos,word in enumerate(verse_words):
			# print (word)
			cur.execute("INSERT INTO "+table_name+" (word,occurences) VALUES (%s,%s)",(word,str(lid)+"_"+str(pos+1)))
		
		verse=bible_text.readline()
		lid = lid+1
		# break
	# cur.execute("SELECT * FROM "+table_name)

	for row in cur:
		print(row)


	db.commit()
	db.close()



def create_alignment_table(src_lang,trg_lang,path):
	alignment = pickle.load(open(path,"rb"))

	db = pymysql.connect(host=host,    # your host, usually localhost
	                     user=user,         # your username
	                     password=password,  # your password
	                     database=database,
	                     charset='utf8mb4')
	cur = db.cursor()
	
	table_name = src_lang+"_"+trg_lang+"_alignment"

	cur.execute("SHOW TABLES LIKE '"+table_name+"'")

	if cur.rowcount>0:
		cur.execute("DROP TABLE "+table_name)

	cur.execute('''CREATE TABLE '''+table_name+''' (
		lid INTEGER NOT NULL,
		source_wordID VARCHAR(50) CHARACTER SET utf8mb4 NOT NULL,
		target_wordID VARCHAR(50) CHARACTER SET utf8mb4 NOT NULL,
		corrected BOOLEAN
		)''')
	cur.execute("ALTER TABLE "+table_name+ " ADD INDEX source_wordID_index(source_wordID)")
	cur.execute("ALTER TABLE "+table_name+ " ADD INDEX target_wordID_index(target_wordID)")
	db.commit()

	for verse in alignment:
		for word_pair in verse[2] :
			if word_pair[0] != 255:
				word1 = int(word_pair[0]) + 1
			else:
				word1 = int(word_pair[0])
			if word_pair[1] != 255:
				word2 = int(word_pair[1]) + 1
			else:
				word2 = int(word_pair[1])
			cur.execute('''INSERT INTO '''+table_name+''' (lid, source_wordID,target_wordID,corrected) VALUES (%s, %s,%s,%s)''',
				# (str(verse[0])+"_"+str(word_pair[0]+1),
				#  str(verse[1])+"_"+str(word_pair[1]+1),
				#  0)
				# )
				(int(verse[1]),
				str(verse[0])+"_"+str(word1),
				str(verse[1])+"_"+str(word2),
				0)
				)

	db.commit()
	db.close()




if __name__ == '__main__':
	
	if len(sys.argv)==3:
		lang = sys.argv[1]
		path = sys.argv[2]
		create_concordance_table(lang)

		insert_concordance_into_table(lang,path)
	elif len(sys.argv)==4:
		src_lang=sys.argv[1]
		trg_lang=sys.argv[2]
		path=sys.argv[3]

		create_alignment_table(src_lang,trg_lang,path)
	else:
		print("usage: python3 Add_to_DB.py lang path\nlang-the 3 letter language code\npath-path to bible text(one verse per line)\n")
		print("OR\n python3 Add_to_DB.py src_lang trg_lang path_to_alignment_pickle_file\n")
		sys.exit(0)


