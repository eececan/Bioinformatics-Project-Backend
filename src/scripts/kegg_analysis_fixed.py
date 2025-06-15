print("Starting kegg_analysis_fixed_resumable.py...")
import requests
import time 
import os   
from dbhelper import db_connect, create_db_info

species_code = "hsa"  
KEGG_DB_NAME = "KEGG"
KEGG_BASE_URL = "https://rest.kegg.jp"
PROGRESS_FILE = "data/kegg/kegg_analysis_progress.txt" 
API_DELAY_SECONDS = 0.5 

def load_last_processed_index():
    """Loads the index of the last successfully processed gene."""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r") as f:
                content = f.read().strip() 
                if content:
                    return int(content)
                return -1 
        except ValueError:
            print(f"Warning: Progress file '{PROGRESS_FILE}' contains invalid data. Starting from scratch.")
            return -1
        except Exception as e:
            print(f"Warning: Could not read progress file '{PROGRESS_FILE}': {e}. Starting from scratch.")
            return -1
    return -1 

def save_last_processed_index(index):
    """Saves the index of the last successfully processed gene."""
    try:
        with open(PROGRESS_FILE, "w") as f:
            f.write(str(index))
    except Exception as e:
        print(f"Error saving progress to '{PROGRESS_FILE}': {e}")

def get_kegg_gene_id(symbol):
    """Find KEGG gene ID (Entrez) for a symbol."""
    url = f"{KEGG_BASE_URL}/find/genes/{symbol}"
    print(f"  Querying KEGG Gene ID: {url}")
    try:
        response = requests.get(url, timeout=10) 
        response.raise_for_status() 
        print(f"  KEGG Gene ID URL Status: {response.status_code}")
        for line in response.text.strip().split("\n"):
            if line.startswith(f"{species_code}:"):
                return line.split("\t")[0].split(":")[1]
        print(f"  KEGG ID not found for symbol: {symbol}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"  Error fetching KEGG Gene ID for {symbol}: {e}")
        return None
    finally:
        time.sleep(API_DELAY_SECONDS)

def get_pathways_for_gene(entrez_id):
    """Return list of pathway IDs (e.g., mmu04630) for a given gene ID."""
    url = f"{KEGG_BASE_URL}/link/pathway/{species_code}:{entrez_id}"
    print(f"  Querying KEGG Pathways for {entrez_id}: {url}")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        print(f"  KEGG Pathway URL Status: {response.status_code}")
        results = []
        for line in response.text.strip().split("\n"):
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            if parts[1].startswith("path:"):
                pathway_id = parts[1].split(":")[1] 
                results.append(pathway_id)
        return results
    except requests.exceptions.RequestException as e:
        print(f"  Error fetching pathways for {entrez_id}: {e}")
        return []
    finally:
        time.sleep(API_DELAY_SECONDS)

def get_pathway_name(pathway_id):
    """Fetch human-readable name of a pathway."""
    full_pathway_id_for_kegg = f"path:{pathway_id}" 
    url = f"{KEGG_BASE_URL}/get/{pathway_id}" 
    print(f"  Querying KEGG Pathway Name for {pathway_id}: {url}")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        print(f"  KEGG Pathway Name URL Status: {response.status_code}")
        for line in response.text.strip().split("\n"):
            if line.startswith("NAME"):
                return line.split("NAME")[1].strip().split(" - ")[0] 
        print(f"  Pathway name not found for: {pathway_id}")
        return "Unknown Pathway"
    except requests.exceptions.RequestException as e:
        print(f"  Error fetching pathway name for {pathway_id}: {e}")
        return "Unknown Pathway (API Error)"
    finally:
        time.sleep(API_DELAY_SECONDS)

def fetch_genes_from_db():
    """Fetch gene symbols from the Neo4j database (nodes labeled 'Target')."""
    genes = []
    with db_connect() as session:
        result = session.run("MATCH (t:Target) WHERE t.name IS NOT NULL RETURN t.name AS symbol ORDER BY t.name") 
        for record in result:
            genes.append(record["symbol"])
    print(f"Fetched {len(genes)} gene(s) (Targets) from database.")
    return genes

def is_gene_kegg_processed_in_db(session, gene_symbol):
    """Checks if the gene is already connected to any KEGG pathway in the DB."""
    query = """
    MATCH (t:Target {name: $gene_symbol})-[:PART_OF_PATHWAY]->(p:Pathway {source: $kegg_db_name})
    RETURN count(p) > 0 AS is_processed
    """
    result = session.run(query, gene_symbol=gene_symbol, kegg_db_name=KEGG_DB_NAME)
    record = result.single()
    return record["is_processed"] if record else False

def add_pathway_to_db(pathway_id, pathway_name):
    """Add a pathway node to the Neo4j database."""
    with db_connect() as session:
        session.run("""
            MERGE (p:Pathway {id: $pathway_id, source: $source})
            ON CREATE SET p.name = $pathway_name, p.created_at = timestamp()
            ON MATCH SET p.name = $pathway_name, p.updated_at = timestamp()
            """, pathway_id=pathway_id, pathway_name=pathway_name, source=KEGG_DB_NAME)
        print(f"  Added/Merged pathway: {pathway_id} - {pathway_name}")

def connect_gene_to_pathway(gene_symbol, pathway_id):
    """Connect a 'Target' node (representing a gene) to a 'Pathway' node."""
    with db_connect() as session:
        session.run("""
            MATCH (t:Target {name: $gene_symbol})
            MATCH (p:Pathway {id: $pathway_id, source: $kegg_db_name})
            MERGE (t)-[r:PART_OF_PATHWAY]->(p)
            ON CREATE SET r.created_at = timestamp()
            """, gene_symbol=gene_symbol, pathway_id=pathway_id, kegg_db_name=KEGG_DB_NAME)
        print(f"  Connected gene {gene_symbol} to pathway {pathway_id}")

def main():
    """Main logic to fetch genes from DB, get KEGG pathways, and update DB."""
    print("Initializing KEGG database info...")
    create_db_info(KEGG_DB_NAME, KEGG_BASE_URL)

    print("Fetching genes from database...")
    all_genes_from_db = fetch_genes_from_db()
    if not all_genes_from_db:
        print("No genes found in the database. Exiting.")
        return

    print(f"Fetched genes (Targets) from database: {all_genes_from_db}")
    total_genes = len(all_genes_from_db)
    last_processed_idx = load_last_processed_index()
    start_index = last_processed_idx + 1

    print(f"Found {total_genes} genes. Last processed index: {last_processed_idx}. Starting from index: {start_index}")

    genes_processed_this_run = 0
    genes_skipped_this_run = 0

    with db_connect() as db_session_for_checks:
        for current_idx in range(total_genes):
            gene_symbol = all_genes_from_db[current_idx]

            if current_idx < start_index:
                genes_skipped_this_run +=1
                continue

            print(f"\n--- Processing Gene {current_idx + 1}/{total_genes}: {gene_symbol} (Index: {current_idx}) ---")

            if is_gene_kegg_processed_in_db(db_session_for_checks, gene_symbol):
                print(f"  INFO: {gene_symbol} already has KEGG pathways in DB. Skipping API calls and marking as processed.")
                save_last_processed_index(current_idx) 
                genes_skipped_this_run +=1
                continue

            entrez_id = get_kegg_gene_id(gene_symbol)
            if not entrez_id:
                print(f"  ❌ {gene_symbol}: Gene symbol not found in KEGG or API error.")
                save_last_processed_index(current_idx)
                genes_processed_this_run +=1
                continue

            print(f"  Found Entrez ID: {entrez_id} for {gene_symbol}")
            pathways = get_pathways_for_gene(entrez_id)

            if pathways:
                print(f"  ✅ {gene_symbol} (Entrez ID {entrez_id}) is involved in {len(pathways)} pathway(s):")
                for pid in pathways:
                    pname = get_pathway_name(pid)
                    print(f"    - {pid}: {pname}")
                    add_pathway_to_db(pid, pname)
                    connect_gene_to_pathway(gene_symbol, pid)
            else:
                print(f"  ⚠️ {gene_symbol} (Entrez ID {entrez_id}) has no known KEGG pathways or API error during pathway fetch.")

            save_last_processed_index(current_idx)
            genes_processed_this_run +=1
            print(f"  --- Finished processing {gene_symbol} ---")


    print("\n========================================")
    print("KEGG Analysis Complete.")
    print(f"Total genes from DB: {total_genes}")
    print(f"Genes processed/attempted in this run: {genes_processed_this_run}")
    print(f"Genes skipped (already processed or per progress file): {genes_skipped_this_run + (start_index if start_index > 0 else 0)}")
    print(f"Progress saved in: {PROGRESS_FILE}")
    print("========================================")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nScript interrupted by user. Progress up to the last fully processed gene should be saved.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
        print("Progress up to the last fully processed gene might be saved. Check progress file.")