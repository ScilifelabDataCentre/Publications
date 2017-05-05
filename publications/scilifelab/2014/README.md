Load data for publication year 2017
===================================

The database must have been initialized and the admin account created.

The v3 file was copied from v2 and edited manually to include more PMIDs
found by manual searches.

The DOIs in the v3 file were imported manually.

Publications requiring explicit addition:

Book: 
Bioinformatics Bioinformatics Short-term Support and Infrastructure (BILS) 
Anna Edberg, Eva Freyhult, Salomon Sand, Sisse
Fagt, Vibeke Kildegaard Knudsen, Lene Frost Andersen, Anna Karin
Lindroos, Daniel Soeria-Atmadja, Mats G. Gustafsson, Hammerling, Ulf
Discovery and characterisation of dietary patterns in two Nordic
countries: Using non-supervised and supervised multivariate
statistical techniques to analyse dietary survey data
 TemaNord 548 2013 no N/A

DOI-less: http://imsear.hellis.org/handle/123456789/164367

U.S. Patent No. 20,130,004,512.
U.S. Patent No. 20,130,034,560.
US Patent Application 14/196,228
US Patent No 8,703,432 22 Apr 2014

Book:
Clinical Proteomics Mass spectrometry
Helena Bäckvall & Janne Lehtiö
The Low Molecular Weight Proteome
Methods and Protocols Series: Methods in Molecular Biology 1023
223 pages 2013 no N/A


To do
-----

- Input the few remaining by hand, when possible.


Main loading scripts
--------------------

### add_pmid.py

Add PMID to each row of the CSV file using the given DOI and CrossRef.

Copied result to 'publikationer faciliteter 2010-2014 pmid v2.csv'
and edited away some garbage, such as empty lines and title 'N/A'.

### fetch_pmids.py

Fetch the XML files from PubMed using the PMIDs in the CSV file.


### create_labels.py

Create the labels in the database from the CSV file.


### import_publications.py

Import publications having PMIDs in the CSV file. Use the files downloaded
by the fetch_pmids.py script, if done. This script also handles the few
DOI-only publications in the input CSV file.

