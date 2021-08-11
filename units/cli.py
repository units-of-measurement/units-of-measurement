import csv
import os
import sys

from argparse import ArgumentParser
from collections import defaultdict
from .convert import convert, graph_to_html

ENCODING = "utf-8-sig"


def main():
    parser = ArgumentParser()
    parser.add_argument("input", help="Input list of UCUM codes")
    parser.add_argument("-s", "--si", help="SI unit labels and codes")
    parser.add_argument("-p", "--prefixes", help="SI prefix labels and codes")
    parser.add_argument("-e", "--exponents", help="Exponent labels")
    parser.add_argument("-m", "--mappings", help="External ontology term to UCUM code mappings")
    parser.add_argument(
        "-f", "--format", help="Output format: ttl, json-ld, or html (default: ttl)", default="ttl"
    )
    parser.add_argument("-l", "--lang", help="Language for annotations (default: en)", default="en")
    parser.add_argument(
        "-x", "--exclude-mappings", action="store_true", help="Exclude ontology mappings"
    )
    args = parser.parse_args()

    outfmt = args.format
    if outfmt not in ["html", "json-ld", "ttl"]:
        raise Exception("Unknown output format: " + outfmt)

    # Read in provided files
    sep = "\t"
    if args.input.endswith(".csv"):
        sep = ","
    with open(args.input, "r", encoding=ENCODING) as f:
        reader = csv.reader(f, delimiter=sep)
        inputs = [x[0] for x in reader]

    label_key = f"label_{args.lang}"
    def_key = f"definition_{args.lang}"

    # Get the SI->UCUM mappings
    ucum_si = {}
    si_file = args.si or os.path.join(os.path.dirname(__file__), "resources/si_input.csv")
    sep = "\t"
    if si_file.endswith(".csv"):
        sep = ","
    with open(si_file, "r", encoding=ENCODING) as f:
        reader = csv.DictReader(f, delimiter=sep)
        for row in reader:
            ucum_si[row["UCUM_symbol"]] = {
                "symbol": row["SI_symbol"],
                label_key: row[label_key],
                def_key: row[def_key],
            }

    # Get the scientific prefixes
    unit_prefixes = {}
    prefixes_file = args.prefixes or os.path.join(
        os.path.dirname(__file__), "resources/prefixes.csv"
    )
    sep = "\t"
    if prefixes_file.endswith(".csv"):
        sep = ","
    with open(prefixes_file, "r", encoding=ENCODING) as f:
        reader = csv.DictReader(f, delimiter=sep)
        for row in reader:
            unit_prefixes[row["symbol"]] = {label_key: row[label_key], "number": row["prefix_num"]}

    # Get the exponents
    unit_exponents = {}
    exponents_file = (
        args.exponents
        or args.mappings
        or os.path.join(os.path.dirname(__file__), "resources/exponents.csv")
    )
    sep = "\t"
    if exponents_file.endswith(".csv"):
        sep = ","
    with open(exponents_file, "r", encoding=ENCODING) as f:
        reader = csv.DictReader(f, delimiter=sep)
        for row in reader:
            unit_exponents[row["power"]] = {label_key: row[label_key]}

    # Get the ontology mappings
    mappings = defaultdict(list)
    mappings_file = args.mappings or os.path.join(
        os.path.dirname(__file__), "resources/mappings.csv"
    )
    sep = "\t"
    if mappings_file.endswith(".csv"):
        sep = ","
    if not args.exclude_mappings:
        with open(mappings_file, "r", encoding=ENCODING) as f:
            reader = csv.DictReader(f, delimiter=sep)
            for row in reader:
                iri = row["IRI"]
                if iri not in mappings:
                    mappings[iri] = []
                mappings[iri].append(row["UCUM"])

    gout = convert(inputs, ucum_si, unit_prefixes, unit_exponents, mappings, lang=args.lang)
    if outfmt == "html":
        sys.stdout.write(graph_to_html(gout))
    else:
        sys.stdout.write(gout.serialize(format=outfmt).decode(ENCODING))


if __name__ == "__main__":
    main()
