import csv
import sys
import os

def sort_bed_by_score(input_bed_path, output_bed_path):
    print(f"Reading and sorting PicTar BED file: {input_bed_path}...")
    print(f"Output will be sorted by score (5th column) in descending order.")

    all_lines = []
    data_lines_with_scores = []
    header_comment_lines = [] 

    try:
        with open(input_bed_path, 'r', encoding='utf-8', newline='') as f_in:
            reader = csv.reader(f_in, delimiter='\t')
            for i, row in enumerate(reader):
                if not row: 
                    continue
                
                if row[0].startswith('track') or row[0].startswith('#'):
                    header_comment_lines.append(row)
                    continue

                if len(row) >= 5: 
                    try:
                        score = float(row[4])
                        data_lines_with_scores.append({'score': score, 'data': row})
                    except ValueError:
                        print(f"Warning: Row {i+1} has an invalid score '{row[4]}'. Treating as a non-data line to be placed at the end.")
                        all_lines.append(row) 
                else:
                    print(f"Warning: Row {i+1} has fewer than 5 columns. Treating as a non-data line.")
                    all_lines.append(row) 
        
        sorted_data_lines = sorted(data_lines_with_scores, key=lambda item: item['score'], reverse=True)

        output_dir = os.path.dirname(output_bed_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created output directory: {output_dir}")

        with open(output_bed_path, 'w', encoding='utf-8', newline='') as f_out:
            writer = csv.writer(f_out, delimiter='\t')
            
            if header_comment_lines:
                for header_row in header_comment_lines:
                    writer.writerow(header_row)
            
            for item in sorted_data_lines:
                writer.writerow(item['data']) 
            
            if all_lines:
                print(f"Appending {len(all_lines)} non-data or malformed score lines to the end of the sorted file.")
                for other_row in all_lines:
                    writer.writerow(other_row)

        print(f"\nSorting complete.")
        print(f"  Processed {len(header_comment_lines) + len(sorted_data_lines) + len(all_lines)} total lines from input.")
        print(f"  Sorted {len(sorted_data_lines)} data lines by score.")
        print(f"  Sorted data (and headers/comments) written to: {output_bed_path}")

    except FileNotFoundError:
        print(f"Error: Input PicTar BED file not found at {input_bed_path}")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred during sorting: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python sort_pictar_bed_by_score.py <input_pictar.bed> <output_sorted_pictar.bed>")
        sys.exit(1)
    
    input_file_arg = sys.argv[1]
    output_file_arg = sys.argv[2]

    sort_bed_by_score(input_file_arg, output_file_arg)