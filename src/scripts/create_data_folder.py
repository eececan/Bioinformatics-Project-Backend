import os
import requests
import gzip
import shutil
import zipfile
from ftplib import FTP

# --- Configuration ---
BASE_PROJECT_DIR = "bioinformatics_project" # Name of the main project folder
DATA_DIR = os.path.join(BASE_PROJECT_DIR, "data")

# URLs - Updated as of May 2025 (Verify if issues occur)
MIRBASE_FTP_HOST = "mirbase.org" # Updated from ftp.mirbase.org
MIRBASE_FTP_PATH_CURRENT = "/pub/mirbase/CURRENT/"
MIARNA_DAT_GZ = "miRNA.dat.gz"
ALIASES_TXT_GZ = "aliases.txt.gz"

TARGETSCAN_MOUSE_URL = "https://www.targetscan.org/mmu_80/mmu_80_data_download/Conserved_Family_Conserved_Targets_Info.txt.zip"
# Note: mmu_80 is the current version as of checking. This might update.

MIRTARBASE_MOUSE_URL = "https://mirtarbase.cuhk.edu.cn/mtb_v9/download/mus_musculus.tsv.gz"
# Note: This is for miRTarBase v9.0. This URL provides a TSV file.

RNA22_DOWNLOAD_PAGE = "https://cm.jefferson.edu/data-tools-downloads/rna22-full-sets-of-predictions/"
# User will need to download "MusMusculus,mRNA,ENSEMBL65,miRbase18,RNA22v2" archive from this page.

PICTAR_UCSC_PAGE = "https://genome.ucsc.edu/cgi-bin/hgTables"
# User needs to manually download PicTar BED files for mm7 (or ideally a newer assembly if PicTar data exists for it)

# --- Helper Functions ---
def create_dir_if_not_exists(dir_path):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        print(f"Created directory: {dir_path}")
    else:
        print(f"Directory already exists: {dir_path}")

def download_file_http(url, local_filename):
    print(f"Downloading {url} to {local_filename}...")
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"Successfully downloaded {local_filename}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {url}: {e}")
        return False

def download_file_ftp(host, remote_path, local_filename):
    print(f"Downloading ftp://{host}{remote_path} to {local_filename}...")
    try:
        with FTP(host) as ftp:
            ftp.login() # Anonymous login
            # It seems the files are directly under /pub/mirbase/CURRENT/
            # The ftp.cwd(remote_base_dir) might not be needed if path is absolute
            with open(local_filename, 'wb') as f:
                ftp.retrbinary(f"RETR {remote_path}", f.write)
        print(f"Successfully downloaded {local_filename}")
        return True
    except Exception as e:
        print(f"Error downloading FTP file {remote_path} from {host}: {e}")
        return False

def extract_gz(gz_path, output_path):
    print(f"Extracting {gz_path} to {output_path}...")
    try:
        with gzip.open(gz_path, 'rb') as f_in:
            with open(output_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        print(f"Successfully extracted to {output_path}")
        os.remove(gz_path) # Remove the .gz file after extraction
        print(f"Removed {gz_path}")
        return True
    except Exception as e:
        print(f"Error extracting {gz_path}: {e}")
        return False

def extract_zip(zip_path, output_dir):
    print(f"Extracting {zip_path} to {output_dir}...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(output_dir)
        print(f"Successfully extracted to {output_dir}")
        # os.remove(zip_path) # Optionally remove the .zip file
        # print(f"Removed {zip_path}")
        return True
    except Exception as e:
        print(f"Error extracting {zip_path}: {e}")
        return False

# --- Main Script ---
if __name__ == "__main__":
    print("--- Starting Project Setup ---")

    # 1. Create Base Directory Structure
    create_dir_if_not_exists(BASE_PROJECT_DIR)
    create_dir_if_not_exists(DATA_DIR)

    src_dir = os.path.join(BASE_PROJECT_DIR, "src")
    create_dir_if_not_exists(src_dir)
    print(f"Please place your Python scripts (dbhelper.py, mirbase.py, etc.) in: {src_dir}")

    sub_data_dirs = ["mirbase", "mirtarbase", "pictar", "pictar/genome", "rna22", "targetscan"]
    for sub_dir in sub_data_dirs:
        create_dir_if_not_exists(os.path.join(DATA_DIR, sub_dir))

    # 2. Download miRBase files
    print("\n--- Downloading miRBase Data ---")
    mirbase_data_path = os.path.join(DATA_DIR, "mirbase")
    mirna_dat_gz_local = os.path.join(mirbase_data_path, MIARNA_DAT_GZ)
    mirna_dat_local = os.path.join(mirbase_data_path, "miRNA.dat")
    aliases_txt_gz_local = os.path.join(DATA_DIR, "aliases.txt.gz") # Place directly in data/ as per structure
    aliases_txt_local = os.path.join(DATA_DIR, "aliases.txt")

    if download_file_ftp(MIRBASE_FTP_HOST, MIRBASE_FTP_PATH_CURRENT + MIARNA_DAT_GZ, mirna_dat_gz_local):
        extract_gz(mirna_dat_gz_local, mirna_dat_local)

    if download_file_ftp(MIRBASE_FTP_HOST, MIRBASE_FTP_PATH_CURRENT + ALIASES_TXT_GZ, aliases_txt_gz_local):
        extract_gz(aliases_txt_gz_local, aliases_txt_local)

    # 3. Download TargetScan
    print("\n--- Downloading TargetScan Data ---")
    targetscan_data_path = os.path.join(DATA_DIR, "targetscan")
    targetscan_zip_local = os.path.join(targetscan_data_path, "TargetScan_mmu_conserved_targets.zip")
    targetscan_txt_local = os.path.join(targetscan_data_path, "Conserved_Family_Conserved_Targets_Info.txt") # Expected name

    if download_file_http(TARGETSCAN_MOUSE_URL, targetscan_zip_local):
        # Extract specifically the file we need if the zip contains multiple or a folder
        print(f"Extracting TargetScan data from {targetscan_zip_local}...")
        try:
            with zipfile.ZipFile(targetscan_zip_local, 'r') as zip_ref:
                # Look for the specific file name, might be in a subfolder in the zip
                member_to_extract = None
                for member in zip_ref.namelist():
                    if "Conserved_Family_Conserved_Targets_Info.txt" in member:
                        member_to_extract = member
                        break
                if member_to_extract:
                    # Extract to targetscan_data_path, ensuring the final name is as expected
                    zip_ref.extract(member_to_extract, targetscan_data_path)
                    extracted_file_path = os.path.join(targetscan_data_path, member_to_extract)
                    # Rename if the extracted file is in a subdirectory or has a different name
                    if extracted_file_path != targetscan_txt_local:
                         shutil.move(extracted_file_path, targetscan_txt_local)
                         # Clean up empty directory if created by extract
                         if os.path.isdir(os.path.dirname(extracted_file_path)) and not os.listdir(os.path.dirname(extracted_file_path)):
                             if os.path.dirname(extracted_file_path) != targetscan_data_path :
                                 os.rmdir(os.path.dirname(extracted_file_path))

                    print(f"Successfully extracted TargetScan data to {targetscan_txt_local}")
                else:
                    print(f"Could not find 'Conserved_Family_Conserved_Targets_Info.txt' in {targetscan_zip_local}. Please extract manually.")
        except Exception as e:
            print(f"Error extracting {targetscan_zip_local}: {e}. Please extract manually.")


    # 4. Download miRTarBase
    print("\n--- Downloading miRTarBase Data ---")
    mirtarbase_data_path = os.path.join(DATA_DIR, "mirtarbase")
    mirtarbase_tsv_gz_local = os.path.join(mirtarbase_data_path, "mus_musculus.tsv.gz")
    mirtarbase_tsv_local = os.path.join(mirtarbase_data_path, "mmu_MTI.tsv") # Your script expects mmu_MTI.csv, this is tsv

    if download_file_http(MIRTARBASE_MOUSE_URL, mirtarbase_tsv_gz_local):
        if extract_gz(mirtarbase_tsv_gz_local, mirtarbase_tsv_local):
            print(f"miRTarBase TSV file saved as {mirtarbase_tsv_local}.")
            print("NOTE: Your original script expected 'mmu_MTI.csv'. This downloaded file is 'mmu_MTI.tsv'.")
            print("You may need to adjust your mirtarbase script to read this TSV (tab-separated) file,")
            print("or rename this file to .csv if your script can handle TSV with a .csv extension and appropriate delimiter settings.")


    # 5. Instructions for Manual Downloads
    print("\n--- Manual Download Instructions ---")

    # RNA22
    rna22_local_path = os.path.join(DATA_DIR, "rna22")
    print(f"\nRNA22:")
    print(f"1. Go to: {RNA22_DOWNLOAD_PAGE}")
    print(f"2. Find and download the dataset for 'MusMusculus', specifically the one corresponding to")
    print(f"   'mRNA,ENSEMBL65,miRbase18,RNA22v2' (this might be an archive like .zip or .tar.gz).")
    print(f"3. Extract all the individual miRNA prediction files into: {rna22_local_path}")

    # PicTar
    pictar_local_path = os.path.join(DATA_DIR, "pictar", "genome")
    pictar_mirna_accession_path = os.path.join(DATA_DIR, "pictar", "mirna_accession.dat")
    print(f"\nPicTar:")
    print(f"1. Go to UCSC Table Browser: {PICTAR_UCSC_PAGE}")
    print(f"2. Select options for Mouse mm7 assembly (or ideally a newer assembly if PicTar data is available for it):")
    print(f"   - clade: Mammal, genome: Mouse, assembly: Aug. 2005 (NCBI35/mm7)")
    print(f"   - group: Expression and Regulation, track: PicTar miRNA")
    print(f"   - table: picTarMiRNAChicken (for PicTar13) and/or picTarMiRNADog (for PicTar7)")
    print(f"   - output format: BED - browser extensible data")
    print(f"3. Download the BED file(s) and place them in: {pictar_local_path}")
    print(f"   (e.g., {os.path.join(pictar_local_path, 'picTarMiRNAChicken_mm7.bed')})")
    print(f"4. For PicTar's 'mirna_accession.dat': This file maps PicTar's miRNA names to accessions.")
    print(f"   The original PDF was vague on its source. If the PicTar website (pictar.mdc-berlin.de, likely defunct)")
    print(f"   doesn't provide it, you may need to create this mapping yourself by comparing PicTar miRNA names")
    print(f"   to miRBase data, or adapt your `pictar_fixed.py` script's `miRNA2accession` function.")
    print(f"   Place it at: {pictar_mirna_accession_path} if you obtain/create it.")


    # Cache files (will be created by scripts)
    print("\n--- Cache File Information ---")
    print(f"The following cache files will be created by your scripts when they run:")
    print(f"- {os.path.join(DATA_DIR, 'ncbi_gene.dat')} (by ncbi.py)")
    # print(f"- {os.path.join(DATA_DIR, 'pictar', 'refseq_geneid.dat')} (by ncbi.py, if get_geneid_by_refseq is called often from pictar script)")


    print("\n--- Setup Script Finished ---")
    print(f"Base project directory: {os.path.abspath(BASE_PROJECT_DIR)}")