import sys
from download import url_request

# UniProt API URL
url_mapping = 'http://www.uniprot.org/mapping/'

# UniProt download base url
url_download = "http://www.uniprot.org/uniprot/<id>.txt"

def uniprot_request(params):
    """
    Perform a request to the API.

    Parameters
    ----------
    params : dict
        Dictionary containing request parameters
    """

    data = url_request(url_mapping, params)
    if data is not None and params['query'] in data:
        return data.splitlines()[1].split()[1]
    else:
        print("Cannot find gene on UniProt: %s" % params['query'])
        return None

def uniprot_download(id):
    """
    Download a single gene information using the API.

    Parameters
    ----------
    id : str
        UniProt ID
    """

    return url_request(url_download.replace('<id>', id), None)

def get_gene_by_ens(ens):
    """
    Return a gene information looking for them using the API.

    Parameters
    ----------
    ens : str
        Ensembl code
    """

    # Prepare the query to get the UniProt ID
    params = {
        'from'   : 'ENSEMBL_ID',
        'to'     : 'ACC',
        'format' : 'tab',
        'query'  : ens
    }

    # Get the UniProt ID from Ensembl
    uniprot_id = uniprot_request(params)
    if uniprot_id is None:
        return None

    # Download the UniProt record
    data = uniprot_download(uniprot_id)

    # Parse data
    gene = {
        'name'      : '',
        'id'        : '',
        'embl'      : ens,
        'species'   : ''
    }
    for line in data.splitlines():
        if gene['name'] == '' and line.startswith('ID'):
            gene['name'] = line.split()[1].split('_')[0]
        elif gene['id'] == '' and 'GeneID' in line:
                gene['id'] = line.split()[2][:-1]
        elif gene['species'] == '' and line.startswith('OS'):
            gene['species'] = line.split(None, 1)[1].split('(')[0][:-1]

    return gene
