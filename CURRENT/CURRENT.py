#!/usr/bin/env python3
'''
By: Noam Zonca (s3482065),
Email: n.zonca@student.rug.nl
'''

import sys
import requests
import spacy
import re
import itertools
import traceback

API_RESULT_LEN = 3
QUERY_RESULT_LEN = 3

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
    elif (len(json['search']) < API_RESULT_LEN):
        nRes = len(json['search'])
    else:
        nRes = API_RESULT_LEN

    return json['search'][0:nRes]

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
        if (len(data['results']['bindings']) < QUERY_RESULT_LEN):
            nRes = len(data['results']['bindings'])
        else:
            nRes = QUERY_RESULT_LEN

        results = []
        for item in range(0, nRes):
            uri = data['results']['bindings'][item]['val1']['value']

            # only want the entity Q-number.
            srch = re.search(r'Q\d+$', uri)
            # avoids all matches for relations (P-values)
            if (srch is not None):
                id = srch.group()
            else:
                continue

            result = {
                'id': id,
                'title': id,
                'url': 'www.wikidata.org/wiki/' + id,
                'concepturi': uri,
                # 'label': ???,
                # 'description': getDescription(id)
            }
            results.append(result)

    return results

# Function used to accept strings as part of an entity(Ent) or a relation(Rel).
def extractEntRel(text, noun_chunks):
    acceptablePOS = [
        'NOUN', 'PROPN', 'ADJ', 'VERB', 'NUM'
    ]

    hardCodeRemovals = [
        'how', 'many'
    ]

    stringLemmas = []
    for nounChunk in noun_chunks:
        # print(nounChunk.text)
        if text in nounChunk.text:
            for w in nounChunk:
                if (w.text.lower() not in hardCodeRemovals) and (w.pos_ in acceptablePOS):
                    stringLemmas.append(w.lemma_)
            string = " ".join(stringLemmas)
            break

    # NEED list acceptableDEP
    # for child in token.children:
    #     if (child.pos_ in acceptablePOS):
    #         stringLemmas.append(w.lemma_)
    # string = " ".join(stringLemmas)
    # break

    return string

# Responsible for understanding the quesion type and mapping the entities/relations
# found, to a wikidata Q-Number.
def questionAnalysis(line):
    nlp = spacy.load('en_core_web_lg')
    result = nlp(line)

    spacy.displacy.serve(result, style='dep')

    for token in result:
        relation = None
        entity = None
        entity2 = None
        Qtype = None

        # print(token.text, token.lemma_, token.dep_, token.pos_, token.head.dep_)
        # What is the X of Y? type
        if token.dep_ == 'pobj':
            if (token.head.dep_ == 'prep') and ((token.head.head.dep_ == 'nsubj') or
                                                (token.head.head.dep_ == 'attr') or
                                                (token.head.head.dep_ == 'dobj')):
                if (token.head.head.head.dep_ == 'ROOT'):
                    Qtype = "What is the X of Y"
                    relation = extractEntRel(token.head.head.text, result.noun_chunks)
                    entity = extractEntRel(token.text, result.noun_chunks)
                    break

        # Questions of the type Who VERB SUBJ?
        elif (token.dep_ == 'dobj'):
            for othertoken in result:
                if othertoken.pos_ == "PRON":
                    Qtype = "What did ENTITY VERB"
                    break
            if Qtype == "What did ENTITY VERB":
                if (token.head.dep_ == 'ROOT') and (token.head.pos_ == 'VERB'):
                    Qtype = "Who VERB SUBJ"
                    relation = token.head.text
                    entity = token.text
                    break

        # Questions of the type Did ENTITY1 RELATION ENTITY2 (Yes/No)
        elif (token.lemma_ == 'do' and token.pos_ == 'AUX'): # token is starting "Did" ... .
            nsubj = aux = dobj = False
            relation = token.lemma_
            root = [toks for toks in result if toks.head == toks][0]
            for child in root.children:
                if (child.dep_ == 'nsubj'):
                    entity2 = extractEntRel(child.text, result.noun_chunks)
                    nsubj = True
                elif (child.dep_ == 'aux'):
                    aux = True
                elif (child.dep_ == 'dobj') or (child.dep_ == 'attr'):
                    entity = extractEntRel(child.text, result.noun_chunks)
                    dobj = True
            # print("nsubj: {}, aux: {}, dobj: {}".format(nsubj, aux, dobj))
            if (nsubj and aux and dobj):
                Qtype = "Did ENTITY1 RELATION ENTITY2"
                break

        # Questions of the type Is ENTITY a ENTITY (Yes/No) (Ex: Is HTML a markup language)
        elif (token.dep_ == 'ROOT' and token.lemma_ == 'be'):
            pron = True
            for othertoken in result:
                if othertoken.pos_ == "PRON":
                    pron = False
                    break
            if (pron):
                attr = nsubj = False
                relation = token.lemma_
                for child in token.children:
                    if (child.dep_ == 'nsubj'):
                        entity = extractEntRel(child.text, result.noun_chunks)
                        nsubj = True
                    elif (child.dep_ == 'attr'):
                        entity2 = extractEntRel(child.text, result.noun_chunks)
                        attr = True
                # print("nsubj: {}, attr: {}".format(nsubj, attr))
                if (nsubj and attr):
                    Qtype = "Is ENTITY a ENTITY"
                    break

        # Questions of the type How many Xs VERB Y VERB?
        elif ((token.dep_ == 'ROOT') and (re.match(r'^how many', line, re.I) is not None)):
            aux = nsubj1 = nsubj2 = False
            for child in token.children:
                if (child.dep_ == 'nsubj'):
                    entity = extractEntRel(child.text, result.noun_chunks)
                    nsubj1 = True
                elif (child.dep_ == 'aux'):
                    aux = True
                    childChild = [child for child in child.children if child.dep_ == 'nsubj'][0]
                    relation = extractEntRel(childChild.text, result.noun_chunks)
                    nsubj2 = True
            print("aux: {} nsubj1: {} nsubj2: {}".format(aux, nsubj1, nsubj2))
            if (aux and nsubj1 and nsubj2):
                Qtype = "How many Xs VERB Y VERB"
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
                break
        # else:
        #     print(" NOTHING")
    if Qtype == None:
        raise Exception("Question type not recognised.")

    # hardcoding things that won't get recognised
    hardCodings = {
        "is" : ["become", "be"],
        "Nobel prize ID" : ["nobel prize", "nobel peace prize"]
    }

    # a little ratchet, but so so sweet.
    for vals in hardCodings.values():
        if (relation in vals):
            relation = list(hardCodings.keys())[list(hardCodings.values()).index(vals)]

    print("relation: {}\nentity: {}\nentity2: {}\nQtype: {}\n-----------".format(
            relation, entity, entity2, Qtype))

    relationAPI = []
    entityAPI = []
    entityQuery = []
    entity2API = []
    entity2Query = []

    try: # attempt to map relation.
        relationAPI = wikiDataAPI(relation, 'relation')
    except Exception:
        raise Exception('Could not map relation.')
    else:
        try: # try mapping entity using API
            entityAPI = wikiDataAPI(entity, 'entity')
        except Exception:
            pass

        try: # try mapping entity using Query
            entityQuery = wikiDataQuery(entity)
        except Exception:
            pass

        # if both fail, raise exception.
        if (not entityAPI) and (not entityQuery):
            raise Exception('Could not map entity using API nor Query.')

    if entity2 is not None:
        try:
            entity2API = wikiDataAPI(entity2, 'entity')
            entity2Query = wikiDataQuery(entity2)
        except Exception:
            if (not entity2API) and (not entity2Query):
                raise Exception('Could not map entity2 using API nor Query.')

    values = {
        "relation" : relationAPI,
        "entity" : entityAPI + entityQuery,
        "entity2" : entity2API + entity2Query if (entity2 is not None) else None
    }

    print("values:")
    print("rel:")
    for i in range(0, len(values["relation"])):
        print("{} - {}".format(values["relation"][i]["id"], values["relation"][i]["url"]))

    print("ent:")
    for j in range(0, len(values["entity"])):
        print("{} - {}".format(values["entity"][j]["id"], values["entity"][j]["url"]))

    print("ent2:")
    if (entity2 is not None):
        for k in range(0, len(values["entity2"])):
            print("{} - {}".format(values["entity2"][k]["id"], values["entity2"][k]["url"]))
    else:
        print("None")

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
def queryType(combo, Qtype):
    queryTypes = {
        "What is the X of Y" : (createRelationQuery(combo[0]['id'], combo[1]['id']), 'answerLabel'),
        "Who VERB SUBJ" : (createRelationQuery(combo[0]['id'], combo[1]['id']), 'answerLabel'),
        "Did ENTITY1 RELATION ENTITY2" : (createRelationQuery(combo[0]['id'], combo[1]['id']), 'answerLabel'),
        "What did ENTITY VERB" : (createRelationQuery(combo[0]['id'], combo[1]['id']), 'answerLabel'),
        "Is ENTITY a ENTITY" : (createRelationQuery(combo[0]['id'], combo[1]['id']), 'answerLabel'),
        "How many Xs VERB Y VERB" : (createQuantityQuery(combo[0]['id'], combo[1]['id']), 'count')
    }

    return queryTypes.get(Qtype)

def runQuery(query):
    url = 'https://query.wikidata.org/sparql'
    headers = {'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebkit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36'}

    data = None

    try:
        data = requests.get(url, headers=headers, params={'query': query, 'format':'json'}).json()
    except Exception as e:
        print("Could not run query:")
        traceback.print_exc()
        return

    # print("data:", data['results']['bindings'], sep='\n')

    return data['results']['bindings']

def validAns(results, values, Qtype, answerSpot):
    if (Qtype == "Is ENTITY a ENTITY") or (Qtype == "Did ENTITY1 RELATION ENTITY2"):
        for item in values['entity2']:
            for ans in results:
                if ans['answer']['value'] == item['concepturi']:
                    print("Yes")
                    return True
        return False
    else:
        return True

def main(line):
    try:
        values, Qtype = questionAnalysis(line)
    except Exception as e:
        traceback.print_exc()
    else:
        results = []
        answerSpot = None
        for combo in itertools.product(values['relation'], values['entity']):
            print("\ntrying combo: \nrel: {} - {} \nent: {} - {}".format(
                    combo[0]["id"], combo[0]["url"],
                    combo[1]["id"], combo[1]["url"]))

            query, answerSpot = queryType(combo, Qtype)
            results = runQuery(query)
            ansGood = validAns(results, values, Qtype, answerSpot)

            if (results and ansGood): # found good answer.
                break
            else:
                print("combo failed")

        # if no answer can be found, and have tried all combos
        if (not results):
            print("Answer not found.")
        elif (ansGood == False):
            print("No")
        else:
            answ = []
            for i in results:
                answ.append(i[answerSpot]['value'])
            print(answ)

if __name__ == '__main__':
    questions = {
        1: "What is the mass of the human brain?",
        2: "What is the charge of an electron?",
        3: "Name all founders of the United Nations",
        4: "Is calculus a theory?",
        5: "Is HTML a markup language?", # Note: Only works with the large model
        6: "Did Alexander Fleming invent penicillin?", # Note: also only works w/ large model
        7: "How many nobel prizes has Marie Curie won?",
        8: "What is the name of the biggest planet in our Solar system?",
        9: "When did Neil Armstrong die?",
        10: "What is the temperature at the center of the Sun?"
    }

    # print 10 example questions
    print("-- \tExample Questions\t --")
    for item in range(1, len(questions)+1):
        print(item, questions.get(item), sep='\t')

    if (len(sys.argv) == 2) and (sys.argv[1].isdigit()):
        line = questions.get(int(sys.argv[1]))
        main(line)
    else:
        print("\n-- \tType your question!\t --")
        for line in sys.stdin:
            line = line.rstrip()
            if (line.isdigit() and (int(line) > 0 and int(line) <= 10)):
                line = questions.get(int(line))
                print(line)

            main(line)

            print("-- \tType your question!\t --")
