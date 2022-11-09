# units

This repo serves two purposes:

- specification for encoding UCUM units as linked data URIs
- a reference implementation in Python

## Draft Specification

UCUM codes are translated into URIs using the following scheme:

`https://w3id.org/uom/{encode(normalize(code))}`

Here the expression is braces is evaluated using two functions:

- a normalize function (see below)
- [Percent encoding](https://en.wikipedia.org/wiki/Percent-encoding) rules

For example

- `m/s2` -> `m.s-2` -> <https://w3id.org/uom/m.s-2>
- `[diop]` -> <https://w3id.org/uom/%5Bdiop%5D>

Normalization: There may be multiple ways to write a unit as a UCUM code. The following normalization is first applied:

1. convert `/` (division) to negative exponents
2. sort parts by exponent, from positive to negative
3. when the exponent is the same, sort parts alphabetically

## Getting Started

The `ontodev-units` package will be downloadable from PyPI in the future, but at this time, you need to setup from source. Download this repository then install the requirements:
```
python3 -m pip install -r requirements.txt
```

Then, install `ontodev-units` from this directory:
```
python3 -m pip install .
```

Confirm installation by running:
```
uom -h
```

## Usage

```
uom INPUT > OUTPUT
```

... where the `INPUT` is the path to a file containing a list of UCUM codes to convert to linked data. This file should have one UCUM code per line.

You can also pipe input in with one code per new line. If you only include one code, it does not need to be surrounded by double quotes.

```
uom <<< "mol.s-1
           L2" > OUTPUT
```

Optional arguments:
* `-s`/`--si`: see [SI Mapping Table](#si-mapping-table). If not included, the default is [this file](units_of_measurement/resources/si_input.csv).
* `-p`/`--prefixes`: see [Prefixes Table](#prefixes-table). If not included, the default is [this file](units_of_measurement/resources/prefixes.csv).
* `-e`/`--exponents`: see [Exponents Table](#exponents-table). If not included, the default is [this file](units_of_measurement/resources/exponents.csv).
* `-m`/`--mappings`: see [Ontology Mapping Tables](#ontology-mapping-tables). If not included, the default is [this file](units_of_measurement/resources/mappings.csv).
* `-b`/`--base-iri`: the base IRI for the "unit" namespace. The default is `https://w3id.org/uom/`.
* `-x`/`--exclude-mappings`: If this flag is included, exclude ontology mappings from the output
* `-f`/`--format`: output format (`ttl`, `json-ld`, `xml`, or `html`). If not included, the default is `ttl`.
* `-l`/`--lang`: the language used for input labels and definitions. The default is `en` and if you specify a different language, you must include your own input files (above args). Note that output definitons are currently only in English.


### Input Tables

#### SI Mapping Table

This table can be found [here](units_of_measurement/resources/si_input.csv).

This table maps standard SI symbols to UCUM symbols. This file requires the following fields:
* `UCUM_symbol`
* `SI_symbol`
* `label_en`: The label in English (you can replace 'en' with another lang tag if you're using a different language as specified in the command line, e.g., `label_fr`)
* `exact_synonym_en`: An optional field for exact English synonyms; mutliple synonyms should be pipe-separated (same as above, e.g., `exact_synonym_fr`)
* `definition_en`: The definition in English (same as above, e.g., `definition_fr`)

For example (with truncated defintion):

| UCUM_symbol | SI_symbol | label_en       | exact_synonym_en |definition_en               |
| ----------- | --------- | -------------- | ---------------- |--------------------------- |
| Cel         | °C        | degree Celsius |                  | A special named SI unit... |
| m           | m         | metre          | meter            | An SI base unit which...   |

#### Prefixes Table

This table can be found [here](units_of_measurement/resources/prefixes.csv).

This table contains details for scientific prefixes and their powers. The following fields are required:
* `label_en`: The label in English (you can replace 'en' with another lang tag if you're using a different language as specified in the command line, e.g., `label_fr`)
* `symbol`: The standard symbol for the prefix
* `prefix_num`: The power as superscript

For example:

| label_en | symbol | prefix_num |
| -------- | ------ | ---------- |
| yotta    | Y      | ²⁴         |
| zetta    | Z      | ²¹         |

#### Exponents Table

This table can be found [here](units_of_measurement/resources/exponents.csv).

This table contains mappings between the exponent number and it's label. The following fields are required:
* `power`: the exponent number
* `label_en`: The label in English (you can replace 'en' with another lang tag if you're using a different language as specified in the command line, e.g., `label_fr`)

For example:

| power | label_en |
| ----- | -------- |
| 2     | square   |
| 3     | cubic    |

#### Ontology Mapping Tables

This table can be found [here](units_of_measurement/resources/mappings.csv).

This table maps UCUM codes to ontology terms, with each row representing one mapping.

These tables require the following columns:
* `IRI`: The ontology term IRI
* `UCUM`: The UCUM code

For example:

| IRI                                                  | UCUM |
| ---------------------------------------------------- | ---- |
| http://vocab.nerc.ac.uk/collection/P06/current/AMPB/ | A    |
| http://qudt.org/vocab/unit/SR                        | sr   |

## Testing

The `units` package uses `pytest`. To run tests:
```
pytest
```

Note that you should always locally re-install the package before running the tests (`python3 -m pip install .`).

### Resources

All test resources reside in `tests/resources/`. For each test, there is a `.txt` file containing a list of UCUM codes and a `.ttl` file containing the expected `units` output.

When making major changes to the `units` package, you can refresh all tests by running:
```
make refresh_tests
```

Note that this will regenerate all `.ttl` files in the `tests/resources/` directory, so make sure your changes are not introducing any bugs before doing this!

### Adding new tests

To add a new test, simply create a new `test_[NUM].txt` file in the test resources directory with a list of UCUM codes, and then use the `units` package to create a corresponding `test_[NUM].ttl` output:
```
units tests/resources/test_[NUM].txt > tests/resources/test_[NUM].ttl
```

`NUM` should be the next available integer, i.e., if `test_3` is the last test, the new test should be `test_4`.

Once you've added the resources, update `tests/test_units.py` to include this. On [line 36](tests/test_units.py#L36), increase the end of the range by one:
```
def test_units():
    for n in range(1, [NEW_END]):
        convert_test(n)
```

The `NEW_END` should be equal to `NUM + 1`, so if your new test is `test_4`, the `NEW_END` should be `5`.
