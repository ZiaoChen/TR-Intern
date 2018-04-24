# -*- coding: utf-8 -*-
from paradise_papers_aws import *
import urllib3

def write_json_2_neo4j_entity(json_x, label):
    row1 = "{"
    for field in json_x:
        try:
            value = str(json_x[field])
        except:
            value = json_x[field]
        for remove_char in ['"', "'", '\\']:
            value = value.replace(remove_char, '')
        for remove_char in ['.', '(', ')', '-']:
            field = field.replace(remove_char, '_')
        row1 += field + ":'" + value + "',"
    row1 = row1.strip(',') + "}"
    r = session.run("MERGE (a:" + label + " " + row1 + ") ON CREATE SET a:New")
    return 1

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
        all(x in nodes(p)[1..-2] WHERE labels(x)=['DF_entity'] OR labels(x)=['DF_entity','New']) and
        ID(a)=""" + str(target_id) + """
        with distinct a,b
        match p1=shortestPath((a)-[*]-(b))
        where all(x in nodes(p1)[1..-2] WHERE labels(x)=['DF_entity'] OR labels(x)=['DF_entity','New'])
        return nodes(p1) limit 100
    """)
    r1 = list(r)
    paths = [[node.id for node in path[0]] for path in r1]
    scores = [path_score(path) for path in paths]
    total_score = sum(scores)
    return {'paths': paths, 'scores': scores, 'total_score': total_score}


if __name__ == '__main__':
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
    pwd = 'datafusion'
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

    names_norm = set([normalize_name(str(x)) for x in names])
    print("All names are normalized")

    # for name in names_norm:
    #     r = session.run("CREATE (a:Officer_norm:New {name:'" + name + "',type:'" + name_type(name) + "'})")

    print("Officer_norm created")

    # create link from original name to normalized name
    # for name in names:
    #     name = str(name)
    #     name_norm = normalize_name(name)
    #     for remove_char in ['"', "'", '\\']:
    #         name = name.replace(remove_char, '')
    #     r = session.run(
    #         "MATCH (a:Officer:New),(b:Officer_norm:New) WHERE (a.name='" + name + "') and (b.name='" + name_norm + "') CREATE (a)-[r:norm_name_to]->(b)")

    print("All links from officer to officer_norm created")

    # with open('matched_df_uri.txt', 'w') as f:
    #     uri = search_entities(list(names_norm))
    #     for x in uri:
    #         r = f.write(json.dumps(x) + '\n')

    headers = get_token_headers()
    search_entities(list(names_norm), headers)

    print("Officers Matched with Data Fusion")


    ####################################
    # screen searching results, to remove low-confidence matches
    ####################################
    uri = []

    with open('matched_df_uri.txt', 'rb') as f:
        for l in f:
            uri.append(json.loads(l.strip('\n')))
    print("Match Data Fusion Entity Retrieved")
    uri1 = screen_df_results(uri)
    print("Low confidence entities filtered")

    ####################################
    # expand networks from matched results
    ####################################

    # 1 degree
    uri_list = list(set([str(x['uri']) for x in uri1]))
    chunk_size = 100
    uri_chunks = [uri_list[i:i + chunk_size] for i in range(0, len(uri_list), chunk_size)]

    f_entities = open('degree_1_entities.txt', 'w')
    f_paths = open('degree_1_paths.txt', 'w')
    for i in range(len(uri_chunks)):
        print("Retrieving degree 1 DF entities: %d / %d" %(i, len(uri_chunks)))
        try:
            connecteds = Parallel(n_jobs=-1)(delayed(get_connected_entities)(x, 100, headers) for x in uri_chunks[i])
            for connected in connecteds:
                for x in connected['entities']:
                    r = f_entities.write(json.dumps(x) + '\n')
                    f_entities.flush()
                for x in connected['paths']:
                    r = f_paths.write(json.dumps(x) + '\n')
                    f_paths.flush()
        except:
            time.sleep(5)
        if i % 10 == 0:
            print(str(i) + '/' + str(len(uri_chunks)) + ' completed at ' + str(datetime.datetime.now()))
    f_entities.close()
    f_paths.close()
    print("First Degree entities and paths stored")

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
    print(len(uri_chunks))
    for i in range(len(uri_chunks)):
        print("Retrieving degree 2 DF entities: %d / %d" % (i, len(uri_chunks)))
        try:
            connecteds = Parallel(n_jobs=-1)(delayed(get_connected_entities)(x, 100, headers) for x in uri_chunks[i])
            for connected in connecteds:
                for x in connected['entities']:
                    r = f_entities.write(json.dumps(x) + '\n')
                    f_entities.flush()
                for x in connected['paths']:
                    r = f_paths.write(json.dumps(x) + '\n')
                    f_paths.flush()
        except:
            time.sleep(5)
        if i % 10 == 0:
            print(str(i) + '/' + str(len(uri_chunks)) + ' completed at ' + str(datetime.datetime.now()))
    f_entities.close()
    f_paths.close()
    print("Second degree entities and paths stored")

    ####################################
    # upload DF matched results
    ####################################
    uri2 = {}
    for x in uri1:
        if x['uri'] not in uri2:
            uri2[x['uri']] = x

    uri2 = list(uri2.values())
    print("There are in total %d matched df entities to upload." % len(uri2))
    counter = 0
    for x in uri2:
        counter += 1
        r = write_json_2_neo4j_entity(x, 'DF_entity')
        print("Uploading matched DF entities: %d / %d" % (counter, len(uri2)))

    print("All matched DF_entities uploaded")
    # CREATE INDEX ON :DF_entity(uri)

    # build neo4j links
    counter = 0
    for x in uri1:
        counter += 1
        r = session.run(
            "MATCH (a:Officer_norm:New),(b:DF_entity) WHERE (a.name='" + x['source_name_norm'] + "') and (b.uri='" + x[
                'uri'] + "') CREATE (a)-[r:match_to]->(b)")
        print("Uploading links for matched DF entities: %d / %d" % (counter, len(uri1)))
    print("Links between DF_entity and officers built")

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
    print ("Existing DF entities retrieved")
    existing_uri = set([x['a.uri'] for x in r1])

    df_entities = {}

    for file_name in ['degree_1_entities.txt', 'degree_2_entities.txt']:
        with open(file_name) as f:
            for l in f:
                l1 = json.loads(l)
                if l1['uri'] not in existing_uri:
                    df_entities[l1['uri']] = l1

    df_entities1 = list(df_entities.values())

    counter = 0
    for x in df_entities1:
        counter += 1
        r = write_json_2_neo4j_entity(x, 'DF_entity')
        print("Uploading expanded DF entities: %d / %d" % (counter, len(df_entities1)))
    print("Expanded DF_entities uploaded")

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

    df_relations2.groupby('predicate',as_index=False).agg({'uri1':np.size}).sort_values('uri1',ascending=False)
    df_relations2.groupby('contextUri',as_index=False).agg({'uri1':np.size}).sort_values('uri1',ascending=False)['contextUri']
    print("Total Number of relations to be uploaded: %d" % len(df_relations2))

    for i in range(len(df_relations2)):
        try:
            uri1 = df_relations2.iloc[i]['uri1']
            uri2 = df_relations2.iloc[i]['uri2']
            predicate = df_relations2.iloc[i]['predicate']
            r = session.run(
                "MATCH (a:DF_entity),(b:DF_entity) WHERE (a.uri='" + uri1 + "') and (b.uri='" + uri2 + "') MERGE (a)-[r:" + predicate + "]->(b)")
        except:
            # driver = GraphDatabase.driver("bolt://ec2-54-169-74-170.ap-southeast-1.compute.amazonaws.com:7687",
            #                               auth=basic_auth("neo4j", "offshore"))
            driver = GraphDatabase.driver("bolt://ec2-13-228-37-181.ap-southeast-1.compute.amazonaws.com:7687",
                                          auth=basic_auth("neo4j", "chenziao"))
            session = driver.session()
        print("Uploading relations of expanded DF entities: %d / %d" % (counter, len(df_relations2)))

    print("All relations uploaded")

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

    total = 2000000
    step = 10000

    for i in range(0, total, step):
        r = session.run("""
            match (a:Entity:New)<-[:OFFICER_OF]-(:Officer:New)-[:norm_name_to]->(c:Officer_norm:New)
            where not (c)-[:match_to]->(:DF_entity)
            with a,c
            skip """ + str(i) + """
            limit """ + str(step) + """
            merge (a)<-[:connect_to_offshore_entity]-(c)
        """)
        print("Building links between offshore entities and officers: %d / %d" % (i, len(total/step)))

    # entity base for query
    total = 2000000
    step = 10000

    for i in range(0, total, step):
        r = session.run("""
            match (a:Entity)<-[:connect_to_offshore_entity]-(b:Officer_norm)
            with distinct b
            skip """ + str(i) + """
            limit """ + str(step) + """
            set b.searchable=1,b.category=b.type
        """)
        print("Indexing for all entities that needs to be scored: %d / %d" % (i, len(total / step)))

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
        print("Indexing for all entities that needs to be scored: %d / %d" % (i, len(total / step)))

    ####################################
    # scoring algorithm
    ####################################
    # weight of a relation type
    with open('relation_weight.txt') as f:
        weight = {}
        for l in f:
            if l.split('\t')[0] != 'Relation':
                weight[l.split('\t')[0]] = float(l.split('\t')[-1])

    ####################################
    # scoring process
    ####################################
    node_id = []

    total = 2000000
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
        print("Retrieving all entities that needs to be scored: %d / %d" % (i, len(total / step)))

    with open('offshore_score.txt', 'a') as f:
        for i in range(len(node_id)):
            r = f.write(str(node_id[i]) + '|' + str(paths_to_offshore(node_id[i])['total_score']) + '\n')
            f.flush()
            if i % 1000 == 0:
                print('Scoring ' + str(i) + '/' + str(len(node_id)) + ' at ' + str(datetime.datetime.now()))

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
