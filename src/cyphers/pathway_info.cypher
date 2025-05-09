neo4j cypher for adding pathways :

// STAT4
MATCH (g:Target {name: 'STAT4'})
MERGE (p1:Pathway {id: 'mmu04217', name: 'Necroptosis'})
MERGE (g)-[:PART_OF]->(p1)
MERGE (p2:Pathway {id: 'mmu04630', name: 'JAK-STAT signaling pathway'})
MERGE (g)-[:PART_OF]->(p2)
MERGE (p3:Pathway {id: 'mmu04658', name: 'Th1 and Th2 cell differentiation'})
MERGE (g)-[:PART_OF]->(p3)
MERGE (p4:Pathway {id: 'mmu05161', name: 'Hepatitis B'})
MERGE (g)-[:PART_OF]->(p4)
MERGE (p5:Pathway {id: 'mmu05200', name: 'Pathways in cancer'})
MERGE (g)-[:PART_OF]->(p5)
MERGE (p6:Pathway {id: 'mmu05321', name: 'Inflammatory bowel disease'})
MERGE (g)-[:PART_OF]->(p6)

WITH 1 AS dummy

// SIK2
MATCH (g:Target {name: 'SIK2'})
MERGE (p:Pathway {id: 'mmu04922', name: 'Glucagon signaling pathway'})
MERGE (g)-[:PART_OF]->(p)

WITH 1 AS dummy

// RAB31
MATCH (g:Target {name: 'RAB31'})
MERGE (p:Pathway {id: 'mmu04144', name: 'Endocytosis'})
MERGE (g)-[:PART_OF]->(p)

WITH 1 AS dummy

// GADL1
MATCH (g:Target {name: 'GADL1'})
MERGE (p1:Pathway {id: 'mmu00410', name: 'beta-Alanine metabolism'})
MERGE (g)-[:PART_OF]->(p1)
MERGE (p2:Pathway {id: 'mmu00430', name: 'Taurine and hypotaurine metabolism'})
MERGE (g)-[:PART_OF]->(p2)
MERGE (p3:Pathway {id: 'mmu00770', name: 'Pantothenate and CoA biosynthesis'})
MERGE (g)-[:PART_OF]->(p3)
MERGE (p4:Pathway {id: 'mmu01100', name: 'Metabolic pathways'})
MERGE (g)-[:PART_OF]->(p4)

WITH 1 AS dummy

// PSN2
MATCH (g:Target {name: 'PSN2'})
MERGE (p1:Pathway {id: 'mmu00062', name: 'Fatty acid elongation'})
MERGE (g)-[:PART_OF]->(p1)
MERGE (p2:Pathway {id: 'mmu01040', name: 'Biosynthesis of unsaturated fatty acids'})
MERGE (g)-[:PART_OF]->(p2)
MERGE (p3:Pathway {id: 'mmu01100', name: 'Metabolic pathways'})
MERGE (g)-[:PART_OF]->(p3)
MERGE (p4:Pathway {id: 'mmu01212', name: 'Fatty acid metabolism'})
MERGE (g)-[:PART_OF]->(p4)
