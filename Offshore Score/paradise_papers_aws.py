#coding=utf-8
import os, sys, glob
import json
import pandas as pd
import numpy as np
from neo4j.v1 import GraphDatabase, basic_auth
from gevent.pool import Pool
import datetime
# import eikon as ek
import re
# import dateparser
import requests
from joblib import Parallel, delayed
import multiprocessing
import collections
import warnings
import time
import probablepeople as pp

# os.chdir('/')

url = 'https://dds-test.thomsonreuters.com/datafusion/'
user = 'jiaming.zhan@thomsonreuters.com'
pwd = 'jiaming'

def get_token_headers():
    headers = {'Content-Type': 'application/json'}
    data = {'username': user, 'password': pwd}
    r = requests.post(url + 'oauth/token', headers=headers, json=data, verify=False).json()
    headers['Accept'] = 'application/json'
    headers['Authorization'] = r['token_type'] + ' ' + r['access_token']
    return headers



# create normalized names as nodes in neo4j
def normalize_name(x):
    x = x.upper()
    x = re.sub(r'[^A-Z0-9 ]+', ' ', x)
    x = re.sub(r' +', ' ', x)
    x = x.strip()
    x = re.sub(r' LIMITED', ' LTD', x)
    x = re.sub(r' CORPORATION', ' CORP', x)
    x = re.sub(r' INCORPORATED', ' INC', x)
    return x


def name_type(x):
    return 'organization' if any([y in x.split() for y in
                                  ['LTD', 'SERVICES', 'TRUST', 'MANAGEMENT', 'HOLDINGS', 'INTERNATIONAL', 'PORTADOR',
                                   'INC', 'COMPANY', 'GROUP', 'SAMOA', 'CORP', 'INVESTMENTS', 'FOUNDATION',
                                   'PORTCULLIS', 'TRUSTNET', 'CORPORATE', 'MOSSFON', 'INVESTMENT', 'BVI', 'JERSEY',
                                   'HOLDING', 'EQUITY', 'ENTERPRISES']]) else 'individual'

# CREATE INDEX ON :Officer(name)
# CREATE INDEX ON :Officer_norm(name)

####################################
# search in DF, to resolve companies and persons
####################################
def search_entity(name, headers):
    data = {'searchString': name, 'entityTypeId': [4, 16], 'limit': 1,
            'extraFields': '*'}  # 4 is Person, 16 is Organization
    r = requests.get(url + 'api/entity/search', headers=headers, json=data, verify=False).json()['entities']
    r = [x for x in r if 'sourceID_attr' not in x]
    if len(r) > 0:
        r1 = r[0]
        r1['source_name_norm'] = name
        return r1
    else:
        return {}


def search_entities(name_list, headers):
    chunk_size = 100
    name_chunks = [name_list[i:i + chunk_size] for i in range(0, len(name_list), chunk_size)]
    warnings.filterwarnings("ignore")
    # uri = []
    print("There are in total %d chunks of names to complete" % len(name_chunks))
    for i in range(964, len(name_chunks)):
        print(i)
        try:
            # uri += Parallel(n_jobs=-1)(delayed(search_entity)(x) for x in name_chunks[i])
            uri = Parallel(n_jobs=-1)(delayed(search_entity)(x, headers) for x in name_chunks[i])
            with open('matched_df_uri.txt', 'a') as f:
                r = f.write(json.dumps(uri) + '\n')
                f.flush()
        except:
            print("timeout!")
            time.sleep(5)
        if i % 10 == 0:
            print(str(i) + '/' + str(len(name_chunks)) + ' completed at ' + str(datetime.datetime.now()))
    #return uri


# def search_entities(name_list):
#     uri = []
#     for i in range(len(name_list)):
#         print(i)
#         uri.append(search_entity(name_list[i]))
#     return uri


def match_individual_name(source_name, df_label, full_name, family_name, given_name):
    match = any([
        re.sub(r'[^a-zA-Z0-9]', '', str(source_name).lower()) == re.sub(r'[^a-zA-Z0-9]', '', str(df_label).lower()),
        re.sub(r'[^a-zA-Z0-9]', '', str(source_name).lower()) == re.sub(r'[^a-zA-Z0-9]', '', str(full_name).lower()),
        re.sub(r'[^a-zA-Z0-9]', '', str(source_name).lower()) == re.sub(r'[^a-zA-Z0-9]', '',
                                                                        str(family_name).lower() + str(
                                                                            given_name).lower()),
        re.sub(r'[^a-zA-Z0-9]', '', str(source_name).lower()) == re.sub(r'[^a-zA-Z0-9]', '',
                                                                        str(given_name).lower() + str(
                                                                            family_name).lower())
    ])
    return match


# parse company names for fuzzy matching
def fuzzy_match(txt1, txt2):
    s1 = [re.sub(r'[^a-zA-Z0-9]', '', x[0]).lower() for x in pp.parse(txt1) if x[1] == 'CorporationName']
    s2 = [re.sub(r'[^a-zA-Z0-9]', '', x[0]).lower() for x in pp.parse(txt2) if x[1] == 'CorporationName']
    l1, l2 = len(s1), len(s2)
    set1 = {" ".join(s1[j:j + i]) for i in range(1, l1 + 1) for j in range(l1 + 1 - i)}
    set2 = {" ".join(s2[j:j + i]) for i in range(1, l2 + 1) for j in range(l2 + 1 - i)}
    r = sorted(set1.intersection(set2), key=lambda x: len(x.split()))
    rs = [j for k, j in enumerate(r) if all(j not in r[i] for i in range(k + 1, len(r)))]
    rs = [x.split() for x in rs if len(x.split()) > 1]
    matched_len = sum([len(x) for x in rs])
    base = np.mean([len(s1), len(s2)])
    matched_score = matched_len / base if base > 0 else 0
    return min(1, matched_score)


def match_organization_name(source_name, df_label, common_name, official_name):
    match = any([
        # re.sub(r'[^a-zA-Z0-9]', '', str(source_name).lower()) == re.sub(r'[^a-zA-Z0-9]', '', str(df_label).lower()),
        # re.sub(r'[^a-zA-Z0-9]', '', str(source_name).lower()) == re.sub(r'[^a-zA-Z0-9]', '', str(common_name).lower()),
        # re.sub(r'[^a-zA-Z0-9]', '', str(source_name).lower()) == re.sub(r'[^a-zA-Z0-9]', '', str(official_name).lower())
        re.sub(r'[^a-zA-Z0-9]', '', source_name.lower()) == re.sub(r'[^a-zA-Z0-9]', '', df_label.lower()),
        re.sub(r'[^a-zA-Z0-9]', '', source_name.lower()) == re.sub(r'[^a-zA-Z0-9]', '', common_name.lower()),
        re.sub(r'[^a-zA-Z0-9]', '', source_name.lower()) == re.sub(r'[^a-zA-Z0-9]', '', official_name.lower())
    ])
    return match


def fuzzy_match_organization_name(source_name, df_label, common_name, official_name):
    exact_match = match_organization_name(source_name, df_label, common_name, official_name)
    fuzzy_match_score = np.mean([
        fuzzy_match(source_name, df_label),
        fuzzy_match(source_name, common_name),
        fuzzy_match(source_name, official_name)
    ])
    return True if exact_match or fuzzy_match_score >= 0.8 else False


def screen_df_results(uri):
    uri1 = []
    for chunk in uri:
        for x in chunk:
            if x:
                df_country = x['isDomiciledIn_attr'] if 'isDomiciledIn_attr' in x else ''
                df_country = df_country[0] if type(df_country) == list else df_country
                df_country = '' if pd.isnull(df_country) else df_country
                source_country = x['source_country'] if 'source_country' in x else ''
                source_country = '' if pd.isnull(source_country) else source_country
                country_match = True if (df_country == source_country) or df_country == '' or source_country == '' else False
                if country_match:
                    source_name = x['source_name_norm'] if 'source_name_norm' in x else ''
                    df_label = x['label'] if 'label' in x else ''
                    full_name = x['FullName_attr'] if 'FullName_attr' in x else ''
                    family_name = x['family-name_attr'] if 'family-name_attr' in x else ''
                    given_name = x['given-name_attr'] if 'given-name_attr' in x else ''
                    common_name = x['CommonName_attr'] if 'CommonName_attr' in x else ''
                    common_name = common_name[0] if type(common_name) == list else common_name
                    official_name = x['officialName_attr'] if 'officialName_attr' in x else ''
                    official_name = official_name[0] if type(official_name) == list else official_name
                    if x['type'] == 'expert' and match_individual_name(source_name, df_label, full_name, family_name,
                                                                       given_name):
                        uri1.append(x)
                    elif x['type'] == '1464971960180_organization' and fuzzy_match_organization_name(source_name, df_label,
                                                                                                     common_name,
                                                                                                     official_name):
                        uri1.append(x)
                    else:
                        pass
    return uri1


####################################
# expand networks from matched results
####################################
def get_connected_entities(uri, count, headers):
    data = {'uri': uri, 'entityTypeId': [4, 16], 'level': 1, 'rowsPerLevel': count, 'maxRelatedEntities': 1000,
            'extraFields': '*'}
    r = requests.get(url + 'api/entity/analyze/search', headers=headers, json=data, verify=False).json()
    return r