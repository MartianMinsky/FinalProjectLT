#!/usr/bin/python3

# Members:
# Nathan Bosch (s3475344)
# Jeongu Kim   (s2894742)
# KJR Sabandar (s2864819)
# Daan Windt   (s3486429)


import sys
import requests
import re
import spacy

nlp = spacy.load('en_core_web_sm')

url = 'https://query.wikidata.org/sparql'
api_url = 'https://www.wikidata.org/w/api.php'

permutation = [(0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (2, 1), (0, 2), (1, 2),
               (2, 2)]
count_questions_properties = ['P31', 'P279', 'P361', 'P527', 'P2670']


# Finds X of Y, returns string 'no results' if no results found
def get_results(xstring, ystring):
    Xparams = {'action': 'wbsearchentities',
               'language': 'en',
               'format': 'json',
               'type': 'property'}

    Yparams = {'action': 'wbsearchentities',
               'language': 'en',
               'format': 'json'}
    try:
        Yparams['search'] = ystring
        Yjson = requests.get(api_url, Yparams).json()
        Xparams['search'] = xstring
        Xjson = requests.get(api_url, Xparams).json()

    # loop through all the search results of X and Y
        for result in Yjson['search']:
            y = result['id']
            for result in Xjson['search']:
                x = result['id']
                data = get_data(x, y)
                if data['results']['bindings'] != []:
                    return data
        return ('no results')
    except Exception:
        return ('no results')


# Extracts data from wikidata API
def get_data(x, y):
    query = '''
    SELECT  ?itemLabel
    WHERE
    {{
        wd:{} wdt:{} ?item.
        SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
    }}'''.format(y, x)

    data = requests.get(url, params={'query': query, 'format': 'json'}).json()
    return data


# Extracts data and puts it into a list
def extract_answer(data):
    mylist = []
    if data == "no results":
        return mylist
    for item in data['results']['bindings']:
        for var in item:
            mylist.append(item[var]['value'])
    return mylist


def get_id(string, idType, qualifier, qualIndex):
    params = {'action': 'wbsearchentities',
              'language': 'en',
              'format': 'json'
              }
    if idType == 'property':
        params['type'] = 'property'

    params['search'] = string.rstrip()
    json = requests.get(api_url, params).json()
    ret = []
    qualifier[qualIndex] = add_hardcoded_ids(ret, string, idType)
    try:
        for i in json['search']:
            ret.append(i['id'])
        ret.append("")
        return ret
    except KeyError:
        ret.append("")
        return ret


def get_xstring_data(ystring, zstring):
    url3 = api_url
    Yparams = {'action': 'wbsearchentities',
               'language': 'en',
               'format': 'json'
               }

    Zparams = {'action': 'wbsearchentities',
               'language': 'en',
               'format': 'json'
               }

    try:
        Zparams['search'] = zstring
        Zjson = requests.get(url3, Zparams).json()
        Yparams['search'] = ystring
        Yjson = requests.get(url3, Yparams).json()

        # loop through all the search results of Y and Z
        for result in Yjson['search']:
            y = result['id']
            for result in Zjson['search']:
                z = result['id']
                data = get_property_data(y, z)
                if data['results']['bindings'] != []:
                    return data
        return ('no results')
    except Exception:
        return ('no results')


def get_property_data(y, z):
    url4 = 'https://query.wikidata.org/sparql'
    query = (
            '''
            SELECT  ?itemLabel
            WHERE
            {{
                wd:{} ?itemLabel wd:{}.
                SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
            }}'''.format(y, z))

    data = requests.get(url4, params={'query': query, 'format': 'json'}).json()
    return data


########################################################################

# Sends a request to the wikidata api, retrieving an entity of a given name
def find_entity(entity, index):
    entity.replace("_", " ")
    params = {'action': 'wbsearchentities', 'language': 'en', 'format': 'json'}
    params['search'] = entity.rstrip()
    json = requests.get(api_url, params).json()
    return json['search'][index]


# Sends a request to the wikidata api, retrieving a property of a given name
def find_property(property, index):
    property.replace("_", " ")
    params = {'action': 'wbsearchentities',
              'language': 'en',
              'format': 'json',
              'type': 'property'}
    params['search'] = property.rstrip()
    json = requests.get(api_url, params).json()
    return json['search'][index]


########################################################################

def check_be_z_the_x_of_y(parse):
    for w in parse:
        if w.dep_ == "pobj":
            return True
    return False


def check_be_z_x_y(parse):
    for w in parse:
        if w.pos_ == "VERB" and w.dep_ != "ROOT":
            return True
    return False


def find_string(w, parse, string):
    for x in parse:
        if x.dep_ == "compound" and x.head.lemma_ == w.lemma_ :
            if string == "":
                string = x.text
            else:
                string += " " + x.text
        elif x.text == w.text and string == "":
            string = w.text
        else:
            if x.text == w.text:
                string += " " + w.text
    return string


########################################################################

def find_do_z_x_y(parse):
    xstring, ystring, zstring = "", "", ""
    for w in parse:
        # Find ystring
        if w.dep_ == "nsubj":
            zstring = find_string(w, parse, zstring)

        # Find xstring
        if w.dep_ == "ROOT" and (w.pos_ == "VERB" or w.pos_ == "NOUN"):
            xstring = w.text
            # Find preposition if any
            for x in w.subtree:
                if x.dep_ == "prep" and x.head.lemma_ == w.lemma_:
                    xstring += " " + x.text
        # Find zstring
        if w.dep_ == "pobj" or w.dep_ == "dobj":
            ystring = find_string(w, parse, ystring)

    return (xstring, ystring, zstring)


def find_be_z_the_x_of_y(parse, question):
    xstring, ystring, zstring = "", "", ""

    if parse[0].text == 'Is':
        m = re.search('Is (.*) the (.*) of (.*)?', question)
    if parse[0].text == 'Are':
        m = re.search('Are (.*) the (.*) of (.*)?', question)
    if parse[0].text == 'Was':
        m = re.search('Was (.*) the (.*) of (.*)?', question)
    if parse[0].text == 'Were':
        m = re.search('Were (.*) the (.*) of (.*)?', question)

    xstring = m.group(2)
    ystring = m.group(3)
    zstring = m.group(1)
    ystring = ystring.replace("?", "")

    return (xstring, ystring, zstring)


def find_be_y_z(parse):
    xstring, ystring, zstring = "", "", ""
    xstring = "is a"
    for w in parse:
        # find ystring
        if w.dep_ == "nsubj":
            ystring = find_string(w, parse, ystring)
        # find zstring
        if (w.dep_ == "appos" or w.dep_ == "attr" or w.dep_ == "acomp"):
            zstring = find_string(w, parse, zstring)
    data = get_xstring_data(ystring, zstring)
    if data != "no results":
        myList = extract_answer(data)
        xstring = myList[0]
    return xstring, ystring, zstring


########################################################################

def count_questions_get_x_and_y(parse):
    x = ""
    y = ""
    for token in parse:
        if token.tag_ == "NNS" and y == "":
            x = token.lemma_
            if token.dep_ == "compound":
                x += "_" + token.head.lemma_
        elif x != "" and (token.tag_ == "NN" or token.tag_ == "NNS" or token.tag_ == "NNP"):
            y = token.lemma_
            if token.dep_ == "compound":
                y += "_" + token.head.lemma_
            break
    return x, y


# Highest lowest first last question
def highest_lowest_questions_get_x_and_y(parse):
    x = ""
    y = ""
    for token in parse:
        if token.pos_ == "ADJ":
            x = token.text
            x += "_" + token.head.lemma_
        elif token.dep_ == "pobj" and (token.tag_ == "NN" or token.tag_ == "NNS"):
            y = token.lemma_
            if token.dep_ == "compound":
                y += "_" + token.head.lemma_
            break
    return x, y


def find_how_xyz_format(parsed, h, iteration):
    # Find x
    xObject = h.head
    x = find_compound(parsed, h, xObject, True)  # Find anything that might need to be included in x
    if (iteration == 0):
        x = "cause of "+x
    if (iteration == 1):
        x = "manner of "+x

    # Find y
    y = ""
    for i in parsed:
        if (i.head == xObject and (i.dep_ == "nsubj" or i.dep_ == "nsubjpass")):
            yObject = i
            y = find_compound(parsed, h, yObject, True)  # Find anything that might need to be included in y
            break

    # z cannot be present in these kinds of sentences
    z = ""

    return [x, y, z]


def find_when_xyz_format(parsed, h):
    # When was y x(verb)?

    # Find x
    xObject = h.head.head
    x = find_compound(parsed, h, xObject, True)  # Find anything that might need to be included in x
    x = "date of "+x

    # Find y
    y = ""
    for i in parsed:
        if (i.head.pos_ == "VERB" and (i.dep_ == "nsubj" or i.dep_ == "nsubjpass")):
            yObject = i
            y = find_compound(parsed, h, yObject, True)  # Find anything that might need to be included in y
            break

    # z cannot be present in these kinds of sentences
    z = ""

    return [x, y, z]


def find_where_xyz_format(parsed, h):
    # Where was y x(verb)?

    # Find x
    xObject = h.head.head
    x = find_compound(parsed, h, xObject, True)  # Find anything that might need to be included in x
    x = "place of "+x

    # Find y
    y = ""
    for i in parsed:
        if (i.head.pos_ == "VERB" and (i.dep_ == "nsubj" or i.dep_ == "nsubjpass")):
            yObject = i
            y = find_compound(parsed, h, yObject, True)  # Find anything that might need to be included in y
            break

    # z cannot be present in these kinds of sentences
    z = ""

    return [x, y, z]


def find_possessive_xyz_format(parsed, h, propDate):
    # Find x
    xObject = h.head.head
    x = ""
    if (not xObject.pos_ == "PRON"):
        x = find_compound(parsed, h, xObject, False)  # Find anything that might need to be included in x
        if(propDate):
            x = "date of" + x

    # Find y
    yObject = h.head
    y = ""
    if (not yObject.pos_ == "PRON"):
        y = find_compound(parsed, h, yObject, False)  # Find anything that might need to be included in y

    # Find z
    possibleIs = xObject.head
    z = ""
    if (possibleIs.lemma_ == "be"):
        for i in parsed:
            if ((i.pos_ == "NOUN" or i.pos_ == "PROPN") and i.head == possibleIs and not i == xObject):
                zObject = i
                z = find_compound(parsed, h, zObject, False)  # Find anything that might need to be included in z
                break
    return [x, y, z]


def find_standard_xyz_format(parsed, h, typ):
    # Find x
    xObject = h.head
    x = ""
    if (not xObject.pos_ == "PRON"):
        x = find_compound(parsed, h, xObject, False)  # Find anything that might need to be included in x
        x = typ + x

    # Find y
    y = ""
    for i in parsed:
        if (i.head == h and not i.pos_ == "PRON"):
            yObject = i
            y = find_compound(parsed, h, yObject, False)  # Find anything that might need to be included in y
            break

    # Find z
    possibleIs = xObject.head
    z = ""
    if (possibleIs.lemma_ == "be"):
        for i in parsed:
            if ((i.pos_ == "NOUN" or i.pos_ == "PROPN") and i.head == possibleIs and not i == xObject):
                zObject = i
                z = find_compound(parsed, h, zObject, False)  # Find anything that might need to be included in z
                break
    return [x, y, z]


def yes_no_questions_get_x_y_z(parse, question):
    xstring, ystring, zstring = "", "", ""
    switcher = "off"

    # Do Z X Y? (Did Elvis Presley influence the Beatles?)
    if parse[0].lemma_ == "do":
        xstring, ystring, zstring = find_do_z_x_y(parse)
        switcher = "on"

    # Be Z X Y? (Was Kendrick Lamar born in Compton?)
    elif check_be_z_x_y(parse) is True:
        xstring, ystring, zstring = find_be_z_x_y(parse)
        switcher = "on"

    # Be Z the X of Y? (Is Donda West the mother of Kanye West)
    elif check_be_z_the_x_of_y(parse) is True:
        xstring, ystring, zstring = find_be_z_the_x_of_y(parse, question)

    # Be Z Y? (Is Shakira a model, Is Michael Jackson a male)
    else:
        xstring, ystring, zstring = find_be_y_z(parse)

    return xstring, ystring, zstring, switcher


def find_be_z_x_y(parse):
    xstring, ystring, zstring = "", "", ""
    for w in parse:
        # Find ystring
        if w.dep_ == "nsubj":
            ystring = find_string(w, parse, ystring)

        # Find xstring
        if w.dep_ != "ROOT" and w.pos_ == "VERB":
            xstring = w.text
            # Find preposition if any
            for x in w.subtree:
                if x.dep_ == "prep" and x.head.lemma_ == w.lemma_:
                    xstring += " " + x.text
        # Find zstring
        if w.dep_ == "pobj" or w.dep_ == "dobj":
            zstring = find_string(w, parse, zstring)

    return (xstring, ystring, zstring)


########################################################################


def find_compound(parsed, h, x, mustBeNoun):
    # Find any words that should be part of x but are not automatically found
    compound = ""
    abort = 0
    xText = x.lemma_
    if (x.pos_ == "VERB" and mustBeNoun):
        xText = verb_to_noun(xText)
    for i in parsed:
        if i == x:
            if (abort == 0):
                return compound + xText
            else:
                return ""
        if (i.dep_ == "compound" or i.dep_ == "amod" or (i.dep_ == "det" and (i.lemma_ == "what" or i.lemma_ == "which"))):
            compound += i.lemma_
            compound += " "
        elif (i.dep_ == "prep" and i.lemma_ == "of" and not i == h):
            compound += i.head.lemma_
            compound += " "
            compound += i.lemma_
            compound += " "
        else:
            compound = ""
            abort = 0


def verb_to_noun(verb):
    if (verb == "bear"):
        return "birth"
    if (verb == "die"):
        return "death"
    if (verb == "write"):
        return "writer"
    if (verb == "started"):
        return "founded by"
    if (verb == "sings" or verb == "sung"):
        return "performer"
    return verb


def add_hardcoded_ids(ret, string, typ):
    qualifier = ""
    if (string == "member" and typ == "property"):
        ret.append("P527")  # Has part
    if (string == "real name" and typ == "property"):
        ret.append("P1477")  # Birth name
    if (string == "album" and typ == "property"):
        ret.append("P361")  # Part of, add qualifier for "album"
        qualifier = string
    if ((string == "drummer" or string == "guitarist" or string == "instrumentalist" or string == "singer" or string == "pianist" or string == "bassist") and typ == "property"):
        ret.append("P527")  # Has part, we are looking for members and use its function within the band or similar as a qualifier
        qualifier = string
    return qualifier


########################################################################

# Count query generation, simply plugs in values for x and y
def gen_count_query(x, x_id, y, y_id, property):
    x = x.replace(" ", "")
    new_query = ((
        """
        SELECT ?%s
        WHERE
        {
          wd:%s p:%s [
          ps:%s wd:%s;
          pq:P1114 ?%s ].
          SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE]". }
        }
        """) % (x, y_id, property, property, x_id, x))
    return new_query


def gen_other_count_query(x_id, y_id):
    new_query = ((
        """
        SELECT (COUNT(*) AS ?item) WHERE {
        wd:%s wdt:%s ?item.
        SERVICE wikibase:label { bd:serviceParam
        wikibase:language "[AUTO_LANGUAGE],en". } }
        """) % (y_id, x_id))
    return new_query


def gen_highest_lowest_query(x, x_id, y, y_id):
    x = x.replace(" ", "")
    y = y.replace(" ", "")
    y = y.replace(".", "")
    new_query = (("""SELECT ?%s ?%s WHERE {wd:%s wdt:%s ?%s"""
                  """. SERVICE wikibase:label { bd:serviceParam"""
                  """ wikibase:language "[AUTO_LANGUAGE],en". } }""")
                 % (x, x+"Label", y_id, x_id, x))
    return new_query


def construct_query_xyz(x, y, z, qualifiers):
    qualString = ["", "", ""]
    if ((x == "" and y == "") or (x == "" and z == "") or (y == "" and z == "")):
        return "Nothing"
    propQuery = False
    if (x == ""):
        x = "?answer"
        propQuery = True
    else:
        x = "wdt:"+x

    if (y == ""):
        y = "?answer"
    else:
        y = "wd:"+y

    if (z == ""):
        z = "?answer"
    else:
        z = "wd:"+z
    if (not qualifiers[0] == ""):
            qualString[0] = z + " ?thing0 wd:" + get_id(qualifiers[0], "object", [""], 0)[0] + " ."
            qualString[0] ='''  ?wut0 wdt:P279 wd:%s .
                {
                %s ?thing0 wd:%s .
                }
                UNION
                {
                %s ?thing0 ?wut0 .
                }''' % (get_id(qualifiers[0], "object", [""], 0)[0], z, get_id(qualifiers[0], "object", [""], 0)[0], z)
    if (not qualifiers[1] == ""):
            qualString[1] = y + " ?thing1 wd:" + get_id(qualifiers[1], "object", [""], 0)[0] + " ."
            qualString[1] ='''  ?wut1 wdt:P279 wd:%s .
                {
                %s ?thing1 wd:%s .
                }
                UNION
                {
                %s ?thing1 ?wut1 .
                }''' % (get_id(qualifiers[1], "object", [""], 0)[0], y, get_id(qualifiers[1], "object", [""], 0)[0], y)
    if (not qualifiers[2] == ""):
            qualString[2] = z + " ?thing2 wd:" + get_id(qualifiers[2], "object", [""], 0)[0] + " ."
            qualString[2] ='''  ?wut2 wdt:P279 wd:%s .
                {
                %s ?thing2 wd:%s .
                }
                UNION
                {
                %s ?thing2 ?wut2 .
                }''' % (get_id(qualifiers[2], "object", [""], 0)[0], z, get_id(qualifiers[2], "object", [""], 0)[0], z)
    if(propQuery):
        query = '''
            SELECT DISTINCT ?propLabel
                Where{
                hint:Query hint:optimizer "None" .
                %s %s %s .
                %s
                %s
                %s
                ?prop wikibase:directClaim ?answer .
                SERVICE wikibase:label {
                    bd:serviceParam wikibase:language "en" .
                }
            }
            ''' % (y, x, z, qualString[0], qualString[1], qualString[2])
    else:
        query = '''
            SELECT DISTINCT ?answerLabel
                Where{
                %s %s %s .
                %s
                %s
                %s
                SERVICE wikibase:label {
                    bd:serviceParam wikibase:language "en" .
                }
            }
            ''' % (y, x, z, qualString[0], qualString[1], qualString[2])
    return query


########################################################################


# Sends a request to wikidata with a sparql query, returns the result
def run_specific_query(query):
    try:
        data_request = requests.get(url, params={'query': query,
                                                 'format': 'json'})
        data = data_request.json()
        return data['results']['bindings']
    except Exception:
        return None


def find_xyz_answer(x, y, z):
    answer = ""
    depth = 5  # Increase for better chance of finding obscure answers, decrease for slightly better performance and bigger chance to find less obscure answers
    qualifiers = ["", "", ""]
    xId = get_id(x, "property", qualifiers, 0)
    yId = get_id(y, "object", qualifiers, 1)
    if ("what" in y or "which" in y):
        qualifiers[1] = y.strip("what").strip("which").strip()
        yId = [""]
        y = ""
    zId = get_id(z, "object", qualifiers, 2)
    if ("what" in z or "which" in z):
        qualifiers[2] = z.strip("what").strip("which").strip()
        zId = [""]
        z = ""
    for numi, i in enumerate(xId):
        if (numi == depth):
            break
        for numj, j in enumerate(yId):
            if (numj == depth):
                break
            for numk, k in enumerate(zId):
                if (numk == depth):
                    break
                if (not ((i == "" and j == "") or (i == "" and k == "") or (j == "" and k == ""))):
                    query = construct_query_xyz(i, j, k, qualifiers)
                    if (not query == "Nothing"):
                        answer = []
                        returned_query = run_specific_query(query)
                        for item in returned_query:
                            for var in item:
                                answer.append(item[var]['value'])
                        if (not answer == []):
                            return answer
    return "No answer was found"


########################################################################

# Can print list answers in a single line
def print_answer(answers):
    for answer in answers:
        print(answer, end='\t', flush=True)
    print('')


########################################################################
def isCase_1(parse):
    if parse[0].lemma_ == 'be' or parse[0].lemma_ == 'do':
        return True
    else:
        return False


def isCase_2(question):
    if "highest" in question or "lowest" in question or "first" in question or "last" in question:
        return True
    return False


def isCase_3(parse):
    if parse[0].text == 'How' and parse[1].text == "many":
        return True
    return False


########################################################################

def findAnswerCase_1(parse, question):
    finalAnswer = []
    candidateAnswer = []
    swticher = "off"
    xstring, ystring, zstring, switcher = yes_no_questions_get_x_y_z(parse, question)
    candidateAnswer.append(zstring)
    data = get_results(xstring, ystring)
    if data:
        listAnswers = extract_answer(data)
        if zstring in listAnswers:
            finalAnswer.append('Yes')
        elif candidateAnswer == extract_answer(data):
            finalAnswer.append('Yes')
        else:
            finalAnswer.append('No')
    else:
        # Fail Case
        finalAnswer.append('Yes')
    if switcher == "on" and finalAnswer[0] == 'No':
        finalAnswer.clear()
        temp = ystring
        ystring = zstring
        zstring = temp
        candidateAnswer.clear()
        candidateAnswer.append(zstring)
        data = get_results(xstring, ystring)

        if data:
            listAnswers = extract_answer(data)
            if zstring in listAnswers:
                finalAnswer.append('Yes')
            elif candidateAnswer == extract_answer(data):
                finalAnswer.append('Yes')
            else:
                finalAnswer.append('No')

    return finalAnswer


def findAnswerCase_2(parse, times=0):
    if (times >= 8):
        return []
    x, y = highest_lowest_questions_get_x_and_y(parse)
    times_tried = permutation[times]
    try:
        x_property = find_property(x, times_tried[0])
        print(x_property['id'])
        y_element = find_entity(y, times_tried[1])
        print(y_element['id'])
    except Exception:
        return findAnswerCase_2(parse, times+1)
    sparql_query = gen_highest_lowest_query(x, x_property['id'], y, y_element['id'])
    query_result = run_specific_query(sparql_query)
    if query_result == []:
        return findAnswerCase_2(parse, times+1)
    else:
        answer = []
        for item in query_result:
            for idx, var in enumerate(item):
                if idx == 0:
                    continue
                answer.append(item[var]['value'])
        return answer


def findAnswerCase_3(parse, times=0):
    if (times >= 8):
        return []
    x, y = count_questions_get_x_and_y(parse)
    times_tried = permutation[times]
    try:
        x_property = find_property(x, times_tried[0])
        y_element = find_entity(y, times_tried[1])
    except Exception:
        return findAnswerCase_3(parse, times+1)
    for i in range(len(count_questions_properties)):
        sparql_query = gen_count_query(x, x_property['id'], y, y_element['id'], count_questions_properties[i])
        query_result = run_specific_query(sparql_query)
        if query_result != []:
            break
    if query_result == []:
        sparql_query = gen_other_count_query(x_property['id'], y_element['id'])
        query_result = run_specific_query(sparql_query)
    if query_result == []:
        return findAnswerCase_3(parse, times+1)
    else:
        answer = []
        for item in query_result:
            for var in item:
                answer.append(item[var]['value'])
        return answer


def findFailCase(parsed):
    for h in parsed:
        # Find standard case: z is (the) x of y
        if (h.dep_ == "prep"):
            li = find_standard_xyz_format(parsed, h, "")
            x = li[0]
            y = li[1]
            z = li[2]

            answer = find_xyz_answer(x, y, z)
            if (not answer == "No answer was found"):
                return answer

        # Find questions using the possessive ("'s")
        if (h.tag_ == "POS"):
            li = find_possessive_xyz_format(parsed, h, "")
            x = li[0]
            y = li[1]
            z = li[2]

            answer = find_xyz_answer(x, y, z)
            if (not answer == "No answer was found"):
                return answer

        # Find questions starting with "where"
        if (h.head.pos_ == "VERB" and h.lemma_ == "where"):
            if (h.head.dep_ == "ROOT"):
                li = find_standard_xyz_format(parsed, h, "place of ")
                x = li[0]
                y = li[1]
                z = li[2]

                answer = find_xyz_answer(x, y, z)
                if (not answer == "No answer was found"):
                    return answer

                li = find_standard_xyz_format(parsed, h, "")
                x = li[0]
                y = li[1]
                z = li[2]

                answer = find_xyz_answer(x, y, z)
                if (not answer == "No answer was found"):
                    return answer

            li = find_where_xyz_format(parsed, h)
            x = li[0]
            y = li[1]
            z = li[2]

            answer = find_xyz_answer(x, y, z)
            if (not answer == "No answer was found"):
                return answer

        # Find questions starting with "when"
        if (h.head.pos_ == "VERB" and h.lemma_ == "when"):
            if (h.head.dep_ == "ROOT"):
                li = find_standard_xyz_format(parsed, h, "time of ")
                x = li[0]
                y = li[1]
                z = li[2]

                answer = find_xyz_answer(x, y, z)
                if (not answer == "No answer was found"):
                    return answer

                li = find_standard_xyz_format(parsed, h, "")
                x = li[0]
                y = li[1]
                z = li[2]

                answer = find_xyz_answer(x, y, z)
                if (not answer == "No answer was found"):
                    return answer

            li = find_when_xyz_format(parsed, h)
            x = li[0]
            y = li[1]
            z = li[2]

            answer = find_xyz_answer(x, y, z)
            if (not answer == "No answer was found"):
                return answer
        # Find questions starting with "how"
        if (h.lemma_ == "how"):
            for i in range(0, 1, 2):
                li = find_how_xyz_format(parsed, h, i)
                x = li[0]
                y = li[1]
                z = li[2]

                answer = find_xyz_answer(x, y, z)
                if (not answer == "No answer was found"):
                    return answer

    return ["No answer was found"]


########################################################################
def get_id_and_question(sentence):
    id = 0
    question = ""
    for index, letter in enumerate(sentence):
        if letter.isdigit():
            id *= 10
            id += int(letter)
        elif letter == "\t":
            question = sentence[index:]
            break
    if id == 0 or question == "":
        question = sentence
    return id, question.strip()


def find_answer(sentence):

    id, question = get_id_and_question(sentence)
    print(str(id) + " " + question)
    parse = nlp(question)  # Remove number and tab from the question

    answer = []
    # Yes/No Questions
    if isCase_1(parse) is True:
        answer = findAnswerCase_1(parse, question)

    # Highest/Lowest Questions
    elif isCase_2(question) is True:
        answer = findAnswerCase_2(parse)

    # Count Questions
    elif isCase_3(parse) is True:
        answer = findAnswerCase_3(parse)

    # Fail Case: What/Who/Where/When/How Questions
    else:
        answer = findFailCase(parse)

    print_answer(answer)

    return id, answer


def main(argv):
    f = open("answers.txt", "w+")
    if len(argv) > 1 and ".txt" in argv[1]:
        file = argv[1]
        r = open(file, "r")
        for sentence in r:
            id, answer = find_answer(sentence)
            answer_string = ""
            for i, a in enumerate(answer):
                answer_string += str(a)
                if i < len(answer) - 1:
                    answer_string += "\t"
            f.write("{id}\t".format(id=id) + answer_string + "\n")
        r.close()
    else:
        for sentence in sys.stdin:
            id, answer = find_answer(sentence)
            answer_string = ""
            for i, a in enumerate(answer):
                answer_string += str(a)
                if i < len(answer) - 1:
                    answer_string += "\t"
            f.write("{id}\t".format(id=id) + answer_string + "\n")
    f.close()


if __name__ == "__main__":
    main(sys.argv)
