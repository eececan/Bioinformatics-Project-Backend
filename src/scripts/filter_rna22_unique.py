import sys
import os
import csv
from collections import defaultdict

def extract_unique_mirna_gene_pairs(filtered_rna22_dir, output_pairs_filepath):
    print(f"Reading filtered RNA22 files from: {filtered_rna22_dir}")
    print(f"Writing unique miRNA-Gene-Score triples to: {output_pairs_filepath}")

    if not os.path.exists(filtered_rna22_dir):
        print(f"Error: Input directory with filtered files '{filtered_rna22_dir}' not found.")
        sys.exit(1)

    output_dir = os.path.dirname(output_pairs_filepath)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
            print(f"Created output directory: {output_dir}")
        except OSError as e:
            print(f"Error creating output directory '{output_dir}': {e}")
            sys.exit(1)

    # Dictionary to store running averages for each miRNA-gene pair
    # Format: (mirna, gene) -> (sum_of_scores, count)
    mirna_gene_running_avg = defaultdict(lambda: (0.0, 0))
    total_strong_predictions_read = 0

    for filename in os.listdir(filtered_rna22_dir):
        if filename.endswith("_confident.txt"): 
            input_filepath = os.path.join(filtered_rna22_dir, filename)
            print(f"  Processing file: {filename}...")
            try:
                with open(input_filepath, 'r', encoding='utf-8', newline='') as f_in:
                    reader = csv.reader(f_in, delimiter='\t')
                    for i, row in enumerate(reader):
                        total_strong_predictions_read += 1
                        if not row or len(row) < 6:
                            continue

                        mirna_id_tool = row[0].strip()
                        target_identifier_tool = row[1].strip()
                        score = float(row[5].strip())

                        target_ensembl_gene_id = target_identifier_tool.split('_')[0]
                        target_ensembl_gene_id = target_ensembl_gene_id.split('.')[0]

                        if not mirna_id_tool or not target_ensembl_gene_id or not score:
                            continue

                        standardized_mirna_name = mirna_id_tool.replace("_", "-")
                        current_sum, current_count = mirna_gene_running_avg[(standardized_mirna_name, target_ensembl_gene_id)]
                        mirna_gene_running_avg[(standardized_mirna_name, target_ensembl_gene_id)] = (current_sum + score, current_count + 1)
                        
                        if total_strong_predictions_read % 100000 == 0:
                            print(f"    Read {total_strong_predictions_read} strong predictions so far...")

            except Exception as e_file:
                print(f"  Error processing file {filename}: {e_file}")
    
    # Calculate final averages
    unique_mirna_gene_score_triples = set()
    for (mirna, gene), (total_score, count) in mirna_gene_running_avg.items():
        avg_score = total_score / count
        unique_mirna_gene_score_triples.add((mirna, gene, str(avg_score)))
    
    print(f"\nExtraction complete.")
    print(f"  Total strong predictions read from all files: {total_strong_predictions_read}")
    print(f"  Number of unique miRNA-Gene-Score triples found: {len(unique_mirna_gene_score_triples)}")

    try:
        with open(output_pairs_filepath, 'w', encoding='utf-8', newline='') as f_out:
            writer = csv.writer(f_out, delimiter='\t')
            writer.writerow(["miRNA_ID", "Target_Ensembl_Gene_ID", "Score"])
            sorted_triples = sorted(list(unique_mirna_gene_score_triples))
            for mirna, gene, score in sorted_triples:
                writer.writerow([mirna, gene, score])
        print(f"  Unique triples written to: {output_pairs_filepath}")
    except IOError as e_io:
        print(f"Error writing output file '{output_pairs_filepath}': {e_io}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python extract_unique_rna22_pairs.py <input_filtered_rna22_directory> <output_unique_pairs_file.tsv>")
        print("Example: python extract_unique_rna22_pairs.py data/rna22_confident data/rna22_unique_strong_pairs.tsv")
        sys.exit(1)
    
    input_filtered_dir_arg = sys.argv[1]
    output_pairs_file_arg = sys.argv[2]
    extract_unique_mirna_gene_pairs(input_filtered_dir_arg, output_pairs_file_arg)
