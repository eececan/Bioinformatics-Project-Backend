import sys
import csv
from dbhelper import db_connect, create_db_info, create_relation_info, close_driver
from ncbi import get_gene_by_id 

def run_mirtarbase_import(data_file_path, species_prefix_filter):
    """
    Main function to import miRTarBase data into Neo4j.
    """
    print(f"Starting miRTarBase import for species prefix: {species_prefix_filter}")
    print(f"Processing data file: {data_file_path}")

    database_name_display = 'miRTarBase'
    database_url_official = 'http://mirtarbase.mbc.nctu.edu.tw/'
    data_source_link_specific = 'http://mirtarbase.mbc.nctu.edu.tw/cache/download/6.1/mmu_MTI.xls' 
    
    create_db_info(database_name_display, database_url_official)

    min_score_val = float('inf') 
    max_score_val = float('-inf') 

    processed_rows_count = 0
    created_relationships_count = 0
    skipped_rows_count = 0

    try:
        with db_connect() as session: 
            with open(data_file_path, mode='r', newline='', encoding='utf-8') as csvfile:
                csvfile.readline() 
                reader = csv.reader(csvfile) 

                for i, row in enumerate(reader):
                    current_row_num = i + 2 

                    if not row: 
                        skipped_rows_count += 1
                        continue
                    
                    if len(row) != 9:
                        print(f"    ⚠️ Row {current_row_num}: Malformed (expected 9 columns, got {len(row)}). Skipping. Data: {row}")
                        skipped_rows_count += 1
                        continue
                    
                    mirna_name_from_tool = row[1].strip()
                    target_symbol_from_tool = row[3].strip()
                    raw_gene_id_from_tool = row[4].strip() 
                    
                    experiments_data = row[6].strip() 
                    
                    experiment_or_pmid_score = row[8].strip() 

                    if not mirna_name_from_tool.lower().startswith(species_prefix_filter.lower()):
                        skipped_rows_count += 1
                        continue

                    if not raw_gene_id_from_tool:
                        print(f"    ⚠️ Row {current_row_num}: Missing GeneID. Skipping. Data: {row}")
                        skipped_rows_count += 1
                        continue
                    try:
                        cleaned_target_gene_id = str(int(float(raw_gene_id_from_tool)))
                    except ValueError:
                        print(f"    ⚠️ Row {current_row_num}: Invalid GeneID format '{raw_gene_id_from_tool}'. Skipping.")
                        skipped_rows_count += 1
                        continue
                    
                    standard_mirna_name_for_match = mirna_name_from_tool

                    params_for_cypher = {
                        'p_mirna_name_tool': mirna_name_from_tool,
                        'p_target_symbol_tool': target_symbol_from_tool,
                        'p_target_geneid_tool_original': raw_gene_id_from_tool,
                        'p_relation_name_prop': database_name_display, 
                        'p_tool_score_prop': experiment_or_pmid_score, 
                        'p_standard_mirna_name_match': standard_mirna_name_for_match,
                        'p_standard_target_geneid_match': cleaned_target_gene_id,
                        'p_experiments': experiments_data 
                    }

                    try:
                        score_float = float(experiment_or_pmid_score)
                        if score_float < min_score_val: min_score_val = score_float
                        if score_float > max_score_val: max_score_val = score_float
                    except ValueError:
                        pass 

                    mirna_check_query = "MATCH (m:microRNA {name: $p_standard_mirna_name_match}) RETURN m.name LIMIT 1"
                    mirna_record = session.run(mirna_check_query, params_for_cypher).single()
                    if not mirna_record:
                        print(f"    ⚠️ Row {current_row_num}: microRNA node '{params_for_cypher['p_standard_mirna_name_match']}' not found in DB. Skipping.")
                        skipped_rows_count += 1
                        continue

                    target_check_query = "MATCH (t:Target {geneid: $p_standard_target_geneid_match}) RETURN t.name LIMIT 1"
                    target_record = session.run(target_check_query, params_for_cypher).single()

                    if not target_record:
                        gene_details_from_ncbi = get_gene_by_id(params_for_cypher['p_standard_target_geneid_match'])
                        
                        if gene_details_from_ncbi:
                            merge_target_params = {
                                'm_geneid': str(gene_details_from_ncbi.get('id', params_for_cypher['p_standard_target_geneid_match'])),
                                'm_name': gene_details_from_ncbi.get('name', params_for_cypher['p_target_symbol_tool']),
                                'm_species': gene_details_from_ncbi.get('species', "Mus musculus"),
                                'm_ens_code': gene_details_from_ncbi.get('embl', ''),
                                'm_ncbi_link': str(gene_details_from_ncbi.get('id', params_for_cypher['p_standard_target_geneid_match']))
                            }
                            if not merge_target_params['m_geneid']:
                                print(f"    ❌ Row {current_row_num}: Critical error - GeneID became empty after NCBI fetch for '{params_for_cypher['p_standard_target_geneid_match']}'. Skipping.")
                                skipped_rows_count +=1
                                continue

                            session.run("""
                                MERGE (t:Target {geneid: $m_geneid})
                                ON CREATE SET t.name = $m_name, t.species = $m_species, t.ens_code = $m_ens_code, t.ncbi_link = $m_ncbi_link
                                ON MATCH SET  t.name = $m_name, t.species = $m_species, t.ens_code = $m_ens_code, t.ncbi_link = $m_ncbi_link 
                            """, merge_target_params)
                            print(f"    ➕ Row {current_row_num}: Created/Merged Target node '{merge_target_params['m_name']}' (GeneID: {merge_target_params['m_geneid']})")
                        else:
                            print(f"    ❌ Row {current_row_num}: Could not fetch details for GeneID '{params_for_cypher['p_standard_target_geneid_match']}' from NCBI. Creating minimal Target node.")
                            minimal_target_params = {
                                'min_geneid': params_for_cypher['p_standard_target_geneid_match'],
                                'min_name': params_for_cypher['p_target_symbol_tool'] or params_for_cypher['p_standard_target_geneid_match'],
                                'min_species': "Mus musculus" 
                            }
                            session.run("""
                                MERGE (t:Target {geneid: $min_geneid})
                                ON CREATE SET t.name = $min_name, t.species = $min_species
                            """, minimal_target_params)
                            print(f"    ➕ Row {current_row_num}: Created minimal Target node for GeneID '{minimal_target_params['min_geneid']}'")
                    
                    create_relationship_query = """
                    MATCH (mir:microRNA {name: $p_standard_mirna_name_match})
                    MATCH (gene:Target {geneid: $p_standard_target_geneid_match})
                    CREATE (mir)-[r:miRTarBase {
                        tool_name: $p_relation_name_prop,
                        score: $p_tool_score_prop, 
                        experiments: $p_experiments,                 // Added experiment property
                        source_microrna: $p_mirna_name_tool,
                        source_target_symbol: $p_target_symbol_tool,
                        source_target_geneid_original: $p_target_geneid_tool_original
                    }]->(gene)
                    """

                    try:
                        result_summary = session.run(create_relationship_query, params_for_cypher).consume()
                        
                        if result_summary.counters.relationships_created > 0:
                            created_relationships_count += 1
                        else:
                            print(f"    ⚠️ Row {current_row_num}: Relationship not created (by summary counters) for '{params_for_cypher['p_standard_mirna_name_match']}' -> '{params_for_cypher['p_standard_target_geneid_match']}'. Check MATCH conditions or if an identical relationship was somehow prevented by constraints (unlikely for CREATE).")
                    except Exception as e_rel:
                        print(f"    ❌ Row {current_row_num}: Error creating miRTarBase relationship for '{params_for_cypher['p_standard_mirna_name_match']}' -> '{params_for_cypher['p_standard_target_geneid_match']}': {e_rel}")

                    processed_rows_count += 1
                    if processed_rows_count % 500 == 0:
                        print(f"  Processed {processed_rows_count} rows from miRTarBase file...")

            print(f"\nFinished processing miRTarBase file: {data_file_path}")
            print(f"  Total rows read (excluding header): {i+1 if 'i' in locals() else 0}") 
            print(f"  Rows processed for relationship creation: {processed_rows_count}")
            print(f"  Relationships successfully created: {created_relationships_count}")
            print(f"  Rows skipped (malformed, species mismatch, missing ID, etc.): {skipped_rows_count}")

            final_min_score = min_score_val if min_score_val != float('inf') else 0.0 
            final_max_score = max_score_val if max_max_score != float('-inf') else 0.0 
            create_relation_info(database_name_display, data_source_link_specific, final_min_score, final_max_score, 0.0)

    except FileNotFoundError as e:
        print(f"❌ Error: miRTarBase data file not found at '{data_file_path}' {e}")
    except Exception as e_main:
        print(f"❌ An unexpected critical error occurred during miRTarBase import: {e_main}")
        import traceback
        traceback.print_exc()
    finally:
        close_driver() 

    print("miRTarBase import script finished.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python mirtarbase_fixed.py <path_to_mirtarbase_data_file.csv> <species_prefix_for_miRNA (e.g., mmu)>")
        sys.exit(1)
    
    mirtarbase_file_arg = sys.argv[1]
    species_prefix_arg = sys.argv[2]
    
    run_mirtarbase_import(mirtarbase_file_arg, species_prefix_arg)