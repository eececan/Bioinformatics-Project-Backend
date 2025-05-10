import sys
import os
import re
from dbhelper import db_connect
from ncbi import get_gene_by_id, get_gene_by_name

data_file = '../data/uniprot_sprot.dat'
data_dir = '../data/uniprot_sprot/'

# Check if a folder containing splitted data blocks exists
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

    # Open the data file for reading
    with open(data_file, 'r') as f:
        inblock = False
        filename = None

        for line in f:

            # Internal block processing
            if inblock:

                # Write the current line to the gene file
                file.write(line)

                # Check for the end of the gene data block
                if line.startswith('//'):
                    inblock = False
                    file.close()

            # Check for the start of the gene data block
            if line.startswith('ID'):

                # Flag that we are in a data block
                inblock = True

                # Generate the filename for the gene
                filename = data_dir + line.split()[1] + '.dat'

                # Open the gene file for writing
                file = open(filename, 'w')

                # Write the first line containg the gene ID
                file.write(line)

                print("Processing: " + line, end="")
                print("to " + filename)

# Check for command line arguments
if len(sys.argv) < 3:
    print("Usage: " + sys.argv[0] + " <geneID> <species>")
    print("\tto print information about a specific gene")
    print("Usage: " + sys.argv[0] + " import <species>")
    print("\tto import all the gene information from a species")
    exit()

# Name of the species
species = sys.argv[2].upper()

# List of genes
genes = []

# DB session
session = None

if sys.argv[1] == 'import':
    # Generate the genes list
    genes = [file.split('_')[0] for file in os.listdir(data_dir)
             if file.endswith(species + '.dat')]

    # Open a connection to the db
    session = db_connect()
else:
    # Get a single gene name from the command line
    genes = [sys.argv[1].upper()]

for gene in genes:
    # Single gene data file processing
    with open(data_dir + gene + '_' + species + '.dat', 'r') as f:
        gene = {
            'name'      : '',
            'id'        : '',
            'embl'      : '',
            'species'   : ''
        }
        for line in f:

            # Name
            if gene['name'] == '' and line.startswith('ID'):
                gene['name'] = line.split()[1].split('_')[0]
            elif line.startswith('DR'):
                # ID
                if gene['id'] == '' and 'GeneID' in line:
                    gene['id'] = line.split()[2][:-1]
                # Ensembl ID
                elif gene['embl'] == '' and 'Ensembl' in line:
                    gene['embl'] = line.split()[4][:-1]
            # Species
            elif gene['species'] == '' and line.startswith('OS'):
                gene['species'] = line.split(None, 1)[1][:-2]

        # NCBI fallback
        # Look for the Ensembl ID and GeneID on NCBI
        if gene['embl'] == '':
            if gene['id'] != '':

                # Try searching using the GeneID
                gene = get_gene_by_id(gene['id'])

            elif gene['name'] != '':

                # Try searching using the name
                gene = get_gene_by_name(gene['name'])

        if sys.argv[1] == 'import'  \
            and gene['name'] != '' \
            and gene['id'] != '' \
            and gene['embl'] != '':

            session.run("MERGE (n:Target {"
                          "name: '%s',"
                          "species: 'Mus musculus',"
                          "geneid: '%s',"
                          "ens_code: '%s',"
                          "ncbi_link: '%s'"
                        "})" %
                (gene['name'], gene['id'], gene['embl'], gene['id']))

if session:
    # Close the session
    session.close()
