import csv
import os

from collections import defaultdict
from typing import Dict

ENCODING = "utf-8-sig"


def get_si_mappings(filepath: str = None, lang: str = "en") -> Dict[str, dict]:
    label_key = f"label_{lang}"
    def_key = f"definition_{lang}"
    syn_key = f"exact_synonym_{lang}"
    ucum_si = {}
    si_file = filepath or os.path.join(os.path.dirname(__file__), "resources/si_input.csv")
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
                syn_key: row[syn_key],
            }
    return ucum_si


def get_exponents(filepath: str = None, lang: str = "en") -> Dict[str, dict]:
    label_key = f"label_{lang}"
    unit_exponents = {}
    exponents_file = filepath or os.path.join(os.path.dirname(__file__), "resources/exponents.csv")
    sep = "\t"
    if exponents_file.endswith(".csv"):
        sep = ","
    with open(exponents_file, "r", encoding=ENCODING) as f:
        reader = csv.DictReader(f, delimiter=sep)
        for row in reader:
            unit_exponents[row["power"]] = {label_key: row[label_key]}
    return unit_exponents


def get_prefixes(filepath: str = None, lang: str = "en") -> Dict[str, dict]:
    label_key = f"label_{lang}"
    unit_prefixes = {}
    prefixes_file = filepath or os.path.join(os.path.dirname(__file__), "resources/prefixes.csv")
    sep = "\t"
    if prefixes_file.endswith(".csv"):
        sep = ","
    with open(prefixes_file, "r", encoding=ENCODING) as f:
        reader = csv.DictReader(f, delimiter=sep)
        for row in reader:
            unit_prefixes[row["symbol"]] = {label_key: row[label_key], "number": row["prefix_num"]}
    return unit_prefixes


def get_mappings(filepath: str = None) -> Dict[str, list]:
    mappings = defaultdict(list)
    mappings_file = filepath or os.path.join(os.path.dirname(__file__), "resources/mappings.csv")
    sep = "\t"
    if mappings_file.endswith(".csv"):
        sep = ","
    with open(mappings_file, "r", encoding=ENCODING) as f:
        reader = csv.DictReader(f, delimiter=sep)
        for row in reader:
            iri = row["IRI"]
            if iri not in mappings:
                mappings[iri] = []
            mappings[iri].append(row["UCUM"])
    return mappings
