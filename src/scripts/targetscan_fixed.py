import sys
import ncbi
import uniprot
import ensembl
from dbhelper import db_connect, create_db_info, create_relation_info

mirbase_aliases = '../data/mirbase/aliases.txt'

# Check for command line arguments
if len(sys.argv) < 3:
    print("Usage: %s <targetscan data file> <species prefix, ex. mmu>" % sys.argv[0])
    exit()

# Data file
data_file = sys.argv[1]

# Species prefix
species = sys.argv[2]

# Dictionary for species prefix to species id mapping
# http://www.targetscan.org/mmu_61/docs/species.html
speciesid = {
    'mmu' : ['Mus musculus', '10090']
}

# Open a connection to the db
session = db_connect()

# Create the DB_info node
create_db_info('TargetScan', 'http://www.targetscan.org')

# TargetScan data source link
source_db_link = 'http://www.targetscan.org/mmu_71/mmu_71_data_download/Conserved_Family_Conserved_Targets_Info.txt.zip'

# Min and max value of the score
min_value = 0
max_value = 0

# Process data
with open(data_file, 'r') as f:

    # Skip the first line containing headers
    f.readline()

    for line in f:
        row = line.split()

        # Filter by species
        if row[4] != speciesid[species][1]:
            continue

        # The case of multiple miRNA on one line
        # Fix missing 'miR' in multiple miRNA per line
        mirnas = [e if e.startswith('mi') else 'miR-' + e
                    for e in row[0].split('/')]

        # Loop over the list of miRNA
        # (even if it contains just one element)
        for mirna in mirnas:

            # Select the data we need
            params = {
                'miRNA'     : mirna,
                'miRNAname' : species + '-' + mirna,
                'target'    : row[1],
                'ens'       : row[1][:row[1].find('.')],
                'relation'  : 'TargetScan',
                'score'     : row[10]
            }

            # Save min and max value
            try:
                score = float(params['score'])
                if score < min_value: min_value = score
                if score > max_value: max_value = score
            except:
                pass

            # Check if we can find a matching microRNA
            r = session.run("MATCH (m:microRNA)"
                            "WHERE m.name =~ ('(?i)'+{miRNAname})"
                           "RETURN m", params)
            try:
                r.peek()
            except exceptions.ResultError:

                found = False

                # Try to find the microRNA in the mirbase aliases
                with open(mirbase_aliases, 'r') as f:
                    for line in f:
                        if params['miRNAname'] + ';' in line:
                            r = session.run("MATCH (m:microRNA "
                                            "{accession:'%s'}) RETURN m" %
                                           line.split()[0])
                            try:
                                params['miRNAname'] = r.single()['m']['name']
                            except:
                                print("microRNA found in mirbase"
                                      "aliases but not in DB: %s" %
                                      params['miRNAname'])
                            found = True

                # Add the new microRNA node
                if not found and '.' in params['miRNAname']:
                    session.run("CREATE (m:microRNA {"
                                "name:'%s', species:'%s'})" %
                               (params['miRNAname'], speciesid[species][0]))
                    continue

                if not found:
                    print("Cannot find microRNA node: %s" %
                          params['miRNAname'])
                    continue

            # Check if we can find a matching target using the Ensembl
            r = session.run("MATCH (t:Target {ens_code:{ens}}) RETURN t",
                            params)
            try:
                r.peek()
            except exceptions.ResultError:
                gene = None

                # Try to find the new gene info on NCBI
                gene = ncbi.get_gene_by_ens(params['ens'])

                # Try to find the Ensembl on UniProt
                if gene is None:
                    gene = uniprot.get_gene_by_ens(params['ens'])

                # Try to find the Ensembl on ensembl.org
                if gene is None:
                    gene = ensembl.get_gene_by_id(params['ens'])
                    if gene is not None and gene['species'] == '':
                        gene['species'] = speciesid[species][0]

                if gene is None:
                    print("Cannot find Target node with Ensembl: %s" %
                      params['ens'])
                    continue
                session.run("MERGE (t:Target {"
                              "name:{name},"
                              "species:{species},"
                              "geneid:{id},"
                              "ens_code:{embl},"
                              "ncbi_link:{id}"
                            "})", gene)

            # Execute the query
            r = session.run("MATCH"
                              "(m:microRNA),"
                              "(t:Target {ens_code:{ens}})"
                            "WHERE m.name =~ ('(?i)'+{miRNAname})"
                            "CREATE (m)-[:TargetScan "
                              "{name:{relation},"
                              "score:{score},"
                              "source_microrna:{miRNA},"
                              "source_target:{target}}]->(t)",
                            params).consume()

            # Check if the relationship was created
            if not r.counters.contains_updates:
                print("Duplicate entry: %s" % r.parameters)
            else:
                print(params)

# Create the Relation_general_info node
create_relation_info('TargetScan', source_db_link, min_value, max_value, 0)

# Close the db session
session.close()
