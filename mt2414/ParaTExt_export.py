import pymysql,codecs

host="localhost"    # your host, usually localhost
user="root"         # your username
password="password"  # your password
database="AutographaMT_Staging"






query = '''select Book, Chapter, Verse, LidSrc, PositionSrc, WordSrc, LidTrg, PositionTrg, Strongs 
from {} left join Bcv_LidMap on LidSrc=Bcv_LidMap.ID 
order by LidSrc, PositionSrc;'''

xml_header = '''<?xml version="1.0"?>

<Mappings xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
'''
xml_footer = '''</Mappings>'''
xml_content_template = '''  <Mapping Reference="{}" Warning="false" Verified="false" Proposed="false" BeyondVerse="false">

    <SourceLinks>

      <SourceLink Word="{}" Strong="{}" Index="{}"></SourceLink>

    </SourceLinks>

    <TargetLinks>

      <TargetLink>{}</TargetLink>

    </TargetLinks>

  </Mapping>
'''

def export(conn,table):
	cur = conn.cursor()
	dynamic_query = query.format(table)
	cur.execute(dynamic_query)
	# print(query_result)

	next_row = cur.fetchone()
	prev_lid = None


	output_string = xml_header
	verse_buffer = []
	while(next_row):
		LidSrc = next_row[3]
		LidTrg = next_row[6]
		if LidSrc != LidTrg:
			print('SKIPPING an alignment: Across Verses')
			next_row = cur.fetchone()
			continue


		Book = next_row[0]
		Chapter = next_row[1]
		Verse = next_row[2]
		PositionSrc = next_row[4]
		WordSrc = next_row[5]
		Strongs = next_row[8]
		PositionTrg = next_row[7] 

		index = 0
		if LidSrc!=prev_lid:
			prev_lid = LidSrc
			verse_buffer = [WordSrc]
		else:
			for w in verse_buffer:
				if w==WordSrc:
					index += 1
			verse_buffer.append(WordSrc)

		Reference=str(Book).zfill(3)+str(Chapter).zfill(3)+str(Verse).zfill(3)+"00"
		Word=str(WordSrc)
		Strong="G"+str(Strongs).zfill(4)
		Index=str(index)
		TargetLink=str(Book).zfill(3)+str(Chapter).zfill(3)+str(Verse).zfill(3)+"00"+str(PositionTrg*2).zfill(3)

		filled_template = xml_content_template.format(Reference,Word,Strong,Index,TargetLink)

		output_string += filled_template

		next_row = cur.fetchone()
		# break
	output_string += xml_footer
	cur.close()
	return output_string



if __name__ == '__main__':
	db = pymysql.connect(host=host,   
		                     user=user, 
		                     password=password, 
		                     database=database,
		                     charset='utf8mb4')
	tablename = "Tel_5_Grk_UGNT4_Alignment"
	output_string = export(db,tablename)

	db.close()
	file='ParaTExt_export.xml'
	outfile = codecs.open(file,mode='w',encoding='utf-8')
	outfile.write(output_string)
	outfile.close()