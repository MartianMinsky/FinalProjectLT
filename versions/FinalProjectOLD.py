#!/usr/bin/env python3
'''
By: Noam Zonca (s3482065),
Email: n.zonca@student.rug.nl
'''

import sys
import requests
import spacy
import re

def wikiDataAPI(item, type):
    url = 'https://www.wikidata.org/w/api.php'
    params = {'action':'wbsearchentities',
              'language':'en',
              'format':'json'}

    if (type == 'relation'):
        params['type'] = 'property'

    params['search'] = item
    json = requests.get(url,params).json()

    if (not json['search']):
        raise Exception('Did not find property or entity using API!')

    id = json['search'][0]['id']
    return id

def wikiDataAPILabel(item, type):
    url = 'https://www.wikidata.org/w/api.php'
    params = {'action':'wbsearchentities',
              'language':'en',
              'format':'json'}

    if (type == 'relation'):
        params['type'] = 'property'

    params['search'] = item
    json = requests.get(url,params).json()

    if (not json['search']):
        raise Exception('Did not find property or entity using API!')

    id = json['search'][0]['label']
    return id

def wikiDataQuery(item):
    query = '''
    SELECT ?val1 ?val2 WHERE {
      ?val1 rdfs:label "''' + item + '''"@en.
    }
    '''
    url = 'https://query.wikidata.org/sparql'

    data = requests.get(url, params={'query': query, 'format':'json'}).json()

    if (not data['results']['bindings']):
        raise Exception('Did not find property or entity using rdfs:label!')
    else:
        uri = data['results']['bindings'][0]['val1']['value']
    # only want the entity Q-number.
    result = re.search(r'Q\d+$', uri).group()
    return result

# questions of type: What is the X of Y?
def createRelationQuery(relation, entity):
    query = '''
    SELECT  ?answer ?answerLabel WHERE {
        wd:''' + entity + ''' wdt:''' + relation + ''' ?answer
        SERVICE wikibase:label {
            bd:serviceParam wikibase:language "en" .
        }
    }
    '''
    return query

def runQuery(query, type):
    url = 'https://query.wikidata.org/sparql'
    headers = {'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebkit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36'}
    data = None
    try:
        data = requests.get(url, headers=headers, params={'query': query, 'format':'json'}).json()
    except:
        print("Could not find an answer")
        return

    # disambiguate name of variable answer to the query is stored in.
    vars = data['head']['vars']
    # print(vars)
    answerSpot = 'answerLabel'

    final_results = []
    for item in data['results']['bindings']:
        final_results.append(item[answerSpot]['value'])

    if type == "relation":
        print(final_results)
    elif type in final_results:
        print("Yes")
    else:
        print("No")

# Run a query to get a description from an entity Y
def get_description(Y):
    url = 'https://query.wikidata.org/sparql'
    query = '''SELECT ?label WHERE {wd:''' + Y + ''' schema:description ?label.
                    FILTER(LANG(?label) = "en")
                     }
    '''
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebkit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36'
    }
    data = requests.get(url, headers=headers, params={'query': query, 'format':'json'}).json()
    result = []
    for item in data['results']['bindings']:
        # print(item['label']['value'])
        result.append(item['label']['value'])
    return " ".join(result)

# Responsible for understanding the quesion type, calling the mapping functions,
# and
def questionAnalysis(line):
    nlp = spacy.load('en_core_web_sm')
    result = nlp(line)

    # print("TEXT\t\tPOS\t\tDEP\t\tHEAD")
    # for w in result:
    #     print(w.text, w.pos_, w.dep_, w.head.text, sep='\t\t')
    # print("----")
    # for ent in result.ents:
    #     print(ent.lemma_, ent.label_)

    relation = None
    entity = None
    entity2 = None

    for token in result:
        # What is the X of Y? type
        if token.dep_ == 'pobj':
            if (token.head.dep_ == 'prep') and (token.head.head.dep_ == 'nsubj'):
                if (token.head.head.head.dep_ == 'ROOT'):
                    relationLemmas = []
                    for nounChunk in result.noun_chunks:
                        if token.head.head.text in nounChunk.text:
                            for w in nounChunk:
                                if (w.pos_ == 'ADJ') or (w.pos_ == 'NOUN'):
                                    relationLemmas.append(w.text)
                            relation = " ".join(relationLemmas)
                    entityLemmas = []
                    for nounChunk in result.noun_chunks:
                        if token.text in nounChunk.text:
                            for w in nounChunk:
                                if (w.pos_ == 'ADJ') or (w.pos_ == 'NOUN') or (w.pos_ == 'PROPN'):
                                    entityLemmas.append(w.text)
                            entity = " ".join(entityLemmas)

        # Questions of the type Who VERB SUBJ?
        elif (token.dep_ == 'dobj'):
            if (token.head.dep_ == 'ROOT') and (token.head.pos_ == 'VERB'):
                relation = token.head.text
                entity = token.text

        # Questions of the type What did ENTITY VERB?
        elif (token.pos_ == 'PROPN') and (token.head.dep_ == 'ROOT'):
            entity = result.ents[-1].lemma_
            relation = token.head.head.lemma_
            break

        # Questions of the type Is ENTITY a ENTITY (Ex: Is HTML a markup language)
        elif (token.dep_ == 'attr') and (token.pos_ == 'NOUN'):
            if (token.head.dep_ == 'ROOT'):
                relation = token.head.text

                entityLemmas = []
                for nounChunk in result.noun_chunks:
                    if token.text in nounChunk.text:
                        for w in nounChunk:
                            if w.pos_ == 'ADJ' or w.pos_ == 'NOUN':
                                entityLemmas.append(w.text)
                        entity2 = " ".join(entityLemmas)

                # print(relation, entity)
                for othertoken in result:
                    if othertoken.dep_ == 'nsubj':
                        entity = othertoken.lemma_
                        break

    if (relation is None) or (entity is None):
        raise Exception("Question type not recognised.")

    # print("relation: {}\nentity: {}".format(relation, entity))

    try:
        relationId = wikiDataAPI(relation, 'relation')
        entityId1 = wikiDataAPI(entity, 'entity')
        if entity2 != None:
            entity2Id1 = wikiDataAPILabel(entity2, 'entity')

        entityId2 = wikiDataQuery(entity)
    except Exception as e:
        # print(e)
        if ((relationId is not None)):
            if (entityId1 is not None):
                return relationId, entityId1
            else:
                return relationId, entityId2
        else:
            raise Exception('Could not map relation or identity.')
    else:
        #check for conflicts
        if (entityId1 not in entityId2):
            usrAns = input("Do you mean\n(1):\n{}\nor (2):\n{}?\n".format(get_description(entityId1), get_description(entityId2)))
            if (str(usrAns) == "1"):
                entityId = entityId1
            else:
                entityId = entityId2
        else:
            entityId = entityId1

    query = createRelationQuery(relationId, entityId)
    print(query)
    print("Relation = {}\nEntity1 = {}\nEntity2 = {}\n".format(relationId, entityId, entity2Id1))
    if entity2 == None:
        return query, "relation"
    elif entity2Id1 != None:
        return query, entity2Id1

if __name__ == '__main__':
    questions = {
        1: "What is the diameter of the universe?",
        2: "What is the temperature of the Sun?",
        3: "What are the parts of the Inner Solar System?",
        4: "What is the diameter of the Milky Way?",
        5: "What is the electric charge of an electron?",
        6: "What is the cause of the universe?",
        7: "Is HTML a markup language?",
        8: "Is calculus a theory?",
        9: "When did Neil Armstrong die?",
        10: "What is the mass of the human brain?"
    }

    # print 10 example questions
    print("-- \tExample Questions\t --")
    for item in range(1, len(questions)+1):
        print(item, questions.get(item))

    print("\n-- \tType your question!\t --")
    for line in sys.stdin:
        line = line.rstrip()

        try:
            query, type = questionAnalysis(line)

            # ids, Qtype = questionAnalysis(line)
        except Exception as e:
            print(e)
        else:
            query = queryType(ids, Qtype)
            # results = runQuery()
            # printAns(results, Qtype)
            runQuery(query, type)
        print("-- \tType your question!\t --")

'''
Notes:
I want to make it so that when the program asks the user which entity s/he would like to select (in case multiple are found)
it presents them by printing their description, not the number.
Edit: Implemented the above

Possible structure to recognise:

- What is the X of Y?
- Who/What/When VERB SUBJ.
- Who/What/When AUX ENTITY VERB2
- Is ENTITY a(n) ENTITY?
'''
