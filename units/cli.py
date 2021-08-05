import csv

from argparse import ArgumentParser
from .convert import convert

ENCODING = "utf-8-sig"


def main():
    parser = ArgumentParser()
    parser.add_argument("-i", "--input", help="Input list of UCUM codes", required=True)
    parser.add_argument("-s", "--si", help="SI unit labels and codes", required=True)
    parser.add_argument("-p", "--prefixes", help="SI prefix labels and codes", required=True)
    parser.add_argument("-e", "--exponents", help="Exponent labels", required=True)
    parser.add_argument("-o", "--output", help="Output TTL file", required=True)
    parser.add_argument("-l", "--lang", help="Language for annotations (default: en)", default="en")
    parser.add_argument("-O", "--om-mappings", help="")
    parser.add_argument("-Q", "--qudt-mappings", help="")
    parser.add_argument("-U", "--uo-mappings", help="")
    parser.add_argument("-B", "--oboe-mappings", help="")
    parser.add_argument("-N", "--nerc-mappings", help="")
    args = parser.parse_args()

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

    mappings = []
    for fp in [
        args.om_mappings,
        args.qudt_mappings,
        args.uo_mappings,
        args.oboe_mappings,
        args.nerc_mappings,
    ]:
        if not fp:
            continue
        sep = "\t"
        if fp.endswith(".csv"):
            sep = ","
        with open(fp, "r", encoding=ENCODING) as f:
            reader = csv.DictReader(f, delimiter=sep)
            for row in reader:
                mappings.append(row)

    ttl = convert(inputs, ucum_si, unit_prefixes, unit_exponents, mappings, lang=args.lang)
    with open(args.output, "w") as f:
        f.write(ttl)


if __name__ == "__main__":
    main()
