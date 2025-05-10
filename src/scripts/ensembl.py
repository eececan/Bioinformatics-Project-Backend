import json
from download import url_request

# Ensembl REST API URL
ensembl_rest_url = 'http://rest.ensembl.org/xrefs/id/<id>?external_db=MGI&content-type=application/json'

def download_gene_data(id):
    """
    Query the API to download a gene information.

    Parameters
    ----------
    id : str
        Ensembl code
    """

    return url_request(ensembl_rest_url.replace('<id>', id), None)

def get_gene_by_id(id):
    """
    Return a dictionary containing gene information downloaded from ensembl.org.

    Parameters
    ----------
    id : str
        Ensembl code
    """

    try:
        data = json.loads(download_gene_data(id))[0]
        return {
            'name'    : data['display_id'],
            'embl'    : id,
            'species' : '',
            'id'      : ''
        }
    except:
        print("Cannot find gene by Ensembl on Ensembl.org: %s" % id)
        return None
