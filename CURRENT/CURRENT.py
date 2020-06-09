DEBUG = 0

#!/usr/bin/env python3
'''
Team members:
  Noam Zonca (s3482065), n.zonca@student.rug.nl
  Winward Fang (s3205843), w.fang@student.rug.nl
'''

import sys
import requests
import spacy
import re
import itertools
import traceback

API_RESULT_LEN = 4
QUERY_RESULT_LEN = 4

# returns whole dictionary with all info
def wikiDataAPI(item, type):
    url = 'https://www.wikidata.org/w/api.php'
    params = {'action':'wbsearchentities',
              'language':'en',
              'format':'json'}

    if (type == 'relation'):
        params['type'] = 'property'

    params['search'] = item.rstrip()
    json = requests.get(url,params).json()

    if (not json['search']):
        raise Exception('Did not find property or entity using API!')
    elif (len(json['search']) < API_RESULT_LEN):
        nRes = len(json['search'])
    else:
        nRes = API_RESULT_LEN

    return json['search'][0:nRes]

# Function used to accept strings as part of an entity(Ent) or a relation(Rel).
def extractEntRel(token, noun_chunks):
    acceptablePOS = [
        'NOUN', 'PROPN', 'ADJ', 'VERB', 'NUM'
    ]

    hardCodeRemovals = [
        'many'
    ]

    text = token.text
    string = None

    stringLemmas = []
    for nounChunk in noun_chunks:
        # print(nounChunk.text)
        if text in nounChunk.text:
            for w in nounChunk:
                if (w.pos_ in acceptablePOS) and (w.lemma_ not in hardCodeRemovals):
                    stringLemmas.append(w.lemma_)
            string = " ".join(stringLemmas)
            break

    # NEED list acceptableDEP
    # for child in token.children:
    #     if (child.pos_ in acceptablePOS):
    #         stringLemmas.append(w.lemma_)
    # string = " ".join(stringLemmas)
    # break

    # doesn't work, because if you give it root, it's gonna look at the whole sentence.
    # for w in w.subtree:
    #     if (W.pos_ in acceptablePOS):
    #             stringLemmas.append(w.lemma_)
    #     string = " ".join(stringLemmas)
    #     break

    return string if string is not None else token.lemma_

# Responsible for understanding the quesion type and mapping the entities/relations
# found, to a wikidata Q-Number.
def questionAnalysis(line):
    result = nlp(line)

    # spacy.displacy.serve(result, style='dep')

    for token in result:
        relation = None
        entity = None
        entity2 = None
        Qtype = None

        nsubj = nsubj2 = aux = pcomp = ccomp = attr = advmod = dobj = False
        # print(token.text, token.lemma_, token.dep_, token.pos_, token.head.dep_)
        # What is the X of Y? type
        if token.dep_ == 'pobj':
            if (token.head.dep_ == 'prep') and ((token.head.head.dep_ == 'nsubj') or
                                                (token.head.head.dep_ == 'attr') or
                                                (token.head.head.dep_ == 'dobj')):
                if (token.head.head.head.dep_ == 'ROOT'):
                    Qtype = "What is the X of Y"
                    relation = extractEntRel(token.head.head, result.noun_chunks)
                    entity = extractEntRel(token, result.noun_chunks)
                    break

        # # Questions of the type Who VERB SUBJ?
        # elif (token.dep_ == 'dobj'):
        #     for othertoken in result:
        #         if othertoken.pos_ == "PRON":
        #             Qtype = "What did ENTITY VERB"
        #             break
        #     if Qtype == "What did ENTITY VERB":
        #         if (token.head.dep_ == 'ROOT') and (token.head.pos_ == 'VERB'):
        #             Qtype = "Who VERB SUBJ"
        #             relation = token.head.text
        #             entity = token.text
        #             break

        # Questions of the type Did ENTITY1 RELATION ENTITY2 (Yes/No)
        elif (token.lemma_ == 'do' and (re.search(r'^(does|do|did)', line, re.I) is not None)): # token is starting w/ "Do" lemma ... .
            root = [toks for toks in result if toks.head == toks][0]
            relation = root.lemma_
            for child in root.children:
                if (child.dep_ == 'nsubj'):
                    entity2 = extractEntRel(child, result.noun_chunks)
                    nsubj = True
                elif (child.dep_ == 'aux'):
                    aux = True
                elif (child.dep_ == 'dobj') or (child.dep_ == 'attr'):
                    entity = extractEntRel(child, result.noun_chunks)
                    dobj = True
            # print("nsubj: {}, aux: {}, dobj: {}".format(nsubj, aux, dobj))
            if (nsubj and aux and dobj and (not attr) and (not advmod)):
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
                relation = token.lemma_ # should just be the "is"
                for child in token.children:
                    if (child.dep_ == 'nsubj'):
                        entity = extractEntRel(child, result.noun_chunks)
                        nsubj = True
                    elif (child.dep_ == 'attr'):
                        entity2 = extractEntRel(child, result.noun_chunks)
                        attr = True
                # print("nsubj: {}, attr: {}".format(nsubj, attr))
                if (nsubj and attr and (not aux) and (not advmod) and (not dobj)):
                    Qtype = "Is ENTITY a ENTITY"
                    break

        # Questions of the type How many Xs VERB Y VERB?
        elif ((token.dep_ == 'ROOT') and (re.match(r'^how many', line, re.I) is not None)):
            nsubj2 = False
            if (token.text == re.search(r'(\b\w+\b).?$', line, re.I).group(1)):
                for child in token.children:
                    # How many ... has ... ROOT. or  How many ... did ... VERB
                    if (child.dep_ == 'nsubj'):
                        entity = extractEntRel(child, result.noun_chunks)
                        nsubj2 = True
                    elif (child.dep_ == 'dobj'):
                        dobj = True
                        relation = extractEntRel(child, result.noun_chunks)
                    elif (child.dep_ == 'aux'):
                        aux = True
                        auxChildren = [child for child in child.children if child.dep_ == 'nsubj']
                        if (not auxChildren):
                            continue
                        childChild = auxChildren[0]
                        relation = extractEntRel(childChild, result.noun_chunks)
                        nsubj = True
            else:
                for child in token.children:
                    # received, root is has for some reason.
                    if (child.dep_ == 'ccomp'):
                        ccomp = True
                        ccompChildren = [child for child in child.children if child.dep_ == 'nsubj']
                        if (not ccompChildren):
                            continue
                        childChild = ccompChildren[0]
                        entity = extractEntRel(childChild, result.noun_chunks)
                        nsubj2 = True
                    elif (child.dep_ == 'nsubj'):
                        relation = extractEntRel(child, result.noun_chunks)
                        nsubj = True
            # print("aux: {} dobj: {} nsubj: {} nsubj2: {}".format(aux, dobj, nsubj, nsubj2))
            if ((nsubj2 and aux and (dobj or nsubj)) or (ccomp and nsubj and nsubj2)):
                Qtype = "How many Xs VERB Y VERB"
                break

        # Questions of the type What did ENTITY VERB?
        elif ((token.dep_ == 'ROOT') and (token.text == re.search(r'(\b\w+\b).?$', line, re.I).group(1))):
            # relation = token.lemma_
            relation = extractEntRel(token, result.noun_chunks)
            for child in token.children:
                if ((child.dep_ == 'advmod') or (child.dep_ == 'dobj' and child.pos_ == 'PRON')):
                    advmod = True
                    dobj = True
                elif (child.dep_ == 'aux'):
                    aux = True
                elif (child.dep_ == 'nsubj'):
                    entity = extractEntRel(child, result.noun_chunks)
                    nsubj = True
            # print("advmod: {} nsubj: {} aux: {}".format(advmod, nsubj, aux))
            if ((advmod or dobj) and nsubj and aux and (not attr)):
                Qtype = "What did ENTITY VERB"
                break

        # Questions of the type: At what X did Y VERB?
        elif ((token.dep_ == 'prep') and ('at' == re.search(r'^(\b\w+\b)', line, re.I).group(1).lower())):
            prep = True
            prepChildren = [child for child in token.children if child.dep_ == 'pcomp']
            if (not prepChildren):
                continue
            childChild = prepChildren[0]
            relation = extractEntRel(childChild, result.noun_chunks)
            pcomp = True

            root = [toks for toks in result if toks.head == toks][0]
            for child in root.children:
                if (child.dep_ == 'aux'):
                    aux = True

            for leftChld in root.lefts: pass
            # entity = leftChld.lemma_
            entity = extractEntRel(leftChld, result.noun_chunks)

            if (prep and pcomp and aux):
                Qtype = "At what X did Y VERB"
                break

        # Questions of the type: How X is Y?
        elif ((token.dep_ == 'advmod') and ('how' == re.search(r'^(\b\w+\b)', line, re.I).group(1).lower())):
            root = [toks for toks in result if toks.head == toks][0]
            for child in root.children:
                if (child.dep_ == 'nsubj'):
                    nsubj = True
                    entity = extractEntRel(child, result.noun_chunks)
                    nsubjChildren = [child for child in root.children if (child.dep_ == 'acomp') or (child.dep_ == 'advmod')]
                    if (not nsubjChildren):
                        continue
                    childChild = nsubjChildren[0]
                    relation = extractEntRel(childChild, result.noun_chunks)
                    advmod = True
            if (nsubj and advmod):
                Qtype = "How X is Y"
                break

        # else:
        #     print(" NOTHING")

    if (Qtype == None):
        raise Exception("Question type not recognised.")

    # hardcoding things that won't get recognised
    hardCodings = {
        "is" : ["become", "be"],
        "Nobel prize ID" : ["nobel prize", "nobel peace prize"],
        "occupation" : ["do"],
        "has part" : ["component", "part"],
        "educated at" : ["study"],
        "languages spoken, written or signed" : ["language", "speak"],
        "size" : ["big", "small", "large"],
        "distance" : ["far", "away"]
        # "educated at" : ["go school"] # doesn't work, will never match "go school."
    }

    # a little ratchet, but so so sweet.
    for vals in hardCodings.values():
        if (relation in vals):
            relation = list(hardCodings.keys())[list(hardCodings.values()).index(vals)]
    
    if DEBUG:
      print("relation: {}\nentity: {}\nentity2: {}\nQtype: {}\n-----------".format(
              relation, entity, entity2, Qtype))

    relationAPI = []
    entityAPI = []
    entity2API = []

    try: # attempt to map relation.
        relationAPI = wikiDataAPI(relation, 'relation')
    except Exception:
        raise Exception('Could not map relation.')
    else:
        try: # try mapping entity using API
            entityAPI = wikiDataAPI(entity, 'entity')
        except Exception:
            pass

    if entity2 is not None:
        try:
            entity2API = wikiDataAPI(entity2, 'entity')
        except Exception:
            if not entity2API:
                raise Exception('Could not map entity2 using API nor Query.')

    values = {
        "relation" : relationAPI,
        "entity" : entityAPI,
        "entity2" : entity2API if (entity2 is not None) else None
    }
    
    if DEBUG:
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
      print("-----------")

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
        "At what X did Y VERB" : (createRelationQuery(combo[0]['id'], combo[1]['id']), 'answerLabel'),
        "How X is Y" : (createRelationQuery(combo[0]['id'], combo[1]['id']), 'answerLabel'),
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
                    return True
        return False
    else:
        return True

def printAns(results, answerSpot, qN, Qtype, ansGood):
    if (results and ansGood):
        answ = []
        for i in results:
            answ.append(i[answerSpot]['value'])

        print(qN, end='\t')
        if (Qtype == "Is ENTITY a ENTITY") or (Qtype == "Did ENTITY1 RELATION ENTITY2"):
            if (ansGood):
                print("Yes", end='')
            else:
                print("No", end='')
        else:
            for element in answ:
                print(element, end='\t')
        print()
    else:
        print("Answer not found.")

def writeAns(results, answerSpot, qN, Qtype, ansGood):
    line = str(qN)
    if (results):
        answ = []
        for i in results:
            answ.append(i[answerSpot]['value'])

        # format the line to be written to ansFile
        if (Qtype == "Is ENTITY a ENTITY") or (Qtype == "Did ENTITY1 RELATION ENTITY2"):
            if (ansGood):
                line += ('\t' + "Yes")
            else:
                line += ('\t' + "No")
        else:
            for element in answ:
                line += ("\t" + str(element))
    line += '\n'

    with open("answers.txt", 'a') as ansFile:
        ansFile.write(line)

def main(line, qN=1):
    try:
        values, Qtype = questionAnalysis(line)
    except Exception as e:
        traceback.print_exc()
    else:
        results = []
        answerSpot = None
        for combo in itertools.product(values['relation'], values['entity']):
            if DEBUG:
              print("\ntrying combo: \nrel: {} - {} \nent: {} - {}".format(
                      combo[0]["id"], combo[0]["url"],
                      combo[1]["id"], combo[1]["url"]))

            query, answerSpot = queryType(combo, Qtype)
            results = runQuery(query)
            ansGood = validAns(results, values, Qtype, answerSpot)

            if (results and ansGood): # found good answer.
                break
            elif DEBUG:
                print("combo failed")

        # output
        printAns(results, answerSpot, qN, Qtype, ansGood)
        writeAns(results, answerSpot, qN, Qtype, ansGood)

if __name__ == '__main__':
    print("Loading model..")
    if DEBUG:
      nlp = spacy.load('en_core_web_sm')
    else:
      nlp = spacy.load('en_core_web_lg')

    questions = {
        1: "What is the mass of the human brain?",
        2: "What is the charge of an electron?",
        3: "Name all founders of the United Nations",
        4: "Is calculus a theory?",
        5: "At what speed does Jupiter move?",
        6: "Did Alexander Fleming invent penicillin?", # Note: also only works w/ large model
        7: "How many nobel prizes has Marie Curie won?",
        8: "What is the name of the biggest planet in our Solar system?",
        9: "When did Neil Armstrong die?",
        10: "What is the temperature at the center of the Sun?"
    }

    # print 10 example questions
    print("\n-- \tExample Questions\t --")
    for item in range(1, len(questions)+1):
        print(item, questions.get(item), sep='\t')

    open("answers.txt", 'w').close()
    # allow args as numbers to reference a sample question
    if (len(sys.argv) == 2) and (sys.argv[1].isdigit()):
        line = questions.get(int(sys.argv[1]))
        main(line)

    # Read a file.
    elif (len(sys.argv) == 2):
        questionsFile = sys.argv[1]
        inputQuestions = {}
        print("\n-- \tReading File {}\t --".format(questionsFile))
        with open(questionsFile, 'r') as qFile:
            for line in qFile:
                line = line.rstrip()
                if not line: break
                q = line.split("\t")
                # print(q)
                inputQuestions[q[0]] = q[1]

        print("\n-- \tInput Questions\t --")
        for qN in inputQuestions:
            Q = inputQuestions.get(qN)
            print(qN, Q, sep='\t')

        # run every Question in the input file
        for qN in inputQuestions:
            Q = inputQuestions.get(qN)
            print("\n-- \tAnswering Input Question:\t --")
            print(qN, Q, sep='\t')
            main(Q, qN)

    # just read from stdin
    else:
        print("\n-- \tType your question!\t --")
        qN = 1
        for line in sys.stdin:
            line = line.rstrip()
            
            # line is a digit corresponding to one of the example questions
            if (line.isdigit() and (int(line) > 0 and int(line) <= 10)):
                line = questions.get(int(line))
                print(line)

            main(line, qN)
            qN += 1
            print("-- \tType your question!\t --")
