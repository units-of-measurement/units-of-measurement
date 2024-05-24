import csv
import sys

from argparse import ArgumentParser
from io import TextIOWrapper
from .convert import convert, graph_to_html
from .helpers import ENCODING, get_exponents, get_mappings, get_prefixes, get_si_mappings


def main():
    parser = ArgumentParser()
    parser.add_argument("input", nargs="?", default=sys.stdin, help="Input list of UCUM codes")
    parser.add_argument("-s", "--si", help="SI unit labels and codes")
    parser.add_argument("-p", "--prefixes", help="SI prefix labels and codes")
    parser.add_argument("-e", "--exponents", help="Exponent labels")
    parser.add_argument("-m", "--mappings", help="External ontology term to UCUM code mappings")
    parser.add_argument(
        "-f",
        "--format",
        help="Output format: ttl, json-ld, html, xml (default: ttl)",
        default="ttl",
    )
    parser.add_argument("-l", "--lang", help="Language for annotations (default: en)", default="en")
    parser.add_argument(
        "-x", "--exclude-mappings", action="store_true", help="Exclude ontology mappings"
    )
    parser.add_argument(
        "-b", "--base-iri", default="https://w3id.org/uom/", help="Base IRI for units"
    )
    parser.add_argument(
        "--strict", action='store_true', default=True, help="If strict then throw error on unparseable unit"
    )
    parser.add_argument(
        "--no-strict", action='store_false', help="If no-strict then do not throw error on unparseable unit"
    )
    args = parser.parse_args()

    outfmt = args.format
    if outfmt not in ["html", "json-ld", "ttl", "xml"]:
        raise Exception("Unknown output format: " + outfmt)

    # Read in provided files
    sep = "\t"
    if isinstance(args.input, TextIOWrapper):
        inputs = [x.strip() for x in args.input.readlines()]
    else:
        if args.input.endswith(".csv"):
            sep = ","
        with open(args.input, "r", encoding=ENCODING) as f:
            reader = csv.reader(f, delimiter=sep)
            inputs = [x[0].strip() for x in reader]

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

    gout = convert(
        inputs,
        ucum_si,
        unit_prefixes,
        unit_exponents,
        mappings,
        lang=args.lang,
        base_iri=args.base_iri,
        fail_on_err=args.strict,
    )
    if outfmt == "html":
        outstr = graph_to_html(gout)
    elif outfmt == "json-ld":
        jsonld_context = {}
        for ns, base in dict(gout.namespaces()).items():
            jsonld_context[ns] = str(base)
        jsonld_context = {"@context": jsonld_context}
        outstr = gout.serialize(format=outfmt, context=jsonld_context)
    else:
        outstr = gout.serialize(format=outfmt)

    # Handle backwards compatibility between rdflib 5.x.x and 6.x.x
    if isinstance(outstr, bytes):
        outstr = outstr.decode(ENCODING)
    sys.stdout.write(outstr)


if __name__ == "__main__":
    main()
