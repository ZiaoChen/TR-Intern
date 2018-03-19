from neo4j.v1 import GraphDatabase

# Connect to Neo4j server
driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'chenziao'))
session = driver.session()

# Remove all existing nodes first
session.run("match (n) delete n")

# Insert Officer Nodes
r = session.run("""LOAD CSV WITH HEADERS FROM 'file:///paradise_papers.nodes.officer.csv' AS csvLine
with csvLine
where csvLine.sourceID <> 'Paradise Papers - Appleby'
Merge (p:Officer { node_id: csvLine.node_id, name: csvLine.name})
on create SET 
p.sourceID = toString(csvLine.sourceID),
p.country_codes = toString(csvLine.country_codes),
p.countries = toString(csvLine.countries),
p.status = toString(csvLine.status),
p.valid_until = toString(csvLine.valid_until),
p.note = toString(csvLine.note)""")
print(list(r))

# Insert Entity Nodes
a = session.run("""LOAD CSV WITH HEADERS FROM 'file:///paradise_papers.nodes.entity.csv' AS csvLine
with csvLine
where csvLine.sourceID <> 'Paradise Papers - Appleby'
Merge (p:Entity { node_id: csvLine.node_id, name: csvLine.name})
on create set
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

# Insert Edges
a = session.run("""LOAD CSV WITH HEADERS FROM 'file:///paradise_papers.nodes.entity.csv' AS csvLine
with csvLine
where csvLine.sourceID <> 'Paradise Papers - Appleby'
match (from{id: toString(csvLine.START_ID)})
match (to{id: toString(csvLine.END_ID)})
merge (from)-[r:csvLine.TYPE]->(to)
on create set
r.start_date = toString(csvLine.start_date),
r.end_date = toString(csvLine.end_date),
r.sourceID = toString(csvLine.sourceID),
r.valid_until = toString(csvLine.valid_until)""")