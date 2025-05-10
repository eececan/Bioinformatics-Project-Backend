
import sys
import re
from dbhelper import db_connect

"""
Store a microRNA in the db if not already there.
Return True if the new node is created.

Parameters
----------
miRNA : dict
    microRNA properties for the new node creation.
"""
def store_miRNA(miRNA):
    try:
        r = session.run("MATCH (m:microRNA {name: $id}) RETURN m", miRNA)
        record = r.single()
        if record:
            print(f"✅ Found existing microRNA in DB: {record['m']}")
        else:
            raise Exception("No match found")
    except Exception as e:
        print(f"⚠️ MATCH failed or not found for microRNA {miRNA['id']}: {e}")
        try:
            session.run("""
                CREATE (m:microRNA {
                    name: $id,
                    accession: $accession,
                    species: $species,
                    mirbase_link: $accession
                })
            """, miRNA)
            print(f"➕ Created new microRNA node: {miRNA['id']}")
            return True
        except Exception as e2:
            print(f"❌ CREATE failed for microRNA {miRNA['id']}: {e2}")
    return False

# Check command line arguments
if len(sys.argv) < 4:
    print("Usage: %s <mirbase .dat file> <species name, ex. 'Mus musculus'>"
          " <species prefix, ex. mmu>" % sys.argv[0])
    exit()

# Connect to the db
session = db_connect()

# Process the data file
with open(sys.argv[1], 'r') as f:
    data = {}
    in_data_block = False
    previous_line = ''

    for line in f:
        if line.startswith('ID') and line.split()[1].startswith(sys.argv[3]):
            in_data_block = True
            data = {'id': line.split()[1], 'species': sys.argv[2]}
            if previous_line.startswith('AC'):
                data['accession'] = line.split()[1]
                store_miRNA(data)

        elif in_data_block:
            if line.startswith('AC'):
                data['accession'] = line.split()[1][:-1]
                store_miRNA(data)

            if '/accession=' in line:
                data['accession'] = re.search(r'/accession="([^"]+)"', line).group(1)

            elif '/product=' in line:
                data['id'] = re.search(r'/product="([^"]+)"', line).group(1)
                store_miRNA(data)

            elif line.startswith('//'):
                in_data_block = False

        previous_line = line

# Close the session
session.close()
