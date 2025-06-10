import csv
import sys
import os
import math 

def calculate_percentile_score(scores_list, percentile):
    """Calculates the score at a given percentile from a sorted list of scores."""
    if not scores_list:
        return 0 
    
    index = int(math.ceil((percentile / 100.0) * len(scores_list))) -1 
    if index < 0:
        index = 0
    if index >= len(scores_list):
        index = len(scores_list) - 1
        
    return scores_list[index]

def filter_pictar_by_percentiles(input_bed_path, output_basename):
    print(f"Reading PicTar BED file to determine score percentiles: {input_bed_path}...")

    all_scores = []
    header_comment_lines = []
    malformed_lines_for_later = [] 

    try:
        with open(input_bed_path, 'r', encoding='utf-8', newline='') as f_in:
            reader = csv.reader(f_in, delimiter='\t')
            for i, row in enumerate(reader):
                if not row: continue
                if row[0].startswith('track') or row[0].startswith('#'):
                    header_comment_lines.append(row)
                    continue
                if len(row) >= 5:
                    try:
                        score = float(row[4])
                        all_scores.append(score)
                    except ValueError:
                        malformed_lines_for_later.append(row)
                else:
                    malformed_lines_for_later.append(row)
        
        if not all_scores:
            print("No valid numeric scores found in the input file. Cannot determine percentiles.")
            for suffix in ["_high_sensitivity.bed", "_medium_sensitivity.bed", "_low_sensitivity.bed"]:
                with open(output_basename + suffix, 'w', encoding='utf-8', newline='') as f_empty_out:
                    writer = csv.writer(f_empty_out, delimiter='\t')
                    for header_row in header_comment_lines: 
                        writer.writerow(header_row)
            return

        all_scores.sort() 

        cutoff_high_sensitivity_score = calculate_percentile_score(all_scores, 90) 
        cutoff_medium_sensitivity_score = calculate_percentile_score(all_scores, 70)
        cutoff_low_sensitivity_score = calculate_percentile_score(all_scores, 50)

        print("\nCalculated Score Thresholds:")
        print(f"  High Sensitivity (top 10%): Scores >= {cutoff_high_sensitivity_score:.2f} (90th percentile)")
        print(f"  Medium Sensitivity (top 30%): Scores >= {cutoff_medium_sensitivity_score:.2f} (70th percentile)")
        print(f"  Low Sensitivity (top 50%): Scores >= {cutoff_low_sensitivity_score:.2f} (50th percentile / median)")
        
        output_files_data = {
            "high": {'path': output_basename + "_high_sensitivity.bed", 'threshold': cutoff_high_sensitivity_score, 'writer': None, 'count': 0, 'file_handle': None},
            "medium": {'path': output_basename + "_medium_sensitivity.bed", 'threshold': cutoff_medium_sensitivity_score, 'writer': None, 'count': 0, 'file_handle': None},
            "low": {'path': output_basename + "_low_sensitivity.bed", 'threshold': cutoff_low_sensitivity_score, 'writer': None, 'count': 0, 'file_handle': None}
        }

        for level_data in output_files_data.values():
            output_dir = os.path.dirname(level_data['path'])
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
                print(f"Created output directory: {output_dir}")
            level_data['file_handle'] = open(level_data['path'], 'w', encoding='utf-8', newline='')
            level_data['writer'] = csv.writer(level_data['file_handle'], delimiter='\t')
            for header_row in header_comment_lines:
                level_data['writer'].writerow(header_row)
        
        processed_data_rows_count = 0
        with open(input_bed_path, 'r', encoding='utf-8', newline='') as f_in_process:
            reader_process = csv.reader(f_in_process, delimiter='\t')
            for row in reader_process:
                if not row or row[0].startswith('track') or row[0].startswith('#'):
                    continue 

                processed_data_rows_count +=1
                if len(row) >= 5:
                    try:
                        current_score = float(row[4])
                        for level, data in output_files_data.items():
                            if current_score >= data['threshold']:
                                data['writer'].writerow(row)
                                data['count'] += 1
                    except ValueError:
                        pass 
                
                if processed_data_rows_count % 20000 == 0:
                    print(f"  Filtering: Processed {processed_data_rows_count} data rows...")

        for level_data in output_files_data.values():
            if level_data['file_handle']:
                level_data['file_handle'].close()
            print(f"  Filtered file '{level_data['path']}' contains {level_data['count']} data rows.")
        
        if malformed_lines_for_later:
            print(f"Note: {len(malformed_lines_for_later)} lines with malformed scores or too few columns were not included in percentile calculations or filtered outputs.")

        print("\nPercentile-based filtering complete.")

    except FileNotFoundError:
        print(f"Error: Input PicTar BED file not found at {input_bed_path}")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python filter_pictar_by_percentiles.py <input_pictar.bed> <output_file_basename>")
        print("Example: python filter_pictar_by_percentiles.py data/pictar_in.bed data/pictar_filtered")
        print("This will create: data/pictar_filtered_high_sensitivity.bed, ..._medium_sensitivity.bed, ..._low_sensitivity.bed")
        sys.exit(1)
    
    input_file_arg = sys.argv[1]
    output_basename_arg = sys.argv[2] 
    filter_pictar_by_percentiles(input_file_arg, output_basename_arg)