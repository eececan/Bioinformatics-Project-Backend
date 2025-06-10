import sys
import re
import os
import time
import json 
import urllib.parse
from download import url_request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DATA_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, '..', 'data'))
UNIPROT_CACHE_DIR = BASE_DATA_DIR
UNIPROT_ENS_AC_CACHE_FILE = os.path.join(UNIPROT_CACHE_DIR, 'uniprot_ens_ac_cache.dat') 
UNIPROT_ENTRY_CACHE_FILE = os.path.join(UNIPROT_CACHE_DIR, 'uniprot_entry_cache.dat') 

UNIPROT_IDMAPPING_RUN_URL = "https://rest.uniprot.org/idmapping/run"
UNIPROT_IDMAPPING_STATUS_URL_TEMPLATE = "https://rest.uniprot.org/idmapping/status/{}" 
UNIPROT_IDMAPPING_RESULTS_URL_TEMPLATE = "https://rest.uniprot.org/idmapping/stream/{}" 
UNIPROT_FETCH_TEXT_URL_TEMPLATE = "https://rest.uniprot.org/uniprotkb/{}.txt"

def _ensure_dir_exists(file_path):
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        try: os.makedirs(directory);
        except OSError as e: print(f"UniProt Helper: Error creating dir '{directory}': {e}"); return False
    return True

def _map_ensembl_to_uniprot_ac(ensembl_gene_id):
    if not ensembl_gene_id: return None
    clean_ensembl_id = ensembl_gene_id.strip().upper()

    payload = { "from": "Ensembl", "to": "UniProtKB", "ids": clean_ensembl_id }
    headers_post = {'Accept': 'application/json', 'Content-Type':'application/x-www-form-urlencoded'}
    
    submit_response_text = url_request(UNIPROT_IDMAPPING_RUN_URL, data_payload=payload, method="POST", headers=headers_post)

    if not submit_response_text:
        print(f"UniProt ID Mapping: Failed to submit job for {clean_ensembl_id}.")
        return None
    try:
        job_id = json.loads(submit_response_text).get("jobId")
        if not job_id:
            print(f"UniProt ID Mapping: No jobId for {clean_ensembl_id}. Resp: {submit_response_text[:200]}")
            return None
    except json.JSONDecodeError:
        print(f"UniProt ID Mapping: Could not decode jobId for {clean_ensembl_id}. Resp: {submit_response_text[:200]}")
        return None

    status_url = UNIPROT_IDMAPPING_STATUS_URL_TEMPLATE.format(job_id)
    headers_get = {'Accept': 'application/json'}
    for attempt in range(10): 
        status_response_text = url_request(status_url, None, method="GET", headers=headers_get)
        if not status_response_text: 
            print(f"UniProt ID Mapping: Failed to get status for job {job_id} (attempt {attempt+1})."); 
            if attempt == 9: return None 
            time.sleep(3); continue

        try:
            status_data = json.loads(status_response_text)
            job_status = status_data.get("jobStatus")
            if job_status == "FINISHED":
                results_url = UNIPROT_IDMAPPING_RESULTS_URL_TEMPLATE.format(job_id) + "?format=tsv&fields=accession&size=1" 
                results_tsv = url_request(results_url, None, method="GET", headers=headers_get)
                if results_tsv:
                    lines = results_tsv.strip().splitlines()
                    if len(lines) > 1: 
                        data_parts = lines[1].split('\t') 
                        if len(data_parts) >= 1 and data_parts[0]: 
                            return data_parts[0] 
                print(f"UniProt ID Mapping: No results or format error for job {job_id}. TSV: {results_tsv[:200] if results_tsv else 'None'}")
                return None 
            elif job_status in ["RUNNING", "QUEUED"]: 
                if attempt < 9: time.sleep(3 * (attempt + 1)) 
                else: print(f"UniProt ID Mapping: Job {job_id} still running/queued after max attempts."); return None
            else: 
                print(f"UniProt ID Mapping: Job {job_id} failed or unexpected status: {job_status}. Info: {status_data.get('warnings') or status_data.get('errors')}")
                return None
        except json.JSONDecodeError: print(f"UniProt ID Mapping: Could not decode status/results for job {job_id}. Resp: {status_response_text[:200]}"); return None
        except Exception as e_status: print(f"UniProt ID Mapping: Error checking status job {job_id}: {e_status}"); return None
            
    print(f"UniProt ID Mapping: Job {job_id} timed out for {clean_ensembl_id}.")
    return None

def _parse_uniprot_text_entry(entry_text, uniprot_ac_val, ensembl_id_source=None):
    if not entry_text: return None
    gene_info = {'name': None, 'id': '', 'embl': ensembl_id_source or '', 'species': None, 'ac': uniprot_ac_val}
    try:
        for line in entry_text.splitlines():
            if line.startswith("AC   ") and not gene_info['ac']: 
                gene_info['ac'] = line.split()[1].split(';')[0] 
            elif line.startswith("OS   ") and not gene_info['species']:
                match = re.match(r"OS   (.*?)(?: \(.*|$)", line) 
                if match: gene_info['species'] = match.group(1).strip().rstrip('.')
            elif line.startswith("GN   "): 
                if not gene_info['name']:
                    name_match = re.search(r"Name=([^;{]+)", line) 
                    if name_match: gene_info['name'] = name_match.group(1).strip().upper()
            elif line.startswith("DR   GeneID;"): 
                if not gene_info['id']:
                    gid_match = re.search(r"GeneID;\s*(\d+);", line)
                    if gid_match: gene_info['id'] = gid_match.group(1)
            elif line.startswith("DR   Ensembl;"): 
                if not gene_info['embl'] or gene_info['embl'] == ensembl_id_source: 
                    ensg_match = re.search(r"(ENS[A-Z]*G\d+(\.\d+)?)", line, re.IGNORECASE) 
                    if ensg_match: gene_info['embl'] = ensg_match.group(1).upper() 
        
        return gene_info if gene_info['name'] and gene_info['ac'] else None
    except Exception as e_parse: print(f"UniProt (_parse_text): Error parsing AC '{uniprot_ac_val}': {e_parse}"); return None

def get_gene_by_ens(ensembl_gene_id):
    if not ensembl_gene_id: return None
    clean_ensembl_id = ensembl_gene_id.strip().upper() 
    uniprot_ac = None

    if _ensure_dir_exists(UNIPROT_ENS_AC_CACHE_FILE):
        try:
            with open(UNIPROT_ENS_AC_CACHE_FILE, 'r', encoding='utf-8') as f_c:
                for line in f_c:
                    parts = line.strip().split('\t')
                    if len(parts) == 2 and parts[0].upper() == clean_ensembl_id:
                        uniprot_ac = parts[1] if parts[1] != "NOT_MAPPED" else None; break
        except FileNotFoundError: pass

    if not uniprot_ac:
        uniprot_ac = _map_ensembl_to_uniprot_ac(clean_ensembl_id) 
        if _ensure_dir_exists(UNIPROT_ENS_AC_CACHE_FILE):
            try:
                with open(UNIPROT_ENS_AC_CACHE_FILE, 'a', encoding='utf-8') as f_c:
                    f_c.write(f"{clean_ensembl_id}\t{uniprot_ac or 'NOT_MAPPED'}\n")
            except IOError as e: print(f"Warning: UniProt ENS->AC Cache Write Error: {e}")
        if not uniprot_ac: return None

    if _ensure_dir_exists(UNIPROT_ENTRY_CACHE_FILE):
        try:
            with open(UNIPROT_ENTRY_CACHE_FILE, 'r', encoding='utf-8') as f_c:
                for line in f_c:
                    parts = line.strip().split('\t')
                    if len(parts) == 5 and parts[0] == uniprot_ac:
                        if parts[1] == "NOT_PARSED": return None
                        return {'ac': parts[0], 'name': parts[1], 'id': parts[2], 'species': parts[3], 'embl': parts[4]}
        except FileNotFoundError: pass

    entry_url = UNIPROT_FETCH_TEXT_URL_TEMPLATE.format(urllib.parse.quote(uniprot_ac))
    entry_text = url_request(entry_url, None, method="GET")
    if not entry_text: print(f"UniProt: Failed to fetch entry for AC: {uniprot_ac}"); return None

    parsed_info = _parse_uniprot_text_entry(entry_text, uniprot_ac, clean_ensembl_id) 
    if _ensure_dir_exists(UNIPROT_ENTRY_CACHE_FILE):
        try:
            with open(UNIPROT_ENTRY_CACHE_FILE, 'a', encoding='utf-8') as f_c:
                if parsed_info:
                    f_c.write(f"{parsed_info.get('ac','')}\t{parsed_info.get('name','')}\t{parsed_info.get('id','')}\t{parsed_info.get('species','')}\t{parsed_info.get('embl','')}\n")
                else:
                    f_c.write(f"{uniprot_ac}\tNOT_PARSED\tNOT_PARSED\tNOT_PARSED\t{clean_ensembl_id}\n")
        except IOError as e: print(f"Warning: UniProt Entry Cache Write Error: {e}")
    return parsed_info