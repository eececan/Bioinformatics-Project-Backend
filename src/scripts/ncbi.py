import sys
import re
import os 
from download import url_request 

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DATA_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, '..', 'data')) 

GENE_CACHE_DIR = BASE_DATA_DIR 
NCBI_GENE_CACHE_FILE = os.path.join(GENE_CACHE_DIR, 'ncbi_gene.dat')

REFSEQ_CACHE_SUBDIR = os.path.join(BASE_DATA_DIR, 'pictar') 
REFSEQ_GENEID_CACHE_FILE = os.path.join(REFSEQ_CACHE_SUBDIR, 'refseq_geneid.dat')

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
API_KEY = None 

def _ensure_dir_exists(file_path):
    """Helper to ensure the directory for a file exists."""
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        try:
            os.makedirs(directory)
            print(f"NCBI Helper: Created directory '{directory}'")
        except OSError as e:
            print(f"NCBI Helper: Error creating directory '{directory}': {e}")
            return False
    return True

def _query_eutils(base_url, params_dict):
    """Helper function to query NCBI E-utils with basic error checking."""
    query_params = params_dict.copy() 
    if API_KEY:
        query_params['api_key'] = API_KEY
    
    param_string = "&".join([f"{k}={v}" for k, v in query_params.items()])
    full_url = f"{base_url}?{param_string}"
    
    response_text = url_request(full_url, None) 
    if not response_text:
        print(f"NCBI E-utils query failed or returned empty response for URL: {full_url}")
    return response_text

def get_geneid_by_refseq(refseq_accession):
    """
    Get NCBI GeneID for a given RefSeq transcript accession.
    Checks local cache first, then queries NCBI E-utils.
    Returns GeneID as a string, or None if not found/error.
    """
    if not refseq_accession or not isinstance(refseq_accession, str):
        print("NCBI (get_geneid_by_refseq): Invalid RefSeq accession input.")
        return None
    
    refseq_id_cleaned = refseq_accession.strip().split('.')[0] 

    if _ensure_dir_exists(REFSEQ_GENEID_CACHE_FILE): 
        try:
            with open(REFSEQ_GENEID_CACHE_FILE, 'r', encoding='utf-8') as f_cache:
                for line in f_cache:
                    parts = line.strip().split('\t')
                    if len(parts) == 2 and parts[0] == refseq_id_cleaned:
                        if parts[1] == "NOT_FOUND":
                            return None
                        return parts[1] 
        except FileNotFoundError:
            pass 

    esearch_params = {'db': 'nuccore', 'term': refseq_id_cleaned, 'retmode': 'xml'}
    xml_response_esearch = _query_eutils(ESEARCH_URL, esearch_params)
    if not xml_response_esearch:
        return None 

    uid_match = re.search(r"<Id>(\d+)</Id>", xml_response_esearch)
    if not uid_match:
        print(f"NCBI (get_geneid_by_refseq): No nuccore UID found for RefSeq '{refseq_id_cleaned}'.")
        if _ensure_dir_exists(REFSEQ_GENEID_CACHE_FILE):
            try:
                with open(REFSEQ_GENEID_CACHE_FILE, 'a', encoding='utf-8') as f_cache:
                    f_cache.write(f"{refseq_id_cleaned}\tNOT_FOUND\n")
            except IOError as e: print(f"Warning: Could not write NOT_FOUND to RefSeq cache: {e}")
        return None
    nuccore_uid = uid_match.group(1)

    efetch_params = {'db': 'nuccore', 'id': nuccore_uid, 'rettype': 'gb', 'retmode': 'text'}
    gb_data = _query_eutils(EFETCH_URL, efetch_params)
    if not gb_data:
        return None 

    gene_id_match = re.search(r'/db_xref="GeneID:(\d+)"', gb_data)
    if gene_id_match:
        gene_id = gene_id_match.group(1)
        if _ensure_dir_exists(REFSEQ_GENEID_CACHE_FILE): 
            try:
                with open(REFSEQ_GENEID_CACHE_FILE, 'a', encoding='utf-8') as f_cache:
                    f_cache.write(f"{refseq_id_cleaned}\t{gene_id}\n")
            except IOError as e: print(f"Warning: Could not write to RefSeq cache: {e}")
        return gene_id
    else:
        print(f"NCBI (get_geneid_by_refseq): No GeneID cross-reference found for RefSeq '{refseq_id_cleaned}' (Nuccore UID: {nuccore_uid}).")
        if _ensure_dir_exists(REFSEQ_GENEID_CACHE_FILE):
            try:
                with open(REFSEQ_GENEID_CACHE_FILE, 'a', encoding='utf-8') as f_cache:
                    f_cache.write(f"{refseq_id_cleaned}\tNOT_FOUND\n")
            except IOError as e: print(f"Warning: Could not write NOT_FOUND to RefSeq cache: {e}")
        return None


def _parse_gene_efetch_xml(xml_data, requested_gene_id_for_error_log="Unknown"):
    """
    Parses XML output from NCBI EFetch (db=gene).
    Returns a dictionary {'name', 'id', 'embl', 'species'} or None.
    This is a simplified parser; for robustness, an XML library (e.g., xml.etree.ElementTree) is better.
    """
    if not xml_data: return None
    gene_info = {'name': None, 'id': None, 'embl': '', 'species': None} 

    try:
        geneid_match = re.search(r"<Gene-track_geneid>(\d+)</Gene-track_geneid>", xml_data)
        if geneid_match: gene_info['id'] = geneid_match.group(1)

        symbol_match = re.search(r"<Gene-ref_locus>([^<]+)</Gene-ref_locus>", xml_data)
        if symbol_match: gene_info['name'] = symbol_match.group(1).upper()

        species_match = re.search(r"<Org-ref_taxname>([^<]+)</Org-ref_taxname>", xml_data)
        if species_match: gene_info['species'] = species_match.group(1)

        ensembl_dbtag_block_match = re.search(r"<Dbtag>\s*<Dbtag_db>ENSEMBL</Dbtag_db>\s*<Dbtag_tag>\s*<Object-id>\s*<Object-id_str>([^<]+)</Object-id_str>", xml_data, re.IGNORECASE)
        if ensembl_dbtag_block_match:
            gene_info['embl'] = ensembl_dbtag_block_match.group(1)
        
        if gene_info['id'] and gene_info['name']: 
            return gene_info
        else:
            return None
    except Exception as e:
        print(f"NCBI (_parse_gene_efetch_xml): Error parsing XML for GeneID '{requested_gene_id_for_error_log}': {e}")
        return None


def _fetch_and_cache_gene_details(gene_id_to_fetch):
    """Fetches full gene details from NCBI by GeneID and caches them."""
    if not gene_id_to_fetch: return None

    efetch_params = {'db': 'gene', 'id': str(gene_id_to_fetch).strip(), 'retmode': 'xml'}
    xml_data = _query_eutils(EFETCH_URL, efetch_params)
    gene_details = _parse_gene_efetch_xml(xml_data, str(gene_id_to_fetch))

    if _ensure_dir_exists(NCBI_GENE_CACHE_FILE): 
        try:
            with open(NCBI_GENE_CACHE_FILE, 'a', encoding='utf-8') as f_cache:
                if gene_details:
                    f_cache.write(f"{gene_details.get('name','')}\t{gene_details.get('embl','')}\t{gene_details.get('id','')}\t{gene_details.get('species','')}\n")
                else:
                    print(f"NCBI API (Gene Details): Could not fetch/parse for GeneID {gene_id_to_fetch}. Caching as NOT_FOUND.")
                    f_cache.write(f"NOT_FOUND_SYMBOL\tNOT_FOUND_EMBL\t{gene_id_to_fetch}\tNOT_FOUND_SPECIES\n")
        except IOError as e: print(f"Warning: Could not write to NCBI Gene Cache: {e}")
    return gene_details


def get_gene_record_from_cache_line(line_parts):
    """Helper to parse a line from ncbi_gene.dat into a dict."""
    if len(line_parts) == 4:
        if line_parts[0] == "NOT_FOUND_SYMBOL" and line_parts[2] == "NOT_FOUND_EMBL": 
            return None 
        return {'name': line_parts[0], 'embl': line_parts[1], 'id': line_parts[2], 'species': line_parts[3]}
    return None


def get_gene_by_id(gene_id_input):
    """Get gene details by NCBI GeneID. Checks cache first."""
    if not gene_id_input: return None
    try:
        clean_gene_id_str = str(int(float(str(gene_id_input))))
    except ValueError:
        print(f"NCBI (get_gene_by_id): Invalid GeneID format '{gene_id_input}'.")
        return None

    if _ensure_dir_exists(NCBI_GENE_CACHE_FILE):
        try:
            with open(NCBI_GENE_CACHE_FILE, 'r', encoding='utf-8') as f_cache:
                for line in f_cache:
                    parts = line.strip().split('\t')
                    if len(parts) == 4 and parts[2] == clean_gene_id_str: 
                        return get_gene_record_from_cache_line(parts)
        except FileNotFoundError:
            pass 

    return _fetch_and_cache_gene_details(clean_gene_id_str)


def get_gene_by_name(gene_symbol, species_filter=None):
    """Get gene details by gene symbol. Checks cache first."""
    if not gene_symbol: return None
    clean_gene_symbol = gene_symbol.strip().upper() 

    if _ensure_dir_exists(NCBI_GENE_CACHE_FILE):
        try:
            with open(NCBI_GENE_CACHE_FILE, 'r', encoding='utf-8') as f_cache:
                for line in f_cache:
                    parts = line.strip().split('\t')
                    if len(parts) == 4 and parts[0].upper() == clean_gene_symbol:
                        if species_filter and parts[3].lower() != species_filter.strip().lower():
                            continue
                        return get_gene_record_from_cache_line(parts)
        except FileNotFoundError:
            pass

    term = f"{clean_gene_symbol}[Gene Name]"
    if species_filter:
        term += f" AND \"{species_filter.strip()}\"[Organism]" 
    
    esearch_params = {'db': 'gene', 'term': term, 'retmode': 'xml'}
    xml_response_esearch = _query_eutils(ESEARCH_URL, esearch_params)
    if not xml_response_esearch: return None

    id_list_match = re.findall(r"<Id>(\d+)</Id>", xml_response_esearch)
    if not id_list_match:
        print(f"NCBI (get_gene_by_name): No GeneID found for Symbol '{clean_gene_symbol}' (Species: {species_filter}).")
        if _ensure_dir_exists(NCBI_GENE_CACHE_FILE):
            try:
                with open(NCBI_GENE_CACHE_FILE, 'a', encoding='utf-8') as f_cache:
                    f_cache.write(f"{clean_gene_symbol}\tSYMBOL_NOT_FOUND_EMBL\tSYMBOL_NOT_FOUND_ID\t{species_filter or 'ANY'}\n")
            except IOError as e: print(f"Warning: Could not write SYMBOL_NOT_FOUND to Gene Cache: {e}")
        return None
    
    gene_id_to_fetch = id_list_match[0] 
    return _fetch_and_cache_gene_details(gene_id_to_fetch) 


def get_gene_by_ens(ensembl_id, species_filter=None):
    """Get gene details by Ensembl ID. Checks cache first."""
    if not ensembl_id: return None
    clean_ensembl_id = ensembl_id.strip().upper() 

    if _ensure_dir_exists(NCBI_GENE_CACHE_FILE):
        try:
            with open(NCBI_GENE_CACHE_FILE, 'r', encoding='utf-8') as f_cache:
                for line in f_cache:
                    parts = line.strip().split('\t')
                    if len(parts) == 4 and parts[1].upper() == clean_ensembl_id: 
                        if species_filter and parts[3].lower() != species_filter.strip().lower():
                            continue
                        return get_gene_record_from_cache_line(parts)
        except FileNotFoundError:
            pass

    term = f"{clean_ensembl_id}[Accession]" 
    if species_filter:
        term += f" AND \"{species_filter.strip()}\"[Organism]"

    esearch_params = {'db': 'gene', 'term': term, 'retmode': 'xml'}
    xml_response_esearch = _query_eutils(ESEARCH_URL, esearch_params)
    if not xml_response_esearch: return None

    id_list_match = re.findall(r"<Id>(\d+)</Id>", xml_response_esearch)
    if not id_list_match:
        print(f"NCBI (get_gene_by_ens): No GeneID found for Ensembl '{clean_ensembl_id}' (Species: {species_filter}).")
        if _ensure_dir_exists(NCBI_GENE_CACHE_FILE):
            try:
                with open(NCBI_GENE_CACHE_FILE, 'a', encoding='utf-8') as f_cache:
                    f_cache.write(f"ENSEMBL_NOT_FOUND_SYMBOL\t{clean_ensembl_id}\tENSEMBL_NOT_FOUND_ID\t{species_filter or 'ANY'}\n")
            except IOError as e: print(f"Warning: Could not write ENSEMBL_NOT_FOUND to Gene Cache: {e}")
        return None

    gene_id_to_fetch = id_list_match[0]
    return _fetch_and_cache_gene_details(gene_id_to_fetch)