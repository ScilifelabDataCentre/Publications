"Convert CSV (from XSLX) publications to a text format suitable for printing."

import csv

CSV_FILENAME = "ALM_publications.csv"
TXT_FILENAME = "ALM_publications.txt"

TITLE = 0
AUTHORS = 1
JOURNAL = 2
YEAR = 3
VOLUME = 6
ISSUE = 7
PAGES = 8
DOI_URL = 15

MAXLINE = 80

def write(outfile, line, extension, comma=True):
    parts = extension.split()
    for part in parts:
        length = len(line) + len(part) + 1
        if comma:
            length += 1
        if length > MAXLINE:
            outfile.write(line + "\n")
            line = indent + part
        else:
            if comma:
                line += ","
            line += " " + part
    return line

with open(CSV_FILENAME) as infile:
    reader = csv.reader(infile)
    header = next(reader)
    rows = list(reader)

print(header)
print(len(rows))

with open(TXT_FILENAME, "w") as outfile:
    for number, row in enumerate(rows, 1):
        line = f"{number}."
        indent = " " * (len(line) + 1)
        line = write(outfile, line, row[AUTHORS], comma=False)
        line = write(outfile, line, f'"{row[TITLE]}"', comma=False)
        line = write(outfile, line, row[JOURNAL])
        line = write(outfile, line, row[YEAR])
        if row[VOLUME]:
            line = write(outfile, line, row[VOLUME])
        if row[ISSUE]:
            line = write(outfile, line, row[ISSUE])
        if row[PAGES]:
            line = write(outfile, line, row[PAGES])
        if row[DOI_URL]:
            line = write(outfile, line, row[DOI_URL])
        if line:
            outfile.write(line)
        outfile.write("\n\n")
