from lark import Lark, Transformer


class UnitsTransformer(Transformer):
    def SIGN(self, args):
        return args[0]

    def DIGIT(self, args):
        return args[0]

    def digits(self, args):
        return "".join(args)

    def factor(self, args):
        return args[0]

    def exponent(self, args):
        if len(args) == 1:
            return {
                "exponent": int(args[0]),
            }
        if len(args) == 2:
            return {
                "exponent": int("".join(args)),
            }

    def start(self, args):
        return args

    def term(self, args):
        if len(args) == 1:
            return args[0]
        elif len(args) == 3:
            return [args[0], {**args[1], **args[2]}]

    def component(self, args):
        return args[0]

    def simple_unit(self, args):
        if len(args) == 1:
            return args[0]
        elif len(args) == 2:
            return {**args[0], **args[1]}

    def annotatable(self, args):
        if len(args) == 1:
            return args[0]
        elif len(args) == 2:
            return {**args[0], **args[1]}

    # def annotation(self, args):
    #     return args[0]

    def OPERATOR(self, args):
        return {
            "operator": args[0],
        }

    def PREFIX(self, args):
        if args == "da":
            return {
                "prefix": args[0:2],
            }
        else:
            return {
                "prefix": args[0],
            }

    def METRIC(self, args):
        # print(args[:])
        return {
            "type": "metric",
            "unit": args[:],
        }

    def NON_PRE_METRIC(self, args):
        # print(args[:])
        return {
            "type": "metric",
            "unit": args[:],
        }

    def CONVENTIONAL(self, args):
        # print(args[:])
        return {
            "type": "conventional",
            "unit": args[:],
        }

    def CONVENTIONAL_BRACKETS(self, args):
        # print(args[:])
        return {
            "type": "conventional",
            "unit": args[:],
        }

    def CONVENTIONAL_MIXED_BRACKETS(self, args):
        # print(args[:])
        return {
            "type": "conventional",
            "unit": args[:],
        }

    def EXCEPTION(self, args):
        # print(args[:])
        return {
            "prefix": "d",
            "type": "metric",
            "unit": "ar",
        }

    # def ANNOTATION(self, args):
    #     return {
    #       "type": "non-unit",
    #       "unit": "".join(args)
    #     }


# SI grammar based on "Exhibit 1" https://ucum.org/ucum.html
si_grammar = Lark(
    """
SIGN: "-"
DIGIT: "0" | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9"
digits: DIGIT digits | DIGIT
factor: digits
exponent: SIGN digits | digits
simple_unit: METRIC
            | PREFIX? METRIC
            | NON_PRE_METRIC
            | CONVENTIONAL
            | CONVENTIONAL_BRACKETS
            | CONVENTIONAL_MIXED_BRACKETS
            | EXCEPTION
annotatable: simple_unit exponent
           | simple_unit
component: annotatable
         | factor
term: term OPERATOR component
    | component
start: "/" term | term
OPERATOR: /\.|\//
PREFIX: "Y" | "Z" | "E" | "P"| "T" | "G" | "M" | "k" | "h" | "da" | "d" | "c" | "m" | "u" | "n" | "p" | "f" | "a" | "z" | "y"
METRIC: "ar" | "A"| "Bq" | "B" | "cd" | "C" |  "eV" | "F" | "Gy" | "g" | "Hz" | "H" | "J"| "kat" | "K" | "lm" | "lx" | "L" | "mol" |  "m" | "Np" | "N" | "Ohm" | "Pa" | "rad" | "Sv" | "sr" | "s" | "S" | "T" | "t"| "u" | "V" | "Wb" | "W" | "''" 
NON_PRE_METRIC: "AU" | "Cel" | "deg" | "d" | "h" | "min" | "'" 
CONVENTIONAL: "%" | "a_g" | "a_j" | "a_t" | "Ao" | "atm" | "att" | "a" | "bar" | "Bd" | "Bi" | "bit_s" | "bit" | "By" | "b" | "cal_IT" | "cal_m" | "cal_th" | "cal" | "Ci" | "circ" | "dyn" | "eq" | "erg" | "g%" | "Gal" | "Gb" | "gf" | "gon" | "G" | "Ky" | "Lmb" |  "mho" | "mo_g" | "mo_j" | "mo_s" | "mo" | "Mx" | "Oe" | "osm" | "pc" | "ph" | "P" | "RAD" | "REM" | "R" | "sb" | "sph" | "St" | "st" | "tex" | "U" | "wk"
CONVENTIONAL_BRACKETS: "[acr_br]" | "[acr_us]" | "[Amb'a'1'U]" | "[anti'Xa'U]" | "[APL'U]" | "[arb'U]" | "[AU]" | "[BAU]" | "[bbl_us]" | "[bdsk'U]" | "[beth'U]" | "[bf_i]" | "[Btu_39]" | "[Btu_59]" | "[Btu_60]" | "[Btu_IT]" | "[Btu_m]" | "[Btu_th]" | "[Btu]" | "[bu_br]" | "[bu_us]" | "[c]" | "[Cal]" | "[car_Au]" | "[car_m]" | "[CCID_50]" | "[cft_i]" | "[CFU]" | "[ch_br]" | "[ch_us]" | "[Ch]" | "[cicero]" | "[cin_i]" | "[cml_i]" | "[cr_i]" | "[crd_us]" | "[cup_m]" | "[cup_us]" | "[cyd_i]" | "[D'ag'U]" | "[degF]" | "[degR]" | "[degRe]" | "[den]" | "[didot]" | "[diop]" | "[dpt_us]" | "[dqt_us]" | "[dr_ap]" | "[dr_av]" | "[drp]" | "[dye'U]" | "[e]" | "[EID_50]" | "[ELU]" | "[eps_0]" | "[EU]" | "[fdr_br]" | "[fdr_us]" | "[FEU]" | "[FFU]" | "[foz_br]" | "[foz_m]" | "[foz_us]" | "[ft_br]" | "[ft_i]" | "[ft_us]" | "[fth_br]" | "[fth_i]" | "[fth_us]" | "[fur_us]" | "[G]" | "[g]" | "[gal_br]" | "[gal_us]" | "[gal_wi]" | "[gil_br]" | "[gil_us]" | "[GPL'U]" | "[gr]" | "[h]" | "[hd_i]" | "[hnsf'U]" | "[hp_C]" | "[hp_M]" | "[hp_Q]" | "[hp_X]" | "[hp'_C]" | "[hp'_M]" | "[hp'_Q]" | "[hp'_X]" | "[HP]" | "[HPF]" | "[in_br]" | "[in_i'H2O]" | "[in_i'Hg]" | "[in_i]" | "[in_us]" | "[IR]" | "[IU]" | "[iU]" | "[k]" | "[ka'U]" | "[kn_br]" | "[kn_i]" | "[knk'U]" | "[kp_C]" | "[kp_M]" | "[kp_Q]" | "[kp_X]" | "[lb_ap]" | "[lb_av]" | "[lb_tr]" | "[lbf_av]" | "[lcwt_av]" | "[Lf]" | "[ligne]" | "[lk_br]" | "[lk_us]" | "[lne]" | "[LPF]" | "[lton_av]" | "[ly]" | "[m_e]" | "[m_p]" |  "[mclg'U]" | "[mesh_i]" | "[MET]" | "[mi_br]" | "[mi_i]" | "[mi_us]" | "[mil_i]" | "[mil_us]" | "[min_br]" | "[min_us]" | "[MPL'U]" | "[mu_0]" | "[nmi_br]" | "[nmi_i]" | "[oz_ap]" | "[oz_av]" | "[oz_m]" | "[oz_tr]" | "[p'diop]" | "[pc_br]" | "[pca_pr]" | "[pca]" | "[PFU]" | "[pH]" | "[pi]" | "[pied]" | "[pk_br]" | "[pk_us]" | "[pnt_pr]" | "[pnt]" | "[PNU]" | "[pouce]" | "[ppb]" | "[ppm]" | "[ppth]" | "[pptr]" | "[PRU]" | "[psi]" | "[pt_br]" | "[pt_us]" | "[pwt_tr]" | "[qt_br]" | "[qt_us]" | "[rch_us]" | "[rd_br]" | "[rd_us]" | "[rlk_us]" | "[S]" | "[sc_ap]" | "[sct]" | "[scwt_av]" | "[sft_i]" | "[sin_i]" | "[smgy'U]" | "[smi_us]" | "[smoot]" | "[srd_us]" | "[ston_av]" | "[stone_av]" | "[syd_i]" | "[tb'U]" | "[tbs_m]" | "[tbs_us]" | "[TCID_50]" | "[todd'U]" | "[tsp_m]" | "[tsp_us]" | "[twp]" | "[USP'U]" | "[wood'U]" | "[yd_br]" | "[yd_i]" | "[yd_us]"
CONVENTIONAL_MIXED_BRACKETS: "%[slope]" | "B[10.nV]" | "B[kW]" | "B[mV]" | "B[SPL]" | "B[uV]" | "B[V]" | "B[W]" | "cal_[15]" | "cal_[20]" | "m[H2O]" | "m[Hg]" 
EXCEPTION: "dar"
%ignore " "           // Disregard spaces in text
"""
)
