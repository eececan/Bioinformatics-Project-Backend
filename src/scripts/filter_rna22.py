import sys
import os
import csv

def prefilter_rna22_files(input_rna22_dir, output_rna22_dir, score_threshold):
    print(f"Reading RNA22 files from: {input_rna22_dir}")
    print(f"Writing filtered files to: {output_rna22_dir}")
    print(f"Filtering for scores <= {score_threshold} (more negative is better)")

    if not os.path.exists(input_rna22_dir):
        print(f"Error: Input directory '{input_rna22_dir}' not found.")
        sys.exit(1)

    if not os.path.exists(output_rna22_dir):
        try:
            os.makedirs(output_rna22_dir)
            print(f"Created output directory: {output_rna22_dir}")
        except OSError as e:
            print(f"Error creating output directory '{output_rna22_dir}': {e}")
            sys.exit(1)

    total_files_processed = 0
    total_rows_read_overall = 0
    total_rows_kept_overall = 0
    invalid_score_lines_count = 0
    skipped_due_to_length = 0

    for filename in os.listdir(input_rna22_dir):
        if filename.endswith(".txt"): 
            input_filepath = os.path.join(input_rna22_dir, filename)
            output_filename = os.path.splitext(filename)[0] + "_confident" + ".txt"
            output_filepath = os.path.join(output_rna22_dir, output_filename)

            current_file_rows_read = 0
            current_file_rows_kept = 0
            first_invalid_score_logged_this_file = False 
            
            try:
                with open(input_filepath, 'r', encoding='utf-8', newline='') as f_in, \
                     open(output_filepath, 'w', encoding='utf-8', newline='') as f_out:
                    
                    reader = csv.reader(f_in, delimiter='\t')
                    writer = csv.writer(f_out, delimiter='\t')

                    print(f"  Processing file: {filename}...")

                    for i, row in enumerate(reader):
                        current_file_rows_read += 1
                        total_rows_read_overall +=1

                        if not row or len(row) < 6: 
                            skipped_due_to_length += 1
                            continue
                        
                        score_str_from_file = "N/A_COLUMN_MISSING" 
                        if len(row) > 5: 
                            score_str_from_file = row[5].strip() 
                        else: 
                            skipped_due_to_length += 1
                            continue
                        
                        try:
                            current_score = float(score_str_from_file)
                        except ValueError:
                            invalid_score_lines_count += 1
                            if not first_invalid_score_logged_this_file: 
                                print(f"    DEBUG (File: {filename}, Row: {i+1}): Invalid score string encountered: '{score_str_from_file}' (raw value from col 6: '{row[5]}')")
                                first_invalid_score_logged_this_file = True
                            continue 
                        
                        passes_filter = current_score <= score_threshold
                        
                        if passes_filter:
                            writer.writerow(row)
                            current_file_rows_kept += 1
                            total_rows_kept_overall +=1
                        
                if current_file_rows_read > 0 : 
                    print(f"    Finished {filename}. Kept {current_file_rows_kept} / {current_file_rows_read} data rows.")
                else:
                    print(f"    Finished {filename}. No processable data rows found.")
                total_files_processed +=1

            except Exception as e_file:
                print(f"  Error processing file {filename}: {e_file}")
    
    print(f"\nRNA22 prefiltering complete.")
    print(f"  Total files processed: {total_files_processed}")
    print(f"  Total data rows read across all files: {total_rows_read_overall}")
    print(f"  Total data rows kept after filtering: {total_rows_kept_overall}")
    print(f"  Total lines skipped due to insufficient columns: {skipped_due_to_length}")
    print(f"  Total lines with invalid scores skipped: {invalid_score_lines_count}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python prefilter_rna22.py <input_rna22_directory> <output_filtered_directory> <max_score_threshold>")
        print("Example: python prefilter_rna22.py data/rna22 data/rna22_confident -20.0")
        print("  Note: <max_score_threshold> should be negative (e.g., -20.0); more negative is better.")
        sys.exit(1)
    
    input_dir_arg = sys.argv[1]
    output_dir_arg = sys.argv[2]
    try:
        score_threshold_arg = float(sys.argv[3])
    except ValueError:
        print("Error: max_score_threshold (3rd argument) must be a number.")
        sys.exit(1)

    prefilter_rna22_files(input_dir_arg, output_dir_arg, score_threshold_arg)