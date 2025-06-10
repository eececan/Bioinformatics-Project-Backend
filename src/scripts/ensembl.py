import json
import os
import urllib.parse 
from download import url_request 

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DATA_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, '..', 'data'))
ENSEMBL_CACHE_DIR = BASE_DATA_DIR 
ENSEMBL_CACHE_FILE = os.path.join(ENSEMBL_CACHE_DIR, 'ensembl_gene_cache.dat') 

ENSEMBL_LOOKUP_URL_TEMPLATE = "https://rest.ensembl.org/lookup/id/{}?expand=xrefs&content-type=application/json"

def _ensure_dir_exists(file_path):
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        try: os.makedirs(directory);
        except OSError as e: print(f"Ensembl Helper: Error creating dir '{directory}': {e}"); return False
    return True


def _parse_ensembl_lookup_json(json_data, ensembl_id_val):
    if not json_data: return None
    try:
        data = json.loads(json_data)
        if data.get('error'):
            print(f"Ensembl API Error for {ensembl_id_val}: {data.get('error')}")
            return None

        gene_info = {
            'name': data.get('display_name'), 
            'embl': data.get('id', ensembl_id_val).upper(), 
            'species': None,
            'id': '' 
        }
        species_raw = data.get('species')
        if species_raw:
            gene_info['species'] = ' '.join(word.capitalize() for word in species_raw.split('_'))
        
        xrefs_data = data.get('xrefs', []) 
        for xref in xrefs_data:
            db_name_lower = xref.get('dbname','').lower()
            if db_name_lower in ['entrezgene', 'ncbi_gene', 'ncbigene', 'ncbi_geneid']:
                ncbi_gene_id_val = xref.get('primary_id')
                if ncbi_gene_id_val: gene_info['id'] = ncbi_gene_id_val.strip(); break
                display_id_xref = xref.get('display_id', '')
                if display_id_xref.upper().startswith("GENEID:"):
                    try: gene_info['id'] = display_id_xref.split(':')[1].strip(); break
                    except: pass 
        
        return gene_info if gene_info['name'] and gene_info['embl'] else None
    except json.JSONDecodeError: print(f"Ensembl API: Failed to decode JSON for {ensembl_id_val}"); return None
    except Exception as e: print(f"Ensembl API: Error parsing for {ensembl_id_val}: {e}"); return None


def get_gene_by_id(ensembl_id_val):
    if not ensembl_id_val: return None
    clean_ensembl_id = ensembl_id_val.strip() 

    if _ensure_dir_exists(ENSEMBL_CACHE_FILE):
        try:
            with open(ENSEMBL_CACHE_FILE, 'r', encoding='utf-8') as f_cache:
                for line in f_cache:
                    parts = line.strip().split('\t')
                    if len(parts) == 4 and parts[1] == clean_ensembl_id:
                        if parts[0] == "NOT_FOUND_SYMBOL": return None
                        return {'name': parts[0], 'embl': parts[1], 'id': parts[2], 'species': parts[3]}
        except FileNotFoundError: pass 

    lookup_url = ENSEMBL_LOOKUP_URL_TEMPLATE.format(clean_ensembl_id) 
    
    request_headers = {
        'Accept': 'application/json',
    }
    
    json_response = url_request(lookup_url, None, method="GET", headers=request_headers)
    
    gene_details = _parse_ensembl_lookup_json(json_response, clean_ensembl_id)

    if _ensure_dir_exists(ENSEMBL_CACHE_FILE):
        try:
            with open(ENSEMBL_CACHE_FILE, 'a', encoding='utf-8') as f_cache:
                if gene_details:
                    f_cache.write(f"{gene_details.get('name','')}\t{gene_details.get('embl','')}\t{gene_details.get('id','')}\t{gene_details.get('species','')}\n")
                else:
                    f_cache.write(f"NOT_FOUND_SYMBOL\t{clean_ensembl_id}\tNOT_FOUND_ID\tNOT_FOUND_SPECIES\n")
        except IOError as e: print(f"Warning: Could not write to Ensembl Gene Cache: {e}")
    return gene_details