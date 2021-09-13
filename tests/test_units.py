from rdflib import Graph
from rdflib.compare import graph_diff, to_isomorphic
from units_of_measurement.convert import convert, get_alternative_ucum_code


def dump_ttl(g):
    for line in g.serialize(format="ttl").splitlines():
        if line:
            print(line)


def convert_test(n):
    input_path = f"tests/resources/test_{n}.txt"
    output_path = f"tests/resources/test_{n}.ttl"
    with open(input_path, "r") as f:
        input_codes = [x.strip() for x in f.readlines()]
    g_actual = convert(input_codes)
    g_expected = Graph()
    g_expected.parse(output_path, format="ttl")

    iso_actual = to_isomorphic(g_actual)
    iso_expected = to_isomorphic(g_expected)
    if iso_actual != iso_expected:
        _, in_first, in_second = graph_diff(iso_actual, iso_expected)
        print("The actual and expected graphs differ")
        if in_first:
            print("\n----- Contents of actual graph not in expected graph -----")
            dump_ttl(in_first)
        if in_second:
            print("\n----- Contents of expected graph not in actual graph -----")
            dump_ttl(in_second)
    assert iso_actual == iso_expected


def test_units():
    for n in range(1, 3):
        convert_test(n)


def test_get_alternative_ucum_code():
    assert "m/s" == get_alternative_ucum_code("m.s-1")
    assert "m.s" == get_alternative_ucum_code("m.s")
    assert "/s" == get_alternative_ucum_code("s-1")
