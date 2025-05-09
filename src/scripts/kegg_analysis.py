import requests

# Mouse gene list
genes = ["STAT4", "SIK2", "RAB31", "GADL1", "PSN2", "QPCT"]
species_code = "mmu"  # Mus musculus in KEGG

def get_kegg_gene_id(symbol):
    """Find KEGG gene ID (Entrez) for a symbol."""
    url = f"https://rest.kegg.jp/find/genes/{symbol}"
    response = requests.get(url)
    for line in response.text.strip().split("\n"):
        if line.startswith(f"{species_code}:"):
            return line.split("\t")[0].split(":")[1]
    return None

def get_pathways_for_gene(entrez_id):
    """Return list of pathway IDs (e.g., mmu04630) for a given gene ID."""
    url = f"https://rest.kegg.jp/link/pathway/{species_code}:{entrez_id}"
    response = requests.get(url)
    results = []
    for line in response.text.strip().split("\n"):
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        pathway_id = parts[1].split(":")[1]
        results.append(pathway_id)
    return results

def get_pathway_name(pathway_id):
    """Fetch human-readable name of a pathway."""
    url = f"https://rest.kegg.jp/get/{pathway_id}"
    response = requests.get(url)
    for line in response.text.strip().split("\n"):
        if line.startswith("NAME"):
            return line.split("NAME")[1].strip()
    return "Unknown"

# Main logic
for gene in genes:
    entrez_id = get_kegg_gene_id(gene)
    if not entrez_id:
        print(f"❌ {gene}: Gene not found in KEGG")
        continue

    pathways = get_pathways_for_gene(entrez_id)
    if pathways:
        print(f"\n✅ {gene} (Entrez ID {entrez_id}) is involved in:")
        for pid in pathways:
            pname = get_pathway_name(pid)
            print(f"   - {pid}: {pname}")
    else:
        print(f"⚠️ {gene} (Entrez ID {entrez_id}) has no known KEGG pathways")
