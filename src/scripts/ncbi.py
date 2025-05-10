import sys
import re
from download import url_request

# Gene
ncbi_gene_data = '../data/ncbi_gene.dat'
ncbi_search_gene_url = 'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=gene&term=<name>[sym]'
ncbi_fetch_gene_url = 'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=gene&id=<id>'

# RefSeq
ncbi_refseq_data = '../data/pictar/refseq_geneid.dat'
ncbi_search_refseq_url = 'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=nuccore&term=<term>'
ncbi_fetch_refseq_url = 'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=nuccore&id=<id>'

def get_geneid_by_refseq(refseq):
    """
    Download a gene information using the RefSeq.

    Parameters
    ----------
    refseq : str
        RefSeq nucleotide identifier
    """

    # Start looking if we already saved this RefSeq on file
    with open(ncbi_refseq_data, 'r') as f:
        for line in f:
            if refseq in line:
                return line.split()[1]

    # Not on file. Use the API.
    gene_id = None
    try:
        # Get the NCBI id searching for this RefSeq
        ncbi_id = re.search(r'<Id>([^<]+)</Id>',
            url_request(ncbi_search_refseq_url.replace('<term>', refseq), None)
        ).group(1)

        # Get the GeneID from the matched sequence
        gene_id = re.search(r'GeneID[^0-9]+([0-9]+)',
            url_request(ncbi_fetch_refseq_url.replace('<id>', ncbi_id), None)
        ).group(1)
    except:
        print(sys.exc_info()[1])
        print("RefSeq not found: %s" % refseq)
        return None

    # Write down the new found GeneID
    with open(ncbi_refseq_data, 'a') as f:
        f.write(refseq + "\t" + gene_id  + "\n")

    return gene_id


def download_gene_data(id):
    """
    Download a gene data using GeneID.

    Parameters
    ----------
    id : int
        GeneID used by NCBI
    """

    return url_request(ncbi_fetch_gene_url.replace('<id>', id), None)

def write_gene_in_datafile(gene):
    """
    Write down on file the new found gene information
    so that we don't have to download them again.

    Parameters
    ----------
    gene : dict
        Dictionary containing gene information to save on file
    """

    with open(ncbi_gene_data, 'a') as f:
        f.write(gene['name'] + '\t' +
                gene['embl'] + '\t' +
                gene['id'] + '\t' +
                gene['species'] + '\n')

def get_gene_from_record(record):
    """
    Return a dictionary of gene data parsed from a record on file.

    Parameters
    ----------
    record : str
        Raw record line
    """

    data = record.split()
    return {
        'name'    : data[0],
        'embl'    : data[1],
        'id'      : data[2],
        'species' : ' '.join(data[3:])
    }

def get_gene_from_ncbi_data(data):
    """
    Parse NCBI API raw data to get gene information.

    Parameters
    ----------
    data : str
        Raw NCBI API data
    """

    gene = {
        'name'    : re.search(r'locus "([^"]+)', data).group(1).upper(),
        'id'      : re.search(r'geneid ([0-9]+)', data).group(1),
        'species' : re.search(r'taxname "([^"]+)', data).group(1),
        'embl'    : '_'
    }
    try:
        gene['embl'] = re.search(r'Ensembl"[^"]+"([^"]+)', data).group(1)
    except:
        print("Cannot find Ensembl for: %s" % gene['id'])
    return gene

def get_gene_by_id(geneid):
    """
    Return a gene looking for it using the GeneID.

    Parameters
    ----------
    geneid : int
        GeneID used by NCBI
    """

    gene = None

    # Search in the data file for the GeneID
    with open(ncbi_gene_data, 'r') as f:
        for line in f:
            if '\t' + geneid + '\t' in line:
                return get_gene_from_record(line)

    # Query NCBI using the GeneID
    try:
        gene = get_gene_from_ncbi_data(download_gene_data(geneid))
    except:
        print(sys.exc_info()[1])
        print("Cannot find GeneID on NCBI: %s" % geneid)
        return None

    # Write down the new found gene data
    if gene is not None:
        write_gene_in_datafile(gene)

    return gene

def get_gene_by_ens(ens):
    """
    Return a gene looking for it using the Ensembl code.

    Parameters
    ----------
    ens : str
        Ensembl code
    """

    gene = None

    # Search in the data file for the Ensembl
    with open(ncbi_gene_data, 'r') as f:
        for line in f:
            if '\t' + ens + '\t' in line:
                return get_gene_from_record(line)

    # Query NCBI using the Ensembl
    try:
        # Try to match using the Ensembl
        ncbi_id = re.search(r'<Id>([^<]+)',
            url_request(ncbi_search_gene_url.replace('<name>[sym]', ens), None)
        ).group(1)

        # Get data using the retrieved id
        gene = get_gene_from_ncbi_data(download_gene_data(ncbi_id))
        gene['embl'] = ens
    except:
        print(sys.exc_info()[1])
        print("Cannot find gene by Ensembl on NCBI: %s" % ens)

    # Write down the new found gene data
    if gene is not None:
        write_gene_in_datafile(gene)

    return gene

def get_gene_by_name(name):
    """
    Return a gene looking for it using its name (symbol).

    Parameters
    ----------
    name : str
        Gene name (symbol)
    """

    gene = None

    # Search by name in the data file
    with open(ncbi_gene_data, 'r') as f:
        for line in f:
            if line.startswith(name):
                return get_gene_from_record(line)

    # Query the online database
    try:
        # Try to match using the gene name
        ncbi_id = re.search(r'<Id>([^<]+)',
            url_request(ncbi_search_gene_url.replace('<name>', name), None)
        ).group(1)

        # Get data using the retrieved id
        gene = get_gene_from_ncbi_data(download_gene_data(ncbi_id))
    except:
        print(sys.exc_info()[1])
        print("Cannot find gene by name on NCBI: %s" % name)
        return None

    # Write down the new found gene data
    if gene is not None:
        write_gene_in_datafile(gene)

    return gene
