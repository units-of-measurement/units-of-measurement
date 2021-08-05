import json
import logging
import re

from collections import Iterable
from itertools import permutations
from urllib.parse import quote as url_quote
from .grammar import si_grammar, UnitsTransformer

KG_DEFINITION_EN = (
    "An SI base unit which 1) is the SI unit of mass and 2) is defined by taking "
    "the fixed numerical value of the Planck constant, h, to be 6.626 070 15 × "
    "10⁻³⁴ when expressed in the unit joule second, which is equal to kilogram "
    "square metre per second, where the metre and the second are defined in terms "
    "of c and ∆νCs."
)

QUDT_REGEX = r"(http://qudt.org/vocab/unit/)(.*)"
OM_REGEX = r"(http://www.ontology-of-units-of-measure.org/resource/om-2/)(.*)"
UO_REGEX = r"(http://purl.obolibrary.org/obo/UO_)(.*)"
OBOE_REGEX = r"(http://ecoinformatics.org/oboe/oboe.1.2/oboe-standards.owl#)(.*)"
NERC_REGEX = r"(http://vocab.nerc.ac.uk/collection/P06/current/)(.*)(/)"

ONTOLOGY_PREFIXES = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "IAO": "http://purl.obolibrary.org/obo/IAO_",
    "unit": "https://w3id.org/units/",
    "UO": "http://purl.obolibrary.org/obo/UO_",
    "OM": "http://www.ontology-of-units-of-measure.org/resource/om-2/",
    "QUDT": "http://qudt.org/vocab/unit/",
    "OBOE": "http://ecoinformatics.org/oboe/oboe.1.2/oboe-standards.owl#",
    "NERC_P06": "http://vocab.nerc.ac.uk/collection/P06/current/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
}


def convert(
    inputs: list,
    ucum_si: dict,
    unit_prefixes: dict,
    unit_exponents: dict,
    mappings: list,
    lang="en",
):
    """

    :param inputs: list of UCUM codes
    :param ucum_si: UCUM symbol -> dict containing symbol, label, and definition
                   (e.g., "A": {"symbol": "A", "label_en": "ampere", "definition_en": "..."})
    :param unit_prefixes: prefix symbol -> label and prefix base 10 number
                    (e.g., "Y": {"label_en": "yotta", "number": 24})
    :param unit_exponents: dict of power to label (e.g., 2: "square")
    :param mappings: ontology mappings
    :param lang: language for annotations (default: en)
    :return: TTL string representing given UCUM codes
    """
    # Add prefixes header
    ttl_str = ""
    for ns, base in ONTOLOGY_PREFIXES.items():
        ttl_str += f"@prefix {ns}: <{base}> .\n"

    # Add definition annotation property
    ttl_str += "\nIAO:0000115 a owl:AnnotationProperty ;\n"
    ttl_str += '  rdfs:label "definition" .\n\n'

    # Process given inputs
    for inpt in inputs:
        # Parse the input with Lark
        try:
            tree = si_grammar.parse(inpt)
            result = UnitsTransformer().transform(tree)
        except:
            logging.error(f"Could not process '{inpt}' with SI parser - this input will be skipped")
            continue

        # Attempt to flatten the result tree
        try:
            res_flat = flatten(result)
        except:
            logging.error(f"Could not flatten result from '{inpt}' - this input will be skipped")
            continue

        # Convert result into list of dicts
        processed_units = []
        for r in res_flat:
            processed_units.append(process_result(r, inpt))

        # Determine type SI vs. conventional to optionally add SI codes
        types = [u["type"] for u in processed_units]

        num_list = []
        denom_list = []
        for u in processed_units:
            # Optionally add SI codes
            if "conventional" not in types:
                # Create the SI code from prefix & unit
                symbol_code = get_symbol_code(u, ucum_si)
                if symbol_code:
                    u["si_code"] = symbol_code

            # Create the UCUM codes from prefix & unit
            u["ucum_code"] = u["prefix"] + u["unit"]

            # Create label from units & prefixes
            label = get_label_parts(u, ucum_si, unit_prefixes, unit_exponents)
            if label:
                u[f"label_{lang}"] = label

            # Split numerator and denominator into two lists
            if str(u["exponent"])[0] == "-":
                denom_list.append(u)
            else:
                num_list.append(u)

        # Sort in canonical alphabetical order
        try:
            num_list = sorted(num_list, key=lambda k: (k["ucum_code"].casefold(), k))
            denom_list = sorted(denom_list, key=lambda k: (k["ucum_code"].casefold(), k))
        except:
            logging.error(f"Could not sort result from '{inpt}' - this input will be skipped")
            continue

        # Generate canonical term label
        label = get_canonical_label(num_list, denom_list, lang=lang)

        # Generate canonical English definition
        definition = get_canonical_definition(
            num_list, denom_list, ucum_si, unit_prefixes, unit_exponents, lang=lang
        )

        # Generate canonical SI code
        # TODO: fix superscript issue with fstrings
        si_code = get_canonical_si_code(num_list, denom_list)

        # Generate canonical UCUM code
        ucum_code = get_canonical_ucum_code(num_list, denom_list)

        # Generate list of UCUM codes from results
        ucum_si_list = get_si_ucum_list(processed_units)

        # Map UCUM codes to external ontologies
        # TODO: change this to use mappings of UCUM strings by calling phase 2 on Simon's mappings
        mappings_complete = map_ucum_codes(ucum_si_list, mappings)

        # Format TTL from parser results
        ttl_str += format_ttl(ucum_code, label, si_code, definition, mappings_complete, lang=lang)
        ttl_str += "\n"
    return ttl_str


def flatten(x):
    """
    https://stackoverflow.com/questions/42102473/parsing-values-from-a-list-of-dictionaries-with-nested-list-in-python
    """
    if isinstance(x, dict):
        return [x]
    elif isinstance(x, Iterable):
        return [a for i in x for a in flatten(i)]
    else:
        return [x]


def format_ttl(ucum_code, label, si_code, definition, mappings, lang="en"):
    qudt_list = []
    om_list = []
    uo_list = []
    oboe_list = []
    nerc_list = []

    for m in mappings:
        if re.search(QUDT_REGEX, m):
            match = re.search(QUDT_REGEX, m)
            qudt_id = match.group(2)
            qudt_id = "QUDT:" + qudt_id
            qudt_list.append(qudt_id)
        if re.search(OM_REGEX, m):
            match = re.search(OM_REGEX, m)
            om_id = match.group(2)
            om_id = "OM:" + om_id
            om_list.append(om_id)
        if re.search(UO_REGEX, m):
            match = re.search(UO_REGEX, m)
            uo_id = match.group(2)
            uo_id = "UO:" + uo_id
            uo_list.append(uo_id)
        if re.search(OBOE_REGEX, m):
            match = re.search(OBOE_REGEX, m)
            oboe_id = match.group(2)
            oboe_id = "OBOE:" + oboe_id
            oboe_list.append(oboe_id)
        if re.search(NERC_REGEX, m):
            match = re.search(NERC_REGEX, m)
            nerc_id = match.group(2)
            nerc_id = "NERC_P06:" + nerc_id
            nerc_list.append(nerc_id)

    # Create an identifier from the UCUM code
    return_str = f"unit:{url_quote(ucum_code)}\n"
    # Assert that this is an owl instance
    return_list = ["  a owl:NamedIndividual"]

    # Add annotations
    if label:
        return_list.append(f'  rdfs:label "{label}"@{lang}')
    if definition:
        return_list.append(f'  IAO:0000115 "{definition}"@{lang}')
    if si_code:
        return_list.append(f'  unit:SI_code "{si_code}"')
    if ucum_code:
        return_list.append(f'  unit:ucum_code "{ucum_code}"')
    [return_list.append(f"  skos:exactMatch {x}") for x in qudt_list if qudt_list]
    [return_list.append(f"  skos:exactMatch {x}") for x in om_list if om_list]
    [return_list.append(f"  skos:exactMatch {x}") for x in uo_list if uo_list]
    [return_list.append(f"  skos:exactMatch {x}") for x in oboe_list if oboe_list]
    [return_list.append(f"  skos:exactMatch {x}") for x in nerc_list if nerc_list]

    # Add ; and . for ttl formatting
    for i, has_more in lookahead(return_list):
        if has_more:
            return_str += i + " ;\n"
        else:
            return_str += i + " .\n"
    return return_str


def get_canonical_label(num_list, denom_list, lang="en"):
    if not denom_list:
        # No denominators
        return " ".join([n[f"label_{lang}"] for n in num_list])
    elif not num_list:
        # No numerators
        result = ["reciprocal"]
        result.extend([d[f"label_{lang}"] for d in denom_list])
        return " ".join(result)
    # Mix of numerators and denominators
    result = []
    result.extend([n[f"label_{lang}"] for n in num_list])
    result.append("per")
    result.extend([d[f"label_{lang}"] for d in denom_list])
    return " ".join(result)


def get_canonical_definition(
    num_list, denom_list, ucum_si, unit_prefixes, unit_exponents, lang="en"
):
    """"""
    if not denom_list and len(num_list) == 1 and num_list[0]["exponent"] == 1:
        # No denominators and an SI base with no exponent
        prefix = num_list[0].get("prefix", "")
        unit = num_list[0]["unit"]
        unit_details = ucum_si.get(unit, {})
        if prefix == "":
            # No prefix
            if unit_details:
                return unit_details[f"definition_{lang}"]
            return None
        elif prefix == "k" and unit == "g":
            # Special case for kg
            return KG_DEFINITION_EN
        # Regular with prefix
        if not unit_details:
            logging.error("Unknown unit: " + unit)
            return None
        si_label = unit_details.get(f"label_{lang}")
        prefix_details = unit_prefixes.get(prefix)
        if not prefix_details:
            prefix_num = ""
        else:
            prefix_num = prefix_details["number"]
        return f"A unit which is equal to 10{prefix_num} {si_label}."
    elif not denom_list:
        # No denominators
        definition_parts = get_definition_parts(
            num_list, ucum_si, unit_prefixes, unit_exponents, lang=lang
        )
        if definition_parts:
            return "A unit which is equal to " + " by ".join(definition_parts) + "."
        return None
    elif not num_list:
        # No numerators
        definition_parts = get_definition_parts(
            denom_list, ucum_si, unit_prefixes, unit_exponents, lang=lang
        )
        if definition_parts:
            return (
                "A unit which is equal to the reciprocal of " + " by ".join(definition_parts) + "."
            )
        return None
    # Mix of numerators and denominators
    num_parts = get_definition_parts(num_list, ucum_si, unit_prefixes, unit_exponents, lang=lang)
    denom_parts = get_definition_parts(
        denom_list, ucum_si, unit_prefixes, unit_exponents, lang=lang
    )
    if num_parts and denom_parts:
        return (
            "A unit which is equal to "
            + " by ".join(num_parts)
            + " per "
            + " by ".join(denom_parts)
            + "."
        )
    return None


def get_canonical_si_code(num_list, denom_list):
    # TODO: use a dict of exponents mapping to f string superscript nums to write out superscript
    #       OR use the prefix numbers
    return_lst = []
    for n in num_list:
        if "si_code" in n:
            if str(n["exponent"]) == "1":
                return_lst.append(n["si_code"])
            else:
                return_lst.append(n["si_code"] + str(n["exponent"]))
        else:
            return None
    for n in denom_list:
        if "si_code" in n:
            return_lst.append(n["si_code"] + str(n["exponent"]))
    return " ".join(return_lst)


def get_canonical_ucum_code(num_list, denom_list):
    return_lst = []
    for n in num_list:
        if str(n["exponent"]) == "1":
            return_lst.append(n["ucum_code"])
        else:
            return_lst.append(n["ucum_code"] + str(n["exponent"]))
    for n in denom_list:
        return_lst.append(n["ucum_code"] + str(n["exponent"]))
    return ".".join(return_lst)


def get_definition_parts(units_list, umuc_si, unit_prefixes, unit_exponents, lang="en"):
    """"""
    return_lst = []
    for u in units_list:
        unit_details = umuc_si.get(u["unit"])
        if not unit_details:
            logging.error("Unknown unit: " + u["unit"])
            return None

        unit = unit_details[f"label_{lang}"]
        power = get_exponent(u, unit_exponents, lang=lang)

        # Get the prefix
        prefix_details = unit_prefixes.get(u["prefix"])
        if prefix_details:
            # Check if this prefix has a number
            prefix_num = prefix_details.get("number")
            if prefix_num:
                prefix_val = f"10{prefix_num}"
            else:
                prefix_val = "1"
        else:
            prefix_val = "1"

        # Create definition part
        if power:
            return_lst.append(f"{prefix_val} {power} {unit}")
        else:
            return_lst.append(f"{prefix_val} {unit}")
    return return_lst


def get_exponent(unit, unit_exponents, lang="en"):
    """"""
    power = str(unit["exponent"]).replace("-", "")
    power_details = unit_exponents.get(power)
    if not power_details:
        return None
    return power_details.get(f"label_{lang}")


def get_label_parts(result, ucum_si, unit_prefixes, unit_exponents, lang="en"):
    unit_details = ucum_si.get(result["unit"])
    if not unit_details:
        logging.error("No 'unit' entry in results:\n" + json.dumps(result, indent=4))
        return None

    # Get unit and maybe revise prefix
    unit = unit_details[f"label_{lang}"]
    prefix_details = unit_prefixes.get(result["prefix"])
    if prefix_details:
        prefix = prefix_details[f"label_{lang}"]
    else:
        prefix = ""
    if unit == "are":
        if prefix == "hecto":
            prefix = "hect"
        elif prefix == "deca":
            prefix = "dec"

    # Check for an exponent & return formatted string
    power = get_exponent(result, unit_exponents, lang=lang)
    if power is None:
        return prefix + unit
    return power + " " + prefix + unit


def get_si_ucum_list(dict_list):
    """
    Create permutations of possible UCUM strings for input unit list
    E.g., 'm.s-1' -> ['m.s-1', 's-1.m']
    https://www.geeksforgeeks.org/generate-all-the-permutation-of-a-list-in-python/
    At the moment only handels the ucum "." cases not the "/" cases
    TODO: add the / UCUM cases
    """
    return_list = []
    code_exp_list = []
    for d in dict_list:
        if d["exponent"] == 1:
            exp = ""
        else:
            exp = str(d["exponent"])
        x = d["ucum_code"] + exp
        code_exp_list.append(x)
    code_exp_list = list(permutations(code_exp_list))

    for p in code_exp_list:
        ucum_str_list = []
        for i in p:
            ucum_str_list.append(i)
        outstr = ".".join(ucum_str_list)
        return_list.append(outstr)
    return return_list


def get_symbol_code(result, ucum_si):
    """
    Get a code str based on prefix and unit
    """
    result_unit = result["unit"]
    unit_details = ucum_si.get(result_unit)
    if not unit_details:
        logging.warning(f"No SI code for '{result_unit}'")
        return None
    unit = unit_details["symbol"]
    pref = result.get("prefix", "")
    return pref + unit


def lookahead(iterable):
    """Pass through all values from the given iterable, augmented by the
    information if there are more values to come after the current one
    (True), or if it is the last value (False).
    https://stackoverflow.com/questions/1630320/what-is-the-pythonic-way-to-detect-the-last-element-in-a-for-loop
    """
    # Get an iterator and pull the first value.
    it = iter(iterable)
    last = next(it)
    # Run the iterator to exhaustion (starting from the second value).
    for val in it:
        # Report the *previous* value (more to come).
        try:
            yield last, True
            last = val
        except StopIteration:
            return
    # Report the last value.
    try:
        yield last, False
    except StopIteration:
        return


def map_ucum_codes(ucum_list, ontology_mapping_list):
    """
    Temporary lookup to UCUM to ontology mappings. Later version will use the phase 2
    UCUM parser to parse the UCUM mappings (first column at least) and convert those to
    canonical UCUM string via our function to do so, then look those up based on input
    """
    return_list = []
    for u in ucum_list:
        for x in ontology_mapping_list:
            if u == x["UCUM1"] or u == x["UCUM2"] or u == x["UCUM3"] or u == x["UCUM4"]:
                return_list.append(x["IRI"])
    return return_list


def process_result(result, original):
    """
    Removes operators "." or "/" to get this back `'operator': '.',`
    Deals with start = "/" special case
    Writes out all terms with prefixes (empty string if none exist)
    Write out all terms with exponents (including 1 if none exist)
    """
    # Get prefix if existing:
    if "prefix" in result:
        prefix = result["prefix"]
    else:
        prefix = ""

    if result.get("operator") == "/":
        # if it doesn't have an exponent key create one at -1 else change exp to -
        if "exponent" not in result:
            x = {
                "prefix": prefix,
                "type": result["type"],
                "unit": result["unit"],
                "exponent": int("-1"),
            }
            return x
        exp = int("-" + str(result["exponent"]))
        x = {"prefix": prefix, "type": result["type"], "unit": result["unit"], "exponent": exp}
        return x
    # no operator or . case
    # Get or create exponent
    if "exponent" in result and original[0] == "/":
        exponent = int("-" + str(result["exponent"]))
    elif "exponent" in result:
        exponent = result["exponent"]
    elif original[0] == "/":
        exponent = -1
    else:
        exponent = 1
    x = {"prefix": prefix, "type": result["type"], "unit": result["unit"], "exponent": exponent}
    return x
