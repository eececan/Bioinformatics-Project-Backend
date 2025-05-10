# --- SCRIPT: filter_mirtarbase.py ---
import csv
import sys
import os # Import os module for path manipulation

def prefilter_mirtarbase_csv(input_csv_path, output_csv_path, species_prefix):
    print(f"Reading input CSV: {input_csv_path}...")
    
    # --- DEFINE YOUR CONFIDENCE CRITERIA HERE ---
    # Criterion A: Strong experiment keywords (case-insensitive)
    # Updated based on your provided image (CLIP-seq was added, others were there)
    strong_experiment_keywords = [
        "luciferase reporter assay", "western blot", "qRT-PCR", "rt-qpcr", 
        "clip-seq", "par-clip", "rip-seq", "degradome-seq", "pasilc" 
    ]
    
    # Criterion B: Support types to EXCLUDE (case-insensitive for matching)
    # We will keep rows where the support type is NOT in this list.
    weak_support_type_keywords = [
        "functional mti (weak)" 
        # Add other phrases that indicate weak support if present in your data
    ]
    # --- END OF CRITERIA DEFINITION ---

    # Dynamically find column indices from the header
    header = []
    mirna_col_idx = -1
    experiments_col_idx = -1
    support_type_col_idx = -1

    try:
        with open(input_csv_path, 'r', encoding='utf-8', newline='') as f_in:
            reader_for_header = csv.reader(f_in)
            try:
                header = next(reader_for_header) # Read the first line (header)
            except StopIteration:
                print(f"Error: Input CSV file '{input_csv_path}' is empty or has no header.")
                sys.exit(1)
                
            header_lower = [h.strip().lower() for h in header]

            # Find indices (adjust exact header names if different in your CSV)
            try:
                # Ensure these strings EXACTLY match your CSV headers (after lowercasing)
                mirna_col_idx = header_lower.index("mirna") 
            except ValueError:
                print("Error: 'miRNA' column (expected header 'mirna') not found in CSV header. Please check header names.")
                print(f"   Header found: {header}")
                sys.exit(1)
            try:
                experiments_col_idx = header_lower.index("experiments")
            except ValueError:
                print("Error: 'Experiments' column not found in CSV header. This column is required for Criterion A.")
                print(f"   Header found: {header}")
                sys.exit(1)
            try:
                support_type_col_idx = header_lower.index("support type")
            except ValueError:
                print("Warning: 'Support type' column not found in CSV header. Criterion B (weak support type removal) will be skipped.")
                support_type_col_idx = -1


            print(f"CSV Header: {header}")
            print(f"  miRNA column index: {mirna_col_idx}")
            print(f"  Experiments column index: {experiments_col_idx}")
            print(f"  Support type column index: {support_type_col_idx if support_type_col_idx != -1 else 'Not Found / Skipped'}")


            kept_rows_count = 0
            processed_data_rows_count = 0 

            # Ensure the output directory exists
            output_dir = os.path.dirname(output_csv_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
                print(f"Created output directory: {output_dir}")


            with open(output_csv_path, 'w', encoding='utf-8', newline='') as f_out:
                writer = csv.writer(f_out)
                writer.writerow(header) # Write the original header to the output file

                for row in reader_for_header: 
                    processed_data_rows_count += 1
                    
                    # Basic validation for row length against max index needed
                    max_needed_idx = mirna_col_idx
                    if experiments_col_idx > max_needed_idx: max_needed_idx = experiments_col_idx
                    if support_type_col_idx != -1 and support_type_col_idx > max_needed_idx:
                        max_needed_idx = support_type_col_idx
                        
                    if not row or len(row) <= max_needed_idx:
                        # print(f"    Skipping malformed row {processed_data_rows_count + 1}: {row}")
                        continue

                    # 0. Species filter
                    mirna_val = row[mirna_col_idx].strip()
                    if not mirna_val.lower().startswith(species_prefix.lower()):
                        continue

                    # 1. Criterion A: Check for strong experimental validation type
                    experiments_val = row[experiments_col_idx].strip().lower()
                    has_strong_experiment = any(keyword in experiments_val for keyword in strong_experiment_keywords)

                    # 2. Criterion B: Check for weak support type
                    is_not_weak_support = True 
                    if support_type_col_idx != -1: # Only apply if column was found
                        support_type_val = row[support_type_col_idx].strip().lower()
                        if any(weak_keyword in support_type_val for weak_keyword in weak_support_type_keywords):
                            is_not_weak_support = False
                    
                    # Combine criteria: Must satisfy BOTH
                    if has_strong_experiment and is_not_weak_support:
                        writer.writerow(row)
                        kept_rows_count += 1
                    
                    if processed_data_rows_count % 50000 == 0:
                        print(f"  Processed {processed_data_rows_count} data rows...")


        print(f"\nPrefiltering complete.")
        print(f"  Total data rows processed (after header): {processed_data_rows_count}")
        print(f"  Rows kept after filtering: {kept_rows_count}")
        print(f"  Filtered data written to: {output_csv_path}")

    except FileNotFoundError:
        print(f"Error: Input CSV file not found at {input_csv_path}")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred during prefiltering: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python filter.py <input_mirtarbase.csv> <output_filtered.csv> <species_prefix (e.g., mmu)>")
        sys.exit(1)
    
    input_file_arg = sys.argv[1]
    output_file_arg = sys.argv[2]
    species_prefix_arg = sys.argv[3]

    prefilter_mirtarbase_csv(input_file_arg, output_file_arg, species_prefix_arg)