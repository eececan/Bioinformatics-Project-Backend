import sys
import csv
import os 
from dbhelper import db_connect, create_db_info, create_relation_info, close_driver
from ncbi import get_geneid_by_refseq, get_gene_by_id 
from neo4j.exceptions import Neo4jError 

PICTAR_MIRNA_ACCESSION_MAP_FILE = '../data/pictar/mirna_accession.dat'
map_file_checked_and_missing = False 

def miRNA2accession(pictar_miRNA_name_original, session):
    global map_file_checked_and_missing 

    if not map_file_checked_and_missing:
        try:
            with open(PICTAR_MIRNA_ACCESSION_MAP_FILE, 'r', encoding='utf-8') as f_map:
                for line in f_map:
                    parts = line.strip().split('\t')
                    if len(parts) == 2 and parts[0].lower() == pictar_miRNA_name_original.lower():
                        return parts[1] 
        except FileNotFoundError:
            if not map_file_checked_and_missing: 
                 print(f"Warning: PicTar miRNA accession map file not found: {PICTAR_MIRNA_ACCESSION_MAP_FILE}. Will use DB match for all subsequent miRNAs.")
            map_file_checked_and_missing = True
        except Exception as e_map:
            if not map_file_checked_and_missing:
                print(f"Warning: Error reading PicTar miRNA map file '{PICTAR_MIRNA_ACCESSION_MAP_FILE}': {e_map}")
            map_file_checked_and_missing = True

    original_lc_stripped = pictar_miRNA_name_original.strip().lower()
    
    name_normalized = original_lc_stripped.replace("_star", "-star") 
    name_normalized = name_normalized.replace("*", "-star")       
    name_normalized = name_normalized.replace("_", "-")           

    processed_name_for_logic = name_normalized
    if not processed_name_for_logic.startswith("hsa-"):
        if processed_name_for_logic.startswith("mir-"): 
            processed_name_for_logic = "hsa-" + processed_name_for_logic
        elif processed_name_for_logic.startswith("let-"): 
            processed_name_for_logic = "hsa-" + processed_name_for_logic
        else: 
            processed_name_for_logic = "hsa-" + processed_name_for_logic
    
    search_candidates = []

    search_candidates.append(processed_name_for_logic)
    if original_lc_stripped != processed_name_for_logic and original_lc_stripped.startswith("hsa-"):
        if original_lc_stripped not in search_candidates : 
             search_candidates.insert(0, original_lc_stripped) 

    is_star_input = processed_name_for_logic.endswith("-star")
    base_name_if_star = ""

    if is_star_input:
        base_name_if_star = processed_name_for_logic[:-len("-star")] 
        family_suffixes_star = ["", "a", "b", "c", "d", "e"] 
        arm_suffixes = ["-5p", "-3p"]
        for fam_sfx in family_suffixes_star:
            if fam_sfx and base_name_if_star.endswith(fam_sfx): continue 
            current_base_for_star = base_name_if_star + fam_sfx
            for arm_sfx in arm_suffixes:
                search_candidates.append(current_base_for_star + arm_sfx)
    else:
        has_arm = processed_name_for_logic.endswith("-5p") or processed_name_for_logic.endswith("-3p")
        
        temp_name_for_family_check = processed_name_for_logic
        if temp_name_for_family_check.endswith("-5p"): temp_name_for_family_check = temp_name_for_family_check[:-3]
        if temp_name_for_family_check.endswith("-3p"): temp_name_for_family_check = temp_name_for_family_check[:-3]
        
        has_family_letter = False
        if len(temp_name_for_family_check) > 0 and temp_name_for_family_check[-1].isalpha() and \
           len(temp_name_for_family_check) > len("hsa-mir-X"): 
            has_family_letter = True

        if not has_arm:
            search_candidates.append(processed_name_for_logic + "-5p")
            search_candidates.append(processed_name_for_logic + "-3p")

        if not has_family_letter:
            family_suffixes_general = ["a", "b", "c", "d", "e"]
            for fam_sfx in family_suffixes_general:
                candidate_with_family = processed_name_for_logic + fam_sfx
                search_candidates.append(candidate_with_family)
                if not has_arm: 
                    search_candidates.append(candidate_with_family + "-5p")
                    search_candidates.append(candidate_with_family + "-3p")
    
    unique_ordered_candidates = []
    for c in search_candidates:
        if c not in unique_ordered_candidates:
            unique_ordered_candidates.append(c)
    
    for candidate_name in unique_ordered_candidates:
        if not candidate_name: continue 
        try:
            query = "MATCH (m:microRNA) WHERE toLower(m.name) = $name_var RETURN m.accession AS acc, m.name AS matched_name LIMIT 1"
            result = session.run(query, name_var=candidate_name) 
            record = result.single()
            if record and record["acc"]:
                print(f"Neo4j Match: Found '{record['matched_name']}' (Acc: {record['acc']}) for PicTar original '{pictar_miRNA_name_original}' (using candidate '{candidate_name}')")
                return record["acc"]
        except Neo4jError as e_neo: print(f"Neo4j Error during miRNA lookup for '{candidate_name}': {e_neo}")
        except Exception as e_lookup: print(f"Unexpected Error during miRNA lookup for '{candidate_name}': {e_lookup}")

    print(f"⚠️ Could not find miRBase accession for PicTar miRNA: {pictar_miRNA_name_original} (Processed as: '{processed_name_for_logic}', Tried: {unique_ordered_candidates})")
    return None


def run_pictar_import(pictar_bed_file_path, relation_name_arg_val):
    print(f"Processing PicTar BED file: {pictar_bed_file_path} for relation: {relation_name_arg_val}")

    create_db_info('PicTar', 'http://pictar.mdc-berlin.de/') 
    source_db_link = 'http://genome.ucsc.edu/cgi-bin/hgTables' 
    min_score_val = float('inf')
    max_score_val = float('-inf')
    
    processed_data_rows_count = 0 
    created_relations_count = 0   
    skipped_rows_count = 0        
    total_lines_read = 0          

    try:
        if not os.path.exists(pictar_bed_file_path):
            print(f"CRITICAL Error: Input PicTar BED file not found at {pictar_bed_file_path}")
            sys.exit(1)
            
        with open(pictar_bed_file_path, 'r', encoding='utf-8') as bedfile_handle:
            with db_connect() as session: 
                reader = csv.reader(bedfile_handle, delimiter='\t')
                
                for i, row in enumerate(reader):
                    total_lines_read += 1
                    current_row_num_for_log = i + 1 

                    try: 
                        if not row or len(row) < 5: 
                            skipped_rows_count += 1
                            continue 
                        
                        name_field_parts = row[3].split(':')
                        if len(name_field_parts) != 2:
                            skipped_rows_count += 1
                            continue 
                        
                        target_refseq_tool = name_field_parts[0].strip()
                        mirna_name_tool_original = name_field_parts[1].strip() 
                        tool_score_str = row[4].strip()

                        try:
                            current_tool_score = float(tool_score_str)
                        except ValueError:
                            print(f"Warning: Row {current_row_num_for_log} has invalid score '{tool_score_str}'. Skipping this row.")
                            skipped_rows_count += 1
                            continue
                        
                        params_for_cypher = {
                            'pictar_mirna_name_original': mirna_name_tool_original,
                            'target_refseq_tool': target_refseq_tool,
                            'tool_score_val': current_tool_score,
                            'relation_name_val': relation_name_arg_val 
                        }

                        if current_tool_score < min_score_val: min_score_val = current_tool_score
                        if current_tool_score > max_score_val: max_score_val = current_tool_score
                        
                        standard_mirna_accession = miRNA2accession(mirna_name_tool_original, session)
                        if not standard_mirna_accession:
                            skipped_rows_count += 1
                            continue
                        params_for_cypher['standard_mirna_accession_match'] = standard_mirna_accession

                        standard_target_geneid = get_geneid_by_refseq(params_for_cypher['target_refseq_tool'])
                        if not standard_target_geneid:
                            skipped_rows_count += 1
                            continue
                        params_for_cypher['standard_target_geneid_match'] = standard_target_geneid

                        target_node_query = "MATCH (t:Target {geneid: $standard_target_geneid_match}) RETURN t.name LIMIT 1"
                        target_result = session.run(target_node_query, params_for_cypher)
                        if not target_result.single():
                            gene_details = get_gene_by_id(params_for_cypher['standard_target_geneid_match'])
                            if gene_details:
                                create_target_params = {
                                    'p_name': gene_details.get('name', params_for_cypher['target_refseq_tool']), 
                                    'p_species': gene_details.get('species', "Homo sapiens"), 
                                    'p_geneid': str(gene_details.get('id', params_for_cypher['standard_target_geneid_match'])), 
                                    'p_ens_code': gene_details.get('embl', ''),
                                    'p_ncbi_link': str(gene_details.get('id', params_for_cypher['standard_target_geneid_match']))
                                }
                                if not create_target_params['p_geneid']: 
                                     print(f"Error: GeneID missing after NCBI fetch for {params_for_cypher['standard_target_geneid_match']}. Skipping row {current_row_num_for_log}.")
                                     skipped_rows_count += 1
                                     continue

                                session.run("""
                                    MERGE (t:Target {geneid: $p_geneid})
                                    ON CREATE SET t.name = $p_name, t.species = $p_species, t.ens_code = $p_ens_code, t.ncbi_link = $p_ncbi_link
                                    ON MATCH SET t.name = $p_name, t.species = $p_species, t.ens_code = $p_ens_code
                                """, create_target_params)
                            else:
                                print(f"❌ Could not fetch details for GeneID {params_for_cypher['standard_target_geneid_match']} (Row {current_row_num_for_log}). Creating minimal Target node.")
                                session.run("""
                                    MERGE (t:Target {geneid: $standard_target_geneid_match})
                                    ON CREATE SET t.name = $target_refseq_tool, t.species = 'Homo sapiens' 
                                    """, params_for_cypher) 
                        
                        merge_relation_query = f"""
                        MATCH (mir:microRNA {{accession: $standard_mirna_accession_match}})
                        MATCH (gene:Target {{geneid: $standard_target_geneid_match}})
                        MERGE (mir)-[r:{relation_name_arg_val} {{ 
                            source_microrna: $pictar_mirna_name_original, 
                            source_target_refseq: $target_refseq_tool 
                            // Adding score to the MERGE key would make each score variant unique
                        }}]->(gene)
                        ON CREATE SET 
                            r.tool_name = $relation_name_val, 
                            r.score = $tool_score_val 
                        ON MATCH SET // Example: update score if a new row for the same site has a better score
                            r.score = CASE 
                                        WHEN $tool_score_val > r.score THEN $tool_score_val 
                                        ELSE r.score 
                                      END 
                        """

                        rel_result_summary = session.run(merge_relation_query, params_for_cypher).consume()
                        if rel_result_summary.counters.relationships_created > 0:
                            created_relations_count += 1
                        
                        processed_data_rows_count +=1 
                        if processed_data_rows_count % 500 == 0:
                            print(f"  Processed {processed_data_rows_count} valid PicTar data rows...")
                    
                    except Exception as e_row: 
                        print(f"❌ Error processing PicTar row {current_row_num_for_log} ('{row if row else 'EMPTY'}'): {e_row}")
                        skipped_rows_count += 1
                        continue 
            
            print(f"\nFinished PicTar processing from {pictar_bed_file_path}.")
            print(f"  Total lines read from file: {total_lines_read}")
            print(f"  Data rows processed (attempted for import): {processed_data_rows_count}")
            print(f"  Relationships CREATED by MERGE this run: {created_relations_count}") 
            print(f"  Rows skipped (malformed, miRNA/RefSeq map fail, invalid score etc.): {skipped_rows_count}")
            
            final_min_score = min_score_val if min_score_val != float('inf') else 0.0
            final_max_score = max_score_val if max_score_val != float('-inf') else 0.0
            create_relation_info(relation_name_arg_val, source_db_link, final_min_score, final_max_score, 0.0) 

    except FileNotFoundError: 
        print(f"CRITICAL Error: Input PicTar BED file not found at {pictar_bed_file_path}")
        sys.exit(1)
    except Neo4jError as e_neo_main:
        print(f"CRITICAL Neo4j Error during PicTar import (e.g. connection issue): {e_neo_main}")
    except Exception as e_main_critical:
        print(f"An CRITICAL unexpected error occurred during PicTar processing: {e_main_critical}")
        import traceback
        traceback.print_exc()
    finally:
        close_driver()

    print("PicTar import script finished.")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python src/pictar_fixed.py <PicTar_.bed_file_path> <RelationName>")
        sys.exit(1)

    pictar_file_arg = sys.argv[1]
    relation_name_script_arg = sys.argv[2]
    
    run_pictar_import(pictar_file_arg, relation_name_script_arg)