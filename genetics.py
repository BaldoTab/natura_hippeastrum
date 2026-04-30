from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class ChiSquareResult:
    chi2: float
    df: int
    p_approx: float
    interpretacion: str


def chi_square_2cat(obs_dom: int, obs_rec: int, exp_ratio: str) -> ChiSquareResult:
    exp_dom, exp_rec = _ratio_to_parts(exp_ratio)
    total = obs_dom + obs_rec
    if total <= 0:
        return ChiSquareResult(chi2=0.0, df=1, p_approx=1.0, interpretacion="Sin datos")

    exp_dom_n = total * (exp_dom / (exp_dom + exp_rec))
    exp_rec_n = total * (exp_rec / (exp_dom + exp_rec))

    chi2 = _chi2_term(obs_dom, exp_dom_n) + _chi2_term(obs_rec, exp_rec_n)

    # Aproximación muy simple para df=1
    p = math.exp(-0.5 * chi2)

    interpretacion = "Ajuste bueno" if p >= 0.05 else "Desviación significativa"
    return ChiSquareResult(chi2=chi2, df=1, p_approx=p, interpretacion=interpretacion)


def ploidy_cross_result(a: str, b: str) -> str:
    # a,b in {"2n","3n","4n","5n","6n","8n","Desconocido"}
    if "Desconocido" in (a, b):
        return "Desconocido"
    try:
        na = int(a.replace("n", ""))
        nb = int(b.replace("n", ""))
    except Exception:
        return "Desconocido"
    return f"{int((na + nb) / 2)}n"


def ploidy_compat_color(a: str, b: str) -> str:
    # verde=fértil, amarillo=fertilidad reducida, rojo=estéril
    r = ploidy_cross_result(a, b)
    if r in ("3n", "5n"):
        return "red"
    if r == "Desconocido":
        return "gray"
    if a != b:
        return "yellow"
    return "green"


def _chi2_term(o: float, e: float) -> float:
    if e <= 0:
        return 0.0
    return ((o - e) ** 2) / e


def _ratio_to_parts(r: str) -> tuple[int, int]:
    try:
        a, b = r.split(":")
        return int(a), int(b)
    except Exception:
        return 3, 1
