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


####################################
# neo4j connection
####################################
driver = GraphDatabase.driver("bolt://ec2-13-228-37-181.ap-southeast-1.compute.amazonaws.com:7687",
                              auth=basic_auth("neo4j", "chenziao"))
session = driver.session()

####################################
# DF connection
####################################
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


headers = get_token_headers()

####################################
# normalize officer names
####################################
# get all officer names
r1 = []
total = 1000000
step = 10000

for i in range(0, total, step):
    r = session.run("""
        match (a:Officer:New) 
        return a.name
        skip """ + str(i) + """
        limit """ + str(step) + """
    """)
    r = list(r)
    if len(r) > 0:
        r1 += r
    else:
        break

names = set([x['a.name'] for x in r1])
print("All names for new nodes retrieved")


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


names_norm = set([normalize_name(str(x)) for x in names])
print("All names are normalized")


def name_type(x):
    return 'organization' if any([y in x.split() for y in
                                  ['LTD', 'SERVICES', 'TRUST', 'MANAGEMENT', 'HOLDINGS', 'INTERNATIONAL', 'PORTADOR',
                                   'INC', 'COMPANY', 'GROUP', 'SAMOA', 'CORP', 'INVESTMENTS', 'FOUNDATION',
                                   'PORTCULLIS', 'TRUSTNET', 'CORPORATE', 'MOSSFON', 'INVESTMENT', 'BVI', 'JERSEY',
                                   'HOLDING', 'EQUITY', 'ENTERPRISES']]) else 'individual'


# for name in names_norm:
#     r = session.run("CREATE (a:Officer_norm:New {name:'" + name + "',type:'" + name_type(name) + "'})")

print("Officer_norm created")
# CREATE INDEX ON :Officer(name)
# CREATE INDEX ON :Officer_norm(name)


# create link from original name to normalized name
# for name in names:
#     name = str(name)
#     name_norm = normalize_name(name)
#     for remove_char in ['"', "'", '\\']:
#         name = name.replace(remove_char, '')
#     r = session.run(
#         "MATCH (a:Officer:New),(b:Officer_norm:New) WHERE (a.name='" + name + "') and (b.name='" + name_norm + "') CREATE (a)-[r:norm_name_to]->(b)")

print("All links from officer to officer_norm created")


####################################
# search in DF, to resolve companies and persons
####################################
def search_entity(name):
    print(name)
    data = {'searchString': name, 'entityTypeId': [4, 16], 'limit': 10,
            'extraFields': '*'}  # 4 is Person, 16 is Organization
    r = requests.get(url + 'api/entity/search', headers=headers, json=data, verify=False).json()['entities']
    r = [x for x in r if 'sourceID_attr' not in x]
    if len(r) > 0:
        r1 = r[0]
        r1['source_name_norm'] = name
        return r1
    else:
        return {}


def search_entities(name_list):
    chunk_size = 100
    name_chunks = [name_list[i:i + chunk_size] for i in range(0, len(name_list), chunk_size)]
    warnings.filterwarnings("ignore")
    uri = []
    print(len(name_chunks))
    for i in range(len(name_chunks)):
        print(i)
        try:
            uri += Parallel(n_jobs=-1)(delayed(search_entity)(x) for x in name_chunks[i])
            print(uri)
        except:
            print("here")
            time.sleep(5)
        if i % 10 == 0:
            print(str(i) + '/' + str(len(name_chunks)) + ' completed at ' + str(datetime.datetime.now()))
    return uri

# def search_entities(name_list):
#     uri = []
#     for i in range(len(name_list)):
#         print(i)
#         uri.append(search_entity(name_list[i]))
#     return uri

if __name__ == '__main__':
    with open('matched_df_uri.txt', 'w') as f:
        uri = search_entities(list(names_norm))
        for x in uri:
            r = f.write(json.dumps(x) + '\n')

print("Officers Matched with Data Fusion")
####################################
# screen searching results, to remove low-confidence matches
####################################
uri = []

with open('matched_df_uri.txt') as f:
    for l in f:
        uri.append(json.loads(l.strip('\n')))


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
        re.sub(r'[^a-zA-Z0-9]', '', str(source_name).lower()) == re.sub(r'[^a-zA-Z0-9]', '', str(df_label).lower()),
        re.sub(r'[^a-zA-Z0-9]', '', str(source_name).lower()) == re.sub(r'[^a-zA-Z0-9]', '', str(common_name).lower()),
        re.sub(r'[^a-zA-Z0-9]', '', str(source_name).lower()) == re.sub(r'[^a-zA-Z0-9]', '', str(official_name).lower())
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
    for x in uri:
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


uri1 = screen_df_results(uri)


####################################
# expand networks from matched results
####################################
def get_connected_entities(uri, count):
    data = {'uri': uri, 'entityTypeId': [4, 16], 'level': 1, 'rowsPerLevel': count, 'maxRelatedEntities': 1000,
            'extraFields': '*'}
    r = requests.get(url + 'api/entity/analyze/search', headers=headers, json=data, verify=False).json()
    return r


# 1 degree
uri_list = list(set([x['uri'] for x in uri1]))
chunk_size = 100
uri_chunks = [uri_list[i:i + chunk_size] for i in range(0, len(uri_list), chunk_size)]

f_entities = open('degree_1_entities.txt', 'w')
f_paths = open('degree_1_paths.txt', 'w')

for i in range(len(uri_chunks)):
    try:
        connecteds = Parallel(n_jobs=-1)(delayed(get_connected_entities)(x, 1000) for x in uri_chunks[i])
        for connected in connecteds:
            for x in connected['entities']:
                r = f_entities.write(json.dumps(x) + '\n')
            for x in connected['paths']:
                r = f_paths.write(json.dumps(x) + '\n')
    except:
        time.sleep(5)
    if i % 10 == 0:
        print(str(i) + '/' + str(len(uri_chunks)) + ' completed at ' + str(datetime.datetime.now()))

f_entities.close()
f_paths.close()

# 2 degrees
entities_1_degree = []

with open('degree_1_entities.txt') as f:
    for l in f:
        entities_1_degree.append(json.loads(l))

uri_list = list(set([x['uri'] for x in entities_1_degree]) - set([x['uri'] for x in uri1]))
chunk_size = 100
uri_chunks = [uri_list[i:i + chunk_size] for i in range(0, len(uri_list), chunk_size)]

f_entities = open('degree_2_entities.txt', 'w')
f_paths = open('degree_2_paths.txt', 'w')

for i in range(len(uri_chunks)):
    try:
        connecteds = Parallel(n_jobs=-1)(delayed(get_connected_entities)(x, 1000) for x in uri_chunks[i])
        for connected in connecteds:
            for x in connected['entities']:
                r = f_entities.write(json.dumps(x) + '\n')
            for x in connected['paths']:
                r = f_paths.write(json.dumps(x) + '\n')
    except:
        time.sleep(5)
    if i % 10 == 0:
        print(str(i) + '/' + str(len(uri_chunks)) + ' completed at ' + str(datetime.datetime.now()))

f_entities.close()
f_paths.close()

####################################
# upload DF matched results
####################################
uri2 = {}

for x in uri1:
    if x['uri'] not in uri2:
        uri2[x['uri']] = x

uri2 = list(uri2.values())


def write_json_2_neo4j_entity(json_x, label):
    row1 = "{"
    for field in json_x:
        value = str(json_x[field])
        for remove_char in ['"', "'", '\\']:
            value = value.replace(remove_char, '')
        for remove_char in ['.', '(', ')', '-']:
            field = field.replace(remove_char, '_')
        row1 += field + ":'" + value + "',"
    row1 = row1.strip(',') + "}"
    r = session.run("CREATE (a:" + label + " " + row1 + ")")
    return 1


for x in uri2:
    r = write_json_2_neo4j_entity(x, 'DF_entity')

# CREATE INDEX ON :DF_entity(uri)


# build neo4j links
for x in uri1:
    r = session.run(
        "MATCH (a:Officer_norm),(b:DF_entity) WHERE (a.name='" + x['source_name_norm'] + "') and (b.uri='" + x[
            'uri'] + "') CREATE (a)-[r:match_to]->(b)")

####################################
# upload expanded DF entities
####################################
# upload expanded DF entities
r1 = []
total = 1000000
step = 10000

for i in range(0, total, step):
    r = session.run("""
        match (a:DF_entity) 
        return a.uri
        skip """ + str(i) + """
        limit """ + str(step) + """
    """)
    r = list(r)
    if len(r) > 0:
        r1 += r
    else:
        break

existing_uri = set([x['a.uri'] for x in r1])

df_entities = {}

for file_name in ['degree_1_entities.txt', 'degree_2_entities.txt']:
    with open(file_name) as f:
        for l in f:
            l1 = json.loads(l)
            if l1['uri'] not in existing_uri:
                df_entities[l1['uri']] = l1

df_entities1 = list(df_entities.values())

for x in df_entities1:
    r = write_json_2_neo4j_entity(x, 'DF_entity')

# upload expanded DF relations
df_relations = []

for file_name in ['degree_1_paths.txt', 'degree_2_paths.txt']:
    with open(file_name) as f:
        for l in f:
            l1 = json.loads(l)
            df_relations += l1['segments']

df_relations1 = []

for x in df_relations:
    for y in x['predicates']:
        predicate = y['predicateUri'].split('/')[-1]
        direction = y['direction']
        contextUri = y['contextUri']
        if direction == 'OUT':
            uri1 = x['uri1']
            uri2 = x['uri2']
        else:
            uri1 = x['uri2']
            uri2 = x['uri1']
        df_relations1.append({'uri1': uri1, 'uri2': uri2, 'predicate': predicate, 'contextUri': contextUri})

df_relations2 = pd.DataFrame(df_relations1)

df_relations2['predicate'] = [x[0].lower() + x[1:] for x in df_relations2['predicate']]
df_relations2.drop_duplicates(['uri1', 'uri2', 'predicate'], inplace=True)

# df_relations2.groupby('predicate',as_index=False).agg({'uri1':np.size}).sort_values('uri1',ascending=False)
# df_relations2.groupby('contextUri',as_index=False).agg({'uri1':np.size}).sort_values('uri1',ascending=False)['contextUri']


for i in range(len(df_relations2)):
    try:
        uri1 = df_relations2.iloc[i]['uri1']
        uri2 = df_relations2.iloc[i]['uri2']
        predicate = df_relations2.iloc[i]['predicate']
        r = session.run(
            "MATCH (a:DF_entity),(b:DF_entity) WHERE (a.uri='" + uri1 + "') and (b.uri='" + uri2 + "') CREATE (a)-[r:" + predicate + "]->(b)")
    except:
        driver = GraphDatabase.driver("bolt://ec2-54-169-74-170.ap-southeast-1.compute.amazonaws.com:7687",
                                      auth=basic_auth("neo4j", "offshore"))
        session = driver.session()

####################################
# simplify data structure for further steps (build direct links)
####################################
# build direct link between matched DF entities and offshore entities
# match (a:Entity)<-[:OFFICER_OF]-(b:Officer)-[:norm_name_to]->(c:Officer_norm)-[:match_to]->(d:DF_entity)
# create (a)<-[:connect_to_offshore_entity]-(d)
#
# # build direct link between non-matched officers and offshore entities
# match (a:Entity)<-[:OFFICER_OF]-(:Officer)-[:norm_name_to]->(c:Officer_norm)
# where not (c)-[:match_to]->(:DF_entity)
# create (a)<-[:connect_to_offshore_entity]-(c)


total = 1000000
step = 10000

for i in range(0, total, step):
    r = session.run("""
        match (a:Entity)<-[:OFFICER_OF]-(:Officer)-[:norm_name_to]->(c:Officer_norm)
        where not (c)-[:match_to]->(:DF_entity)
        with a,c
        skip """ + str(i) + """
        limit """ + str(step) + """
        create (a)<-[:connect_to_offshore_entity]-(c)
    """)
    print('complete ' + str(i))

# entity base for query
total = 1000000
step = 10000

for i in range(0, total, step):
    r = session.run("""
        match (a:Entity)<-[:connect_to_offshore_entity]-(b:Officer_norm)
        with distinct b
        skip """ + str(i) + """
        limit """ + str(step) + """
        set b.searchable=1,b.category=b.type
    """)
    print('complete ' + str(i))

for i in range(0, total, step):
    r = session.run("""
        match (a:DF_entity)
        with a,
        (case when a.type='expert' then 'individual' else 'organization' end) as category,
        (case when a.type='expert' then a.given_name_attr+' '+a.family_name_attr else a.label end) as name
        skip """ + str(i) + """
        limit """ + str(step) + """
        set a.searchable=1,a.category=category,a.name=name
    """)
    print('complete ' + str(i))

####################################
# scoring algorithm
####################################
# weight of a relation type
with open('relation_weight.txt') as f:
    weight = {}
    for l in f:
        if l.split('\t')[0] != 'Relation':
            weight[l.split('\t')[0]] = float(l.split('\t')[-1])


def relation_weight(rel):
    return weight[rel] if rel in weight else 0.2


# given 2 nodes, get the max score for all relations between them
def relation_score(id1, id2):
    r = session.run("""
        match (a)-[r]-(b)
        where ID(a)=""" + str(id1) + """ and ID(b)=""" + str(id2) + """
        return r
    """)
    r1 = list(r)
    types = [x[0].type for x in r1]
    scores = [relation_weight(x) for x in types]
    max_score = max(scores)
    return {'types': types, 'scores': scores, 'max_score': max_score}


# decay function
def decay(i):
    return np.exp(-i)


# score of a given path
def path_score(path):
    score = 1
    if len(path) > 2:
        for i in range(len(path) - 2):
            id1 = path[-3 - i]
            id2 = path[-2 - i]
            score = score * decay(1) * relation_score(id1, id2)['max_score']
    return score


# calculate offshore score given a Node ID, by aggregating the scores of all shortest paths to offshore entities.
def paths_to_offshore(target_id):
    r = session.run("""
        match p=(a)-[*1..3]-(b:Entity)
        where (not b.countries in ['Hong Kong','Switzerland','Luxembourg','United Kingdom','United Arab Emirates','Singapore','Russia','United States','China','Monaco','Taiwan']) and 
        all(x in nodes(p)[1..-2] WHERE labels(x)=['DF_entity']) and
        ID(a)=""" + str(target_id) + """
        with distinct a,b
        match p1=shortestPath((a)-[*]-(b))
        where all(x in nodes(p1)[1..-2] WHERE labels(x)=['DF_entity'])
        return nodes(p1) limit 100
    """)
    r1 = list(r)
    paths = [[node.id for node in path[0]] for path in r1]
    scores = [path_score(path) for path in paths]
    total_score = sum(scores)
    return {'paths': paths, 'scores': scores, 'total_score': total_score}


####################################
# scoring process
####################################
node_id = []

total = 1000000
step = 10000

for i in range(0, total, step):
    r = session.run("""
        match (a)
        where a.searchable=1
        return ID(a)
        skip """ + str(i) + """
        limit """ + str(step)
                    )
    r1 = list(r)
    node_id += [x[0] for x in r1]
    print('complete ' + str(i))

with open('offshore_score.txt', 'a') as f:
    for i in range(len(node_id)):
        r = f.write(str(node_id[i]) + '|' + str(paths_to_offshore(node_id[i])['total_score']) + '\n')
        if i % 1000 == 0:
            print('complete ' + str(i) + '/' + str(len(node_id)) + ' at ' + str(datetime.datetime.now()))

offshore_score = pd.read_csv('offshore_score.txt', header=None, names=['node_id', 'score'], sep='|')
offshore_score = offshore_score.drop_duplicates('node_id').sort_values('score', ascending=False)
offshore_score = offshore_score[offshore_score['score'] > 0]
limit = np.percentile(offshore_score['score'], q=99)
offshore_score = offshore_score[offshore_score['score'] < limit]

# convert score to percentile
offshore_score['score_norm'] = [int(np.ceil(x)) for x in offshore_score['score'].rank(pct=True) * 100]

offshore_score.to_csv('offshore_score_sorted.txt', index=False)

####################################
# write scores to nodes
####################################
offshore_score = pd.read_csv('offshore_score_sorted.txt')

for i in range(len(offshore_score)):
    r = session.run("""
        match (a)
        where ID(a)=""" + str(int(offshore_score.iloc[i]['node_id'])) + """
        set a.offshore_score=""" + str(offshore_score.iloc[i]['score']) + """,
        a.offshore_score_norm=""" + str(int(offshore_score.iloc[i]['score_norm']))
                    )
    if i % 1000 == 0:
        print('complete ' + str(i) + '/' + str(len(offshore_score)) + ' at ' + str(datetime.datetime.now()))
