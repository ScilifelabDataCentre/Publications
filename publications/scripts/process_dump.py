"Read dump file and do something for each item."

import json
import tarfile

def process_publications(filepath, do_publication):
    "Go through the dump file and perform 'do_puplication' for each such."
    count_publications = 0
    count_items = 0
    infile = tarfile.open(filepath, mode="r")
    for item in infile:
        count_items += 1
        itemfile = infile.extractfile(item)
        itemdata = itemfile.read()
        itemfile.close()
        if item.name.endswith("_att"): continue
        doc = json.loads(itemdata)
        if doc.get("publications_doctype") != "publication": continue
        do_publication(doc)
        count_publications += 1
    infile.close()
    print(f"{count_items=}")
    print(f"{count_publications=}")


def check_xrefs(publication):
    try:
        xrefs = publication["xrefs"]
    except KeyError:
        pass
    else:
        if xrefs is None:
            print(publication["_id"])


class CountDoctype:
    "Check if there are any publications with the erroneous entry 'doctype'."

    def __init__(self):
        self.doctype_count = 0
        self.publications_doctype_count = 0

    def __call__(self, publication):
        if "doctype" in publication:
            self.doctype_count += 1
        if "publications_doctype" in publication:
            self.publications_doctype_count += 1


if __name__ == "__main__":
    counter = CountDoctype()
    process_publications("publications_facilities_dump_2021-06-21.tar.gz",
                         counter)
    print(f"{counter.doctype_count=}")
    print(f"{counter.publications_doctype_count=}")
