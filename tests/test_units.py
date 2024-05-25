import logging
import os

from rdflib import Graph
from rdflib.compare import graph_diff, to_isomorphic
from units_of_measurement.convert import convert, get_alternative_ucum_code

from pathlib import Path

ROOT = os.path.abspath(os.path.dirname(__file__))
RESOURCES_DIR = Path(ROOT) / 'resources'


def dump_ttl(g):
    for line in g.serialize(format="ttl").splitlines():
        if line:
            print(line)


def convert_test(n):
    input_path = RESOURCES_DIR / f"test_{n}.txt"
    output_path = RESOURCES_DIR / f"test_{n}.ttl"
    with open(input_path, "r") as f:
        input_codes = [x.strip() for x in f.readlines()]
    g_actual = convert(input_codes)
    g_expected = Graph()
    g_expected.parse(output_path, format="ttl")

    iso_actual = to_isomorphic(g_actual)
    iso_expected = to_isomorphic(g_expected)
    if iso_actual != iso_expected:
        _, in_first, in_second = graph_diff(iso_actual, iso_expected)
        logging.error("The actual and expected graphs differ")
        if in_first:
            logging.error("\n----- Contents of actual graph not in expected graph -----")
            dump_ttl(in_first)
        if in_second:
            logging.error("\n----- Contents of expected graph not in actual graph -----")
            dump_ttl(in_second)
    assert iso_actual == iso_expected

def test_convert_unsupported():
    failed_as_expected = False
    try:
        convert(['mm[Hg]_'], fail_on_err=True)
    except ValueError as e:
        logging.info(f'Got expected exception: {e}')
        failed_as_expected = True
    assert failed_as_expected
    g = convert(['mm[Hg]_'], fail_on_err=False)
    assert len(list(g.triples((None, None, None)))) == 0

def test_units():
    for n in range(1, 3):
        convert_test(n)


def test_get_alternative_ucum_code():
    assert "m/s" == get_alternative_ucum_code("m.s-1")
    assert "m.s" == get_alternative_ucum_code("m.s")
    assert "/s" == get_alternative_ucum_code("s-1")
