from neo4j import GraphDatabase 

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "test1234" 
_driver = None

def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    return _driver

def close_driver():
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None

def db_connect():
    """
    Connect to the Neo4j database and return a session.
    """
    return get_driver().session()

def create_db_info(name, link):
    """
    Create, if it does not exist, a DB_info node.
    """
    with get_driver().session() as session: 
        params = {
            'name_val': name, 
            'link_val': link
        }
        session.run("""
            MERGE (d:DB_info {name: $name_val, link: $link_val})
        """, params)

def create_relation_info(name, source_db_link, min_value, max_value, cut_off):
    """
    Create (or update) a Relation_general_info node.
    """
    with get_driver().session() as session:
        params = {
            'name_val': name,
            'source_db_link_val': source_db_link,
            'min_value_val': min_value,
            'max_value_val': max_value,
            'cut_off_val': cut_off
        }
        session.run("""
            MERGE (r:Relation_general_info {name: $name_val})
            SET r.source_db_link = $source_db_link_val,
                r.min_value = $min_value_val,
                r.max_value = $max_value_val,
                r.cut_off = $cut_off_val
        """, params)