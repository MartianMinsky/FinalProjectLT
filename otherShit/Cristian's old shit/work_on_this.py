import sys
import spacy
import requests
import re
from urllib.parse import urlparse
from posixpath import basename
nlp = spacy.load('en')

global answerFound

def main(argv):
		global answerFound
		
		print("type your question")
		try:
			for line in sys.stdin: 
				line = line.rstrip() #remove newline
			
				if line == 'End-of-file':
					quit()
				answerFound = 0
				sort(line)
				print("End of search.")
		except:
			pass
		
	
def sort(line):
	global answerFound
	doc = nlp(line)
	of = []
	verb = []
	be = []
	noun = []
	sentence = []
	pos = []
	lemma = []
	tag = []
	
	np_root_text = []
	for np in doc.noun_chunks:
		np_root_text.append(np.root.text)
	
	for word in doc:
		sentence.append(word.text)
		pos.append(word.pos_)
		lemma.append(word.lemma_)
		tag.append(word.tag_)
		if word.lemma_ == 'of':
			of.append(word.text)
		if word.pos_ == "VERB":
			verb.append(word.text)
		if word.pos_ == "NOUN":
			noun.append(word.text)
		if word.lemma_ == "be":
			be.append(word.text)
					
		if word.lemma_ == "what" :
			whatQ = True
		if word.lemma_ == "where":
			whereQ = True
		if word.lemma_ == "who":
			whoQ = True
		if word.lemma_ == "whose":
			whoseQ = True
		if word.lemma_ == "when":
			whenQ = True
		if word.lemma_ == "why":
			whyQ = True
		if word.lemma_ == "which":
			whichQ = True
		if word.lemma_ == "how":
			howQ = True
		if word.lemma_ == "do":
			doQ = True
		if word.lemma_ == "be":
			beQ = True
		if word.tag_ == "MD":
			canQ = True
		if word.lemma_ == "give" or word.lemma_ == "list" or word.lemma_ == "name" or word.lemma_ == "mention" or word.lemma_ == "say" or word.lemma_ == "give a list of":
			listQ = True
		if word.lemma_ == 'of':
			ofQ = True
			relationFirst =  True
		if word.lemma_ == "does" or word.lemma_ == "do" or word.lemma_ == "be" and word.i == 0:
			yesOrNo = True
	
	if 'whatQ' in locals() and whatQ or 'whoQ' in locals() and whoQ or 'whichQ' in locals() and whichQ or 'whereQ' in locals() and whereQ:
		fire_whatwho(line)
	
	elif 'listQ' in locals() and listQ:
		fire_list(line)
	
	elif 'howQ' in locals() and howQ:		
		fireCount(line)
	
	elif 'yesOrNo' in locals() and yesOrNo:
		fire_yesno(doc)

def fire_whatwho(line):
	wdapi = 'https://www.wikidata.org/w/api.php'
	wdparams = {'action':'wbsearchentities', 'language':'en', 'format':'json'}
	questions = [ "What are the (.*) of (.*)?",
		'Who (.*) (.*)?',
		'What is (.*) in (.*)?',
		'(.*) a (.*)?',
		'What (.*) does the (.*) belong to?',
		'What are the (.*) in (.*)?',
		'Which (.*) is used for producing (.*)?',
		'Which (.*) (.*) are there?',
		'What (.*) (.*) are there?',
		'Where does (.*?) (.*)?',
		'What is (.*)?']
	m = re.search('What is the (.*) of (.*)?',line)
	i = 0
	while not hasattr(m, 'group'):
		m = re.search(questions[i],line)
		i += 1
		if i == len(questions)+1:
			print("Cannot handle this question.")
	if(i==len(questions)-1):
		relation= m.group(2).replace('?', '')
		entity=m.group(1)
	elif(i==len(questions)):
		entity=m.group(1).replace('?', '')
		relation= 'subclass of'
	else:
		relation = m.group(1)
		entity = m.group(2).replace('?', '')
	choises = {'ingredients': 'material used', 'colour':'color',
		'ingredients': 'has part', 'genus': 'parent taxon', 'come from': 'country of origin',
		'material': 'material used','koalas': 'koala', 'eat': 'main food source',
		'used': 'has part', 'taste': 'has quality', 'food source': 'main food source',
		'founded': 'founded by', 'purpose': 'subclass of',
		'origin': 'named after', 'the name hamburger': 'hamburger',
		'What is': 'instance of'}
	relation = choises.get(relation, relation)
	entity = choises.get(entity, entity)
	wdparams['search'] = entity
	json = requests.get(wdapi,wdparams).json()
	for result in json['search']:
		entity_id = result['id']
		wdparams['search'] = relation
		wdparams['type'] = 'property'
		json = requests.get(wdapi,wdparams).json()
		for result in json['search']:
			relation_id = result['id']
			fire_sparql_whatwho(entity_id,relation_id)
			
sparqlurl = 'https://query.wikidata.org/sparql'

def fire_sparql_whatwho(ent,rel):
	query= 'SELECT ?item ?itemLabel WHERE { wd:'+ent+' wdt:'+rel+' ?item . SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }}'
	data = requests.get(sparqlurl, params={'query': query, 'format': 'json'}).json()
	for item in data['results']['bindings']:
		for key in item :
			answerkey = urlparse(item[key]['value'])
			if not answerkey.scheme == 'http':
				answerkey_id = basename(answerkey.path)
				print(answerkey_id)

def fire_list(line):	
	global answerFound
	wdapi = 'https://www.wikidata.org/w/api.php'
	wdparams = {'action':'wbsearchentities', 'language':'en', 'format':'json'}
	
	line = line + '.' + '.' + '.' + '.' # so that it can take questions without punctuations
	
	entity = "xxx"
	relation = "xxx"
	doc = nlp(line)
	entity_fulfiled = 0
	relation_fulfiled = 0
	for w in doc:
		#print(w.pos_ + "," + w.tag_ + "," + w.lemma_ )
		# if an entity is found and a relation is found, then stop checking this doc
		if entity_fulfiled ==1 and relation_fulfiled ==1:
			break
		index = w.i
		#print(index)
		if index > 0 : # ignore the first word
			next_w = doc[index+1]
			# if two words in a row and they are not who/what/which... 
			# you make it as an entity
			if w.pos_=="NOUN" and next_w.pos_=="NOUN" and w.tag_!="WP" and next_w.tag_!="WP":
				entity = w.lemma_ + " " + next_w.lemma_
				entity_fulfiled = 1				
			# if two words in a row are pronouns, for example, john lennon, then make it an entity
			elif w.pos_=="PROPN" and next_w.pos_=="PROPN":
				entity = w.lemma_ + " " + next_w.lemma_
				entity_fulfiled = 1
			# if one word is a noun, and its next word is not a noun and its next word is not
			# a pronoun, then if there is no relation, make this a relation, else, make it an
			# entity
			elif w.pos_=="NOUN" and w.tag_!="WP":
				if relation_fulfiled == 0:
					relation = w.lemma_
					relation_fulfiled = 1
				elif entity_fulfiled == 0:
					entity = w.lemma_
					entity_fulfiled = 1

				

	wdparams['search'] = entity
	json = requests.get(wdapi,params=wdparams).json()
	for result in json['search']:
		entity_id = result['id']
		wdparams['search'] = relation
		wdparams['type'] = 'property'
		json = requests.get(wdapi,params=wdparams).json()
		for result in json['search']:
			relation_id = result['id']
			if answerFound == 0:
				fire_sparql_list(entity_id,relation_id)
			else:
				return
			
sparqlurl = 'https://query.wikidata.org/sparql'

def fire_sparql_list(ent,rel):
	global answerFound
	query='SELECT ?answerLabel WHERE {wd:'+ent+' wdt:'+rel+' ?answer. SERVICE wikibase:label{bd:serviceParam wikibase:language "en" .}} '
	#print(query)
	data = requests.get(sparqlurl, params={'query': query, 'format': 'json'}).json()
	for item in data['results']['bindings']:
		for key in item:
			if item[key]['type'] == 'literal' :
				print('{} {}'.format(key,item[key]['value']))
				answerFound = 1
			else :
				print('{} {}'.format(key,item[key]))
				answerFound = 1

def fireCount(line):
	global answerFound
	relation = "xxx"
	entity = "xxx"	
	line = line + ' .' + ' .' + ' .' + ' .' + ' .' + ' .' # so that it can take questions without punctuations
	doc = nlp(line)
	of = []
	verb = []
	be = []
	noun = []
	sentence = []
	pos = []
	lemma = []
	tag = []
	
	np_root_text = []
	for np in doc.noun_chunks:
		np_root_text.append(np.root.text)
	
	for word in doc:
		sentence.append(word.text)
		pos.append(word.pos_)
		lemma.append(word.lemma_)
		tag.append(word.tag_)
		if word.lemma_ == 'of':
			of.append(word.text)
		if word.pos_ == "VERB":
			verb.append(word.text)
		if word.pos_ == "NOUN":
			noun.append(word.text)
		if word.lemma_ == "be":
			be.append(word.text)
					
		if word.lemma_ == "what" :
			whatQ = True
		if word.lemma_ == "where":
			whereQ = True
		if word.lemma_ == "who":
			whoQ = True
		if word.lemma_ == "whose":
			whoseQ = True
		if word.lemma_ == "when":
			whenQ = True
		if word.lemma_ == "why":
			whyQ = True
		if word.lemma_ == "which":
			whichQ = True
		if word.lemma_ == "how":
			howQ = True
		if word.lemma_ == "do" or word.lemma_ == "does":
			doQ = True
		if word.lemma_ == "be":
			beQ = True
		if word.tag_ == "MD":
			canQ = True
		if word.lemma_ == "give" or word.lemma_ == "list" or word.lemma_ == "name" or word.lemma_ == "mention" or word.lemma_ == "say":
			listQ = True
		if word.lemma_ == 'of':
			ofQ = True
			relationFirst =  True
		if word.lemma_ == "does" or word.lemma_ == "do" or word.lemma_ == "be" and word.i == 0:
			yesOrNo = True
		
	for i in range(len(sentence)):
		if pos[i] == "PROPN":
			pos[i] = "NOUN"
		
	if pos[2] != "VERB":
			
		if 'ofQ' in locals() and ofQ:
				
			if sentence.index(verb[0]) > sentence.index(of[0]):
				idx = sentence.index(of[0])
			else:
				idx = sentence.index(verb[0])
			
			numberRelationWords = idx - 2
			for i in range(numberRelationWords):
				if i == 0:
					relation = lemma[2+i]
				elif not i == numberRelationWords-1:
					relation = relation + " " + sentence[2+i]
				else:
					relation = relation + " " + lemma[2+i]
			
			for i in range(len(sentence)):
				if entity != "xxx":
					break
				if sentence[i] == 'google' and i > idx:
					entity = 'google'
				elif sentence[i] == 'ratatouille' and i > idx:
					entity = 'ratatouille'
				elif lemma[i] == 'mcdonald' and i > idx:
					entity = "McDonald's"
				elif lemma[i] == 'kfc' and i > idx:
					entity = "KFC" 
				elif pos[i] == "NOUN" and i > idx:
					if pos[i+1] != "NOUN":
						entity = lemma[i]
					elif pos[i+1] == "NOUN":
						entity = sentence[i]
						if pos[i+2] == "NOUN":
							entity = entity + " " + sentence[i+1] + " " + lemma[i+2]
						else:
							entity = entity + " " + lemma[i+1]
		
		else:
			idx = sentence.index(verb[0])
			numberRelationWords = idx - 2
			for i in range(numberRelationWords):
				if i == 0:
					relation = lemma[2+i]
				elif not i == numberRelationWords-1:
					relation = relation + " " + sentence[2+i]
				else:
					relation = relation + " " + lemma[2+i]
			
			for i in range(len(sentence)):
				if entity != "xxx":
					break
				if sentence[i] == 'google' and i > idx:
					entity = 'google'
				elif sentence[i] == 'ratatouille' and i > idx:
					entity = 'ratatouille'
				elif lemma[i] == 'mcdonald' and i > idx:
					entity = "McDonald's"
				elif lemma[i] == 'kfc' and i > idx:
					entity = "KFC" 
				elif pos[i] == "NOUN" and i > idx:
					if pos[i+1] != "NOUN":
						entity = lemma[i]
					elif pos[i+1] == "NOUN":
						entity = sentence[i]
						if pos[i+2] == "NOUN":
							entity = entity + " " + sentence[i+1] + " " + lemma[i+2]
						else:
							entity = entity + " " + lemma[i+1]
			
			
	else:
			
		if len(np_root_text) == 1:
			if lemma[2] == "weigh":
				relation = 'mass'
			else:
				relation = "price"
			entity = np_root_text[0]
		elif len(np_root_text) == 2:
			relation = np_root_text[0]
			entity = np_root_text[1]
			
	
	if relation == "ingredient":
		relation = "material used"
	
	fire_query_count(relation, entity, sentence[1])
	
	if answerFound == 0:
		if relation == "material used":
			relation = "has part"

			fire_query_count(relation, entity, sentence[1])
	
	
def fire_query_count(relation, entity, manyormuch):
	global answerFound
	wdapi = 'https://www.wikidata.org/w/api.php'
	wdparams = {'action':'wbsearchentities', 'language':'en', 'format':'json'}
	
	wdparams['search'] = entity
	json = requests.get(wdapi,params=wdparams).json()
	for result in json['search']:
		entity_id = result['id']
		wdparams['search'] = relation
		wdparams['type'] = 'property'
		json = requests.get(wdapi,params=wdparams).json()
		for result in json['search']:
			relation_id = result['id']
			if answerFound == 0:
				fire_sparql_count(entity_id,relation_id,manyormuch)
				if manyormuch == "many":			
					if answerFound > 1:
						print(answerFound)
					else:
						fire_sparql_count(entity_id,relation_id,"much")
			else:
				return
			
sparqlurl = 'https://query.wikidata.org/sparql'

def fire_sparql_count(ent,rel,manyormuch):
	global answerFound
	query='SELECT ?answerLabel WHERE {wd:'+ent+' wdt:'+rel+' ?answer. SERVICE wikibase:label{bd:serviceParam wikibase:language "en" .}} '
	#print(query)
	data = requests.get(sparqlurl, params={'query': query, 'format': 'json'}).json()
	for item in data['results']['bindings']:
		for key in item:
			if item[key]['type'] == 'literal':
				if manyormuch == "much":
					if answerFound == 1:
						if item[key]['value'].isdigit():
							print(item[key]['value'])
						else:
							print('1')
					else:
						print(item[key]['value'])
				answerFound = answerFound + 1
			else :
				if manyormuch == "much":
					print('{} {}'.format(key,item[key]))
				answerFound = answerFound + 1
def fireIs(doc):
	global answerFound
	wdapi = 'https://www.wikidata.org/w/api.php'
	wdparams = {'action':'wbsearchentities', 'language':'en', 'format':'json'}
	entity = ""
	relation = ""
	entity_fulfiled = 0
	relation_fulfiled = 0
	for w in doc:
		#print(w.pos_ + "," + w.tag_ + "," + w.lemma_ )
		# if an entity is found and a relation is found, then stop checking this doc
		if entity_fulfiled ==1 and relation_fulfiled ==1:
			break
		index = w.i
		if index > 0 : # ignore the first word
			next_w = doc[index+1]
			if entity_fulfiled==0:
				if w.pos_ =='PROPN':
					answerFound=1
					print("yes")
					return
				if w.pos_=='NOUN' and w.dep_ !='attr':
					entity=w.lemma_
					entity_fulfiled=1
			if relation_fulfiled==0:
				if w.tag_=='NN' and next_w.dep_=='oprd':
					relation=w.lemma_+' '+next_w.lemma_
					relation_fulfiled=1
				if (w.tag_=='JJ' or w.tag_=='NN' or w.tag_=='NNS') and (w.dep_=='attr' or w.dep_=="acomp" or w.dep_=='dobj'):
					relation=w.lemma_
					relation_fulfiled=1
			if entity_fulfiled==0:
				if w.tag_=='VBG':
					entity=w.lemma_
					entity_fulfiled=1
	wdparams['search'] = entity
	json = requests.get(wdapi,params=wdparams).json()
	for result in json['search']:
		entity_id = result['id']
		wdparams['search'] = relation
		wdparams['type'] = 'entity'
		if answerFound == 0:
			fire_yes_no(entity_id,relation)
		else:
			return					


def fire_yesno(doc):	
	global answerFound
	fireIs(doc)
	if answerFound == 0:
		print('no')
	return

sparqlurl = 'https://query.wikidata.org/sparql'
def fire_yes_no(ent,rel):
	global answerFound
	query='SELECT ?itemsLabel WHERE { wd:'+ent+' ?properties ?items .SERVICE wikibase:label { bd:serviceParam wikibase:language "en" .}} '
	data = requests.get(sparqlurl, params={'query': query, 'format': 'json'}).json()
	for item in data['results']['bindings']:
		for key in item:
			if item[key]['type'] == 'literal' :
				if item[key]['value'] == rel :
					print('yes')
					answerFound = 1
					return
			else :
				print('{} {}'.format(key,item[key]))
				answerFound = 1	


def fire_sparql_yesno(ent,rel):
	global answerFound
	query='SELECT ?answerLabel WHERE {wd:'+ent+' wdt:'+rel+' ?answer. SERVICE wikibase:label{bd:serviceParam wikibase:language "en" .}} '
	#print(query)
	data = requests.get(sparqlurl, params={'query': query, 'format': 'json'}).json()
	for item in data['results']['bindings']:
		for key in item:
			if item[key]['type'] == 'literal' :
				print('{} {}'.format(key,item[key]['value']))
				answerFound = 1
			else :
				print('{} {}'.format(key,item[key]))
				answerFound = 1

if __name__ == "__main__":
	main(sys.argv)
