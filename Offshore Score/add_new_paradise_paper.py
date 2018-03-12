from neo4j.v1 import GraphDatabase

driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'chenziao'))
session = driver.session()
session.run("match (n) delete n")
r = session.run("""LOAD CSV WITH HEADERS FROM 'file:///paradise_papers.nodes.officer.csv' AS csvLine
Merge (p:Officer { node_id: csvLine.node_id, name: csvLine.name})
foreach (ignoreMe in case when csvLine.sourceID IS null THEN [] ELSE [1] END | SET p.sourceID = csvLine.sourceID)
foreach (ignoreMe in case when csvLine.country_codes IS null THEN [] ELSE [1] END | SET p.country_codes = csvLine.country_codes)
foreach (ignoreMe in case when csvLine.countries IS null THEN [] ELSE [1] END | SET p.countries = csvLine.countries)
foreach (ignoreMe in case when csvLine.status IS null THEN [] ELSE [1] END | SET p.status = csvLine.status)
foreach (ignoreMe in case when csvLine.valid_until IS null THEN [] ELSE [1] END | SET p.valid_until = csvLine.valid_until)
foreach (ignoreMe in case when csvLine.note IS null THEN [] ELSE [1] END | SET p.note = csvLine.note)""")
print (list(r))
