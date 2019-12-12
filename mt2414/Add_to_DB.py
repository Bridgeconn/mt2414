import glob
import pymysql
import os
import re
from romanize import romanize
from unidecode import unidecode


db_name = 'AutographaMT_Staging'

# # db = pymysql.connect(host="localhost",database="test_new_tables", user="root", password="11111111", charset='utf8mb4')
db = pymysql.connect(host="localhost",database=db_name, user="root", password="password", charset='utf8mb4')
cursor = db.cursor()

status = 'start'

def initialize_DB_BibleWordtable_UGNT(tablename):
	cursor.execute("select * from information_schema.tables where table_schema = %s  and table_name= %s", (db_name, tablename))
	rst = cursor.fetchone()
	if not rst:
		commands = '''
				CREATE TABLE ''' + tablename + ''' (
				LID smallint(5) unsigned,
				Position tinyint(3) unsigned ,
				Word varchar(30) charset utf8mb4,
				Strongs smallint(5) unsigned,
				Lemma varchar(30) charset utf8mb4,
				Morph varchar(30),
				Pronunciation varchar(50) charset utf8mb4,
				Foreign Key(LID) references Bcv_LidMap(ID)
			)
			'''
		cursor.execute(commands)
		print("created new table:"+tablename)
	else:
		cursor.execute("TRUNCATE " + tablename)
		print("emptied existing table: "+tablename)
	db.commit()

def initialize_DB_BibleWordtable_UHB(tablename):
	cursor.execute("select * from information_schema.tables where table_schema = %s  and table_name= %s", (db_name, tablename))
	rst = cursor.fetchone()
	if not rst:
		commands = '''
				CREATE TABLE ''' + tablename + ''' (
				LID smallint(5) unsigned,
				Position tinyint(3) unsigned ,
				Word varchar(30) charset utf8mb4,
				Strongs smallint(5) unsigned,
				Lemma varchar(30) charset utf8mb4,
				Morph varchar(30),
				Pronunciation varchar(50) charset utf8mb4,
				Foreign Key(LID) references Bcv_LidMap(ID)
			)
			'''
		cursor.execute(commands)
		print("created new table:"+tablename)
	else:
		cursor.execute("TRUNCATE " + tablename)
		print("emptied existing table: "+tablename)
	db.commit()
		

def initialize_DB_Bible_text(tablename):
	cursor.execute("select * from information_schema.tables where table_schema = %s  and table_name= %s", (db_name, tablename))
	rst = cursor.fetchone()
	if not rst:
		commands = ''' create table '''+tablename+''' like Hin_4_Text'''
		cursor.execute(commands)
		print('created new table: '+tablename)
	cursor.execute('TRUNCATE '+tablename)
	print('emptied the table')
	db.commit()

def initialize_DB_BibleWordtable(tablename):
	cursor.execute("select * from information_schema.tables where table_schema = %s  and table_name= %s", (db_name, tablename))
	rst = cursor.fetchone()
	if not rst:
		commands = '''	CREATE TABLE ''' + tablename + ''' like Hin_4_BibleWord	'''
		cursor.execute(commands)
		print("created new table:"+tablename)
	else:
		cursor.execute("TRUNCATE " + tablename)
		print("emptied existing table: "+tablename)
	db.commit()


def createDBEntry_Text_table(book, tablename):
	book_num = book['BookCode']
	for chap in book['Chapters']:
		chap_num  = chap['ChapterNumber']
		for verse in chap['Verses']:
			verse_num = verse['VerseNumber']
			try:
				cursor.execute("select ID from Bcv_LidMap where Book=%s and Chapter=%s and Verse=%s",(book_num,chap_num,verse_num))
				lid = cursor.fetchone()
				
			except Exception as e:
				print("error at fetching lid for Book="+str(book_num)+",Chapter="+str(chap_num)+",Verse="+str(verse_num))
				raise e
			usfm = verse['Usfm']
			text = verse['Text']
			pos = 0
			cursor.execute("INSERT INTO " + tablename + "(LID, Verse, Usfm) VALUES(%s,%s,%s)",(lid,text,usfm))
			
	db.commit()
	# cursor.close()
	return 'Done'
	
def createDBEntry_BibleWord(book,tablename):
	skipped_count = 0
	book_num = book['BookCode']
	for chap in book['Chapters']:
		chap_num  = chap['ChapterNumber']
		for verse in chap['Verses']:
			verse_num = verse['VerseNumber']
			lid = 0
			try:
				cursor.execute("select ID from Bcv_LidMap where Book=%s and Chapter=%s and Verse=%s",(book_num,chap_num,verse_num))
				lid = cursor.fetchone()[0]
				
			except Exception as e:
				print("error at fetching lid for Book="+str(book_num)+",Chapter="+str(chap_num)+",Verse="+str(verse_num))
				print('Skipping that entry')
				skipped_count += 1
				continue
				# raise e
			word_sequence = verse["Text"]

			pos = 1
			for word in word_sequence:
				try:
					cursor.execute("INSERT INTO " + tablename + " (LID, Position, Word) VALUES (%s,%s,%s)",(lid,pos,word))
					
				except Exception as e:
					print("error at:")
					print(str(lid)+"\t"+str(pos)+"\t"+word)
					print('Skipping this DB entry')
					raise e
				pos =pos+1
	print(str(skipped_count)+' skipped in this book')
	db.commit()
	return 'Done'


def createDBEntry_UGNT_BibleWord(book,tablename):
	
	book_num = book['BookCode']
	for chap in book['Chapters']:
		chap_num  = chap['ChapterNumber']
		for verse in chap['Verses']:
			verse_num = verse['VerseNumber']
			try:
				cursor.execute("select ID from Bcv_LidMap where Book=%s and Chapter=%s and Verse=%s",(book_num,chap_num,verse_num))
				lid = cursor.fetchone()
				
			except Exception as e:
				print("error at fetching lid for Book="+str(book_num)+",Chapter="+str(chap_num)+",Verse="+str(verse_num))
				raise e
			word_sequence = verse["Text"]
			strong_sequence = verse["Strongs"]

			pos = 1
			for word,strongs,lemma,morph,tw in zip(word_sequence,strong_sequence,verse["Lemma"],verse["Morph"],verse["TW"]):
				try:
					romanized_text = romanize(word)
					cursor.execute("INSERT INTO " + tablename + " (LID, Position, Word, Strongs,Lemma,Morph,TW, Pronunciation) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",(lid,pos,word,strongs,lemma,morph,tw,romanized_text))
					
				except Exception as e:
					print("error at:")
					print(str(lid)+"\t"+str(pos)+"\t"+word+"\t"+str(strongs))
					print('Skipping this DB entry')
					raise e
				pos =pos+1
	db.commit()
	return 'Done'

DB_entry_count = 0
Skip_count = 0

UHB_verses_2_ignore = [
(2,	21,	37),
(4,	26,	1),
(9,	20,	42),
(13,	12,	4),
(19,	3,	1),
(19,	4,	1),
(19,	5,	1),
(19,	6,	1),
(19,	7,	1),
(19,	8,	1),
(19,	9,	1),
(19,	12,	1),
(19,	13,	1),
(19,	18,	1),
(19,	19,	1),
(19,	20,	1),
(19,	21,	1),
(19,	22,	1),
(19,	30,	1),
(19,	31,	1),
(19,	34,	1),
(19,	36,	1),
(19,	38,	1),
(19,	39,	1),
(19,	40,	1),
(19,	41,	1),
(19,	42,	1),
(19,	44,	1),
(19,	45,	1),
(19,	46,	1),
(19,	47,	1),
(19,	48,	1),
(19,	49,	1),
(19,	51,	1),
(19,	52,	1),
(19,	53,	1),
(19,	54,	1),
(19,	55,	1),
(19,	56,	1),
(19,	57,	1),
(19,	58,	1),
(19,	59,	1),
(19,	60,	1),
(19,	61,	1),
(19,	62,	1),
(19,	63,	1),
(19,	64,	1),
(19,	65,	1),
(19,	67,	1),
(19,	68,	1),
(19,	69,	1),
(19,	70,	1),
(19,	75,	1),
(19,	76,	1),
(19,	77,	1),
(19,	80,	1),
(19,	81,	1),
(19,	83,	1),
(19,	84,	1),
(19,	85,	1),
(19,	88,	1),
(19,	89,	1),
(19,	92,	1),
(19,	102,	1),
(19,	108,	1),
(19,	140,	1),
(19,	142,	1)

]

def createDBEntry_UHB_BibleWord(book,tablename):
	global DB_entry_count, Skip_count, UHB_verses_2_ignore


	book_num = book['BookCode']
	for chap in book['Chapters']:
		chap_num  = chap['ChapterNumber']
		for verse in chap['Verses']:
			verse_num = verse['VerseNumber']
			if (int(book_num),chap_num,verse_num) in UHB_verses_2_ignore:
				print("skipping: "+str((book_num,chap_num,verse_num)))
				Skip_count += 1
				continue


			try:
				cursor.execute("select KJV_Book, KJV_Chapter, KJV_Verse from WLC_KJV_VersificationMap where WLC_Book=%s and WLC_Chapter=%s and WLC_Verse=%s",(book_num,chap_num,verse_num))
				res = cursor.fetchone()
				if res:
					new_book_num = res[0]
					new_chap_num = res[1]
					new_verse_num = res[2]
					cursor.execute("select ID from Bcv_LidMap where Book=%s and  Chapter=%s and Verse=%s",(new_book_num,new_chap_num,new_verse_num))
					lid = cursor.fetchone()
				else:
					cursor.execute("select ID from Bcv_LidMap where Book=%s and  Chapter=%s and Verse=%s",(book_num,chap_num,verse_num))
					lid = cursor.fetchone()

				if lid:
					lid = lid[0]
				else:
					if (book_num,chap_num,verse_num) == (11,	22,	44):
						lid = 9524
					else:
						print("skipping: "+str((book_num,chap_num,verse_num)))
						Skip_count += 1
						continue
								
			except Exception as e:
				print("error at fetching lid for Book="+str(book_num)+",Chapter="+str(chap_num)+",Verse="+str(verse_num))
				raise e
			word_sequence = verse["Text"]
			strong_sequence = verse["Strongs"]

			# print("inserting:\t"+str(lid)+"\t"+str(book_num)+"\t"+str(chap_num)+"\t"+str(verse_num))
			pos = 1
			for word,strongs,lemma,morph in zip(word_sequence,strong_sequence,verse["Lemma"],verse["Morph"]):
				
				try:
					romanized_text = unidecode(word)
					if lid == 9524:
						cursor.execute("Select max(Position) from "+tablename+" where LID=9524;")
						prev_pos =cursor.fetchone()[0]
						if prev_pos:
							pos = prev_pos + 1
							print('updated pos for 1Kings 22:44')
						
					cursor.execute("INSERT INTO " + tablename + " (LID, Position, Word, Strongs,Lemma,Morph, Pronunciation) VALUES (%s,%s,%s,%s,%s,%s,%s)",(lid,pos,word,strongs,lemma,morph,romanized_text))
				except Exception as e:
					print("error at:")
					print(str(lid)+"\t"+str(pos)+"\t"+word+"\t"+str(strongs))
					print('Skipping this DB entry')
					raise e
				pos =pos+1
			DB_entry_count += 1
	# print("Skipped till now "+str(Skip_count)+" verses")
	# print("Inserted till now "+str(DB_entry_count)+" verses to DB!")
	db.commit()
	return 'Done'


def updateDBEbtry_Text_Usfm(book,tablename):
	
	book_num = book['BookCode']
	for chap in book['Chapters']:
		chap_num  = chap['ChapterNumber']
		for verse in chap['Verses']:
			verse_num = verse['VerseNumber']
			try:
				cursor.execute("select ID from Bcv_LidMap where Book=%s and Chapter=%s and Verse=%s",(book_num,chap_num,verse_num))
				lid = cursor.fetchone()
				
			except Exception as e:
				print("error at fetching lid for Book="+str(book_num)+",Chapter="+str(chap_num)+",Verse="+str(verse_num))
				raise e
			usfm = verse['Usfm']
			pos = 0
			cursor.execute("UPDATE " + tablename + " SET Usfm = %s Where lid=%s",(usfm,lid))
			
	db.commit()
	# cursor.close()
	return 'Done'




def getBibleBookIds():
	'''
	Returns a tuple of two dictionarys of the books of the Bible, bookcode has bible book codes
	as the key and bookname has bible book names as the key.
	'''
	bookcode = {}
	bookname = {}
	cursor = db.cursor()
	cursor.execute("SELECT * FROM Bible_Book_Lookup")
	rst = cursor.fetchall()
	for item in rst:
		bookname[item[1]] = str(item[0])
		bookcode[item[2]] = str(item[0])
	cursor.close()
	return (bookcode, bookname)

bookNamesDict = getBibleBookIds()[0]
# print(bookNamesDict)

bookname_pattern = re.compile('\\\id (\w{3})')
chapter_num_pattern = re.compile(' (\d+)')
verse_num_pattern = re.compile(' (\d+)')
Grk_word_pattern = re.compile(' (\w+)\|')
Heb_word_pattern = re.compile(' ([^|]+)\|')
Grk_strongs_pattern = re.compile(' strong="G(\d+)"')
Heb_strongs_pattern = re.compile(' strong="[a-z:]*H(\d\d\d\d)[a-z]*"')
Grk_lemma_pattern = re.compile('\|lemma="(\w+)" ')
Heb_lemma_pattern = re.compile('\|lemma="([^"]+)" ')
Grk_morph_pattern = re.compile(' x-morph="([a-zA-Z,]+)')
Heb_morph_pattern = re.compile(' x-morph="([a-zA-Z0-9,:]+)')
tw_pattern = re.compile(' x-tw="([a-zA-Z0-9:/*_]+)"')
non_letters = [',', '"', '!', '.', '\n', '\\','“','”','*']
cross_ref_pattern = re.compile('\([^())]+\)')

def parse_UGNT_files(path,tablename):
	print(path+"/*.usfm")
	files = glob.glob(path+"/*.usfm")
	# print (path)
	print (files)

	initialize_DB_BibleWordtable_UGNT(tablename)

	this_book = {}
	for f in files:
		print("working on: "+f)
		fc = open(f, 'r').read().strip()
		bookName = re.search(bookname_pattern, fc).group(1)
		bc = bookNamesDict[bookName]
		this_book = {'BookName':bookName,'BookCode':bc,"Chapters":[]}
		splitChap = fc.split('\c')
		for chap in splitChap[1:]:
			chap_num = int(re.search(chapter_num_pattern,chap).group(1))
			this_chapter = {'ChapterNumber':chap_num,'Verses':[]}
			splitVerse = chap.split('\\v')
			for verse in splitVerse[1:]:
				verse_num = int(re.search(verse_num_pattern,verse).group(1))
				verse = verse.replace("\\w*","")
				splitWord = verse.split('\\w')
				word_sequence = []
				strong_sequence = []
				lemma_sequence = []
				morph_sequence = []
				tw_sequence = []
				for word in splitWord[1:]:
					text = '-'
					strong = '-'
					lemma = '-'
					morph = '-'
					tw = '-'
					text_search = re.search(Grk_word_pattern,word)
					if(text_search):
						text = text_search.group(1)
					strong_search = re.search(Grk_strongs_pattern,word)
					if(strong_search):
						strong = int(int(strong_search.group(1))/10)
					lemma_search = re.search(Grk_lemma_pattern,word) 
					if(lemma_search):
						lemma = lemma_search.group(1)
					morph_search = re.search(Grk_morph_pattern,word)
					if(morph_search):
						morph = morph_search.group(1)
					tw_search = re.search(tw_pattern,word)
					if(tw_search):
						tw = tw_search.group(1)
					# print(text+"\t"+str(strong)+"\t"+str(lemma)+"\t"+str(morph)+"\t"+str(tw))
					word_sequence.append(text)
					strong_sequence.append(strong)
					lemma_sequence.append(lemma)
					morph_sequence.append(morph)
					tw_sequence.append(tw)
				this_chapter['Verses'].append({'VerseNumber':verse_num,'Text':word_sequence,'Strongs':strong_sequence,'Lemma':lemma_sequence,"Morph":morph_sequence,"TW":tw_sequence})
			this_book['Chapters'].append(this_chapter)
		createDBEntry_UGNT_BibleWord(this_book, tablename)
		# print(this_book)
		# break

def parse_UHB_files(path,tablename):
	# print(path+"/*.usfm")
	files = glob.glob(path+"/*.usfm")
	# print (path)
	# print (files)

	initialize_DB_BibleWordtable_UHB(tablename)

	this_book = {}
	for f in files:
		print("working on: "+f)
		fc = open(f, 'r').read().strip()
		bookName = re.search(bookname_pattern, fc).group(1)
		bc = bookNamesDict[bookName]
		this_book = {'BookName':bookName,'BookCode':bc,"Chapters":[]}
		splitChap = fc.split('\c')
		for chap in splitChap[1:]:
			chap_num = int(re.search(chapter_num_pattern,chap).group(1))
			this_chapter = {'ChapterNumber':chap_num,'Verses':[]}
			splitVerse = chap.split('\\v')
			for verse in splitVerse[1:]:
				verse_num = int(re.search(verse_num_pattern,verse).group(1))
				verse = verse.replace("\\w*","")
				splitWord = verse.split('\\w')
				word_sequence = []
				strong_sequence = []
				lemma_sequence = []
				morph_sequence = []
				for word in splitWord[1:]:
					text = '-'
					strong = None
					lemma = '-'
					morph = '-'
					tw = '-'
					text_search = re.search(Heb_word_pattern,word)
					if(text_search):
						text = text_search.group(1)
					strong_search = re.search(Heb_strongs_pattern,word)
					if(strong_search):
						strong = int(strong_search.group(1))
					lemma_search = re.search(Heb_lemma_pattern,word) 
					if(lemma_search):
						lemma = lemma_search.group(1)
					morph_search = re.search(Heb_morph_pattern,word)
					if(morph_search):
						morph = morph_search.group(1)
					word_sequence.append(text)
					strong_sequence.append(strong)
					lemma_sequence.append(lemma)
					morph_sequence.append(morph)
				this_chapter['Verses'].append({'VerseNumber':verse_num,'Text':word_sequence,'Strongs':strong_sequence,'Lemma':lemma_sequence,"Morph":morph_sequence})
			this_book['Chapters'].append(this_chapter)
			# break
		createDBEntry_UHB_BibleWord(this_book,tablename)
		# print(this_book)
		# break



def parse_files_with_Usfm_markers(path,tablename):
	files = glob.glob(path+"/*.usfm")
	files.sort()

	this_book = {}
	for f in files:
			fc = open(f, 'r').read().strip()
			bookName = re.search(bookname_pattern, fc).group(1)
			bc = bookNamesDict[bookName]
			this_book = {'BookName':bookName,'BookCode':bc,"Chapters":[]}
			splitChap = fc.split('\c')
			book_headers = splitChap[0]+"\c"
			for chap in splitChap[1:]:
				chap_num = int(re.search(chapter_num_pattern,chap).group(1))
				this_chapter = {'ChapterNumber':chap_num,'Verses':[]}
				splitVerse = chap.split('\\v')
				chap_headers = splitVerse[0]
				for verse in splitVerse[1:]:
					verse_num = int(re.search(verse_num_pattern,verse).group(1))
					verse = "\\v"+verse
					if verse_num == 1:
						verse = "\c"+chap_headers+verse
					if verse_num == 1 and chap_num == 1:
						verse = book_headers+ verse
					this_chapter['Verses'].append({'VerseNumber':verse_num,'Usfm':verse})
				this_book['Chapters'].append(this_chapter)
			# updateDBEbtry_Text_Usfm(this_book,tablename)


def parse_files_with_Usfm_and_Text(path,tablename):
	files = glob.glob(path+"/*.SFM")
	files.sort()

	initialize_DB_Bible_text(tablename)

	this_book = {}
	for f in files:
			print('working on '+f)
			fc = open(f, 'r').read().strip()
			bookName = re.search(bookname_pattern, fc).group(1)
			bc = bookNamesDict[bookName]
			this_book = {'BookName':bookName,'BookCode':bc,"Chapters":[]}
			splitChap = fc.split('\c')
			book_headers = splitChap[0]+"\c"
			for chap in splitChap[1:]:
				chap_num = int(re.search(chapter_num_pattern,chap).group(1))
				this_chapter = {'ChapterNumber':chap_num,'Verses':[]}
				splitVerse = chap.split('\\v')
				chap_headers = splitVerse[0]
				for verse in splitVerse[1:]:
					verse_num = int(re.search(verse_num_pattern,verse).group(1))
					verse_full_text = verse
					clean_text = verse_full_text.split('\n')[0].strip()
					clean_text = ' '.join(clean_text.split(' ')[1:])
					usfm = "\\v"+verse
					if verse_num == 1:
						usfm = "\c"+chap_headers+usfm
					if verse_num == 1 and chap_num == 1:
						usfm = book_headers+ usfm
					this_chapter['Verses'].append({'VerseNumber':verse_num,'Usfm':usfm,'Text':clean_text})
				this_book['Chapters'].append(this_chapter)
			createDBEntry_Text_table(this_book,tablename)
			# break

def parse_files_for_BibleWord(path,tablename):
	files = glob.glob(path+"/*.SFM")
	files.sort()

	initialize_DB_BibleWordtable(tablename)

	this_book = {}
	for f in files:
			print('working on '+f)
			fc = open(f, 'r').read().strip()
			bookName = re.search(bookname_pattern, fc).group(1)
			bc = bookNamesDict[bookName]
			this_book = {'BookName':bookName,'BookCode':bc,"Chapters":[]}
			splitChap = fc.split('\c')
			book_headers = splitChap[0]+"\c"
			for chap in splitChap[1:]:
				chap_num = int(re.search(chapter_num_pattern,chap).group(1))
				this_chapter = {'ChapterNumber':chap_num,'Verses':[]}
				splitVerse = chap.split('\\v')
				chap_headers = splitVerse[0]
				for verse in splitVerse[1:]:
					verse_num = int(re.search(verse_num_pattern,verse).group(1))
					verse_full_text = verse
					verse_full_text = verse_full_text.split('\n')[0].strip()
					verse_full_text = ' '.join(verse_full_text.split(' ')[1:])
					verse_full_text =  re.sub(cross_ref_pattern,'',verse_full_text)


					clean_text = ''
					for char in verse_full_text:
						if char not in non_letters:
							clean_text += char
					clean_text = clean_text.strip().split(' ')

					this_chapter['Verses'].append({'VerseNumber':verse_num,'Text':clean_text})
				this_book['Chapters'].append(this_chapter)
			createDBEntry_BibleWord(this_book,tablename)
			# break


def parse_ULB_files_with_Usfm_and_text(path,tablename):
	print(path+"/*.usfm")
	files = glob.glob(path+"/*.usfm")
	files.sort()

	initialize_DB_Bible_text(tablename)

	this_book = {}
	for f in files:
		print("working on: "+f)
		fc = open(f, 'r').read().strip()
		bookName = re.search(bookname_pattern, fc).group(1)
		bc = bookNamesDict[bookName]
		this_book = {'BookName':bookName,'BookCode':bc,"Chapters":[]}
		splitChap = fc.split('\c ')
		usfm_book_head = splitChap[0]
		for chap in splitChap[1:]:
			chap_num = int(chap.split("\n")[0])
			this_chapter = {'ChapterNumber':chap_num,'Verses':[]}
			splitVerse = chap.split('\\v')
			usfm_chapter_head = splitVerse[0]
			for verse in splitVerse[1:]:
				verse_num = int(re.search(verse_num_pattern,verse).group(1))
				verse_full_text = verse.strip()
				clean_text = verse_full_text.split('\n')[0].strip()
				clean_text = ' '.join(clean_text.split(' ')[1:])
				verse_full_text = '\\v '+verse_full_text
				if (verse_num == 1):
					verse_full_text = '\\c' + usfm_chapter_head + verse_full_text
					if (chap_num == 1):
						verse_full_text = usfm_book_head + verse_full_text
				# print('VerseNumber:'+str(verse_num)+'\nUsfm:'+verse_full_text+'\nText:'+clean_text)
				this_chapter['Verses'].append({'VerseNumber':verse_num,'Usfm':verse_full_text,'Text':clean_text})
			this_book['Chapters'].append(this_chapter)
		createDBEntry_Text_table(this_book, tablename)
		# break
	


def parse_ULB_usfm_files_to_BibleWord(path,tablename):
	print(path+"/*.usfm")
	files = glob.glob(path+"/*.usfm")
	# print (path)
	# print (files)

	initialize_DB_BibleWordtable(tablename)

	this_book = {}
	for f in files:
		print("working on: "+f)
		fc = open(f, 'r').read().strip()
		bookName = re.search(bookname_pattern, fc).group(1)
		bc = bookNamesDict[bookName]
		this_book = {'BookName':bookName,'BookCode':bc,"Chapters":[]}
		splitChap = fc.split('\c ')
		for chap in splitChap[1:]:
			chap_num = int(chap.split("\n")[0])
			this_chapter = {'ChapterNumber':chap_num,'Verses':[]}
			splitVerse = chap.split('\\v')
			for verse in splitVerse[1:]:
				verse_num = int(re.search(verse_num_pattern,verse).group(1))
				verse_full_text = verse.strip()
				clean_text = verse_full_text.split('\n')[0].strip()
				for char in non_letters:
					clean_text = clean_text.replace(char,'')
				word_sequence = clean_text.split(' ')[1:]
				# print('VerseNumber:'+str(verse_num)+'Text:'+str(word_sequence))
				this_chapter['Verses'].append({'VerseNumber':verse_num,'Text':word_sequence})
			this_book['Chapters'].append(this_chapter)
		createDBEntry_BibleWord(this_book, tablename)
		# print(this_book)
		break



# parse_UGNT_files("ugnt/ugnt 1","Grk_UGNT1_BibleWord")
# parse_UGNT_files("ugnt/ugnt 2","Grk_UGNT2_BibleWord")
# parse_UGNT_files("ugnt/ugnt 4","Grk_UGNT4_BibleWord")

# parse_UHB_files("../UHB",'Heb_UHB_BibleWord')


# parse_files_with_Usfm_markers("usfm_files/Assamese Stage 5","Asm_5_Text")
# parse_files_with_Usfm_markers("usfm_files/Bengali Stage 5","Ben_5_Text")
# parse_files_with_Usfm_markers("usfm_files/Gujarati Stage 4","Guj_4_Text")
# parse_files_with_Usfm_markers("usfm_files/Kannada Stage 5","Kan_5_Text")
# parse_files_with_Usfm_markers("usfm_files/Malayalam Stage 5","Mal_4_Text")

# parse_files_with_Usfm_markers("usfm_files/Marathi Stage 5","Mar_4_Text")
# parse_files_with_Usfm_markers("usfm_files/Odiya Stage 5","Odi_5_Text")
# parse_files_with_Usfm_markers("usfm_files/Punjabi Stage 5","Pun_5_Text")
# parse_files_with_Usfm_markers("usfm_files/Tamil Stage 5","Tam_5_Text")
# parse_files_with_Usfm_markers("usfm_files/Telegu Stage 5","Tel_5_Text")
# parse_files_with_Usfm_markers("usfm_files/Urdu Stage 5","Urd_5_Text")

# parse_ULB_usfm_files_to_BibleWord('../en_ulb/NT','Eng_ULB_BibleWord')

# parse_ULB_files_with_Usfm_and_text('../en_ulb/NT','Eng_ULB_Text')

parse_files_with_Usfm_and_Text('../../Bibles/Bible NT_OT partial/Hindi Bible/OT/Revised stage 3','Hin_IRV3_OT_Text')
# parse_files_for_BibleWord('../../Bibles/Bible NT_OT partial/Hindi Bible/OT/Revised stage 3','Hin_IRV3_OT_BibleWord')