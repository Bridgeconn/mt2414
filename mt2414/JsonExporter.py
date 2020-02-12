import time
import json

class JsonExporter:

    def __init__(self, db, src_bible_words_table, trg_bible_words_table, bookcode, book, tablename, usfmFlag):
        self.db = db.cursor()
        self.src, self.sVer = src_bible_words_table.split("_")[0:2]
        self.trg, self.tVer = trg_bible_words_table.split("_")[0:2]
        self.tablename = tablename
        self.src_bible_words_table = src_bible_words_table
        self.trg_bible_words_table = trg_bible_words_table
        self.book = book
        self.bc = int(bookcode)
        self.usfmFlag = None


    def alignmentarrayelements(self, a_list):
        '''Alignment Array for a verse'''
        alignmentArrayList = []
        for i in range(len(a_list[0])):
            alignmentArrayelement = {
                "score": a_list[0][i],
                "r0": a_list[1][i][0],
                "r1": a_list[1][i][1],
                "verified": a_list[2][i]
            }
            alignmentArrayList.append(alignmentArrayelement)
        return alignmentArrayList


    def segmentResourceValue(self, r_list):
        '''Individual resource element'''
        metadata = {
            "contextId": r_list[0]
        }
        if r_list[2] == []:
            value = {
                "text": r_list[1],
                "tokens": r_list[1].split(' '),
                "metadata": metadata
            }
        else:
            value = {
                "text": r_list[1],
                "tokens": r_list[1].split(' '),
                "metadata": metadata,
                "usfm": r_list[2]
            }

        return value


    def segmentResourceArray(self, r_list):
        '''Resource Array for a verse'''
        resources = {
            "r0": self.segmentResourceValue([r_list[0], r_list[1], []]),
            "r1": self.segmentResourceValue([r_list[0], r_list[2], r_list[3]])
        }
        return resources


    def generateSegmentList(self, s_list):
        '''Argument contains verse id, resource texts, alignments list and alignment verified list'''
        resources = self.segmentResourceArray(s_list[0])
        alignments = self.alignmentarrayelements(s_list[1])
        return (resources, alignments)


    def segmentArrayElements(self, s_list):
        '''List of resources and alignment tuple'''
        segmentArrayList = []
        for item in s_list:
            value = self.generateSegmentList(item)
            segmentArrayelement = {
                "resources": value[0],
                "alignments": value[1]
            }
            segmentArrayList.append(segmentArrayelement)
        return segmentArrayList


    def metadataResources(self, m_list):
        value = {
            "languageCode": m_list[0],
            "name": m_list[1],
            "version": m_list[2]
        }
        return value


    def metadataArray(self, m_list):
        resources = {
            'r0': self.metadataResources(m_list[0]),
            'r1': self.metadataResources(m_list[1])
        }
        metadata = {
            "resources": resources,
            "modified": int(time.time())
        }
        return metadata


    def generateVerseInPositionOrderList(self, value):
        text_list = ['' for i in range(len(value))]
        for item in value:
            index = item[0]
            text_list[int(index) - 1] = str(item[1])
        return text_list


    def generatePositionalPairsList(self, align_rst):
        '''Create positional pairs dict with LID as key'''
        stage_dict = {}
        positional_pairs = {}
        for item in align_rst:
            pos_pair = str(item[1]) + '-' + str(item[3])
            if item[0] in positional_pairs:
                positional_pairs[item[0]] = positional_pairs[item[0]]  + [pos_pair]
            else:
                positional_pairs[item[0]] = [pos_pair]
            stage_dict[item[0]] = item[5]
        return (positional_pairs, stage_dict)


    def getPhraseBasedAlignmentData(self, positional_pairs):
        '''
        Creates positional pairs by checking for phrases.
        '''
        alignment_dict = {}
        for lid in self.lid_dict.keys():
            align_list = []
            temp_dict = {}
            reverse_temp_dict = {}
            if lid in positional_pairs:
                v = positional_pairs[lid]
                for item in v:
                    s, t = item.split('-')
                    if s in temp_dict:
                        temp_dict[s] = temp_dict[s] + [t]
                    else:
                        temp_dict[s] = [t]
                for r0, r1 in temp_dict.items():
                    key = str(r0)
                    value = ' '.join(str(x) for x in r1)
                    if value in reverse_temp_dict:
                        reverse_temp_dict[value] = reverse_temp_dict[value] + ' ' + key
                    else:
                        reverse_temp_dict[value] = key

                for ky, val in reverse_temp_dict.items():
                    value1 = []
                    for i in ky.split(' '):
                        if i != '255':
                            value1.append(int(i) - 1)
                    value2 = []
                    for j in val.split(' '):
                        if j != '255':
                            value2.append(int(j) - 1)

                    align_list.append([value1, value2])
                alignment_dict[lid] = align_list
        return alignment_dict


    def getBooksLids(self, bookname):
        '''Create LID BCV Dict for a specific book'''

        lid_dict = {}
        self.db.execute("SELECT ID, Book, Chapter, Verse FROM Bcv_LidMap WHERE Book = %s", (bookname,))
        lid_rst = self.db.fetchall()
        for l,b,c,v in lid_rst:
            lid_dict[l] = str(b) + str(c).zfill(3) + str(v).zfill(3)
        return lid_dict        


    def getDataFromDB(self, db_fields, tablename, db_param=None, low=None, high=None):
        '''
        Fetches Data from DB from an LID range. taking the db fields and parameters as arguments
        '''

        if db_param != None:
            param = " WHERE " + db_param + " >= " + str(low) + " AND " + db_param + " < " + str(high)
        else:
            param = ""
        self.db.execute("SELECT " + db_fields + " FROM " + tablename + param)
        align_rst = self.db.fetchall()
        return align_rst


    def generateTextDictFromDbData(self, dbData):
        '''
        Generate LID text Dict From position and word data
        '''

        lidPositionWordDict = {}
        for item in dbData:
            if item[0] in lidPositionWordDict:
                lidPositionWordDict[item[0]] = lidPositionWordDict[item[0]] + [(item[1], item[2])]
            else:
                lidPositionWordDict[item[0]] = [(item[1], item[2])]
        lidTextDict = {}     
        for key in lidPositionWordDict.keys():
            lidTextDict[key] = " ".join(self.generateVerseInPositionOrderList(lidPositionWordDict[key]))
        return lidTextDict


    def exportAlignments(self):
        '''
        Main method to export alignments
        '''
        self.lid_dict = self.getBooksLids(self.bc)
        bcv_dict = {v:k for k,v in self.lid_dict.items()}

        # Generate Range for the book selected
        low = bcv_dict[sorted(list(bcv_dict.keys()))[0]]
        high = low + 1000

        alignedDataFromDB = self.getDataFromDB('LidSrc, PositionSrc, WordSrc, PositionTrg, Strongs, Stage', \
        self.tablename, 'LidSrc', low, high)

        positional_pairs, stage_dict = self.generatePositionalPairsList(alignedDataFromDB)

        # Fetch Source word list from chopped Bible

        src_rst = self.getDataFromDB('LID, Position, Word', self.src_bible_words_table, 'LID', low, high)
        trg_rst = self.getDataFromDB('LID, Position, Word', self.trg_bible_words_table, 'LID', low, high)

        generated_src_text_dict = self.generateTextDictFromDbData(src_rst)
        generated_trg_text_dict = self.generateTextDictFromDbData(trg_rst)


        alignment_dict = self.getPhraseBasedAlignmentData(positional_pairs)

        j_list1 = [[self.trg, self.tVer, '0.1'], [self.src, self.sVer, '0.1']]

        j_list2 = []

        for item in sorted(alignment_dict.keys()):
            bcv = self.lid_dict[item]

            if item in generated_trg_text_dict:
                trg_text = generated_trg_text_dict[item].strip()
            else:
                trg_text = ""


            if item in generated_src_text_dict:
                src_text = generated_src_text_dict[item].strip()
            else:
                src_text = ""


            alignments = alignment_dict[item]
            source_list = [0 for i in range(len(alignments))]

            if stage_dict[item] == 1:
                verified_list = [True for i in range(len(alignments))]
            else:
                verified_list = [False for i in range(len(alignments))]


            contextId = str(bcv)[-6:]
            contextId = self.book.upper() + contextId


            j_list2.append([[contextId, trg_text, src_text, []], [source_list, alignments, verified_list]])


        j_list = [j_list1] + [j_list2]

        metadata = self.metadataArray(j_list[0])
        segments = self.segmentArrayElements(j_list[1])

        json_text = json.dumps({
            "metadata": metadata,
            "conformsTo": "alignment-0.1",
            "segments": segments
            }, ensure_ascii=False)

        self.db.close()

        return json_text



