import sys
import os
import re
from dbhelper import db_connect
from ncbi import get_gene_by_id, get_gene_by_name

data_file = '../data/uniprot_sprot.dat'
data_dir = '../data/uniprot_sprot/'

if not os.path.exists(data_dir):
    os.makedirs(data_dir)

    with open(data_file, 'r') as f:
        inblock = False
        filename = None

        for line in f:
            if inblock:
                file.write(line)
                if line.startswith('//'):
                    inblock = False
                    file.close()

            if line.startswith('ID'):
                inblock = True
                filename = data_dir + line.split()[1] + '.dat'
                file = open(filename, 'w')
                file.write(line)

                print("Processing: " + line, end="")
                print("to " + filename)

if len(sys.argv) < 3:
    print("Usage: " + sys.argv[0] + " <geneID> <species>")
    print("\tto print information about a specific gene")
    print("Usage: " + sys.argv[0] + " import <species>")
    print("\tto import all the gene information from a species")
    exit()

species = sys.argv[2].upper()
genes = []
session = None

if sys.argv[1] == 'import':
    genes = [file.split('_')[0] for file in os.listdir(data_dir)
             if file.endswith(species + '.dat')]

    session = db_connect()
else:
    genes = [sys.argv[1].upper()]

for gene in genes:
    with open(data_dir + gene + '_' + species + '.dat', 'r') as f:
        gene = {
            'name'      : '',
            'id'        : '',
            'embl'      : '',
            'species'   : ''
        }
        for line in f:
            if gene['name'] == '' and line.startswith('ID'):
                gene['name'] = line.split()[1].split('_')[0]
            elif line.startswith('DR'):
                if gene['id'] == '' and 'GeneID' in line:
                    gene['id'] = line.split()[2][:-1]
                elif gene['embl'] == '' and 'Ensembl' in line:
                    gene['embl'] = line.split()[4][:-1]
            elif gene['species'] == '' and line.startswith('OS'):
                gene['species'] = line.split(None, 1)[1][:-2]

        if gene['embl'] == '':
            if gene['id'] != '':
                gene = get_gene_by_id(gene['id'])
            elif gene['name'] != '':
                gene = get_gene_by_name(gene['name'])

        if sys.argv[1] == 'import'  \
            and gene['name'] != '' \
            and gene['id'] != '' \
            and gene['embl'] != '':
            session.run("MERGE (n:Target {"
                          "name: '%s',"
                          "species: 'Homo sapiens',"
                          "geneid: '%s',"
                          "ens_code: '%s',"
                          "ncbi_link: '%s'"
                        "})" %
                (gene['name'], gene['id'], gene['embl'], gene['id']))

if session:
    session.close()
