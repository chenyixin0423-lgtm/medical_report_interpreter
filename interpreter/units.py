"""Small, explicit unit allowlist; no mass/molar or assay-dependent conversions."""
import unicodedata
from math import isfinite


def unit_key(unit: str | None) -> str:
    text = unicodedata.normalize("NFKC", unit or "").replace("μ", "u").replace("µ", "u")
    return text.replace(" ", "").replace("×", "x").replace("^", "").lower()


# factor to canonical unit. Only SI scaling and count-volume identities.
UNITS = {
    "g/l": ("mass", "g/L", 1.0), "g/dl": ("mass", "g/L", 10.0),
    "mg/dl": ("mass", "g/L", 0.01), "mg/l": ("mass", "g/L", 0.001),
    "mmol/l": ("molar", "mmol/L", 1.0), "umol/l": ("molar", "mmol/L", 0.001),
    "10^9/l": ("count", "10^9/L", 1.0), "109/l": ("count", "10^9/L", 1.0),
    "x109/l": ("count", "10^9/L", 1.0), "k/ul": ("count", "10^9/L", 1.0),
    "103/ul": ("count", "10^9/L", 1.0), "x103/ul": ("count", "10^9/L", 1.0),
    "1012/l": ("count", "10^9/L", 1000.0), "x1012/l": ("count", "10^9/L", 1000.0),
    "m/ul": ("count", "10^9/L", 1000.0), "106/ul": ("count", "10^9/L", 1000.0),
    "%": ("fraction", "%", 1.0), "l/l": ("fraction", "%", 100.0),
    "u/l": ("activity", "U/L", 1.0), "iu/l": ("activity", "U/L", 1.0),
    "fl": ("volume", "fL", 1.0), "pg": ("cell_mass", "pg", 1.0),
    "ml/min/1.73m2": ("egfr", "mL/min/1.73m²", 1.0),
}


def specification(unit: str | None):
    return UNITS.get(unit_key(unit))


def convert(value: float, source: str, target: str) -> float:
    a, b = specification(source), specification(target)
    if not a or not b or a[0] != b[0]:
        raise ValueError("Units cannot be safely compared.")
    result = value * a[2] / b[2]
    if not isfinite(result):
        raise ValueError("Converted number is outside supported limits.")
    return result
