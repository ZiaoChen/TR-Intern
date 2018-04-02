from neo4j.v1 import GraphDatabase

# Connect to Neo4j server
driver = GraphDatabase.driver('bolt://ec2-13-228-37-181.ap-southeast-1.compute.amazonaws.com:7687')
# driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'chenziao'))
session = driver.session()

# # Remove all existing nodes first
# for i in range(200):
#     session.run("match (n:New)-[r]-() with r limit %d delete r" %10000)
# for i in range(200):
#     session.run("match (n:New) with n limit %d delete n" %10000)
# print("Nodes and Relationship cleaned")
#
# # Remove original nodes
# session.run("""match (n:Officer)
# where
# n.sourceID = 'Paradise Papers - Malta corporate registry' or
# n.sourceID = 'Paradise Papers - Barbados corporate registry' or
# n.sourceID = 'Paradise Papers - Bahamas corporate registry' or
# n.sourceID = 'Paradise Papers - Lebanon corporate registry'
# OPTIONAL MATCH (n)-[r]-()
# DELETE n, r
# """)
# session.run("""match (n:Entity)
# where
# n.sourceID = 'Paradise Papers - Malta corporate registry' or
# n.sourceID = 'Paradise Papers - Barbados corporate registry' or
# n.sourceID = 'Paradise Papers - Bahamas corporate registry' or
# n.sourceID = 'Paradise Papers - Lebanon corporate registry'
# OPTIONAL MATCH (n)-[r]-()
# DELETE n, r
# """)
# print ("Orginal nodes removed")
#
#
# # Insert Officer Nodes
# r = session.run("""
# USING PERIODIC COMMIT 500
# LOAD CSV WITH HEADERS FROM 'https://drive.google.com/uc?export=download&id=1zM1hoqFs6QTWOcwDn1pB9irBVGgwPkL7' AS csvLine
# with csvLine
# where csvLine.sourceID <> 'Paradise Papers - Appleby'
# create (p:Officer:New { node_id: csvLine.node_id, name: csvLine.name})
# SET
# p.sourceID = toString(csvLine.sourceID),
# p.country_codes = toString(csvLine.country_codes),
# p.countries = toString(csvLine.countries),
# p.status = toString(csvLine.status),
# p.valid_until = toString(csvLine.valid_until),
# p.note = toString(csvLine.note)""")
# print(list(r))
# print("All officer nodes were inserted")
#
# Insert Entity Nodes
a = session.run("""
USING PERIODIC COMMIT 500
LOAD CSV WITH HEADERS FROM 'https://drive.google.com/uc?export=download&id=1H7K2e4OaevLB1R2fn3on3utOPyBV1mIA' AS csvLine
with csvLine
where csvLine.sourceID <> 'Paradise Papers - Appleby'
create (p:Entity:New { node_id: csvLine.node_id, name: csvLine.name})
set
p.jurisdiction = toString(csvLine.jurisdiction),
p.jurisdiction_description = toString(csvLine.jurisdiction_description),
p.sourceID = toString(csvLine.sourceID),
p.country_codes = toString(csvLine.country_codes),
p.countries = toString(csvLine.countries),
p.incorporation_date = toString(csvLine.incorporation_date),
p.inactive_date = toString(csvLine.inactive_date),
p.struck_off_date = toString(csvLine.struck_off_date),
p.closed_date = toString(csvLine.closed_date),
p.ibcRUC = toString(csvLine.ibcRUC),
p.company_type = toString(csvLine.company_type),
p.service_provider = toString(csvLine.service_provider),
p.status = toString(csvLine.status),
p.valid_until = toString(csvLine.valid_until),
p.note = toString(csvLine.note)""")
print(list(a))
print("All entity nodes were inserted")

# Create index
a = session.run("""
create index on :New(node_id)
""")

# a = session.run("""
# create constraint on (g:Entity)
# assert g.node_id is UNIQUE
# """)
# print("Index on entity node id is created")
#
# a = session.run("""
# create index on :Officer(node_id)
# """)

# a = session.run("""
# create constraint on (g:Officer)
# assert g.node_id is UNIQUE """)

print("Index on node id is created")


# https://drive.google.com/uc?export=download&id=1JHYYnouF8nEf44r-F4A7cnOy4tjPbMjC
# Insert Edges
a = session.run("""
USING PERIODIC COMMIT 100
LOAD CSV WITH HEADERS FROM 'https://drive.google.com/uc?export=download&id=1gX9NLPGsQZYLFDcAcYO7SfLVAT3bJbuC' AS csvLine
with csvLine
match (from:New{node_id: toString(csvLine.START_ID)})
using index from:New(node_id)
match (to:New{node_id: toString(csvLine.END_ID)})
using index to:New(node_id)
with from, to, csvLine
where from.sourceID <> 'Paradise Papers - Appleby' and to.sourceID <> 'Paradise Papers - Appleby' and csvLine.TYPE = 'officer_of'
create (from)-[r:connect]->(to)
set
r.start_date = toString(csvLine.start_date),
r.end_date = toString(csvLine.end_date),
r.sourceID = toString(csvLine.sourceID),
r.valid_until = toString(csvLine.valid_until)
""")

print(list(a))
print("All edges were inserted")

# and csvLine.sourceID <> 'Paradise Papers - Malta corporate registry'
# and csvLine.sourceID <> 'Paradise Papers - Barbados corporate registry'
# and csvLine.sourceID <> 'Paradise Papers - Bahamas corporate registry'
# and csvLine.sourceID <> 'Paradise Papers - Lebanon corporate registry'