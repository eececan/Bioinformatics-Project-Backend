import sys
import csv
from dbhelper import db_connect, create_db_info, create_relation_info, close_driver
from ncbi import get_gene_by_id

def run_mirtarbase_import(data_file_path, species_prefix_filter):
    """
    Main function to import miRTarBase data into Neo4j with caching and batch insert.
    """
    print(f"🚀 Starting miRTarBase import for species prefix: {species_prefix_filter}")
    print(f"📂 Processing data file: {data_file_path}")

    database_name_display = 'miRTarBase'
    data_source_link_specific = 'https://cytargetlinker.github.io/pages/linksets/mirtarbase.html'
    database_url_official = 'https://mirtarbase.mbc.nctu.edu.tw/'

    create_db_info(database_name_display, database_url_official)

    min_score_val = float('inf')
    max_score_val = float('-inf')

    processed_rows_count = 0
    created_relationships_count = 0
    skipped_rows_count = 0

    batch_relationships = []
    BATCH_SIZE = 5000

    try:
        with db_connect() as session:
            print("🔍 Fetching all existing microRNA nodes into cache...")
            mirna_cache = set()
            mirna_fetch_query = "MATCH (m:microRNA) RETURN m.name"
            for record in session.run(mirna_fetch_query):
                mirna_cache.add(record['m.name'])
            print(f"✅ Cached {len(mirna_cache)} microRNA nodes.")

            print("🔍 Fetching all existing Target nodes (geneid) into cache...")
            target_cache = set()
            target_fetch_query = "MATCH (t:Target) RETURN t.geneid"
            for record in session.run(target_fetch_query):
                target_cache.add(str(record['t.geneid']))
            print(f"✅ Cached {len(target_cache)} Target nodes.")

            with open(data_file_path, mode='r', newline='', encoding='utf-8') as csvfile:
                csvfile.readline()  # skip header
                reader = csv.reader(csvfile)

                for i, row in enumerate(reader):
                    current_row_num = i + 2  # considering header line

                    if not row:
                        skipped_rows_count += 1
                        print(f"⚠️ Row {current_row_num}: Empty row. Skipping.")
                        continue

                    if len(row) != 9:
                        print(f"⚠️ Row {current_row_num}: Malformed (expected 9 columns, got {len(row)}). Skipping. Data: {row}")
                        skipped_rows_count += 1
                        continue

                    mirna_name_from_tool = row[1].strip()
                    target_symbol_from_tool = row[3].strip()
                    raw_gene_id_from_tool = row[4].strip()
                    experiments_data = row[6].strip()
                    experiment_or_pmid_score = row[8].strip()

                    if not mirna_name_from_tool.lower().startswith(species_prefix_filter.lower()):
                        skipped_rows_count += 1
                        print(f"⚠️ Row {current_row_num}: miRNA '{mirna_name_from_tool}' does not match species prefix '{species_prefix_filter}'. Skipping.")
                        continue

                    if not raw_gene_id_from_tool:
                        print(f"⚠️ Row {current_row_num}: Missing GeneID. Skipping.")
                        skipped_rows_count += 1
                        continue

                    try:
                        cleaned_target_gene_id = str(int(float(raw_gene_id_from_tool)))
                    except ValueError:
                        print(f"⚠️ Row {current_row_num}: Invalid GeneID format '{raw_gene_id_from_tool}'. Skipping.")
                        skipped_rows_count += 1
                        continue

                    # Update min/max score
                    try:
                        score_float = float(experiment_or_pmid_score)
                        if score_float < min_score_val: min_score_val = score_float
                        if score_float > max_score_val: max_score_val = score_float
                    except ValueError:
                        pass

                    standard_mirna_name_for_match = mirna_name_from_tool

                    # --- miRNA node check with suffix variants ---
                    potential_mirna_names = [
                        standard_mirna_name_for_match,
                        f"{standard_mirna_name_for_match}-3p",
                        f"{standard_mirna_name_for_match}-5p"
                    ]

                    found_mirna_names_in_cache = []
                    for candidate in potential_mirna_names:
                        if candidate in mirna_cache:
                            found_mirna_names_in_cache.append(candidate)
                            if candidate != standard_mirna_name_for_match:
                                print(f"ℹ️ Row {current_row_num}: Using alternative microRNA '{candidate}' instead of '{standard_mirna_name_for_match}'.")

                    if not found_mirna_names_in_cache:
                        print(f"⚠️ Row {current_row_num}: microRNA '{standard_mirna_name_for_match}' and variants not found in cache. Skipping.")
                        skipped_rows_count += 1
                        continue
                    # --- end miRNA check ---

                    # --- Target node check ---
                    if cleaned_target_gene_id not in target_cache:
                        # Try fetching from NCBI
                        gene_details_from_ncbi = get_gene_by_id(cleaned_target_gene_id)
                        if gene_details_from_ncbi:
                            merge_target_params = {
                                'm_geneid': str(gene_details_from_ncbi.get('id', cleaned_target_gene_id)),
                                'm_name': gene_details_from_ncbi.get('name', target_symbol_from_tool),
                                'm_species': gene_details_from_ncbi.get('species', "Homo sapiens"),
                                'm_ens_code': gene_details_from_ncbi.get('embl', ''),
                                'm_ncbi_link': str(gene_details_from_ncbi.get('id', cleaned_target_gene_id))
                            }
                            if not merge_target_params['m_geneid']:
                                print(f"❌ Row {current_row_num}: Critical error - GeneID empty after NCBI fetch. Skipping.")
                                skipped_rows_count += 1
                                continue
                            session.run("""
                                MERGE (t:Target {geneid: $m_geneid})
                                ON CREATE SET t.name = $m_name, t.species = $m_species, t.ens_code = $m_ens_code, t.ncbi_link = $m_ncbi_link
                                ON MATCH SET  t.name = $m_name, t.species = $m_species, t.ens_code = $m_ens_code, t.ncbi_link = $m_ncbi_link
                            """, merge_target_params)
                            target_cache.add(merge_target_params['m_geneid'])
                            print(f"➕ Row {current_row_num}: Created/Merged Target node '{merge_target_params['m_name']}' (GeneID: {merge_target_params['m_geneid']}).")
                        else:
                            print(f"➕ Row {current_row_num}: Skipping, not found in NCBI '{cleaned_target_gene_id}'.")
                    # --- end Target node check ---

                    # Prepare relationships to batch
                    for mirna_name_to_use in found_mirna_names_in_cache:
                        rel = {
                            'mirna_name': mirna_name_to_use,
                            'target_geneid': cleaned_target_gene_id,
                            'tool_name': database_name_display,
                            'score': experiment_or_pmid_score,
                            'experiments': experiments_data,
                            'source_mirna': mirna_name_from_tool,
                            'source_target_symbol': target_symbol_from_tool,
                            'source_target_geneid_original': raw_gene_id_from_tool,
                            'row_num': current_row_num
                        }
                        batch_relationships.append(rel)

                    processed_rows_count += 1

                    if processed_rows_count % BATCH_SIZE == 0:
                        created = batch_create_relationships(session, batch_relationships)
                        created_relationships_count += created
                        print(f"🔄 Batch inserted {created} relationships after processing {processed_rows_count} rows.")
                        batch_relationships.clear()

                # Insert any remaining relationships after loop
                if batch_relationships:
                    created = batch_create_relationships(session, batch_relationships)
                    created_relationships_count += created
                    print(f"🔄 Batch inserted last {created} relationships at end of file.")

                print(f"\n✅ Finished processing miRTarBase file: {data_file_path}")
                print(f"📊 Total rows read (excluding header): {i+1 if 'i' in locals() else 0}")
                print(f"📈 Rows processed for relationship creation: {processed_rows_count}")
                print(f"✔️ Relationships successfully created: {created_relationships_count}")
                print(f"🚫 Rows skipped (malformed, species mismatch, missing ID, etc.): {skipped_rows_count}")

                final_min_score = min_score_val if min_score_val != float('inf') else 0.0
                final_max_score = max_score_val if max_score_val != float('-inf') else 0.0
                create_relation_info(database_name_display, data_source_link_specific, final_min_score, final_max_score, 0.0)

    except FileNotFoundError as e:
        print(f"❌ Error: miRTarBase data file not found at '{data_file_path}' {e}")
    except Exception as e_main:
        print(f"❌ An unexpected critical error occurred during miRTarBase import: {e_main}")
        import traceback
        traceback.print_exc()
    finally:
        close_driver()

    print("🏁 miRTarBase import script finished.")


def batch_create_relationships(session, rel_list):
    """
    Batch create miRTarBase relationships from a list of relationship dicts.
    Returns the count of relationships created.
    """
    created_count = 0

    # We will use UNWIND with parameters to batch insert
    batch_query = """
    UNWIND $rels AS rel
    MATCH (mir:microRNA {name: rel.mirna_name})
    MATCH (gene:Target {geneid: rel.target_geneid})
    CREATE (mir)-[r:miRTarBase {
        tool_name: rel.tool_name,
        score: rel.score,
        experiments: rel.experiments,
        source_microrna: rel.source_mirna,
        source_target_symbol: rel.source_target_symbol,
        source_target_geneid_original: rel.source_target_geneid_original
    }]->(gene)
    RETURN count(r) AS created_count
    """

    try:
        result = session.run(batch_query, {'rels': rel_list})
        record = result.single()
        if record:
            created_count = record['created_count']
        else:
            print("⚠️ Warning: No record returned from batch relationship creation.")
    except Exception as e:
        print(f"❌ Error during batch relationship creation: {e}")
        import traceback
        traceback.print_exc()

    return created_count


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python mirtarbase_fixed.py <path_to_mirtarbase_data_file.csv> <species_prefix_for_miRNA (e.g., hsa)>")
        sys.exit(1)

    mirtarbase_file_arg = sys.argv[1]
    species_prefix_arg = sys.argv[2]

    run_mirtarbase_import(mirtarbase_file_arg, species_prefix_arg)