#!/usr/bin/env python3
# FeedbackAligner.py


import re, sys, pickle
import os.path 
import itertools
import time, json
import pymysql

from .TW_strongs_ref_lookup import TWs


class FeedbackAligner:
	def __init__(self,db,src,src_tablename,trg,trg_tablename,alignment_tablename,EngAlignedLexicon_table):

		self.db = db
		
		cur = self.db.cursor()
		
		self.src_table_name = src_tablename
		self.trg_table_name = trg_tablename

		self.alignment_table_name = alignment_tablename
		self.lex_table = EngAlignedLexicon_table
		# self.FeedbackLookup_table_name = src+"_"+trg+"_FeedbackLookup"

		cur.execute("SHOW TABLES LIKE '"+self.src_table_name+"'")
		if cur.rowcount==0:
			print("Table not found: "+self.src_table_name)
			sys.exit(1)


		cur.execute("SHOW TABLES LIKE '"+self.trg_table_name+"'")
		if cur.rowcount==0:
			print("Table not found: "+self.trg_table_name)
			sys.exit(1)
			
		cur.execute("SHOW TABLES LIKE '"+self.alignment_table_name+"'")
		if cur.rowcount==0:
			print("Table not found: "+self.alignment_table_name)
			sys.exit(1)


		
	def __del__(self):
		
		self.db.commit()
		# self.db.close()
		


	def insert_into_lookup_table(self,src_word,trg_word):
		# decide on how to represent feedback info using type and stage
		# and implement this
		return


	def save_alignment_full_verse(self,lid,word_pairs,userId,Type,Stage):
		cur = self.db.cursor()
		
		cur.execute("DELETE FROM "+self.alignment_table_name+" WHERE LidSrc = %s", lid)
		for pair in word_pairs:
		
			cur.execute("INSERT INTO "+self.alignment_table_name+" (LidSrc, LidTrg, PositionSrc, PositionTrg, WordSrc,Strongs, UserId,Type, Stage) VALUES (%s, %s, %s, %s, %s, %s, %s, %s,%s)",
				(pair[0][0], pair[1][0], pair[0][1], pair[1][1],pair[0][2], pair[1][2],userId,Type,Stage))

		self.db.commit()


	


			
	def get_suggested_feedback_alignment_on_verse(self,lid_to_update):
		# decide on how to represent feedback info using type and stage
		# and implement this
		

		return replacement_options
		


		




	def fetch_alignment(self,lid,OT=False):
		cur = self.db.cursor()

		# print(type(lid))
		if(OT):
			cur.execute("SELECT EnglishKJV, Position_KJV from Heb_UHB_Eng_KJV_Aligned_Lexicon where LID =%s Order by Position",(lid))
		else:
			cur.execute("SELECT Word, Position from Eng_ULB_BibleWord where LID = %s Order by Position",(lid))
		eng_verse_word_list = cur.fetchall()

		cur.execute("SELECT Word, Position FROM "+self.src_table_name+" WHERE LID = %s ORDER BY Position ",(lid))
		src_word_list = cur.fetchall()


		
		cur.execute("SELECT Strongs, Position, Word FROM "+self.trg_table_name+" WHERE LID = %s ORDER BY Position ",(lid))
		trg_word_list = cur.fetchall()
		
		if (OT):
			cur.execute("SELECT Position, EnglishKJV,HebrewWord, Transliteration,Pronounciation,Definition FROM "+self.lex_table+" WHERE LID=%s ORDER BY Position",(lid))
		else:
			cur.execute("SELECT Position, EnglishULB_NASB_Lex_Combined, GreekWord, Transliteration, Pronounciation, Definition FROM "+self.lex_table+" WHERE LID = %s ORDER BY Position",(lid))
		eng_word_list = cur.fetchall()

		count_trg = 0
		count_eng = 0
		trg_word_list_appended = []
		while count_trg<len(trg_word_list) and count_eng<len(eng_word_list):
			if(trg_word_list[count_trg][1] == eng_word_list[count_eng][0]):
				lexical_info = {}
				lexical_info["English"] = eng_word_list[count_eng][1]
				lexical_info["OriginalWord"] = eng_word_list[count_eng][2]
				lexical_info["Transliteration"] = eng_word_list[count_eng][3]
				lexical_info["Pronounciation"] = eng_word_list[count_eng][4]
				lexical_info["Definition"] = eng_word_list[count_eng][5]
				trg_word_list_appended.append((trg_word_list[count_trg][0],trg_word_list[count_trg][1],trg_word_list[count_trg][2],lexical_info))
				count_trg += 1
				count_eng += 1
			elif eng_word_list[count_eng][0] == None:
				count_eng +=1
			elif (trg_word_list[count_trg][1] < eng_word_list[count_eng][0]):
				lexical_info = {}
				trg_word_list_appended.append((trg_word_list[count_trg][0],trg_word_list[count_trg][1],trg_word_list[count_trg][2],lexical_info))
				count_trg += 1
			else:
				count_eng +=1	
		if(count_trg<len(trg_word_list)):
			while (count_trg<len(trg_word_list)):
				lexical_info = {}
				trg_word_list_appended.append((trg_word_list[count_trg][0],trg_word_list[count_trg][1],trg_word_list[count_trg][2],lexical_info))
				count_trg += 1
		trg_word_list = trg_word_list_appended

		cur.execute("SELECT LidSrc, LidTrg, PositionSrc, PositionTrg, WordSrc, Strongs, UserID, Type, Stage from "+self.alignment_table_name+" WHERE LidSrc=%s",(lid))
		fetched_alignments = cur.fetchall()
		
		# # for all source_words get _FeedbackLookup entry
		# # and if entry present in trg_verse, add them to replacement_options
		# replacement_options=self.get_suggested_feedback_alignment_on_verse(lid)

		auto_alignments = [ ((row[0],row[2],row[4]),(row[1],row[3],row[5])) for row in fetched_alignments if row[8]==0]
		corrected_alignments = [ ((row[0],row[2],row[4]),(row[1],row[3],row[5])) for row in fetched_alignments if row[8]!=0]
		replacement_options = []
		
		return list(src_word_list), list(trg_word_list), auto_alignments, corrected_alignments, replacement_options, list(eng_verse_word_list)
	


	def on_approve_feedback(self,corrected_src_trg_word_list):
		# decide on how to represent feedback info using type and stage
		# and implement this
		return


	def fetch_aligned_TWs(self,tw_index,strong_list,refs_list,cur):
		
		return_list = {}
		# required format of return_list
		# {
  #       "48004005": {
  #           "words": "('5206', 'मिले।')",
  #           "positions": ["('8', '16')"]
  #       }

		return return_list




	def fetch_all_TW_alignments(self):
		cur = self.db.cursor()

		return_dict_of_aligned_words = {}
		for tw in TWs:
			strong_list = TWs[tw]["strongs"]
			refs_list = TWs[tw]["References"]
			return_list = self.fetch_aligned_TWs(tw,strong_list,refs_list,cur)
			return_dict_of_aligned_words[str(tw)] = return_list

		cur.close()
		return json.dumps(return_dict_of_aligned_words,  ensure_ascii=False)

	def fetch_seleted_TW_alignments(self,tw_index_list):
		cur = self.db.cursor()

		return_dict_of_aligned_words = {}
		for tw in tw_index_list:
			strong_list = TWs[tw]["strongs"]
			refs_list = TWs[tw]["References"]
			return_list = self.fetch_aligned_TWs(tw,strong_list,refs_list,cur)
			return_dict_of_aligned_words[str(tw)] = return_list

		cur.close()
		return json.dumps(return_dict_of_aligned_words,  ensure_ascii=False)





if __name__ == '__main__':


	# connection =  pymysql.connect(host="localhost",    # your host, usually localhost
	#                      user="root",         # your username
	#                      password="password",  # your password
	#                      database = "AutographaMT_Staging",
	#                      charset='utf8mb4')

	# connection =  pymysql.connect(host="103.196.222.37",    # your host, usually localhost
	#                     user="bcs_vo_owner",         # your username
	#                     password="bcs@0pen",  # your password
	#                     database="bcs_vachan_engine_test",
	#                     # database="bcs_vachan_engine_open",
	#                     port=13306,
	#                     charset='utf8mb4')

	# digital ocean 
	connection =  pymysql.connect(host="159.89.167.64",    # your host, usually localhost
	                    user="test_user",         # your username
	                    password="staging&2414",  # your password
	                    database="AutographaMTStaging",
	                    # database="bcs_vachan_engine_open",
	                    port=3306,
	                    charset='utf8mb4')

		

	obj = FeedbackAligner(connection,'Hin','Hin_4_BibleWord','Grk','Grk_WH_BibleWord','Hin_4_Grk_WH_Alignment','Grk_Eng_Aligned_Lexicon')
	# obj = FeedbackAligner(connection,'Hin','Hin_IRV3_OT_BibleWord','Heb','Heb_UHB_BibleWord','Hin_IRV3_Heb_UHB_Alignment')

	start = time.clock()
	
	#obj.on_approve_feedback([("2424 5547","यीशु मसीह"),("5207","सन्तान"),("5257 5547","मसीह . सेवक")])

	src_word_list, trg_word_list, auto_alignments, corrected_alignments, replacement_options, eng_word_list = obj.fetch_alignment(30478)
	# src_word_list, trg_word_list, auto_alignments, corrected_alignments, replacement_options, eng_word_list = obj.fetch_alignment(23094,OT=True)
	print("src_word_list:"+str(src_word_list))
	print("\n")
	print("trg_word_list:"+str(trg_word_list))
	print("\n")
	print("auto_alignments:"+str(auto_alignments))
	print("\n")
	print("corrected_alignments:"+str(corrected_alignments))
	print("\n")
	print("replacement_options:"+str(replacement_options))
	print("\n")
	print("english_word_list:"+str(eng_word_list))




	# obj.update_alignment_on_verse('23146')
	
	# obj.save_alignment_full_verse(23146,[((23146,1,"आम"),(23146,3,300)),((23146,2,"आतमि"),(23146,1,100)),((23146,3,'हात'),(23146,2,200))],9999,99,99)

	# TW_alignments = obj.fetch_all_TW_alignments()
	# TW_alignments = obj.fetch_seleted_TW_alignments([1,2,3])
	#TW_alignments = obj.fetch_seleted_TW_alignments(range(17,22))

	# TW_alignments = obj.fetch_seleted_TW_alignments([18])

	# print(TW_alignments)

	print("Time taken:"+str(time.clock()-start))
	del obj