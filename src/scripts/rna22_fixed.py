import sys
import os

import ncbi
import uniprot
import ensembl
from dbhelper import db_connect, create_db_info, create_relation_info

if len(sys.argv) < 3:
    print("Usage: %s <tsv_file_path> <relation name property, ex. MyInteractions>" % sys.argv[0])
    exit()

tsv_file_path = sys.argv[1]
relation_name_property = sys.argv[2]

species = {
    'mmu': 'Mus musculus',
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

        result_rel = session.run(
            "MATCH (m:microRNA {name:$miRNAname}), (t:Target {ens_code:$target}) "
            "MERGE (m)-[r:RNA22 {name:$relation, source_microrna:$miRNA, source_target:$target}]->(t) "
            "ON CREATE SET r.score = $score "
            "RETURN r",
            params
        )

        summary = result_rel.consume()
        if summary.counters.relationships_created > 0:
            print(f"Info: Line {line_num}: Created: {params['miRNAname']} -> {params['target']} with score {params['score']}")
        else:
            print(f"Info: Line {line_num}: Relationship already exists: {params['miRNAname']} -> {params['target']}")

create_relation_info(relation_name_property, source_db_link, min_value, max_value, default_score_for_tsv)

session.close()
print(f"Finished processing '{tsv_file_path}'.")
