import sys
import csv
from dbhelper import db_connect, create_db_info, create_relation_info, close_driver

def run_tarbase_import(data_file_path):
    """
    Main function to import TarBase data into Neo4j for Homo sapiens.
    This version assumes all data pertains to Homo sapiens and processes it accordingly.
    """
    # --- Hardcoded Species Configuration ---
    TARGET_SPECIES = "Homo sapiens"

    print(f"🚀 Starting TarBase import for species: '{TARGET_SPECIES}'")
    print(f"📂 Processing data file: {data_file_path}")

    # --- Database and Link Information ---
    database_name_display = 'TarBase'
    data_source_link_specific = 'http://www.microrna.gr/tarbase'
    database_url_official = 'http://www.microrna.gr/tarbase'

    create_db_info(database_name_display, database_url_official)

    # --- Score Tracking and Counters ---
    min_score_val = float('inf')
    max_score_val = float('-inf')
    processed_rows_count = 0
    created_relationships_count = 0
    skipped_rows_count = 0

    # --- Batching Configuration ---
    batch_relationships = []
    BATCH_SIZE = 50  # Adjust as needed based on memory/performance

    try:
        with db_connect() as session:
            # --- Caching Existing Nodes for Performance ---
            print("🔍 Fetching all existing microRNA nodes into cache...")
            mirna_cache = set()
            mirna_fetch_query = "MATCH (m:microRNA) RETURN m.name"
            for record in session.run(mirna_fetch_query):
                mirna_cache.add(record['m.name'])
            print(f"✅ Cached {len(mirna_cache)} microRNA nodes.")

            print("🔍 Fetching all existing Target nodes (Ensembl ID) into cache...")
            target_cache = set()
            target_fetch_query = "MATCH (t:Target) WHERE t.species = $species RETURN t.ensembl_id"
            for record in session.run(target_fetch_query, species=TARGET_SPECIES):
                target_cache.add(record['t.ensembl_id'])
            print(f"✅ Cached {len(target_cache)} {TARGET_SPECIES} Target nodes.")

            # --- Processing the TarBase CSV File ---
            with open(data_file_path, mode='r', newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile, delimiter='\t')
                
                # Skip header
                header = next(reader)
                print(f"✅ Header detected and skipped: {header}")

                for i, row in enumerate(reader, start=2): # Start from line 2
                    # --- Data Validation and Extraction ---
                    if not row:
                        skipped_rows_count += 1
                        print(f"⚠️ Row {i}: Empty row. Skipping.")
                        continue

                    if len(row) < 21:
                        print(f"⚠️ Row {i}: Malformed (expected at least 21 columns, got {len(row)}). Skipping.")
                        skipped_rows_count += 1
                        continue

                    # Column mapping (species column `row[0]` is now ignored)
                    mirna_name_from_tool = row[1].strip()
                    mirna_id_from_tool = row[2].strip()
                    gene_name_from_tool = row[3].strip()
                    gene_id_from_tool = row[4].strip() # This is the Ensembl ID
                    confidence = row[17].strip()
                    microt_score_raw = row[20].strip()

                    # --- **REMOVED** species filtering logic ---

                    if not mirna_name_from_tool or not gene_id_from_tool:
                        print(f"⚠️ Row {i}: Missing required miRNA Name ('{mirna_name_from_tool}') or Gene ID ('{gene_id_from_tool}'). Skipping.")
                        skipped_rows_count += 1
                        continue
                    
                    # --- Score Handling ---
                    try:
                        score_float = float(microt_score_raw)
                        if score_float < min_score_val: min_score_val = score_float
                        if score_float > max_score_val: max_score_val = score_float
                    except (ValueError, TypeError):
                        score_float = 0.0 # Default score if not a valid number

                    # --- miRNA Node Check ---
                    potential_mirna_names = [mirna_name_from_tool, f"{mirna_name_from_tool}-3p", f"{mirna_name_from_tool}-5p"]
                    found_mirna_name = next((name for name in potential_mirna_names if name in mirna_cache), None)

                    if not found_mirna_name:
                        # Optional: Add a more detailed log if you want to see which specific miRNAs are being skipped
                        # print(f"ℹ️ Row {i}: microRNA '{mirna_name_from_tool}' not in cache. Skipping.")
                        skipped_rows_count += 1
                        continue

                    # --- Target (Gene) Node Check and Creation ---
                    if gene_id_from_tool not in target_cache:
                        merge_target_params = {
                            'ens_id': gene_id_from_tool,
                            'name': gene_name_from_tool,
                            'species': TARGET_SPECIES  # <-- Hardcoded species
                        }
                        session.run("""
                            MERGE (t:Target {ensembl_id: $ens_id})
                            ON CREATE SET t.name = $name, t.species = $species
                            ON MATCH SET  t.name = $name, t.species = $species
                        """, merge_target_params)
                        target_cache.add(gene_id_from_tool)
                        print(f"➕ Row {i}: Created/Merged Target node '{gene_name_from_tool}' (Ensembl ID: {gene_id_from_tool}).")

                    # --- Prepare Relationship for Batching ---
                    rel_properties = {
                        'mirna_name': found_mirna_name,
                        'target_ensembl_id': gene_id_from_tool,
                        'confidence': confidence,
                        'microt_score': score_float,
                        'source_mirna_name': mirna_name_from_tool,
                        'source_mirna_id': mirna_id_from_tool,
                        'source_gene_name': gene_name_from_tool,
                        'source_gene_id': gene_id_from_tool,
                        'experimental_method': row[12].strip(),
                        'regulation': row[13].strip(),
                        'tissue': row[14].strip(),
                        'pubmed_id': row[16].strip(),
                        'tool_name': database_name_display
                    }
                    batch_relationships.append(rel_properties)
                    processed_rows_count += 1

                    # --- Execute Batch Insert ---
                    if len(batch_relationships) >= BATCH_SIZE:
                        created = batch_create_relationships(session, batch_relationships)
                        created_relationships_count += created
                        print(f"🔄 Batch inserted {created} relationships. Total processed: {processed_rows_count}")
                        batch_relationships.clear()

                # Insert any remaining relationships
                if batch_relationships:
                    created = batch_create_relationships(session, batch_relationships)
                    created_relationships_count += created
                    print(f"🔄 Batch inserted final {created} relationships.")

                # --- Final Summary ---
                print("\n" + "="*50)
                print(f"✅ Finished processing TarBase file: {data_file_path}")
                print(f"📊 Total rows read (including header): {i}")
                print(f"📈 Rows processed for relationship creation: {processed_rows_count}")
                print(f"✔️ Relationships successfully created: {created_relationships_count}")
                print(f"🚫 Rows skipped (missing data, etc.): {skipped_rows_count}")
                print("="*50 + "\n")

                final_min_score = min_score_val if min_score_val != float('inf') else 0.0
                final_max_score = max_score_val if max_score_val != float('-inf') else 1.0
                create_relation_info(database_name_display, data_source_link_specific, final_min_score, final_max_score, 0.5)

    except FileNotFoundError:
        print(f"❌ Error: TarBase data file not found at '{data_file_path}'")
    except Exception as e:
        print(f"❌ An unexpected critical error occurred during TarBase import: {e}")
        import traceback
        traceback.print_exc()
    finally:
        close_driver()

    print("🏁 TarBase import script finished.")

# The batch_create_relationships function remains unchanged from the previous version.
def batch_create_relationships(session, rel_list):
    created_count = 0
    batch_query = """
    UNWIND $rels AS rel_props
    MATCH (mir:microRNA {name: rel_props.mirna_name})
    MATCH (gene:Target {ensembl_id: rel_props.target_ensembl_id})
    MERGE (mir)-[r:TarBase {
        source_mirna_id: rel_props.source_mirna_id,
        source_gene_id: rel_props.source_gene_id,
        experimental_method: rel_props.experimental_method
    }]->(gene)
    ON CREATE SET
        r.confidence = rel_props.confidence,
        r.microt_score = rel_props.microt_score,
        r.source_mirna_name = rel_props.source_mirna_name,
        r.source_gene_name = rel_props.source_gene_name,
        r.regulation = rel_props.regulation,
        r.tissue = rel_props.tissue,
        r.pubmed_id = rel_props.pubmed_id,
        r.tool_name = rel_props.tool_name
    RETURN count(r) AS created_count
    """
    try:
        result = session.run(batch_query, {'rels': rel_list})
        record = result.single()
        if record:
            created_count = record['created_count']
    except Exception as e:
        print(f"❌ Error during batch relationship creation: {e}")
        import traceback
        traceback.print_exc()
    return created_count

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\nUsage: python tarbase_import_human.py <path_to_tarbase_data_file.tsv>")
        print("Example: python tarbase_import_human.py ./DIANA-TarBase_v9.0.tsv\n")
        sys.exit(1)

    tarbase_file_arg = sys.argv[1]
    run_tarbase_import(tarbase_file_arg)