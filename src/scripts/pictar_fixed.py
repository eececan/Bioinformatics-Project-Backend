# --- START OF FILE pictar_fixed.py ---
import sys
import csv
from dbhelper import db_connect, create_db_info, create_relation_info, close_driver
from ncbi import get_geneid_by_refseq, get_gene_by_id # Ensure ncbi.py is updated
from neo4j.exceptions import ResultError # For Neo4j specific exceptions

# This file needs to exist and map PicTar miRNA names to miRBase accessions
# if PicTar names are not directly usable or if they are older versions.
# Format: pictar_mirna_name\tmiRBase_accession (e.g., mmu-mir-1\tMIMAT0000123)
# If PicTar uses standard miRBase names, this might not be strictly needed,
# but the miRNA2accession function would then search against your main miRBase import.
PICTAR_MIRNA_ACCESSION_MAP_FILE = '../data/pictar/mirna_accession.dat'

def miRNA2accession(pictar_miRNA_name, session):
    """
    Tries to find a miRBase accession for a PicTar miRNA name.
    1. Checks a specific PicTar to miRBase accession map file.
    2. If not found, tries to match pictar_miRNA_name (or variants) against
       existing :microRNA nodes in Neo4j by name to get their accession.
    """
    try:
        with open(PICTAR_MIRNA_ACCESSION_MAP_FILE, 'r') as f_map:
            for line in f_map:
                parts = line.strip().split('\t')
                if len(parts) == 2 and parts[0].lower() == pictar_miRNA_name.lower():
                    print(f"PicTar Map: Found accession {parts[1]} for {pictar_miRNA_name}")
                    return parts[1]
    except FileNotFoundError:
        print(f"Warning: PicTar miRNA accession map file not found: {PICTAR_MIRNA_ACCESSION_MAP_FILE}. Will try direct DB match.")

    # Try matching in Neo4j by name (case-insensitive)
    # PicTar names like "mmu-miR-20a" or "miR-20a"
    # Standardize PicTar name for matching if needed (e.g., add 'mmu-' if missing)
    standardized_pictar_name = pictar_miRNA_name
    if not pictar_miRNA_name.lower().startswith("mmu-"): # Assuming Mus Musculus context
         # This is a guess, actual PicTar format needs checking
        if pictar_miRNA_name.lower().startswith("mir-"):
             standardized_pictar_name = "mmu-" + pictar_miRNA_name
        else: # e.g. "let-7a"
             standardized_pictar_name = "mmu-" + pictar_miRNA_name # Might be wrong for some cases

    # Try variants
    name_variants = [
        pictar_miRNA_name,
        standardized_pictar_name,
        pictar_miRNA_name.replace("_", "-"),
        standardized_pictar_name.replace("_", "-")
    ]
    name_variants = list(set(n.lower() for n in name_variants)) # Unique, lowercased

    for name_var in name_variants:
        query = "MATCH (m:microRNA) WHERE toLower(m.name) = $name_var RETURN m.accession AS acc LIMIT 1"
        result = session.run(query, name_var=name_var)
        record = result.single()
        if record and record["acc"]:
            print(f"Neo4j Match: Found accession {record['acc']} for PicTar miRNA variant '{name_var}' (original: {pictar_miRNA_name})")
            return record["acc"]
    
    print(f"⚠️ Could not find miRBase accession for PicTar miRNA: {pictar_miRNA_name}")
    return None


if len(sys.argv) < 3:
    print("Usage: %s <PicTar .bed file> <RelationName (e.g., PicTar7 or PicTar13)>" % sys.argv[0])
    sys.exit(1)

pictar_bed_file = sys.argv[1]
relation_name_arg = sys.argv[2] # e.g., "PicTar7" or "PicTar13"

print(f"Processing PicTar BED file: {pictar_bed_file} for relation: {relation_name_arg}")

create_db_info('PicTar', 'http://pictar.mdc-berlin.de/') # Original site might be down
source_db_link = 'http://genome.ucsc.edu/cgi-bin/hgTables' # Where data was likely downloaded
min_score_val = float('inf')
max_score_val = float('-inf')

try:
    with db_connect() as session:
        with open(pictar_bed_file, 'r', encoding='utf-8') as bedfile_handle:
            reader = csv.reader(bedfile_handle, delimiter='\t')
            
            processed_count = 0
            created_relations_count = 0

            for i, row in enumerate(reader):
                if not row or len(row) < 5: # BED format usually has at least chrom, start, end, name, score
                    print(f"Skipping malformed BED row {i+1}: {row}")
                    continue

                # BED format for PicTar (from PDF):
                # col 0: chrom (e.g. chr1)
                # col 1: chromStart
                # col 2: chromEnd
                # col 3: name (e.g. NM_008866:mmu-miR-10a-5p or targetID:miRNA_name)
                # col 4: score
                # col 5: strand (+/-)
                
                name_field_parts = row[3].split(':')
                if len(name_field_parts) != 2:
                    print(f"Skipping row {i+1} due to unexpected name field format: {row[3]}")
                    continue
                
                target_refseq_tool = name_field_parts[0] # This is a RefSeq ID (e.g., NM_xxxxx, NR_xxxxx)
                mirna_name_tool = name_field_parts[1]   # e.g., mmu-miR-10a-5p

                params = {
                    'pictar_mirna_name': mirna_name_tool,
                    'target_refseq_tool': target_refseq_tool,
                    'tool_score_val': row[4],
                    'relation_name_val': relation_name_arg
                }

                try:
                    score = float(params['tool_score_val'])
                    if score < min_score_val: min_score_val = score
                    if score > max_score_val: max_score_val = score
                except ValueError:
                    print(f"Warning: Could not parse score '{params['tool_score_val']}' for row {i+1}. Setting to 0.")
                    params['tool_score_val'] = 0.0 # Default or skip

                # 1. Get miRBase accession for the PicTar miRNA
                standard_mirna_accession = miRNA2accession(params['pictar_mirna_name'], session)
                if not standard_mirna_accession:
                    print(f"⚠️ Could not map PicTar miRNA '{params['pictar_mirna_name']}' to a miRBase accession. Skipping row {i+1}.")
                    continue
                params['standard_mirna_accession'] = standard_mirna_accession

                # 2. Get GeneID for the RefSeq target
                standard_target_geneid = get_geneid_by_refseq(params['target_refseq_tool']) # from ncbi.py
                if not standard_target_geneid:
                    print(f"⚠️ Could not get GeneID for RefSeq '{params['target_refseq_tool']}'. Skipping row {i+1}.")
                    continue
                params['standard_target_geneid'] = standard_target_geneid

                # 3. Ensure Target node exists (or create it)
                target_node_query = "MATCH (t:Target {geneid: $standard_target_geneid}) RETURN t.name LIMIT 1"
                target_result = session.run(target_node_query, params)
                if not target_result.single():
                    print(f"Target node for GeneID '{params['standard_target_geneid']}' not found. Fetching from NCBI.")
                    gene_details = get_gene_by_id(params['standard_target_geneid'])
                    if gene_details:
                        create_target_params = {
                            'p_name': gene_details.get('name'), 'p_species': gene_details.get('species'),
                            'p_geneid': gene_details.get('id'), 'p_ens_code': gene_details.get('embl', ''),
                            'p_ncbi_link': gene_details.get('id')
                        }
                        if not all(create_target_params.values()): print(f"Warning: Incomplete gene details for {params['standard_target_geneid']}")

                        session.run("""
                            MERGE (t:Target {geneid: $p_geneid})
                            ON CREATE SET t.name = $p_name, t.species = $p_species, t.ens_code = $p_ens_code, t.ncbi_link = $p_ncbi_link
                            ON MATCH SET t.name = $p_name, t.species = $p_species, t.ens_code = $p_ens_code
                        """, create_target_params)
                        print(f"➕ Created/Merged Target node (GeneID: {params['standard_target_geneid']})")
                    else:
                        print(f"❌ Could not fetch details for GeneID {params['standard_target_geneid']}. Skipping row {i+1}.")
                        continue
                
                # 4. Create the :PicTar relationship
                create_relation_query = f"""
                MATCH (mir:microRNA {{accession: $standard_mirna_accession}})
                MATCH (gene:Target {{geneid: $standard_target_geneid}})
                CREATE (mir)-[r:{relation_name_arg} {{ 
                    tool_name: $relation_name_val,
                    score: toFloat($tool_score_val), 
                    source_microrna: $pictar_mirna_name,
                    source_target_refseq: $target_refseq_tool
                }}]->(gene)
                RETURN id(r)
                """
                try:
                    result = session.run(create_relation_query, params)
                    if result.single():
                        created_relations_count += 1
                    else:
                         print(f"⚠️ Relationship {relation_name_arg} not created for {params['pictar_mirna_name']} -> {params['target_refseq_tool']}. Row {i+1}")
                except Exception as e:
                    print(f"❌ Error creating {relation_name_arg} relationship for row {i+1}: {e}")

                processed_count +=1
                if processed_count % 500 == 0:
                    print(f"Processed {processed_count} PicTar rows...")
            
            print(f"Finished PicTar processing. Total rows: {processed_count}. Relationships created: {created_relations_count}")
            create_relation_info(relation_name_arg, source_db_link, min_score_val, max_score_val, 0) # Assuming cut_off is 0

except FileNotFoundError:
    print(f"Error: PicTar BED file not found at {pictar_bed_file}")
except Exception as e:
    print(f"An critical error occurred during PicTar processing: {e}")
finally:
    close_driver()

print("PicTar import finished.")