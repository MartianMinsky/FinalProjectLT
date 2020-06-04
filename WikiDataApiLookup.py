#!/usr/bin/env python3
'''
By: Noam Zonca (s3482065)
Email: n.zonca@student.rug.nl
'''

import requests
import sys
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
        raise Exception('Did not find relation or entity using API!')

    id = json['search'][0]['id']

    # print(json)
    # print()
    for itm in json['search']:
        print("{}: {} - {}".format(item, itm['id'], itm['label']))

if __name__ == '__main__':
    print("insert: <item>//<type (entity/relation)>")
    for line in sys.stdin:
        line = line.rstrip()

        arr = line.split("//")
        try:
            wikiDataAPI(arr[0], arr[1])
        except Exception as e:
            print(e)
        print("insert item and type:")
