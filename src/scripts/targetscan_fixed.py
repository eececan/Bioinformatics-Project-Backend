import sys
import os
import csv 
from dbhelper import db_connect, create_db_info, create_relation_info, close_driver
import ncbi 
import uniprot
import ensembl
from neo4j.exceptions import Neo4jError

MIRBASE_ALIASES_FILE = '../data/mirbase/aliases.txt' 
map_file_aliases_checked_and_missing = False 

def map_targetscan_mirna_to_db(targetscan_mirna_tool_name, species_prefix, session):
    """
    Maps a TargetScan miRNA name (e.g., "miR-124", "miR-101b-3p.2") to a
    standardized miRBase name found in the Neo4j database.
    Returns a dictionary {'name': db_mirna_name, 'accession': db_mirna_accession} or None.
    """
    global map_file_aliases_checked_and_missing

    original_ts_name_lc = targetscan_mirna_tool_name.strip().lower()
    
    base_candidate_with_species = original_ts_name_lc
    if not base_candidate_with_species.startswith(species_prefix.lower() + "-"):
        if base_candidate_with_species.startswith("mir-") or base_candidate_with_species.startswith("let-"):
            base_candidate_with_species = species_prefix.lower() + "-" + base_candidate_with_species
        else: 
            base_candidate_with_species = species_prefix.lower() + "-mir-" + base_candidate_with_species
            
    search_candidates = [base_candidate_with_species] 

    if '.' in base_candidate_with_species:
        parts = base_candidate_with_species.rsplit('.', 1)
        if parts[1].isdigit() or (len(parts[1]) == 1 and 'A' <= parts[1].upper() <= 'Z'):
            search_candidates.append(parts[0]) 

    for current_base_candidate in list(unique_ordered_candidates(search_candidates)): 
        if not (current_base_candidate.endswith("-5p") or current_base_candidate.endswith("-3p")):
            search_candidates.append(current_base_candidate + "-5p")
            search_candidates.append(current_base_candidate + "-3p")
            for fam_sfx in ["a", "b", "c"]: 
                if not current_base_candidate.endswith(fam_sfx): 
                    search_candidates.append(current_base_candidate + fam_sfx + "-5p")
                    search_candidates.append(current_base_candidate + fam_sfx + "-3p")
                    search_candidates.append(current_base_candidate + fam_sfx) 

    final_candidates = unique_ordered_candidates(search_candidates)
    
    for candidate_name in final_candidates:
        print(f"Attempting candidate: {candidate_name!r}") 
        if not candidate_name: 
            print("Skipping empty candidate.")
            continue
        try:
            query = "MATCH (m:microRNA) WHERE toLower(m.name) = $name_var RETURN m.name AS mirna_db_name, m.accession AS mirna_db_accession LIMIT 1"
            result = session.run(query, name_var=candidate_name)
            record = result.single() 

            if record: 
                print(f"TargetScan miRNA Match: Found '{record['mirna_db_name']}' (Acc: {record['mirna_db_accession']}) for tool name '{targetscan_mirna_tool_name}' (using candidate '{candidate_name}')")
                return {'name': record['mirna_db_name'], 'accession': record['mirna_db_accession']}

        except Neo4jError as e_neo: 
            print(f"Neo4j Error during miRNA lookup for candidate '{candidate_name}': {e_neo}")
        except Exception as e: 
            print(f"Error matching TargetScan miRNA candidate '{candidate_name}': {e}")
            
    if not map_file_aliases_checked_and_missing:
        try:
            with open(MIRBASE_ALIASES_FILE, 'r', encoding='utf-8') as f_aliases:
                for line in f_aliases:
                    parts = line.strip().split(';')
                    if len(parts) >= 4:
                        old_id_alias, new_acc_alias, new_id_alias = parts[1].lower(), parts[2], parts[3].lower()
                        if old_id_alias == original_ts_name_lc or \
                           old_id_alias == base_candidate_with_species or \
                           (base_candidate_with_species.rsplit('.',1)[0] == old_id_alias if '.' in base_candidate_with_species else False) :
                            query_alias, params_alias = "", {}
                            if new_id_alias:
                                query_alias = "MATCH (m:microRNA) WHERE toLower(m.name) = $id RETURN m.name, m.accession LIMIT 1"
                                params_alias = {'id': new_id_alias}
                            elif new_acc_alias: 
                                query_alias = "MATCH (m:microRNA {accession: $acc}) RETURN m.name, m.accession LIMIT 1"
                                params_alias = {'acc': new_acc_alias}
                            if query_alias:
                                result_alias = session.run(query_alias, params_alias)
                                record_alias = result_alias.single()
                                if record_alias:
                                    print(f"TargetScan miRNA Alias Match: Original '{targetscan_mirna_tool_name}' -> Alias '{old_id_alias}' -> DB '{record_alias['name']}'")
                                    return {'name': record_alias['name'], 'accession': record_alias['accession']}
        except FileNotFoundError:
            if not map_file_aliases_checked_and_missing: print(f"Warning: miRBase aliases file not found: {MIRBASE_ALIASES_FILE}")
            map_file_aliases_checked_and_missing = True
        except Exception as e_alias:
            if not map_file_aliases_checked_and_missing: print(f"Warning: Error reading miRBase aliases file: {e_alias}")
            map_file_aliases_checked_and_missing = True

    print(f"⚠️ TargetScan: Could not map miRNA '{targetscan_mirna_tool_name}' (Procd: '{base_candidate_with_species}', Tried: {final_candidates})")
    return None

def unique_ordered_candidates(candidates_list):
    seen = set()
    return [x for x in candidates_list if not (x in seen or seen.add(x))]

def run_targetscan_import(data_file_path, species_prefix_arg):
    print(f"Starting TargetScan import for species prefix: {species_prefix_arg}")
    print(f"Processing data file: {data_file_path}")

    database_name_display = 'TargetScan'
    database_url_official = 'http://www.targetscan.org' 
    data_source_link_specific = 'http://www.targetscan.org/mmu_71/mmu_71_data_download/Conserved_Family_Conserved_Targets_Info.txt.zip' 
    
    create_db_info(database_name_display, database_url_official)

    min_pct_score = float('inf') 
    max_pct_score = float('-inf')
    
    processed_interactions_count = 0
    created_relationships_count = 0
    updated_relationships_count = 0
    skipped_interactions_count = 0
    total_lines_read_from_file = 0

    species_id_map_targetscan = {
        'mmu': ('Mus musculus', '10090'), 
        'hsa': ('Homo sapiens', '9606') 
    }
    if species_prefix_arg.lower() not in species_id_map_targetscan:
        print(f"Error: Species prefix '{species_prefix_arg}' not defined for TargetScan mapping.")
        sys.exit(1)
    current_species_name, expected_ncbi_tax_id = species_id_map_targetscan[species_prefix_arg.lower()]

    try:
        if not os.path.exists(data_file_path):
            print(f"CRITICAL Error: Input TargetScan data file not found at {data_file_path}")
            sys.exit(1)

        with open(data_file_path, 'r', encoding='utf-8') as f_targetscan:
            with db_connect() as session:
                header_line_str = f_targetscan.readline().strip()
                total_lines_read_from_file +=1
                header_parts = [h.strip().lower() for h in header_line_str.split('\t')]
                print(f"TargetScan Header: {header_parts}")
                
                try:
                    mir_family_col_idx = header_parts.index("mir family") 
                    gene_id_col_idx = header_parts.index("gene id")
                    species_id_col_idx = header_parts.index("species id")
                    pct_col_idx = header_parts.index("pct")
                except ValueError as ve:
                    print(f"Error finding column in TargetScan header: {ve}. Headers found: {header_parts}")
                    sys.exit(1)


                for i, line in enumerate(f_targetscan): 
                    total_lines_read_from_file +=1
                    current_row_num_for_log = i + 2 

                    try:
                        row = line.strip().split('\t')
                        max_needed_idx = max(mir_family_col_idx, gene_id_col_idx, species_id_col_idx, pct_col_idx)
                        if not row or len(row) <= max_needed_idx:
                            skipped_interactions_count += 1
                            continue
                        
                        if row[species_id_col_idx] != expected_ncbi_tax_id:
                            continue 
                        
                        mirna_tool_entries_str = row[mir_family_col_idx]
                        target_ensembl_full_from_tool = row[gene_id_col_idx] 
                        target_ensembl_base_from_tool = target_ensembl_full_from_tool.split('.')[0]

                        try:
                            current_pct_score_val = float(row[pct_col_idx])
                        except (ValueError, IndexError):
                            skipped_interactions_count += len(mirna_tool_entries_str.split('/'))
                            continue
                        
                        for mirna_name_tool_item in mirna_tool_entries_str.split('/'):
                            mirna_name_tool_item_clean = mirna_name_tool_item.strip()
                            if not mirna_name_tool_item_clean: continue

                            processed_interactions_count += 1

                            params_for_cypher = {
                                'p_mirna_name_tool': mirna_name_tool_item_clean,
                                'p_target_ensembl_base_tool': target_ensembl_base_from_tool,
                                'p_target_ensembl_full_tool': target_ensembl_full_from_tool,
                                'p_pct_score_val': current_pct_score_val,
                                'p_relation_name_prop': database_name_display,
                                'p_current_species_name': current_species_name
                            }

                            if current_pct_score_val < min_pct_score: min_pct_score = current_pct_score_val
                            if current_pct_score_val > max_pct_score: max_pct_score = current_pct_score_val

                            mirna_map_result = map_targetscan_mirna_to_db(params_for_cypher['p_mirna_name_tool'], species_prefix_arg, session)
                            if not mirna_map_result or not mirna_map_result.get('name'):
                                skipped_interactions_count +=1; continue
                            params_for_cypher['p_standard_mirna_name_match'] = mirna_map_result['name']
                            
                            target_check_query = "MATCH (t:Target {ens_code: $p_target_ensembl_base_tool}) RETURN t.name LIMIT 1"
                            target_record = session.run(target_check_query, params_for_cypher).single()
                            if not target_record:
                                gene_details = ensembl.get_gene_by_id(params_for_cypher['p_target_ensembl_base_tool'])
                                if not gene_details: gene_details = ncbi.get_gene_by_ens(params_for_cypher['p_target_ensembl_base_tool'], params_for_cypher['p_current_species_name'])
                                if not gene_details: gene_details = uniprot.get_gene_by_ens(params_for_cypher['p_target_ensembl_base_tool'])
                                
                                if gene_details:
                                    merge_target_params = {
                                        'm_ens_code': gene_details.get('embl', params_for_cypher['p_target_ensembl_base_tool']),
                                        'm_name': gene_details.get('name', params_for_cypher['p_target_ensembl_base_tool']),
                                        'm_species': gene_details.get('species', params_for_cypher['p_current_species_name']),
                                        'm_geneid': gene_details.get('id', ''),
                                        'm_ncbi_link': gene_details.get('id', '')
                                    }
                                    if not merge_target_params['m_ens_code']: skipped_interactions_count+=1; continue
                                    session.run("""
                                        MERGE (t:Target {ens_code: $m_ens_code})
                                        ON CREATE SET t.name = $m_name, t.species = $m_species, t.geneid = $m_geneid, t.ncbi_link = $m_ncbi_link
                                        ON MATCH SET  t.name = $m_name, t.species = $m_species, t.geneid = $m_geneid
                                    """, merge_target_params)
                                else: 
                                    session.run("""
                                        MERGE (t:Target {ens_code: $p_target_ensembl_base_tool})
                                        ON CREATE SET t.name = $p_target_ensembl_base_tool, t.species = $p_current_species_name
                                    """, params_for_cypher)
                            
                            merge_relationship_query = """
                            MATCH (mir:microRNA {name: $p_standard_mirna_name_match})
                            MATCH (gene:Target {ens_code: $p_target_ensembl_base_tool})
                            MERGE (mir)-[r:TargetScan]->(gene) // Keying on nodes and rel type only
                            ON CREATE SET 
                                r.tool_name = $p_relation_name_prop, 
                                r.pct_score = $p_pct_score_val,
                                r.source_microrna_inputs = [$p_mirna_name_tool], // Store original inputs as lists
                                r.source_target_ensembl_inputs = [$p_target_ensembl_full_tool]
                            ON MATCH SET  
                                r.pct_score = CASE WHEN $p_pct_score_val < r.pct_score THEN $p_pct_score_val ELSE r.pct_score END,
                                r.source_microrna_inputs = CASE WHEN NOT $p_mirna_name_tool IN r.source_microrna_inputs THEN r.source_microrna_inputs + $p_mirna_name_tool ELSE r.source_microrna_inputs END,
                                r.source_target_ensembl_inputs = CASE WHEN NOT $p_target_ensembl_full_tool IN r.source_target_ensembl_inputs THEN r.source_target_ensembl_inputs + $p_target_ensembl_full_tool ELSE r.source_target_ensembl_inputs END
                            """
                            rel_result_summary = session.run(merge_relationship_query, params_for_cypher).consume()
                            if rel_result_summary.counters.relationships_created > 0:
                                created_relationships_count += 1
                            elif rel_result_summary.counters.properties_set > 0 : 
                                updated_relationships_count +=1
                    
                    except Exception as e_row:
                        print(f"❌ Error processing TargetScan row {current_row_num_for_log} ('{line.strip()}'): {e_row}")
                        skipped_interactions_count += len(row[mir_family_col_idx].split('/')) if row and len(row) > mir_family_col_idx else 1
                        continue 
                    
                    if (i+1) % 5000 == 0:
                        print(f"  Processed {i+1} lines from TargetScan data file (after header)...")

            print(f"\nFinished TargetScan processing from {data_file_path}")
            print(f"  Total lines read (incl header): {total_lines_read_from_file}")
            print(f"  Interaction pairs considered: {processed_interactions_count}")
            print(f"  New relationships CREATED by MERGE: {created_relationships_count}")
            print(f"  Existing relationships UPDATED by MERGE: {updated_relationships_count}")
            print(f"  Interaction pairs skipped: {skipped_interactions_count}")
            
            final_min_score = min_pct_score if min_pct_score != float('inf') else 0.0
            final_max_score = max_pct_score if max_pct_score != float('-inf') else 1.0
            create_relation_info(database_name_display, data_source_link_specific, final_min_score, final_max_score, 0.0) 

    except FileNotFoundError:
        print(f"CRITICAL Error: Input TargetScan data file not found at {data_file_path}")
        sys.exit(1)
    except Exception as e_main:
        print(f"An CRITICAL unexpected error occurred: {e_main}")
        import traceback
        traceback.print_exc()
    finally:
        close_driver()

    print("TargetScan import script finished.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python src/targetscan_fixed.py <path_to_targetscan_Predicted_Targets_Info.txt> <species_prefix_for_miRNA (e.g., mmu)>")
        sys.exit(1)
    
    targetscan_file_arg = sys.argv[1]
    species_prefix_for_mirna_arg = sys.argv[2]
    
    run_targetscan_import(targetscan_file_arg, species_prefix_for_mirna_arg)