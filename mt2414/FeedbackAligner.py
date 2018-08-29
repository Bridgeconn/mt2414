#!/usr/bin/env python3
# FeedbackAligner.py


import re, sys, pickle
import os.path 
import itertools
import time, json
import pymysql

from TW_strongs_ref_lookup import TWs 


class FeedbackAligner:
	def __init__(self,db,src,trg,tablename):

		self.db = db
		
		cur = self.db.cursor()
		
		self.src_table_name = src+"_bible_concordance"
		self.trg_table_name = trg+"_bible_concordance"

		self.alignment_table_name = tablename
		self.FeedbackLookup_table_name = src+"_"+trg+"_FeedbackLookup"

		cur.execute("SHOW TABLES LIKE '"+self.src_table_name+"'")
		if cur.rowcount==0:
			print("Table not found: "+self.src_table_name)
			sys.exit(0)


		cur.execute("SHOW TABLES LIKE '"+self.trg_table_name+"'")
		if cur.rowcount==0:
			print("Table not found: "+self.trg_table_name)
			sys.exit(0)
			
		cur.execute("SHOW TABLES LIKE '"+self.alignment_table_name+"'")
		if cur.rowcount==0:
			print("Table not found: "+self.alignment_table_name)
			sys.exit(0)


		cur.execute("SHOW TABLES LIKE '"+self.FeedbackLookup_table_name+"'")
		if cur.rowcount==0:
			cur.execute("CREATE TABLE "+self.FeedbackLookup_table_name+
				" (source_word VARCHAR(50) CHARACTER SET utf8mb4 NOT NULL,target_word VARCHAR(50) CHARACTER SET utf8mb4 NOT NULL,confidence_score FLOAT(6,5))")
			cur.execute("ALTER TABLE "+self.FeedbackLookup_table_name+" ADD INDEX source_word_index(source_word)")
			cur.execute("ALTER TABLE "+self.FeedbackLookup_table_name+" ADD INDEX target_word_index(target_word)")
			self.db.commit()
		
	def __del__(self):
		
		self.db.commit()
		# self.db.close()
		


	def insert_into_lookup_table(self,src_word,trg_word):
		try:	
			cur = self.db.cursor()

			src_word_array = src_word.split(" ")
			trg_word_array = trg_word.split(" ")


			# for calculating confidence_score

			#handling multi-word src phrases and multi-word non-contiguous phrases
			#multi-words inputed as, a single string with "space" seperating the words
			#non-contigious words, as a single string with "." for every word in between and all words and dots separated by "space"
			cur.execute("select occurences  from "+self.src_table_name+" where word='"+src_word_array[0]+"'")
			src_word_occurences = [x[0] for x in cur.fetchall()]
			for i,src_word in enumerate(src_word_array):
				if src_word == ".":
					continue
				for fetched_pos in src_word_occurences:
					lid = fetched_pos.split("_")[0]
					pos = int(fetched_pos.split("_")[1])
					pos = pos + i
					check_occurance = lid+"_"+str(pos)
					cur.execute("select word from "+self.src_table_name+" where word='"+src_word+"' and occurences='"+check_occurance+"'")
					if cur.rowcount==0:
						src_word_occurences.remove(fetched_pos)

			total_verses_src_word_occured = len(src_word_occurences)
			if total_verses_src_word_occured==0:
				total_verses_src_word_occured = 1

			

			cur.execute("select occurences  from "+self.trg_table_name+" where word='"+trg_word_array[0]+"'")
			trg_word_occurences = [x[0] for x in cur.fetchall()]
			for i,trg_word in enumerate(trg_word_array):
				if trg_word == ".":
					continue
				for fetched_pos in trg_word_occurences:
					lid = fetched_pos.split("_")[0]
					pos = int(fetched_pos.split("_")[1])
					pos = pos + i
					check_occurance = lid+"_"+str(pos)
					cur.execute("select word from "+self.trg_table_name+" where word='"+trg_word+"' and occurences='"+check_occurance+"'")
					if cur.rowcount==0:
						trg_word_occurences.remove(fetched_pos)

			src_lids = [x.split("_")[0] for x in src_word_occurences]
			trg_lids = [x.split("_")[0] for x in trg_word_occurences]
			
			co_occurence_lid_set = set(src_lids).intersection(set(trg_lids))
			total_verses_trg_word_cooccured = len(co_occurence_lid_set)
			
			co_occurence_pospair_set =[]
			for x,y in itertools.product(src_word_occurences,trg_word_occurences):
				if x.split("_")[0]==y.split("_")[0]:
					co_occurence_pospair_set.append((x,y))
			


			cur.execute("SELECT distinct lid from "+self.alignment_table_name)
			verses_in_aligned_table = [str(x[0]) for x in cur.fetchall()]
			total_cooccurance_verses_INalignedtable = len(co_occurence_lid_set.intersection(set(verses_in_aligned_table)))

			
			if total_cooccurance_verses_INalignedtable==0:
				total_cooccurance_verses_INalignedtable = 1
			
			total_verses_src_trg_aligned = 0
			verses_src_trg_aligned = []
			for pos_pair in co_occurence_pospair_set:
				cur.execute("SELECT lid from "+self.alignment_table_name+" WHERE source_wordID='"+pos_pair[0]+"' and target_wordID='"+pos_pair[1]+"'")
				if cur.rowcount>0:
					verses_src_trg_aligned.append(cur.fetchone()[0])
			total_verses_src_trg_aligned = len(set(verses_src_trg_aligned))
			
			co_occurence_confidence = total_verses_trg_word_cooccured/total_verses_src_word_occured
			aligned_confidence = total_verses_src_trg_aligned / total_cooccurance_verses_INalignedtable
			confidence_score = 0.75*co_occurence_confidence + 0.25*aligned_confidence
	
			print(" ".join(src_word_array)+"---"+" ".join(trg_word_array)+":"+str(confidence_score))
			cur.execute("INSERT INTO "+self.FeedbackLookup_table_name+" (source_word,target_word,confidence_score) VALUES (%s,%s,%s)",
				(" ".join(src_word_array)," ".join(trg_word_array),confidence_score))
			self.db.commit()
			
		except Exception as e:
			print("Warning: word pair not inserted to look up table")
			print(e)



	def save_alignment(self,lid,word_pairs,user):
		cur = self.db.cursor()

		# cur.execute("show tables like '"+src+"_"+trg+"_%_alignment'")
		# read_only_tables = [x[0] for x in cur.fetchall()]
		# no_of_tables = len(read_only_tables)
		# print(read_only_tables)

		for pair in word_pairs:
			#calculate confidence

			cur.execute("INSERT INTO "+self.alignment_table_name+" (lid,source_wordID,target_wordID,user) VALUES (%s,%s,%s,'default')",
				(lid, pair[0],pair[1]))

		self.db.commit()


	


	def update_alignment_on_verse(self,lid_to_update):
		cur = self.db.cursor()

		# get source_word list and target list for the verse from concordance table
		cur.execute("SELECT word,occurences FROM "+self.src_table_name+" WHERE occurences LIKE '"+lid_to_update+"\_%'")
		src_word_list = []
		for row in cur.fetchall():
			src_word_list.append((row[0],row[1]))
		cur.execute("SELECT word,occurences FROM "+self.trg_table_name+" WHERE occurences LIKE '"+lid_to_update+"\_%'")
		trg_word_list = []
		for row in cur.fetchall():
			trg_word_list.append((row[0],row[1]))

		# for all source_words get _FeedbackLookup entry
		# and if entry present in trg_verse, add them to replacement_options
		replacement_options=[]
		mapped = []
		for i,s_wrd in enumerate(src_word_list):

			cur.execute("SELECT source_word, target_word FROM "+self.FeedbackLookup_table_name+" WHERE source_word like '"+s_wrd[0]+"%' ORDER BY  confidence_score DESC, CHAR_LENGTH(source_word) DESC")
			for row in cur.fetchall():
				drop = False
				mapped_src_word = row[0]
				mapped_trg_word = row[1]
				src_pos = []
				src_multiword_list = mapped_src_word.split(" ")
				for j,w in enumerate(src_multiword_list):
					if (i+j)<len(src_word_list) and  src_word_list[i+j][0]==w :
						src_pos.append(src_word_list[i+j][1])
					elif (i+j)<len(src_word_list) and w==".":
						pass
					else:
						drop=True
				
				if drop:
					break

				trg_multiword_list = mapped_trg_word.split(" ")
				trg_pos = []
				for i,t_wrd in enumerate(trg_word_list):
					if t_wrd[1] in mapped:
						continue
					temp_trg_pos = []
					drop = False
					for j,w in enumerate(trg_multiword_list):
						if (i+j)<len(trg_word_list) and  trg_word_list[i+j][0] == w :
							temp_trg_pos.append(trg_word_list[i+j][1])
						elif (i+j)<len(trg_word_list) and w==".":
							pass
						else:
							temp_trg_pos = []
							drop = True
							break
					if not drop:
						trg_pos = temp_trg_pos
						break
				if drop:
					break



				for i,j in itertools.product(src_pos,trg_pos):
					replacement_options.append((i,j))
					mapped.append(j)
					drop = True
				# print('replacement_options'+str(replacement_options))
				if drop:
					break

		print(replacement_options)



		#update the alignment table
		for pair in replacement_options:
			cur.execute("DELETE FROM "+self.alignment_table_name+"  WHERE source_wordID='"+pair[0]+"'")

			cur.execute("DELETE FROM "+self.alignment_table_name+"  WHERE target_wordID='"+pair[1]+"'")

		for pair in replacement_options:

			cur.execute("INSERT INTO "+self.alignment_table_name+" (lid,source_wordID,target_wordID,user) VALUES (%s,%s,%s,'default')",
				(lid_to_update, pair[0],pair[1]))

		self.db.commit()

			
	def get_suggested_feedback_alignment_on_verse(self,lid_to_update):
		cur = self.db.cursor()

		# get source_word list and target list for the verse from concordance table
		cur.execute("SELECT word,occurences FROM "+self.src_table_name+" WHERE occurences LIKE '"+lid_to_update+"\_%'")
		src_word_list = []
		for row in cur.fetchall():
			src_word_list.append((row[0],row[1]))
		cur.execute("SELECT word,occurences FROM "+self.trg_table_name+" WHERE occurences LIKE '"+lid_to_update+"\_%'")
		trg_word_list = []
		for row in cur.fetchall():
			trg_word_list.append((row[0],row[1]))

		# for all source_words get _FeedbackLookup entry
		# and if entry present in trg_verse, add them to replacement_options
		replacement_options=[]
		mapped = []
		for i,s_wrd in enumerate(src_word_list):

			cur.execute("SELECT source_word, target_word FROM "+self.FeedbackLookup_table_name+" WHERE source_word like '"+s_wrd[0]+"%' ORDER BY  confidence_score DESC, CHAR_LENGTH(source_word) DESC")
			for row in cur.fetchall():
				drop = False
				mapped_src_word = row[0]
				mapped_trg_word = row[1]
				src_pos = []
				src_multiword_list = mapped_src_word.split(" ")
				for j,w in enumerate(src_multiword_list):
					if (i+j)<len(src_word_list) and  src_word_list[i+j][0]==w :
						src_pos.append(src_word_list[i+j][1])
					elif (i+j)<len(src_word_list) and w==".":
						pass
					else:
						drop=True
				
				if drop:
					break

				trg_multiword_list = mapped_trg_word.split(" ")
				trg_pos = []
				for i,t_wrd in enumerate(trg_word_list):
					if t_wrd[1] in mapped:
						continue
					temp_trg_pos = []
					drop = False
					for j,w in enumerate(trg_multiword_list):
						if (i+j)<len(trg_word_list) and  trg_word_list[i+j][0] == w :
							temp_trg_pos.append(trg_word_list[i+j][1])
						elif (i+j)<len(trg_word_list) and w==".":
							pass
						else:
							temp_trg_pos = []
							drop = True
							break
					if not drop:
						trg_pos = temp_trg_pos
						break
				if drop:
					break



				for i,j in itertools.product(src_pos,trg_pos):
					replacement_options.append((i,j))
					mapped.append(j)
					drop = True
				# print('replacement_options'+str(replacement_options))
				if drop:
					break

		# print(replacement_options)



		return replacement_options
		


		




	def fetch_alignment(self,lid,auto_alignmenttable):
		cur = self.db.cursor()

		# get source_word list and target list for the verse from concordance table
		cur.execute("SELECT word,occurences FROM "+self.src_table_name+" WHERE occurences LIKE '"+lid+"\_%'")
		src_word_list = []
		for row in cur.fetchall():
			src_word_list.append((row[0],row[1]))
		

		cur.execute("SELECT word,occurences FROM "+self.trg_table_name+" WHERE occurences LIKE '"+lid+"\_%'")
		trg_word_list = []
		for row in cur.fetchall():
			trg_word_list.append((row[0],row[1]))

		
		# get aligned Eng(ULB) text for src(Greek)
		temp_src_word_list = src_word_list
		src_word_list = []
		for i,src_pair in enumerate(temp_src_word_list):
			
			# cur.execute("SELECT a.lid FROM bcv_lid_map_7957 as a INNER JOIN bcv_lid_map_7914 as b on a.bcv =b.bcv where b.lid=LEFT('"+src_pair[1]+"',5)")
			cur.execute("SELECT a.lid FROM bcv_lid_map as a INNER JOIN bcv_lid_map_7914 as b on a.bcv =b.bcv where b.lid=LEFT('"+src_pair[1]+"',5)")

			lid_7957set = cur.fetchone()[0]


			cur.execute("SELECT english FROM lid_lxn_grk_eng WHERE lid = '"+str(lid_7957set)+"' and strong = CONCAT('g',LPAD('"+src_pair[0]+"',4,'0'),'0') ")
			# print("SELECT english FROM lid_lxn_grk_eng WHERE lid = '"+str(lid_7957set)+"' and strong = CONCAT('g',LPAD('"+src_pair[0]+"',4,'0'),'0') ")
			query_result = cur.fetchall()
			if len(query_result)==0:
				src_word_list.append((src_pair[0],src_pair[1],"--"))
			elif len(query_result)==1:
				src_word_list.append((src_pair[0],src_pair[1],query_result[0]))
			else:
				eng_list = [x[0] for x in query_result]
				strng_in_src_list = []
				for j,pair in enumerate(temp_src_word_list):
					if pair[0] == src_pair[0]:
						strng_in_src_list.append(j)
				# print("eng_list:"+str(eng_list))
				# print("strng_in_src_list:"+str(strng_in_src_list))
				# print("i:"+str(i))
				if strng_in_src_list.index(i) < len(eng_list): 
					aligned_eng = eng_list[strng_in_src_list.index(i)]
					src_word_list.append((src_pair[0],src_pair[1],aligned_eng))
				else:
					# not the correct solution. but added to remove the unexplained error
					src_word_list.append((src_pair[0],src_pair[1],query_result[0]))	




		# get the alignments from specified table
		cur.execute("SELECT * from "+auto_alignmenttable+" WHERE lid='"+lid+"'")
		auto_alignments = cur.fetchall()
		
		# get the alignments from master table, if present
		cur.execute("SELECT * from "+self.alignment_table_name+" WHERE lid='"+lid+"'")
		corrected_alignments = cur.fetchall()
		
		# for all source_words get _FeedbackLookup entry
		# and if entry present in trg_verse, add them to replacement_options
		replacement_options=self.get_suggested_feedback_alignment_on_verse(lid)
		
		
		return src_word_list, trg_word_list, auto_alignments, corrected_alignments, replacement_options
	


	def on_approve_feedback(self,corrected_src_trg_word_list):
		for src_trg in corrected_src_trg_word_list:
			src_word_to_update=src_trg[0]
			trg_word_to_update=src_trg[1]

			self.insert_into_lookup_table(src_word_to_update,trg_word_to_update)

			# self.update_all_alignment_by_word(src_word_to_update)


	def fetch_aligned_TWs(self,tw_index,strong_list,refs_list,cur):
		LIDs_dict = {}
		BCVs_dict = {}
		strong_list_edited = [x[1:] for x in strong_list]
		
		return_list = {}
		
		try:
			for bcv in refs_list:
				cur.execute("select lid from bcv_lid_map_7914 where bcv='"+bcv+"'")
				if cur.rowcount>0:
					lid = cur.fetchone()[0]
					# print("lid:"+str(lid))
					LIDs_dict[bcv] = lid
					BCVs_dict[lid] = bcv
			LIDs_list = BCVs_dict.keys()
			BCVs_list = LIDs_dict.keys()
			for l in LIDs_list:
				cur.execute("select occurences, word from "+self.src_table_name+" where occurences like '"+str(l)+"%'")
				source_words = [(x[0],x[1]) for x in cur.fetchall() ]

				cur.execute("select occurences, word from "+self.trg_table_name+" where occurences like '"+str(l)+"%'")
				target_words = [(x[0],x[1]) for x in cur.fetchall() ]

				# print("source_words:"+str(source_words))
				# print("target_words:"+str(target_words))


				present_strongs = []
				aligned_trg_occs = {}
				for wrd in source_words:
					if wrd[1] in strong_list_edited:
						present_strongs.append(wrd)
				present_strongs.sort()

				if (len(present_strongs)>0):
					
					for ps in present_strongs: 

						cur.execute("select target_wordID,word from "+self.alignment_table_name+" , "+self.trg_table_name+" where source_wordID='"+ps[0]+"' and occurences=target_wordID order by target_wordID")
						# if cur.rowcount > 0 :
						# print(cur.fetchall())
						retrived = [(x[0],x[1]) for x in cur.fetchall()]
						if len(retrived)>0:
								if BCVs_dict[l] in return_list:
									# print("***********Came here once************")
									return_list[BCVs_dict[l] ]["strongs"].append(ps)
									return_list[BCVs_dict[l] ]["target"] += retrived
									# print()
								else:
									return_list[BCVs_dict[l]] = {}
									return_list[BCVs_dict[l] ]["strongs"] = [ps]
									return_list[BCVs_dict[l] ]["target"] = retrived
							
				if BCVs_dict[l] in return_list:
					temp_trg = return_list[BCVs_dict[l] ]["target"]
					temp_strongs = return_list[BCVs_dict[l] ]["strongs"]
					trg_string = ""
					pre_pos = -1
					for trg in temp_trg:
						pos = int(trg[0].split("_")[1])
						if pre_pos != -1:
							for i in range(pre_pos,pos):
								trg_string += " ."
						trg_string += " " +trg[1]
						pre_pos = pos
					trg_string = trg_string.strip()

					strongs_string = ""
					pre_pos = -1
					for strongs in temp_strongs:
						pos = int(strongs[0].split("_")[1])
						if pre_pos != -1:
							for i in range(pre_pos,pos):
								strongs_string += " ."
						strongs_string += " " +strongs[1]
						pre_pos = pos
					strongs_string = strongs_string.strip()
					# print(trg_string+" --- "+strongs_string)
					

					return_list[BCVs_dict[l] ]=str((strongs_string,trg_string))




					 
		except Exception as e:
			print(temp_trg)
			raise e
		


		return return_list




	def fetch_all_TW_alignments(self):
		cur = self.db.cursor()

		return_dict_of_aligned_words = {}
		for tw in TWs:
			strong_list = TWs[tw]["strongs"]
			refs_list = TWs[tw]["References"]
			return_list = self.fetch_aligned_TWs(tw,strong_list,refs_list,cur)
			return_dict_of_aligned_words[str(tw)] = return_list
			# print(return_dict_of_aligned_words)
			# if tw==2:
			# 	break

		cur.close()
		return json.dumps(return_dict_of_aligned_words,  ensure_ascii=False)
		# return return_dict_of_aligned_words

	def fetch_seleted_TW_alignments(self,tw_index_list):
		cur = self.db.cursor()

		return_dict_of_aligned_words = {}
		for tw in tw_index_list:
			strong_list = TWs[tw]["strongs"]
			refs_list = TWs[tw]["References"]
			return_list = self.fetch_aligned_TWs(tw,strong_list,refs_list,cur)
			return_dict_of_aligned_words[str(tw)] = return_list
			# print(return_dict_of_aligned_words)
			# if tw==2:
			# 	break

		cur.close()
		return json.dumps(return_dict_of_aligned_words,  ensure_ascii=False)





if __name__ == '__main__':
	if len(sys.argv)==3:
		src = sys.argv[1]
		trg = sys.argv[2]

	else:
		print("Usage: python3 FeedbackAligner.py src trg\n(src,trg - 3 letter lang codes\n")
		sys.exit(0)


	# connection =  pymysql.connect(host="localhost",    # your host, usually localhost
	#                      user="root",         # your username
	#                      password="password",  # your password
	#                      database="itl_db",
	#                      charset='utf8mb4')

	connection =  pymysql.connect(host="103.196.222.37",    # your host, usually localhost
	                     user="bcs_vo_owner",         # your username
	                     password="bcs@0pen",  # your password
	                     database="bcs_vachan_engine_test",
	                     port=13306,
	                     charset='utf8mb4')
		

	master_table = src+"_"+trg+"_alignment"
	obj = FeedbackAligner(connection, src,trg,master_table)

	start = time.clock()
	
	# obj.on_approve_feedback([("2424 5547","यीशु मसीह"),("5207","सन्तान"),("5257 5547","मसीह . सेवक")])

	src_word_list, trg_word_list, auto_alignments, corrected_alignments, replacement_options = obj.fetch_alignment('26021','grk_hin_sw_stm_ne_giza_tw__alignment')
	# print("src_word_list:"+str(src_word_list))
	# print("trg_word_list:"+str(trg_word_list))
	print("auto_alignments:"+str(auto_alignments))
	print("corrected_alignments:"+str(corrected_alignments))
	# print("replacement_options:"+str(replacement_options))




	# obj.update_alignment_on_verse('23146')
	
	# obj.save_alignment(123,[("xxx","YYY")],'testcase')

	# TW_alignments = obj.fetch_all_TW_alignments()
	# TW_alignments = obj.fetch_seleted_TW_alignments([1,2,3,4,5])

	# TW_alignments = obj.fetch_seleted_TW_alignments(range(1,6))

	# print(TW_alignments)

	print("Time taken:"+str(time.clock()-start))
	del obj