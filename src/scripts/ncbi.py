import sys
import re
import os 
import asyncio
import aiohttp
from download import url_request 
from urllib.parse import quote_plus

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DATA_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, '..', 'data')) 

GENE_CACHE_DIR = BASE_DATA_DIR 
NCBI_GENE_CACHE_FILE = os.path.join(GENE_CACHE_DIR, 'ncbi_gene.dat')

REFSEQ_CACHE_SUBDIR = os.path.join(BASE_DATA_DIR, 'pictar') 
REFSEQ_GENEID_CACHE_FILE = os.path.join(REFSEQ_CACHE_SUBDIR, 'refseq_geneid.dat')

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
API_KEY = None 

# Rate limiting settings
MAX_CONCURRENT_REQUESTS = 3
REQUEST_DELAY = 0.34  # seconds between requests

async def _ensure_dir_exists(file_path):
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

async def _query_eutils(session, base_url, params_dict):
    """Helper function to query NCBI E-utils with basic error checking."""
    query_params = params_dict.copy()
    if API_KEY:
        query_params['api_key'] = API_KEY

    # URL-encode each parameter value before joining
    encoded_params = []
    for k, v in query_params.items():
        # Ensure 'v' is a string before encoding
        encoded_value = quote_plus(str(v))
        encoded_params.append(f"{k}={encoded_value}")

    param_string = "&".join(encoded_params)
    full_url = f"{base_url}?{param_string}"
    
    print(f"\nNCBI Debug: Querying URL: {full_url}")
    
    try:
        async with session.get(full_url) as response:
            if response.status == 200:
                response_text = await response.text()
                print(f"NCBI Debug: Query successful, response length: {len(response_text)}")
                return response_text
            else:
                print(f"NCBI Debug: Query failed with status {response.status} for URL: {full_url}")
                return None
    except Exception as e:
        print(f"NCBI Debug: Error during request: {e}")
        return None

async def get_geneid_by_refseq(session, refseq_accession):
    """
    Get NCBI GeneID for a given RefSeq transcript accession.
    Checks local cache first, then queries NCBI E-utils.
    Returns GeneID as a string, or None if not found/error.
    """
    if not refseq_accession or not isinstance(refseq_accession, str):
        print("NCBI (get_geneid_by_refseq): Invalid RefSeq accession input.")
        return None
    
    refseq_id_cleaned = refseq_accession.strip().split('.')[0] 

    if await _ensure_dir_exists(REFSEQ_GENEID_CACHE_FILE): 
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
    xml_response_esearch = await _query_eutils(session, ESEARCH_URL, esearch_params)
    if not xml_response_esearch:
        return None 

    uid_match = re.search(r"<Id>(\d+)</Id>", xml_response_esearch)
    if not uid_match:
        print(f"NCBI (get_geneid_by_refseq): No nuccore UID found for RefSeq '{refseq_id_cleaned}'.")
        if await _ensure_dir_exists(REFSEQ_GENEID_CACHE_FILE):
            try:
                with open(REFSEQ_GENEID_CACHE_FILE, 'a', encoding='utf-8') as f_cache:
                    f_cache.write(f"{refseq_id_cleaned}\tNOT_FOUND\n")
            except IOError as e: print(f"Warning: Could not write NOT_FOUND to RefSeq cache: {e}")
        return None
    nuccore_uid = uid_match.group(1)

    efetch_params = {'db': 'nuccore', 'id': nuccore_uid, 'rettype': 'gb', 'retmode': 'text'}
    gb_data = await _query_eutils(session, EFETCH_URL, efetch_params)
    if not gb_data:
        return None 

    gene_id_match = re.search(r'/db_xref="GeneID:(\d+)"', gb_data)
    if gene_id_match:
        gene_id = gene_id_match.group(1)
        if await _ensure_dir_exists(REFSEQ_GENEID_CACHE_FILE): 
            try:
                with open(REFSEQ_GENEID_CACHE_FILE, 'a', encoding='utf-8') as f_cache:
                    f_cache.write(f"{refseq_id_cleaned}\t{gene_id}\n")
            except IOError as e: print(f"Warning: Could not write to RefSeq cache: {e}")
        return gene_id
    else:
        print(f"NCBI (get_geneid_by_refseq): No GeneID cross-reference found for RefSeq '{refseq_id_cleaned}' (Nuccore UID: {nuccore_uid}).")
        if await _ensure_dir_exists(REFSEQ_GENEID_CACHE_FILE):
            try:
                with open(REFSEQ_GENEID_CACHE_FILE, 'a', encoding='utf-8') as f_cache:
                    f_cache.write(f"{refseq_id_cleaned}\tNOT_FOUND\n")
            except IOError as e: print(f"Warning: Could not write NOT_FOUND to RefSeq cache: {e}")
        return None

async def _fetch_and_cache_gene_details(session, gene_id_to_fetch):
    """Fetches full gene details from NCBI by GeneID and caches them."""
    if not gene_id_to_fetch: 
        print("NCBI Debug: No GeneID provided for fetching")
        return None

    print(f"\nNCBI Debug: Fetching details for GeneID: {gene_id_to_fetch}")
    efetch_params = {'db': 'gene', 'id': str(gene_id_to_fetch).strip(), 'retmode': 'xml'}
    xml_data = await _query_eutils(session, EFETCH_URL, efetch_params)
    
    if not xml_data:
        print(f"NCBI Debug: No XML data received for GeneID {gene_id_to_fetch}")
        return None
        
    gene_details = _parse_gene_efetch_xml(xml_data, str(gene_id_to_fetch))

    if await _ensure_dir_exists(NCBI_GENE_CACHE_FILE): 
        try:
            with open(NCBI_GENE_CACHE_FILE, 'a', encoding='utf-8') as f_cache:
                if gene_details:
                    cache_line = f"{gene_details.get('name','')}\t{gene_details.get('embl','')}\t{gene_details.get('id','')}\t{gene_details.get('species','')}\n"
                    f_cache.write(cache_line)
                    print(f"NCBI Debug: Cached gene details: {cache_line.strip()}")
                else:
                    print(f"NCBI Debug: Could not fetch/parse for GeneID {gene_id_to_fetch}. Caching as NOT_FOUND.")
                    f_cache.write(f"NOT_FOUND_SYMBOL\tNOT_FOUND_EMBL\t{gene_id_to_fetch}\tNOT_FOUND_SPECIES\n")
        except IOError as e: 
            print(f"NCBI Debug: Error writing to cache file: {e}")
    return gene_details

async def get_gene_by_id_async(session, gene_id_input):
    """Get gene details by NCBI GeneID. Checks cache first."""
    if not gene_id_input: 
        print("NCBI Debug: No GeneID provided")
        return None
        
    try:
        clean_gene_id_str = str(int(float(str(gene_id_input))))
        print(f"\nNCBI Debug: Looking up GeneID: {clean_gene_id_str}")
    except ValueError:
        print(f"NCBI Debug: Invalid GeneID format '{gene_id_input}'")
        return None

    if await _ensure_dir_exists(NCBI_GENE_CACHE_FILE):
        try:
            print(f"NCBI Debug: Checking cache file: {NCBI_GENE_CACHE_FILE}")
            with open(NCBI_GENE_CACHE_FILE, 'r', encoding='utf-8') as f_cache:
                for line in f_cache:
                    parts = line.strip().split('\t')
                    if len(parts) == 4 and parts[2] == clean_gene_id_str: 
                        print(f"NCBI Debug: Found gene in cache: {line.strip()}")
                        return get_gene_record_from_cache_line(parts)
            print(f"NCBI Debug: GeneID {clean_gene_id_str} not found in cache")
        except FileNotFoundError:
            print(f"NCBI Debug: Cache file not found: {NCBI_GENE_CACHE_FILE}")
            pass 

    print(f"NCBI Debug: Fetching gene details from NCBI for GeneID: {clean_gene_id_str}")
    return await _fetch_and_cache_gene_details(session, clean_gene_id_str)

async def get_gene_by_name(session, gene_symbol, species_filter=None):
    """Get gene details by gene symbol. Checks cache first."""
    if not gene_symbol: return None
    clean_gene_symbol = gene_symbol.strip().upper() 

    if await _ensure_dir_exists(NCBI_GENE_CACHE_FILE):
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
    xml_response_esearch = await _query_eutils(session, ESEARCH_URL, esearch_params)
    if not xml_response_esearch: return None

    id_list_match = re.findall(r"<Id>(\d+)</Id>", xml_response_esearch)
    if not id_list_match:
        print(f"NCBI (get_gene_by_name): No GeneID found for Symbol '{clean_gene_symbol}' (Species: {species_filter}).")
        if await _ensure_dir_exists(NCBI_GENE_CACHE_FILE):
            try:
                with open(NCBI_GENE_CACHE_FILE, 'a', encoding='utf-8') as f_cache:
                    f_cache.write(f"{clean_gene_symbol}\tSYMBOL_NOT_FOUND_EMBL\tSYMBOL_NOT_FOUND_ID\t{species_filter or 'ANY'}\n")
            except IOError as e: print(f"Warning: Could not write SYMBOL_NOT_FOUND to Gene Cache: {e}")
        return None
    
    gene_id_to_fetch = id_list_match[0] 
    return await _fetch_and_cache_gene_details(session, gene_id_to_fetch)

async def get_gene_by_ens(session, ensembl_id, species_filter=None):
    """Get gene details by Ensembl ID. Checks cache first."""
    if not ensembl_id: return None
    clean_ensembl_id = ensembl_id.strip().upper() 

    if await _ensure_dir_exists(NCBI_GENE_CACHE_FILE):
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
    xml_response_esearch = await _query_eutils(session, ESEARCH_URL, esearch_params)
    if not xml_response_esearch: return None

    id_list_match = re.findall(r"<Id>(\d+)</Id>", xml_response_esearch)
    if not id_list_match:
        print(f"NCBI (get_gene_by_ens): No GeneID found for Ensembl '{clean_ensembl_id}' (Species: {species_filter}).")
        if await _ensure_dir_exists(NCBI_GENE_CACHE_FILE):
            try:
                with open(NCBI_GENE_CACHE_FILE, 'a', encoding='utf-8') as f_cache:
                    f_cache.write(f"ENSEMBL_NOT_FOUND_SYMBOL\t{clean_ensembl_id}\tENSEMBL_NOT_FOUND_ID\t{species_filter or 'ANY'}\n")
            except IOError as e: print(f"Warning: Could not write ENSEMBL_NOT_FOUND to Gene Cache: {e}")
        return None

    gene_id_to_fetch = id_list_match[0]
    return await _fetch_and_cache_gene_details(session, gene_id_to_fetch)

async def fetch_genes_parallel(gene_ids):
    """
    Fetch multiple genes in parallel with rate limiting.
    Returns a dictionary mapping gene IDs to their details.
    """
    if not gene_ids:
        return {}
        
    results = {}
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    
    async def fetch_with_rate_limit(gene_id):
        async with semaphore:
            async with aiohttp.ClientSession() as session:
                result = await get_gene_by_id_async(session, gene_id)
                results[gene_id] = result
                await asyncio.sleep(REQUEST_DELAY)
    
    tasks = [fetch_with_rate_limit(gene_id) for gene_id in gene_ids]
    await asyncio.gather(*tasks)
    return results

def get_gene_by_id(gene_id_input):
    """Synchronous wrapper for get_gene_by_id_async."""
    async def _run():
        async with aiohttp.ClientSession() as session:
            return await get_gene_by_id_async(session, gene_id_input)
    return asyncio.run(_run())

def _parse_gene_efetch_xml(xml_data, requested_gene_id_for_error_log="Unknown"):
    """
    Parses XML output from NCBI EFetch (db=gene).
    Returns a dictionary {'name', 'id', 'embl', 'species'} or None.
    """
    if not xml_data: 
        print(f"NCBI Debug: No XML data provided for GeneID '{requested_gene_id_for_error_log}'")
        return None
        
    gene_info = {'name': None, 'id': None, 'embl': '', 'species': None} 
    print(f"\nNCBI Debug: Parsing XML for GeneID '{requested_gene_id_for_error_log}'")

    try:
        geneid_match = re.search(r"<Gene-track_geneid>(\d+)</Gene-track_geneid>", xml_data)
        if geneid_match: 
            gene_info['id'] = geneid_match.group(1)
            print(f"NCBI Debug: Found GeneID: {gene_info['id']}")

        symbol_match = re.search(r"<Gene-ref_locus>([^<]+)</Gene-ref_locus>", xml_data)
        if symbol_match: 
            gene_info['name'] = symbol_match.group(1).upper()
            print(f"NCBI Debug: Found gene symbol: {gene_info['name']}")

        species_match = re.search(r"<Org-ref_taxname>([^<]+)</Org-ref_taxname>", xml_data)
        if species_match: 
            gene_info['species'] = species_match.group(1)
            print(f"NCBI Debug: Found species: {gene_info['species']}")

        ensembl_dbtag_block_match = re.search(r"<Dbtag>\s*<Dbtag_db>ENSEMBL</Dbtag_db>\s*<Dbtag_tag>\s*<Object-id>\s*<Object-id_str>([^<]+)</Object-id_str>", xml_data, re.IGNORECASE)
        if ensembl_dbtag_block_match:
            gene_info['embl'] = ensembl_dbtag_block_match.group(1)
            print(f"NCBI Debug: Found Ensembl ID: {gene_info['embl']}")
        
        if gene_info['id'] and gene_info['name']: 
            print(f"NCBI Debug: Successfully parsed gene info for GeneID '{requested_gene_id_for_error_log}'")
            return gene_info
        else:
            print(f"NCBI Debug: Missing required fields for GeneID '{requested_gene_id_for_error_log}'")
            print(f"NCBI Debug: Current gene info: {gene_info}")
            return None
    except Exception as e:
        print(f"NCBI Debug: Error parsing XML for GeneID '{requested_gene_id_for_error_log}': {e}")
        return None

def get_gene_record_from_cache_line(line_parts):
    """Helper to parse a line from ncbi_gene.dat into a dict."""
    if len(line_parts) == 4:
        if line_parts[0] == "NOT_FOUND_SYMBOL" and line_parts[2] == "NOT_FOUND_EMBL": 
            return None 
        return {'name': line_parts[0], 'embl': line_parts[1], 'id': line_parts[2], 'species': line_parts[3]}
    return None

def get_gene_by_name_sync(gene_symbol, species_filter=None):
    """Synchronous wrapper for get_gene_by_name."""
    async def _run():
        async with aiohttp.ClientSession() as session:
            return await get_gene_by_name(session, gene_symbol, species_filter)
    return asyncio.run(_run())

def get_gene_by_ens_sync(ensembl_id, species_filter=None):
    """Synchronous wrapper for get_gene_by_ens."""
    async def _run():
        async with aiohttp.ClientSession() as session:
            return await get_gene_by_ens(session, ensembl_id, species_filter)
    return asyncio.run(_run())

# Update the original get_gene_by_name and get_gene_by_ens to use the synchronous version
get_gene_by_name = get_gene_by_name_sync
get_gene_by_ens = get_gene_by_ens_sync
    