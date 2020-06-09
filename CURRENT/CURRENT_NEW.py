DEBUG = 1

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
    
    foundRoot = False
    # 1. Find root
    for token in result:
        if DEBUG:
            print("\t".join((token.text, token.lemma_, token.pos_, token.dep_, token.head.lemma_)))
    
        if token.dep_ == 'ROOT':
            foundRoot = True
            # 2. First question type division based on "root = AUX or VERB?"
            if token.pos_ == 'AUX':
                
            elif token.pos_ == 'VERB':
            
            else: # This should not happen for valid question sentences that are properly tokenized
                raise Exception('Question root is not an AUX or VERB. Check if the question is written properly')
            
            break
    if not foundRoot:
        raise Exception('Question somehow does not contain ROOT after tokenization')
    
    return values, Qtype

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
