#!/usr/bin/env python3
'''
By: Noam Zonca (s3482065),
Email: n.zonca@student.rug.nl
'''

import sys
import requests
import spacy
import re

# returns whole dictionary with all info
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

    return json['search'][0]

# returns only id.
def wikiDataQuery(item):
    query = '''
    SELECT ?val1 WHERE {
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
    id = re.search(r'Q\d+$', uri).group()

    result = {
        'id': id,
        'title': id,
        'url': "https://www.wikidata.org/wiki/{}".format(id),
        'concepturi': uri,
        # 'label': ???,
        'description': getDescription(id)
    }

    return result

# Run a query to get a description from an entity Y
# def getDescription(Y):
#     url = 'https://query.wikidata.org/sparql'
#     query = '''SELECT ?label WHERE {wd:''' + Y + ''' schema:description ?label.
#                     FILTER(LANG(?label) = "en")
#                      }
#     '''
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebkit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36'
#     }
#     data = requests.get(url, headers=headers, params={'query': query, 'format':'json'}).json()
#     result = []
#
#     for item in data['results']['bindings']:
#         result.append(item['label']['value'])
#     return " ".join(result)

# Function used to accept strings as part of an entity(Ent) or a relation(Rel).
def extractEntRel(text, noun_chunks):
    acceptablePOS = [
        'NOUN', 'PROPN', 'ADJ', 'VERB'
    ]

    hardCodeRemovals = [
        'how', 'many'
    ]

    stringLemmas = []
    for nounChunk in noun_chunks:
        if text in nounChunk.text:
            for w in nounChunk:
                if (w.text.lower() not in hardCodeRemovals) and (w.pos_ in acceptablePOS):
                    stringLemmas.append(w.lemma_)
            string = " ".join(stringLemmas)
            break

    return string

# Responsible for understanding the quesion type and mapping the entities/relations
# found, to a wikidata Q-Number.
def questionAnalysis(line):
    nlp = spacy.load('en_core_web_sm')
    result = nlp(line)

    spacy.displacy.serve(result, style='dep')

    relation = None
    entity = None
    entity2 = None
    Qtype = None

    for token in result:
        # print(token.text, token.dep_, token.pos_, token.head.dep_)
        # What is the X of Y? type
        if token.dep_ == 'pobj':
            if (token.head.dep_ == 'prep') and ((token.head.head.dep_ == 'nsubj') or (token.head.head.dep_ == 'attr')):
                if (token.head.head.head.dep_ == 'ROOT'):
                    Qtype = "What is the X of Y"
                    relation = extractEntRel(token.head.head.text, result.noun_chunks)
                    entity = extractEntRel(token.text, result.noun_chunks)
                    break

        # Questions of the type Who VERB SUBJ?
        elif (token.dep_ == 'dobj'):
            if (token.head.dep_ == 'ROOT') and (token.head.pos_ == 'VERB'):
                Qtype = "Who VERB SUBJ"
                relation = token.head.text
                entity = token.text
                break

        # Questions of the type What did ENTITY VERB?
        elif (token.pos_ == 'PROPN') and (token.head.dep_ == 'ROOT'):
            for othertoken in result:
                if othertoken.pos_ == "PRON":
                    Qtype = "What did ENTITY VERB"
                    break
            if Qtype == "What did ENTITY VERB":
                entity = []
                for possible_subject in token.head.children:
                    if (possible_subject.dep_ == 'nsubj') and (possible_subject.pos_ == "PROPN"):
                        Qtype = "What did ENTITY VERB"
                        if (possible_subject.children[0].pos_ == "PROPN"):
                            entity.append(possible_subject.children[0].lemma_)
                        entity.append(possible_verb.lemma_)
                        relation = token.head.lemma_
                        break

        # Questions of the type Is ENTITY a ENTITY (Ex: Is HTML a markup language)
        elif (token.dep_ == 'attr') and (token.pos_ == 'NOUN') and (token.head.dep_ == 'ROOT'):
            Qtype = "Is ENTITY a ENTITY"
            for othertoken in result:
                if othertoken.pos_ == "PRON":
                    Qtype = None
                    break
            if Qtype == "Is ENTITY a ENTITY":
                relation = token.head.text
                entity = extractEntRel(token.text, results.noun_chunks)

                for othertoken in result:
                    if othertoken.dep_ == 'nsubj':
                        entityLemmas = []
                        for child in othertoken.children:
                            entityLemmas.append(child.lemma_)
                        entityLemmas.append(othertoken.lemma_)
                        entity = " ".join(entityLemmas)
                            # break
                        break
                break

        # Questions of the type How many Xs VERB Y VERB?
        elif (token.dep_ == 'advmod') and (token.head.dep_ == 'amod'):
            if ((token.head.head.dep_ == 'nsubj') or (token.head.head.dep_ == 'dobj')) and (token.head.head.head.head.dep_ == 'ROOT'):

                Qtype = "How many Xs VERB Y VERB"
                relation = extractEntRel(token.head.head.text, result.noun_chunks)

                entityLemmas = []

                root = [token for token in result if token.head == token][0]
                for child in root.children:

                #
                # for tok in result:
                #     if to
                #     print(root.text)
                    if (tok.dep_ == 'nsubj') and (tok.head.dep_ == 'ROOT'):
                        # for i in tok.head.children:
                        #     print(i.text)
                        if (len(list(tok.children)) > 0) and (list(tok.children)[0].dep_ == 'compound'):
                            entityLemmas.append(list(tok.children)[0].lemma_)
                        entityLemmas.append(tok.lemma_)
                        break
                entity = " ".join(entityLemmas)
                break

    if Qtype == None:
        raise Exception("Question type not recognised.")


    print("relation: {}\nentity: {}\nentity2: {}\nQtype: {}".format(relation, entity, entity2, Qtype))

    relationAPI = None
    entityAPI = None
    entityQuery = None
    entity2API = None
    entity2Query = None
    entity2Final = None

    try:
        relationAPI = wikiDataAPI(relation, 'relation')

        entityAPI = wikiDataAPI(entity, 'entity')

        if entity2 is not None:
            entity2API = wikiDataAPI(entity2, 'entity')
            entity2Query = wikiDataQuery(entity2)

        entityQuery = wikiDataQuery(entity)

    except Exception as e:
        print(e)
        if ((relationAPI is not None)):
            if (entityAPI is None) and (entityQuery is None):
                raise Exception('Could not map Entity.')
            elif (entityAPI is not None):
                entityFinal = entityAPI
            else:
                entityFinal = entityQuery

            if (entity2API is None) and (entity2Query is None):
                print("Could not map entity2")
            elif (entity2API is not None):
                entity2Final = entity2API
            else:
                entity2Final = entity2Query
        else:
            raise Exception('Could not map relation.')
    else:
        # prioritize API over rdfs:label method.
        entityFinal = entityAPI
        entity2Final = entity2API

    values = {
        "relation" : relationAPI,
        "entity" : entityFinal,
        "entity2" : entity2Final if (entity2Final is not None) else None
    }
    print("values:", values["relation"], values["entity"], values["entity2"], sep='\n')
    return values, Qtype

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

# questions of type: How many things with relation X does Y have?
def createQuantityQuery(relation, entity):
    query = '''
    SELECT  (COUNT(?answer) as ?count) WHERE {
        wd:'''+ entity +''' wdt:'''+ relation +''' ?answer
        SERVICE wikibase:label {
            bd:serviceParam wikibase:language "en" .
        }
    }
    '''
    return query

# returns query and answerSpot, which is the variable in the results from runQuery().
# for now they are all the same, but when we implement new query types, this is a better system.
def queryType(values, Qtype):
    queryTypes = {
        "What is the X of Y" : (createRelationQuery(values['relation']['id'], values['entity']['id']), 'answerLabel'),
        "Who VERB SUBJ" : (createRelationQuery(values['relation']['id'], values['entity']['id']), 'answerLabel'),
        "What did ENTITY VERB" : (createRelationQuery(values['relation']['id'], values['entity']['id']), 'answerLabel'),
        "Is ENTITY a ENTITY" : (createRelationQuery(values['relation']['id'], values['entity']['id']), 'answerLabel'),
        "How many Xs VERB Y VERB" : (createQuantityQuery(values['relation']['id'], values['entity']['id']), 'count')
    }

    return queryTypes.get(Qtype)

def runQuery(query, answerSpot):
    url = 'https://query.wikidata.org/sparql'
    headers = {'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebkit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36'}
    data = None
    try:
        data = requests.get(url, headers=headers, params={'query': query, 'format':'json'}).json()
    except Exception as e:
        print("Could not run query:")
        print(e)
        return

    # print("data:\n", data['results']['bindings'])
    final_results = []
    for item in data['results']['bindings']:
        final_results.append(item[answerSpot]['value'])
    
    # print(final_results)
    return final_results

def printAns(results, values, Qtype):
    if (Qtype == "Is ENTITY a ENTITY"):
        if values['entity2']['label'] in results:
            print("Yes")
        else:
            print("No")
    else:
        if (not results):
            print("Answer not found.")
        else:
            print(results)


def main(line):
    try:
        values, Qtype = questionAnalysis(line)
    except Exception as e:
        print(e)
    else:
        query, answerSpot = queryType(values, Qtype)
        results = runQuery(query, answerSpot)
        printAns(results, values, Qtype)

if __name__ == '__main__':
    main(sys.argv)
    questions = {
        1: "What is the mass of the human brain?",
        2: "What is the electric charge of an electron?",
        3: "Name all founders of the United Nations",
        4: "Is calculus a theory?",
        5: "Did Newton discover penicilin?",
        6: "How many nobel prizes has Marie Curie won?",
        7: "Is HTML a markup language?",
        8: "What is the name of the biggest planet in our Solar system?",
        9: "When did Neil Armstrong die?",
        10: "What is the temperature at the center of the Sun?"
    }

    # print 10 example questions
    print("-- \tExample Questions\t --")
    for item in range(1, len(questions)+1):
        print(item, questions.get(item), sep='\t')

    print("\n-- \tType your question!\t --")
    for line in sys.stdin:
        line = line.rstrip()

        main(line)

        print("-- \tType your question!\t --")

'''
ToDo:

Bugs:
- relationId referenced before assignment for (for example: What are the components of air?)
- When answer returns empty it's because the question of type Is X Y?'s answer is false.
DONE - if answer is empty return "answer not found"?
- Is atropa belladonna a poisonous plant?
    -> tuple index out of range

Improvements:
- What happened to looking into the wikidata library?
DONE - make wikiDataAPI return an array with all the info (id, label and other shit?), rather than having 2 identical functs.
DONE - questionAnalysis() only returns the Q-ids of the entity(s) and the relation and the Q's type.
DONE - queryType() is responsible for calling the right query-making function and also depending on
       the query type, the answerSpot (name of field in data['head']['vars'], which contains the answer. ).
DONE - runQuery() only returns the array containing the answer.
DONE - printAns() makes sure the answer type to be returned is correct (yes/no OR the actual answer)
DONE - Need to disambiguate for entity2? (only yes/no questions.)

Need to Fix:
DONE - Around line 196: entityFinal (which is supposed to be a dict) is mapped to the Q-Number returned from wikiDataQuery()

Notes:
* Access id of a wikiDataAPI result with entity['id']
* values (the matches to wikiDataAPI) are stored in a dict, so anything about them can be accessed:
      the dict: values = {
                  "relation" : relationAPI,
                  "entity" : entityFinal,
                  "entity2" : entity2API if (entity2API is not None) else None
              }
'''
