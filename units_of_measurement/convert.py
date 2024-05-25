import json
import logging
import re

from collections import defaultdict
from collections.abc import Iterable
from itertools import permutations, product
from lark.exceptions import LarkError
from rdflib import Graph, Literal, Namespace, OWL, RDF, RDFS, SKOS
from typing import List, Optional
from ucumvert import get_ucum_parser
from urllib.parse import quote as url_quote
from .grammar import si_grammar, UnitsTransformer, NewUnitsTransformer
from .helpers import get_exponents, get_mappings, get_prefixes, get_si_mappings


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
    "NERC_P06": "http://vocab.nerc.ac.uk/collection/P06/current/",
    "obo": "http://purl.obolibrary.org/obo/",
    "OBOE": "http://ecoinformatics.org/oboe/oboe.1.2/oboe-standards.owl#",
    "OM": "http://www.ontology-of-units-of-measure.org/resource/om-2/",
    "owl": "http://www.w3.org/2002/07/owl#",
    "QUDT": "http://qudt.org/vocab/unit/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "UO": "http://purl.obolibrary.org/obo/UO_",
}

NERC = Namespace(ONTOLOGY_PREFIXES["NERC_P06"])
OBOE = Namespace(ONTOLOGY_PREFIXES["OBOE"])
OM = Namespace(ONTOLOGY_PREFIXES["OM"])
QUDT = Namespace(ONTOLOGY_PREFIXES["QUDT"])
UO = Namespace(ONTOLOGY_PREFIXES["UO"])


ucum_parser = get_ucum_parser()


def convert(  # noqa: C901
    inputs: list,
    ucum_si: dict = None,
    unit_prefixes: dict = None,
    unit_exponents: dict = None,
    mappings: dict = None,
    base_iri: str = "https://w3id.org/uom/",
    lang: str = "en",
    fail_on_err: bool = False,
    use_default_mappings: bool = True
) -> Graph:
    """
    Generates an RDF graph seeded from an input list of UCUM codes

    :param inputs: list of UCUM codes
    :param ucum_si: UCUM symbol -> dict containing symbol, label, and definition
                   (e.g., "A": {"symbol": "A", "label_en": "ampere", "definition_en": "..."})
    :param unit_prefixes: prefix symbol -> label and prefix base 10 number
                    (e.g., "Y": {"label_en": "yotta", "number": 24})
    :param unit_exponents: dict of power to label (e.g., 2: "square")
    :param mappings: mapped ontology term IRI -> list of UCUM codes
    :param base_iri:
    :param lang: language for annotations (default: en)
    :param fail_on_err:
    :param use_default_mappings:
    :return: rdflib graph object
    """
    # Update prefixes with provided base IRI
    ONTOLOGY_PREFIXES["unit"] = base_iri
    gout = Graph()
    # Add ontology prefixes
    for ns, base in ONTOLOGY_PREFIXES.items():
        gout.bind(ns, base)

    # Get the default input files if they were not provided
    if not ucum_si:
        ucum_si = get_si_mappings(lang=lang)
    if not unit_prefixes:
        unit_prefixes = get_prefixes(lang=lang)
    if not unit_exponents:
        unit_exponents = get_exponents(lang=lang)
    if not mappings and use_default_mappings:
        # Mappings will not be included if use_default_mappings is false
        mappings = get_mappings()
    elif use_default_mappings:
        # Add default mappings to user-provided mappings
        mappings.update(get_mappings())

    # Create two-wap equivalent code mappings
    eq_codes = defaultdict(set)
    for ucum_symbol, details in ucum_si.items():
        eq_code = details["equivalent_code"]
        if not eq_code:
            continue
        if ucum_symbol not in eq_codes:
            eq_codes[ucum_symbol] = set()
        for ec in eq_code.split("|"):
            if ec not in eq_codes:
                eq_codes[ec] = set()
            eq_codes[ec].add(ucum_symbol)
            eq_codes[ucum_symbol].add(ec)

    # Process given inputs
    for inpt in inputs:
        ### OLD parser
        # Parse the input with Lark
        # TODO: remove this
        # try:
        #     tree = si_grammar.parse(inpt)
        #     result = UnitsTransformer().transform(tree)
        # except (LarkError, TypeError) as exc:
        #     if fail_on_err:
        #         raise ValueError(f"Could not process '{inpt}' with SI parser") from exc
        #     logging.error(f"Could not process '{inpt}' with SI parser - this input will be skipped")
        #     continue

        # # Attempt to flatten the result tree
        # try:
        #     res_flat = flatten(result)
        # except RecursionError as exc:
        #     if fail_on_err:
        #         raise RecursionError(f"Could not flatten result from '{inpt}'") from exc
        #     logging.error(f"Could not flatten result from '{inpt}' - this input will be skipped")
        #     continue

        # # Convert result into list of dicts
        # processed_units = []
        # for r in res_flat:
        #     processed_units.append(process_result(r, inpt))

        ### NEW Parser
        # TODO: Clean up
        new_tree = ucum_parser.parse(inpt)
        # print('NEW TREE', new_tree)
        new_result = NewUnitsTransformer().transform(new_tree)
        new_processed_units = [new_process_result(r) for r in new_result]
        # print('EQUAL?', new_processed_units == processed_units)
        processed_units = new_processed_units

        ### Continue with OLD code using NEW processed_units

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

            # Try to use the parsed output to create equivalent units
            u["equivalent_codes"] = [u["prefix"] + x for x in get_equivalent_units(ucum_si, u)]

            # Create label from units & prefixes
            label = get_label_part(u, ucum_si, unit_prefixes, unit_exponents, lang=lang)
            if label:
                u[f"label_{lang}"] = label
            else:
                raise ValueError(f"Could not create a label for '{inpt}'")

            # Create synonyms from units & prefixes (empty list if there are none)
            u[f"exact_synonym_{lang}"] = get_synonyms_part(
                u, ucum_si, unit_prefixes, unit_exponents, lang=lang
            )

            # Split numerator and denominator into two lists
            if str(u["exponent"])[0] == "-":
                denom_list.append(u)
            else:
                num_list.append(u)

        # Sort in canonical alphabetical order
        try:
            num_list = sorted(num_list, key=lambda k: (k["ucum_code"].casefold(), k))
            denom_list = sorted(denom_list, key=lambda k: (k["ucum_code"].casefold(), k))
        except ValueError as exc:
            if fail_on_err:
                raise ValueError(f"Could not sort result from '{inpt}'") from exc
            logging.error(f"Could not sort result from '{inpt}' - this input will be skipped")
            continue

        # Generate canonical term label
        label = get_canonical_label(num_list, denom_list, lang=lang)

        # Generate canonical synonyms
        synonyms = get_canonical_synonyms(num_list, denom_list, lang=lang)

        # Generate canonical English definition
        definition = get_canonical_definition(
            num_list, denom_list, ucum_si, unit_prefixes, unit_exponents, lang=lang
        )

        # Generate canonical SI code
        # TODO: fix superscript issue with fstrings
        si_code = get_canonical_si_code(num_list, denom_list)

        # Generate canonical UCUM code
        ucum_codes = [get_canonical_ucum_code(num_list, denom_list)]
        alt_code = get_alternative_ucum_code(ucum_codes[0])
        if alt_code != ucum_codes[0]:
            ucum_codes.append(alt_code)

        # Generate equivalent UCUM codes
        equivalent_codes = get_equivalent_ucum_codes(num_list, denom_list)

        # Add any codes from the two-way mappings based on the canonical code
        for uc in ucum_codes:
            if uc in eq_codes and eq_codes[uc] not in equivalent_codes:
                equivalent_codes.extend(eq_codes[uc])

        # Generate list of UCUM codes from results
        ucum_si_list = get_si_ucum_list(processed_units)

        # Map UCUM codes to external ontologies
        # TODO: change this to use mappings of UCUM strings by calling phase 2 on Simon's mappings
        mappings_complete = [
            iri
            for iri, ucum_codes in mappings.items()
            if set(ucum_si_list).intersection(set(ucum_codes))
        ]

        # Format TTL from parser results
        triples = get_triples(
            ucum_codes,
            equivalent_codes,
            label,
            synonyms,
            si_code,
            definition,
            mappings_complete,
            lang=lang,
        )
        for t in triples:
            gout.add(t)
    return gout


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


def get_alternative_ucum_code(ucum_code):
    """Use the canonical UCUM code to get an alternative UCUM code. This code is not URL-safe."""
    alt_code = []
    idx = 0
    for p in ucum_code.split("."):
        negative = re.match(r"([^-]+)-([0-9]+)", p)
        if negative:
            unit = negative.group(1)
            power = negative.group(2)
            if int(power) > 1:
                label_part = f"{unit}{power}"
            else:
                label_part = unit
            label_part = "/" + label_part
        else:
            label_part = p
            if idx > 0:
                label_part = "." + label_part
        alt_code.append(label_part)
        idx += 1
    return "".join(alt_code)


def get_canonical_label(num_list: List[dict], denom_list: List[dict], lang: str = "en") -> str:
    """Use the processed numerators and denominators from a unit input to create a label."""
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


def get_canonical_definition(  # noqa: C901
    num_list: List[dict],
    denom_list: List[dict],
    ucum_si: dict,
    unit_prefixes: dict,
    unit_exponents: dict,
    lang: str = "en",
) -> Optional[str]:
    """Used the processed numerators and denominators from a unit to create a definition."""
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


def get_canonical_si_code(num_list: List[dict], denom_list: List[dict]) -> Optional[str]:
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


def get_equivalent_ucum_codes(num_list: List[dict], denom_list: List[dict]) -> List[str]:
    """Use the processed numerators and denominators from a unit input to create a list of all
    possible equivalent UCUM codes."""
    possible_codes = []
    has_eq_code = False
    for n in num_list:
        eq_codes = n["equivalent_codes"]
        if eq_codes:
            has_eq_code = True
        else:
            eq_codes = [n["ucum_code"]]
        if str(n["exponent"]) == "1":
            possible_codes.append(eq_codes)
        else:
            possible_codes.append([x + str(n["exponent"]) for x in eq_codes])
    for n in denom_list:
        eq_codes = n["equivalent_codes"]
        if eq_codes:
            has_eq_code = True
        else:
            eq_codes = [n["ucum_code"]]
        possible_codes.append([x + str(n["exponent"]) for x in eq_codes])
    if not has_eq_code:
        return []
    return [".".join(x) for x in product(*possible_codes)]


def get_canonical_synonyms(
    num_list: List[dict], denom_list: List[dict], lang: str = "en"
) -> List[str]:
    """Use the processed numerators and denominators from a unit input to create a list of all
    possible synonyms."""
    if not denom_list:
        # No denominators
        return get_possible_synonyms(num_list, lang=lang)
    elif not num_list:
        # No numerators
        return get_possible_synonyms(denom_list, lang=lang, reciprocal=True)
    # Mix of numerators and denominators
    num_synonyms = get_possible_synonyms(num_list, lang=lang)
    denom_synonyms = get_possible_synonyms(denom_list, lang=lang)
    if not num_synonyms and not denom_synonyms:
        return []
    if not num_synonyms:
        # Synonyms exist for denominator, use label in place of numerator(s)
        num_synonyms = [" ".join([x[f"label_{lang}"] for x in num_list])]
    if not denom_synonyms:
        # Synonyms exist for numerator, use label in place of denominator(s)
        denom_synonyms = [" ".join([x[f"label_{lang}"] for x in denom_list])]
    return [" ".join(x) for x in product(num_synonyms, ["per"], denom_synonyms)]


def get_canonical_ucum_code(num_list: List[dict], denom_list: List[dict]) -> str:
    return_lst = []
    for n in num_list:
        return_lst.append(get_ucum_code_part(n, numerator=True))
    for n in denom_list:
        return_lst.append(get_ucum_code_part(n))
    return ".".join(return_lst)


def get_curie(iri):
    for ns, base in ONTOLOGY_PREFIXES.items():
        if iri.startswith(base):
            return iri.replace(base, ns + ":")
    return iri


def get_definition_parts(
    units_list: List[dict],
    umuc_si: dict,
    unit_prefixes: dict,
    unit_exponents: dict,
    lang: str = "en",
) -> Optional[List[str]]:
    """Get a definition for this part of the parsed term."""
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


def get_equivalent_units(ucum_si, unit):
    """Get a list of equivalent UCUM codes for a given unit."""
    unit_details = ucum_si.get(unit["unit"])
    if unit_details:
        eq_code = unit_details["equivalent_code"]
        if eq_code:
            return eq_code.split("|")
    return []


def get_exponent(result: dict, unit_exponents: dict, lang: str = "en") -> Optional[str]:
    """Get an exponent label based on the parsed result."""
    power = str(result["exponent"]).replace("-", "")
    power_details = unit_exponents.get(power)
    if not power_details:
        return None
    return power_details.get(f"label_{lang}")


def get_label_part(
    result: dict, ucum_si: dict, unit_prefixes: dict, unit_exponents: dict, lang: str = "en"
) -> Optional[str]:
    """Get the label for this part of the parsed term."""
    # Get prefix
    prefix_details = unit_prefixes.get(result["prefix"])
    if prefix_details:
        prefix = prefix_details[f"label_{lang}"]
    else:
        prefix = ""

    # Maybe get unit
    unit_details = ucum_si.get(result["unit"])
    if not unit_details:
        logging.warning("No 'unit' entry in results:\n" + json.dumps(result, indent=4))
        unit = None
    else:
        unit = unit_details[f"label_{lang}"]
        if unit == "are" and prefix in ["hecto", "deca"]:
            prefix = prefix[:-1]

    # Check for an exponent & return formatted string
    power = get_exponent(result, unit_exponents, lang=lang)
    if power is None and unit is None:
        return prefix
    elif power is None:
        return prefix + unit
    return power + " " + prefix + unit


def get_possible_codes(lst, denominator: bool = False):
    code_order = []
    has_eq_code = False
    for n in lst:
        eq_codes = n["equivalent_codes"]
        if not eq_codes:
            eq_codes = [n["ucum_code"]]
        else:
            has_eq_code = True
        if denominator or (str(n["exponent"]) == "1"):
            eq_codes = [x + str(n["exponent"]) for x in eq_codes]
        code_order.append(eq_codes)
    if not has_eq_code:
        return []
    return [".".join(x) for x in product(*code_order)]


def get_possible_synonyms(lst, lang: str = "en", reciprocal: bool = False):
    """Return a list of synonyms that contains all possible in-order permutations of the
    synonym parts."""
    synonym_order = []
    has_synonym = False
    for n in lst:
        synonyms = n[f"exact_synonym_{lang}"]
        if not synonyms:
            # Use the label for this part in place of synonym
            synonym_order.append([n[f"label_{lang}"]])
            continue
        has_synonym = True
        synonym_order.append(synonyms)
    if not has_synonym:
        return []
    combinations = product(*synonym_order)
    if reciprocal:
        return ["reciprocal " + " ".join(x) for x in combinations]
    else:
        return [" ".join(x) for x in combinations]


def get_si_ucum_list(dict_list: List[dict]) -> List[str]:
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


def get_symbol_code(result: dict, ucum_si: dict) -> Optional[str]:
    """Get a code str based on prefix and unit."""
    result_unit = result["unit"]
    unit_details = ucum_si.get(result_unit)
    if not unit_details:
        logging.warning(f"No SI code for '{result_unit}'")
        return None
    unit = unit_details["symbol"]
    pref = result.get("prefix", "")
    return pref + unit


def get_synonyms_part(
    result: dict, ucum_si: dict, unit_prefixes: dict, unit_exponents: dict, lang: str = "en"
) -> Optional[List[str]]:
    """Get a list of synonyms for this part of the parsed term."""
    # Get prefix
    prefix_details = unit_prefixes.get(result["prefix"])
    if prefix_details:
        prefix = prefix_details[f"label_{lang}"]
    else:
        prefix = ""

    # Maybe get unit
    unit_details = ucum_si.get(result["unit"])
    if not unit_details:
        logging.warning("No 'unit' entry in results:\n" + json.dumps(result, indent=4))
        return []
    synonyms = unit_details.get(f"exact_synonym_{lang}")
    if not synonyms:
        return []

    # Check for an exponent & add formatted string
    unit_synonyms = []
    power = get_exponent(result, unit_exponents, lang=lang)
    for unit in synonyms.split("|"):
        if unit == "are" and prefix in ["hecto", "deca"]:
            prefix = prefix[:-1]
        if power is None:
            unit_synonyms.append(prefix + unit)
            continue
        unit_synonyms.append(power + " " + prefix + unit)
    return unit_synonyms


def get_triples(  # noqa: C901
    ucum_codes: List[str],
    equivalent_codes: List[str],
    label: str,
    synonyms: List[str],
    si_code: str,
    definition: str,
    mappings: List[str],
    lang: str = "en",
) -> List[tuple]:
    # Create an identifier from the UCUM code
    unit_ns = Namespace(ONTOLOGY_PREFIXES["unit"])
    # The canonical UCUM code is the first entry in the list
    term = unit_ns[url_quote(ucum_codes[0])]
    # Assert that this is an owl instance & add unit annotation properties
    triples = [
        (term, RDF.type, OWL.NamedIndividual),
        (unit_ns.SI_code, RDF.type, OWL.AnnotationProperty),
        (unit_ns.SI_code, RDFS.label, Literal("SI code")),
        (unit_ns.UCUM_code, RDF.type, OWL.AnnotationProperty),
        (unit_ns.UCUM_code, RDFS.label, Literal("UCUM code")),
    ]

    # Add unit annotation properties

    # Add annotations
    if label:
        triples.append((term, RDFS.label, Literal(label, lang=lang)))
    if synonyms:
        for syn in synonyms:
            triples.append((term, SKOS.altLabel, Literal(syn, lang=lang)))
    if definition:
        triples.append((term, SKOS.definition, Literal(definition, lang=lang)))
    if si_code:
        triples.append((term, unit_ns.SI_code, Literal(si_code)))
    for uc in ucum_codes:
        triples.append((term, unit_ns.UCUM_code, Literal(uc)))
    for ec in equivalent_codes:
        triples.append((term, SKOS.exactMatch, unit_ns[url_quote(ec)]))

    # Add mappings (if present)
    for m in mappings:
        if re.search(QUDT_REGEX, m):
            match = re.search(QUDT_REGEX, m)
            qudt_id = match.group(2)
            mapped_term = QUDT[qudt_id]
        elif re.search(OM_REGEX, m):
            match = re.search(OM_REGEX, m)
            om_id = match.group(2)
            mapped_term = OM[om_id]
        elif re.search(UO_REGEX, m):
            match = re.search(UO_REGEX, m)
            uo_id = match.group(2)
            mapped_term = UO[uo_id]
        elif re.search(OBOE_REGEX, m):
            match = re.search(OBOE_REGEX, m)
            oboe_id = match.group(2)
            mapped_term = OBOE[oboe_id]
        elif re.search(NERC_REGEX, m):
            match = re.search(NERC_REGEX, m)
            nerc_id = match.group(2)
            mapped_term = NERC[nerc_id]
        else:
            logging.warning("Unknown mapping: " + m)
            continue
        triples.append((term, SKOS.exactMatch, mapped_term))
    return triples


def get_ucum_code_part(part, numerator: bool = False):
    """Use the parsed part to create the UCUM code.
    If the part is a numerator, only include exponent if exponent != 1."""
    if numerator and str(part["exponent"]) == "1":
        return part["ucum_code"]
    return part["ucum_code"] + str(part["exponent"])


def graph_to_html(gout: Graph, rdf_type=OWL.NamedIndividual) -> str:  # noqa: C901
    """Convert an rdflib Graph containing UCUM triples to HTML+RDFa."""
    # Create the RDFa prefix string
    prefixes = []
    for ns, base in ONTOLOGY_PREFIXES.items():
        prefixes.append(f"{ns}: {base}")
    prefixes = "\n".join(prefixes)
    html = [f'<div prefix="{prefixes}">']

    # Get all labels
    labels = {}
    for node, val in gout.subject_objects(RDFS.label):
        if labels:
            labels[str(node)] = str(val)
        else:
            labels[str(node)] = str(val)

    # Get the attributes of all individuals (the UCUM codes)
    node_attributes = []
    for node in gout.subjects(RDF.type, rdf_type):
        iri = str(node)
        predicate_values = defaultdict(set)
        predicate_objects = defaultdict(set)
        for predicate, obj in gout.predicate_objects(node):
            p_iri = str(predicate)
            if isinstance(obj, Literal):
                if p_iri not in predicate_values:
                    predicate_values[p_iri] = set()
                predicate_values[p_iri].add(str(obj))
            else:
                if p_iri not in predicate_objects:
                    predicate_objects[p_iri] = set()
                predicate_objects[p_iri].add(str(obj))
        node_curie = get_curie(iri)
        node_label = labels.get(iri, node_curie)
        node_attributes.append(
            {
                "iri": iri,
                "curie": node_curie,
                "label": node_label,
                "values": predicate_values,
                "objects": predicate_objects,
            }
        )

    # For each node, generate the HTML
    for attributes in sorted(node_attributes, key=lambda k: k["label"]):
        iri = attributes["iri"]
        node_curie = attributes["curie"]
        node_label = attributes["label"]
        predicate_objects = attributes["objects"]
        predicate_values = attributes["values"]
        html.append(f'<div resource="{node_curie}">')
        html.append(f"  <h3>{node_label}</h3>")
        html.append(f'  <p class="lead">{iri}</h5>')
        html.append("  <ul>")
        # Handle objects
        for predicate, objects in predicate_objects.items():
            predicate_curie = get_curie(predicate)
            predicate_label = labels.get(predicate, predicate_curie)
            html.append("    <li>")
            html.append(f'      <a href="{predicate}">{predicate_label}</a>')
            html.append("      <ul>")
            for o in objects:
                object_curie = get_curie(o)
                object_label = labels.get(o, object_curie)
                html.append("        <li>")
                html.append(
                    f'{10 * " "}<a rel="{predicate_curie}" resource="{object_curie}" href="{o}">'
                )
                html.append((12 * " ") + object_label)
                html.append(f'{10 * " "}</a>')
                html.append("        </li>")
            html.append("      </ul>")
        # Handle literals
        for predicate, values in predicate_values.items():
            predicate_curie = get_curie(predicate)
            predicate_label = labels.get(predicate, predicate_curie)
            html.append("    <li>")
            html.append(f'      <a href="{predicate}">{predicate_label}</a>')
            html.append("      <ul>")
            for val in values:
                html.append(f'        <li><span property="{predicate_curie}">{val}</span></li>')
            html.append("      </ul>")
            html.append("    </li>")
        html.append("  </ul>")
        html.append("</div>")
    html.append("</div>")
    return "\n".join(html)


# TODO: try to integrate into NewUnitsTransformer.
def new_process_result(result: dict) -> dict:
    if 'operator' in result and result['operator'] == '/':
        if 'exponent' in result:
            result['exponent'] = -1 * result['exponent']
        else:
            result['exponent'] = -1
    if 'operator' in result:
        del result['operator']
    if 'prefix' not in result:
        result['prefix'] = ''
    if 'exponent' not in result:
        result['exponent'] = 1
    return result


def process_result(result: dict, original: str) -> dict:
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
