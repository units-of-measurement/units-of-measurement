# units

[Initial testing repository](https://github.com/kaiiam/UO_revamp) see `nc_name_script` directory. 

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
units -h
```

## Usage

```
units -i INPUT -s SI -p PREFIXES -e EXPONENTS -o OUTPUT
```

Required arguments:
* `-i`/`--input`: the input file containing a list of UCUM codes
* `-s`/`--si`: see [SI Mapping Table](#si-mapping-table)
* `-p`/`--prefixes`: see [Prefixes Table](#prefixes-table)
* `-e`/`--exponents`: see [Exponents Table](#exponents-table)
* `-o`/`--output`: the output file, either Turtle or JSON-LD

Optional arguments:
* `-f`/`--format`: output format (`ttl` or `json-ld`). The default output is TTL, but the output format is guessed based on the file extension of the OUTPUT file. This option can be used to override that.
* `-l`/`--lang`: the language used for input labels and definitions. The default is `en`. Note that output definitons are currently only in English.
* `-m`/`--mappings`: a table mapping UCUM codes to external ontology terms, see [Ontology Mapping Tables](#ontology-mapping-tables). You may provide multiple mapping tables with extra `-m` options (`-m table1.tsv -m table2.tsv`)

#### SI Mapping Table

This table can be found [here](https://github.com/ontodev/units/blob/main/tests/resources/si_input.csv).

This table maps standard SI symbols to UCUM symbols. This file requires the following fields:
* `UCUM_symbol`
* `SI_symbol`
* `label_en`: The label in English (you can replace 'en' with another lang tag if you're using a different language as specified in the command line, e.g., `label_fr`)
* `definition_en`: The definition in English (same as above, e.g., `definition_fr`)

For example (with truncated defintion):

| UCUM_symbol | SI_symbol | label_en       | definition_en              |
| ----------- | --------- | -------------- | -------------------------- |
| Cel         | °C        | degree Celsius | A special named SI unit... |
| Ohm         | Ω         | ohm            | A special named SI unit... |

#### Prefixes Table

This table can be found [here](https://github.com/ontodev/units/blob/main/tests/resources/prefixes.csv).

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

This table can be found [here](https://github.com/ontodev/units/blob/main/tests/resources/exponents.csv).

This table contains mappings between the exponent number and it's label. The following fields are required:
* `power`: the exponent number
* `label_en`: The label in English (you can replace 'en' with another lang tag if you're using a different language as specified in the command line, e.g., `label_fr`)

For example:

| power | label_en |
| ----- | -------- |
| 2     | square   |
| 3     | cubic    |

#### Ontology Mapping Tables

These tables map UCUM codes to ontology terms. Currently, we have the following mappings:
* [OM](https://github.com/ontodev/units/blob/main/tests/resources/om_mapping.csv)
* [QUDT](https://github.com/ontodev/units/blob/main/tests/resources/qudt_mapping.csv)
* [UO](https://github.com/ontodev/units/blob/main/tests/resources/uo_mapping.csv)
* [OBOE](https://github.com/ontodev/units/blob/main/tests/resources/oboe_mapping.csv)
* [NERC](https://github.com/ontodev/units/blob/main/tests/resources/nerc_mapping.csv)

These tables require the following columns:
* `IRI`: The ontology term IRI
* `UCUM`: The UCUM code
