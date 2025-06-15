import sys
import os
from collections import defaultdict

import ncbi
import uniprot
import ensembl
from dbhelper import db_connect, create_db_info, create_relation_info

if len(sys.argv) < 3:
    print("Usage: %s <tsv_file_path> <relation name property, ex. MyInteraction>" % sys.argv[0])
    exit()

tsv_file_path = sys.argv[1]
relation_name_property = sys.argv[2]
BATCH_SIZE = 5000

species = {
    'hsa': 'Homo sapiens',
}

session = db_connect()

create_db_info('RNA22', 'https://cm.jefferson.edu/rna22/')
source_db_link = 'https://cm.jefferson.edu/data-tools-downloads/rna22-full-sets-of-predictions/'

min_value = float('inf')
max_value = float('-inf')
default_score_for_tsv = 0.0

if not os.path.exists(tsv_file_path):
    print(f"Error: TSV file not found: {tsv_file_path}")
    sys.exit(1)

print(f"Processing TSV file: {tsv_file_path}")

def process_batch(batch, session):
    if not batch:
        return
    
    # Prepare batch parameters
    batch_params = []
    for item in batch:
        batch_params.append({
            'miRNAname': item['miRNAname'],
            'target': item['target'],
            'relation': item['relation'],
            'score': item['score'],
            'miRNA': item['miRNA']
        })
    
    # Create relationships in batch
    query = """
    UNWIND $batch as row
    MATCH (m:microRNA {name: row.miRNAname}), (t:Target {ens_code: row.target})
    MERGE (m)-[r:RNA22 {name: row.relation, source_microrna: row.miRNA, source_target: row.target}]->(t)
    ON CREATE SET r.score = row.score
    """
    
    session.run(query, {'batch': batch_params})
    print(f"Processed batch of {len(batch)} records")

# Initialize batch
current_batch = []
total_processed = 0

with open(tsv_file_path, 'r') as f_tsv:
    header = next(f_tsv, None)  

    for line_num, line in enumerate(f_tsv, 1):
        line = line.strip()
        if not line:
            continue

        data_cols = line.split('\t')
        if len(data_cols) < 3:
            print(f"Warning: Line {line_num} in '{tsv_file_path}' has < 3 columns. Skipping: '{line}'")
            continue

        try:
            score_val = float(data_cols[2])
        except ValueError:
            print(f"Warning: Line {line_num}: Invalid score '{data_cols[2]}'. Using default score 0.0.")
            score_val = default_score_for_tsv

        if score_val < min_value: min_value = score_val
        if score_val > max_value: max_value = score_val

        params = {
            'miRNA': data_cols[0],
            'miRNAname': data_cols[0].replace('_', '-'),
            'target': data_cols[1],
            'relation': relation_name_property,
            'score': str(score_val)
        }

        current_species_prefix = None
        try:
            current_species_prefix = params['miRNAname'].split('-')[0].lower()
            if current_species_prefix not in species:
                print(f"Warning: Line {line_num}: Species prefix '{current_species_prefix}' is not recognized.")
        except IndexError:
            print(f"Warning: Line {line_num}: Could not extract species prefix from '{params['miRNAname']}'.")

        # Check if miRNA exists
        r_mirna = session.run(
            "MATCH (m:microRNA) "
            "WHERE m.name =~ ('(?i)' + $miRNAname) "
            "RETURN m.name AS name, m.accession AS accession LIMIT 1",
            {'miRNAname': params['miRNAname']}
        )
        mirna_record = r_mirna.single()

        if not mirna_record:
            print(f"Info: Line {line_num}: microRNA '{params['miRNAname']}' not found. Skipping.")
            continue
        else:
            if mirna_record['name'] != params['miRNAname']:
                params['miRNAname'] = mirna_record['name']

        # Check if target exists, create if not
        r_target = session.run(
            "MATCH (t:Target {ens_code:$target}) RETURN t LIMIT 1",
            {'target': params['target']}
        )
        target_node_exists = r_target.single()

        if not target_node_exists:
            gene_info = ncbi.get_gene_by_ens(params['target']) or \
                        uniprot.get_gene_by_ens(params['target']) or \
                        ensembl.get_gene_by_id(params['target'])

            if gene_info is None:
                print(f"Warning: Line {line_num}: Could not fetch info for target '{params['target']}'. Skipping.")
                continue

            if gene_info.get('species', '') == '':
                gene_info['species'] = species.get(current_species_prefix, 'Unknown')

            final_gene_props = {
                'name': gene_info.get('name'),
                'species': gene_info.get('species'),
                'geneid': str(gene_info.get('id')),
                'ens_code': params['target'],
                'ncbi_link': str(gene_info.get('id'))
            }

            session.run(
                "MERGE (t:Target {ens_code: $ens_code}) "
                "ON CREATE SET t.name = $name, t.species = $species, "
                "t.geneid = $geneid, t.ncbi_link = $ncbi_link",
                final_gene_props
            )

        # Add to current batch
        current_batch.append(params)
        
        # Process batch if it reaches the batch size
        if len(current_batch) >= BATCH_SIZE:
            process_batch(current_batch, session)
            total_processed += len(current_batch)
            print(f"Total processed so far: {total_processed}")
            current_batch = []

# Process any remaining records
if current_batch:
    process_batch(current_batch, session)
    total_processed += len(current_batch)

create_relation_info(relation_name_property, source_db_link, min_value, max_value, default_score_for_tsv)

session.close()
print(f"Finished processing '{tsv_file_path}'. Total records processed: {total_processed}")
