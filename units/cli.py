import csv
import sys

from argparse import ArgumentParser
from .convert import convert, graph_to_html
from .helpers import ENCODING, get_exponents, get_mappings, get_prefixes, get_si_mappings


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

    # Get the SI->UCUM mappings
    ucum_si = get_si_mappings(args.si, args.lang)

    # Get the scientific prefixes
    unit_prefixes = get_prefixes(args.prefixes, args.lang)

    # Get the exponents
    unit_exponents = get_exponents(args.exponents, args.lang)

    # Get the ontology mappings
    mappings = {}
    if not args.exclude_mappings:
        mappings = get_mappings(args.mappings)

    gout = convert(inputs, ucum_si, unit_prefixes, unit_exponents, mappings, lang=args.lang)
    if outfmt == "html":
        sys.stdout.write(graph_to_html(gout))
    else:
        sys.stdout.write(gout.serialize(format=outfmt))


if __name__ == "__main__":
    main()
