import sys
import os
import csv 

def prefilter_targetscan(input_txt_path, output_txt_path, 
                         target_species_id, 
                         allowed_seed_matches, 
                         min_pct_threshold):
    
    print(f"Reading TargetScan data: {input_txt_path}...")
    print(f"Filtering for Species ID: {target_species_id}")
    print(f"Allowed seed matches: {', '.join(allowed_seed_matches)}")
    print(f"Minimum PCT threshold (>=): {min_pct_threshold}")

    kept_rows_count = 0
    processed_data_rows_count = 0
    header_line = None

    try:
        
        output_dir = os.path.dirname(output_txt_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created output directory: {output_dir}")

        with open(input_txt_path, 'r', encoding='utf-8', newline='') as f_in, \
             open(output_txt_path, 'w', encoding='utf-8', newline='') as f_out:
            
            reader = csv.reader(f_in, delimiter='\t') 
            writer = csv.writer(f_out, delimiter='\t')

            try:
                header_line = next(reader) 
                writer.writerow(header_line) 
            except StopIteration:
                print("Error: Input file is empty or has no header.")
                sys.exit(1)

            header_lower = [h.strip().lower() for h in header_line]
            try:
                species_id_col_idx = header_lower.index("species id")
                seed_match_col_idx = header_lower.index("seed match")
                pct_col_idx = header_lower.index("pct")
            except ValueError as ve:
                print(f"Error: Could not find required columns in header: {ve}")
                print(f"  Header found: {header_line}")
                print(f"  Expected (lowercase): 'species id', 'seed match', 'pct'")
                sys.exit(1)

            for row in reader:
                processed_data_rows_count += 1

                if not row or len(row) <= max(species_id_col_idx, seed_match_col_idx, pct_col_idx):
                    continue

                current_species_id = row[species_id_col_idx].strip()
                if current_species_id != target_species_id:
                    continue

                current_seed_match = row[seed_match_col_idx].strip()
                if current_seed_match not in allowed_seed_matches:
                    continue
                
                try:
                    current_pct_score = float(row[pct_col_idx].strip())
                except (ValueError, IndexError):
                    continue
                
                if current_pct_score < min_pct_threshold: 
                    continue
                
                writer.writerow(row)
                kept_rows_count += 1

                if processed_data_rows_count % 50000 == 0:
                    print(f"  Processed {processed_data_rows_count} data rows...")
        
        print(f"\nTargetScan prefiltering complete.")
        print(f"  Total data rows processed (after header): {processed_data_rows_count}")
        print(f"  Rows kept after filtering: {kept_rows_count}")
        print(f"  Filtered data written to: {output_txt_path}")

    except FileNotFoundError:
        print(f"Error: Input TargetScan file not found at {input_txt_path}")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred during TargetScan prefiltering: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 6: 
        print("Usage: python prefilter_targetscan_txt.py <input.txt> <output_filtered.txt> <species_id> <min_pct_score> \"<allowed_seed_matches>\"")
        print("Example for Mus musculus, keeping 8mer & 7mer-m8 sites with PCT <= 0.5:")
        print("  python prefilter_targetscan_txt.py input.txt output.txt 10090 0.5 \"8mer,7mer-m8\"")
        print("  Note: Allowed seed matches should be a comma-separated string enclosed in quotes if it contains spaces or multiple values.")
        sys.exit(1)
    
    input_path_arg = sys.argv[1]
    output_path_arg = sys.argv[2]
    species_id_arg = sys.argv[3]
    try:
        min_pct_arg = float(sys.argv[4])
    except ValueError:
        print("Error: min_pct_score (4th argument) must be a number.")
        sys.exit(1)
    
    allowed_seeds_str_arg = sys.argv[5] 
    allowed_seeds_list_arg = [s.strip() for s in allowed_seeds_str_arg.split(',')]
    prefilter_targetscan(input_path_arg, output_path_arg, species_id_arg, 
                         allowed_seeds_list_arg, min_pct_arg)