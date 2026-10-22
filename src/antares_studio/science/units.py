"""Unités, constantes sourcées et conversions avec contrôle de dimension (SCI-01, SCI-02, SCI-06).

Sources (valeurs exactes ou nominales) :
- IAU 2012 résolution B2 : unité astronomique = 149 597 870 700 m.
- SI (CODATA) : c = 299 792 458 m/s (exact) ; G = 6.674 30 × 10⁻¹¹ m³ kg⁻¹ s⁻² (CODATA 2018).
- IAU 2015 résolution B3 : GM☉ nominal = 1.327 124 4 × 10²⁰ m³ s⁻² ; GM⊕ nominal = 3.986 004 × 10¹⁴ m³ s⁻².
- IAU : année julienne = 365.25 jours ; année-lumière = c × année julienne = 9.460 730 472 580 8 × 10¹⁵ m.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

AU_M = 149_597_870_700.0
C_M_S = 299_792_458.0
G_SI = 6.67430e-11
GM_SUN = 1.3271244e20
GM_EARTH = 3.986004e14
JULIAN_YEAR_S = 365.25 * 86400.0
LIGHT_YEAR_M = C_M_S * JULIAN_YEAR_S
PARSEC_M = AU_M * 648000.0 / math.pi  # définition IAU 2015 (B2) : 1 pc = 648000/π ua

SOURCES: dict[str, str] = {
    "au": "IAU 2012 B2 — https://www.iau.org/static/resolutions/IAU2012_English.pdf",
    "c": "SI / CODATA — https://physics.nist.gov/cgi-bin/cuu/Value?c",
    "G": "CODATA 2018 — https://physics.nist.gov/cgi-bin/cuu/Value?bg",
    "GM": "IAU 2015 B3 — https://www.iau.org/static/resolutions/IAU2015_English.pdf",
    "ly": "IAU : année julienne × c",
    "pc": "IAU 2015 B2 (1 pc = 648000/π ua) — https://www.iau.org/static/resolutions/IAU2015_English.pdf",
    "yr": "IAU : année julienne = 365,25 jours de 86 400 s",
}


class UnitError(ValueError):
    """Unité inconnue, dimensions incompatibles ou valeur non finie."""


@dataclass(frozen=True)
class Unit:
    symbol: str
    dimension: str  # length | time | mass | speed | angle
    factor: float  # valeur en unité SI de base de la dimension


UNITS: dict[str, Unit] = {
    u.symbol: u
    for u in (
        Unit("m", "length", 1.0),
        Unit("km", "length", 1e3),
        Unit("au", "length", AU_M),
        Unit("ly", "length", LIGHT_YEAR_M),
        Unit("pc", "length", PARSEC_M),
        Unit("s", "time", 1.0),
        Unit("min", "time", 60.0),
        Unit("h", "time", 3600.0),
        Unit("d", "time", 86400.0),
        Unit("yr", "time", JULIAN_YEAR_S),
        Unit("kg", "mass", 1.0),
        Unit("m/s", "speed", 1.0),
        Unit("km/s", "speed", 1e3),
        Unit("km/h", "speed", 1e3 / 3600.0),
        Unit("rad", "angle", 1.0),
        Unit("deg", "angle", math.pi / 180.0),
    )
}
ALIASES: dict[str, str] = {"ua": "au", "al": "ly", "°": "deg", "a": "yr", "an": "yr", "j": "d"}


def unit(symbol: str) -> Unit:
    key = ALIASES.get(symbol.strip(), symbol.strip())
    try:
        return UNITS[key]
    except KeyError:
        raise UnitError(f"unité inconnue : {symbol!r}") from None


def check_finite(value: float, what: str = "valeur") -> float:
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise UnitError(f"{what} non finie ou non numérique : {value!r}")
    return float(value)


def convert(value: float, from_unit: str, to_unit: str) -> float:
    """Convertit ``value`` ; ``UnitError`` si les dimensions diffèrent (jamais de résultat absurde)."""
    v = check_finite(value)
    src, dst = unit(from_unit), unit(to_unit)
    if src.dimension != dst.dimension:
        raise UnitError(
            f"dimensions incompatibles : {from_unit} ({src.dimension}) → {to_unit} ({dst.dimension})"
        )
    result = v * src.factor / dst.factor
    if not math.isfinite(result):
        raise UnitError(f"débordement numérique : {value} {from_unit} → {to_unit}")
    return result


@dataclass(frozen=True)
class Quantity:
    """Grandeur physique avec unité ; les opérations vérifient la dimension."""

    value: float
    unit: str

    def to(self, to_unit: str) -> Quantity:
        return Quantity(convert(self.value, self.unit, to_unit), to_unit)

    @property
    def dimension(self) -> str:
        return unit(self.unit).dimension

    def __add__(self, other: Quantity) -> Quantity:
        return Quantity(self.value + other.to(self.unit).value, self.unit)

    def __sub__(self, other: Quantity) -> Quantity:
        return Quantity(self.value - other.to(self.unit).value, self.unit)

    def format(self, digits: int = 4) -> str:
        return f"{self.value:.{digits}g} {self.unit}"


@dataclass(frozen=True)
class Constant:
    key: str
    name: str  # libellé FR
    symbol: str
    value: float
    unit: str  # unité SI affichée
    source: str  # clé de SOURCES


CONSTANTS: tuple[Constant, ...] = (
    Constant("c", "Vitesse de la lumière dans le vide", "c", C_M_S, "m/s", "c"),
    Constant("G", "Constante gravitationnelle", "G", G_SI, "m³ kg⁻¹ s⁻²", "G"),
    Constant("au", "Unité astronomique", "ua", AU_M, "m", "au"),
    Constant("ly", "Année-lumière", "al", LIGHT_YEAR_M, "m", "ly"),
    Constant("pc", "Parsec", "pc", PARSEC_M, "m", "pc"),
    Constant("GM_sun", "Paramètre gravitationnel du Soleil", "GM☉", GM_SUN, "m³ s⁻²", "GM"),
    Constant("GM_earth", "Paramètre gravitationnel de la Terre", "GM⊕", GM_EARTH, "m³ s⁻²", "GM"),
    Constant("yr", "Année julienne", "a", JULIAN_YEAR_S, "s", "yr"),
)

_SUPERSCRIPT = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")


def format_number(value: float, digits: int = 4) -> str:
    """Écriture française pour l'écran : virgule décimale, ``× 10ⁿ`` hors de [10⁻³, 10⁶[."""
    v = check_finite(value)
    digits = max(1, min(15, int(digits)))
    if v == 0:
        return "0"
    exponent = math.floor(math.log10(abs(v)))
    if -3 <= exponent < 6:
        text = f"{v:.{digits}g}"
        if "e" in text:  # arrondi qui franchit une puissance de dix
            text = f"{v:.{max(0, digits - exponent - 1)}f}"
        return text.replace(".", ",")
    mantissa = v / 10**exponent
    text = f"{mantissa:.{digits - 1}f}".rstrip("0").rstrip(".")
    if text in ("10", "-10"):  # 9,9999… arrondi
        text, exponent = text[:-1], exponent + 1
    return f"{text.replace('.', ',')} × 10{str(exponent).translate(_SUPERSCRIPT)}"


def format_quantity(value: float, unit_symbol: str, digits: int = 4) -> str:
    return f"{format_number(value, digits)} {unit_symbol}"


def units_of(dimension: str) -> list[str]:
    return [u.symbol for u in UNITS.values() if u.dimension == dimension]
