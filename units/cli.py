import csv

from argparse import ArgumentParser
from collections import defaultdict
from .convert import convert, graph_to_html

ENCODING = "utf-8-sig"


def main():
    parser = ArgumentParser()
    parser.add_argument("-i", "--input", help="Input list of UCUM codes", required=True)
    parser.add_argument("-s", "--si", help="SI unit labels and codes", required=True)
    parser.add_argument("-p", "--prefixes", help="SI prefix labels and codes", required=True)
    parser.add_argument("-e", "--exponents", help="Exponent labels", required=True)
    parser.add_argument("-o", "--output", help="Output file", required=True)
    parser.add_argument(
        "-f", "--format", help="Output format: ttl, json-ld, or html (default: ttl)"
    )
    parser.add_argument("-l", "--lang", help="Language for annotations (default: en)", default="en")
    parser.add_argument(
        "-m", "--mappings", help="External ontology term to UCUM code mappings", action="append"
    )
    args = parser.parse_args()

    # Get the format from args or guess it from the output file
    if args.format:
        outfmt = args.format
    else:
        if args.output.endswith(".json") or args.output.endswith(".jsonld"):
            outfmt = "json-ld"
        elif args.output.endswith(".html"):
            outfmt = "html"
        else:
            outfmt = "ttl"
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

    sep = "\t"
    if args.si.endswith(".csv"):
        sep = ","
    ucum_si = {}
    with open(args.si, "r", encoding=ENCODING) as f:
        reader = csv.DictReader(f, delimiter=sep)
        for row in reader:
            ucum_si[row["UCUM_symbol"]] = {
                "symbol": row["SI_symbol"],
                label_key: row[label_key],
                def_key: row[def_key],
            }

    sep = "\t"
    if args.prefixes.endswith(".csv"):
        sep = ","
    unit_prefixes = {}
    with open(args.prefixes, "r", encoding=ENCODING) as f:
        reader = csv.DictReader(f, delimiter=sep)
        for row in reader:
            unit_prefixes[row["symbol"]] = {label_key: row[label_key], "number": row["prefix_num"]}

    sep = "\t"
    if args.exponents.endswith(".csv"):
        sep = ","
    unit_exponents = {}
    with open(args.exponents, "r", encoding=ENCODING) as f:
        reader = csv.DictReader(f, delimiter=sep)
        for row in reader:
            unit_exponents[row["power"]] = {label_key: row[label_key]}

    mappings = defaultdict(list)
    if args.mappings:
        for fp in args.mappings:
            if not fp:
                continue
            sep = "\t"
            if fp.endswith(".csv"):
                sep = ","
            with open(fp, "r", encoding=ENCODING) as f:
                reader = csv.DictReader(f, delimiter=sep)
                for row in reader:
                    iri = row["IRI"]
                    if iri not in mappings:
                        mappings[iri] = []
                    mappings[iri].append(row["UCUM"])

    gout = convert(inputs, ucum_si, unit_prefixes, unit_exponents, mappings, lang=args.lang)
    if outfmt == "html":
        html = graph_to_html(gout)
        with open(args.output, "w") as f:
            f.write(html)
    else:
        gout.serialize(args.output, format=outfmt)


if __name__ == "__main__":
    main()
