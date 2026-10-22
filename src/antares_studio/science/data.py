"""Tables de données CSV avec unités (phase 8) : lecture tolérante, diagnostics, jamais d'exécution.

En-tête attendu : ``nom (unité)`` ou ``nom [unité]`` (unité facultative). Séparateur détecté parmi
``;`` ``,`` et tabulation ; virgule décimale acceptée. Les cellules non numériques sont ignorées et
signalées ; une colonne sans aucune valeur numérique est refusée.
"""

from __future__ import annotations

import csv
import io
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

MAX_ROWS = 200_000
MAX_BYTES = 32 * 1024 * 1024
_HEADER = re.compile(r"^\s*(?P<name>[^([\]]+?)\s*(?:[(\[]\s*(?P<unit>[^)\]]*)\s*[)\]])?\s*$")


class DataError(ValueError):
    """Fichier illisible, sans colonne numérique ou trop volumineux."""


@dataclass(frozen=True)
class Column:
    name: str
    unit: str
    values: tuple[float, ...]  # NaN pour une cellule manquante ou non numérique

    @property
    def label(self) -> str:
        return f"{self.name} ({self.unit})" if self.unit else self.name

    def finite(self) -> list[float]:
        return [v for v in self.values if math.isfinite(v)]


@dataclass(frozen=True)
class DataTable:
    columns: tuple[Column, ...]
    diagnostics: tuple[str, ...] = field(default_factory=tuple)

    @property
    def row_count(self) -> int:
        return len(self.columns[0].values) if self.columns else 0

    def column(self, name: str) -> Column | None:
        return next((c for c in self.columns if c.name == name), None)

    def xy(self, x_name: str, y_name: str) -> list[tuple[float, float]]:
        """Couples finis (x, y) dans l'ordre des lignes ; vide si une colonne manque."""
        cx, cy = self.column(x_name), self.column(y_name)
        if cx is None or cy is None:
            return []
        return [
            (x, y) for x, y in zip(cx.values, cy.values, strict=True) if math.isfinite(x) and math.isfinite(y)
        ]


def parse_header(cell: str) -> tuple[str, str]:
    m = _HEADER.match(cell or "")
    if not m or not m.group("name").strip():
        return (cell.strip() or "colonne", "")
    return m.group("name").strip(), (m.group("unit") or "").strip()


def _to_float(cell: str) -> float:
    s = cell.strip().replace(" ", "").replace(" ", "")
    if not s:
        return math.nan
    if "," in s and "." not in s:
        s = s.replace(",", ".")
    try:
        v = float(s)
    except ValueError:
        return math.nan
    return v if math.isfinite(v) else math.nan


def parse_csv(text: str) -> DataTable:
    """Analyse un texte CSV ; ``DataError`` s'il n'y a aucune colonne numérique exploitable."""
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ";" if sample.count(";") >= sample.count(",") else ","
    rows = [r for r in csv.reader(io.StringIO(text), delimiter=delimiter) if any(c.strip() for c in r)]
    if len(rows) < 2:
        raise DataError("le fichier doit contenir une ligne d'en-tête et au moins une ligne de données")
    if len(rows) - 1 > MAX_ROWS:
        raise DataError(f"trop de lignes ({len(rows) - 1} > {MAX_ROWS})")
    headers = [parse_header(h) for h in rows[0]]
    width = len(headers)
    diagnostics: list[str] = []
    bad_cells = 0
    data: list[list[float]] = [[] for _ in headers]
    for li, row in enumerate(rows[1:], start=2):
        if len(row) != width:
            diagnostics.append(f"ligne {li} : {len(row)} cellules au lieu de {width}")
            row = (row + [""] * width)[:width]
        for ci, cell in enumerate(row):
            v = _to_float(cell)
            if math.isnan(v) and cell.strip():
                bad_cells += 1
            data[ci].append(v)
    if bad_cells:
        diagnostics.append(f"{bad_cells} cellule(s) non numérique(s) ignorée(s)")
    columns = [Column(n, u, tuple(vals)) for (n, u), vals in zip(headers, data, strict=True)]
    numeric = [c for c in columns if c.finite()]
    if not numeric:
        raise DataError("aucune colonne numérique : vérifiez le séparateur et le format des nombres")
    for c in columns:
        if not c.finite():
            diagnostics.append(f"colonne « {c.name} » sans valeur numérique")
    seen: set[str] = set()
    for c in columns:
        if c.name in seen:
            diagnostics.append(f"nom de colonne dupliqué : « {c.name} »")
        seen.add(c.name)
    return DataTable(tuple(columns), tuple(diagnostics))


def load_csv(path: Path) -> DataTable:
    p = Path(path)
    if p.stat().st_size > MAX_BYTES:
        raise DataError(f"fichier trop volumineux (> {MAX_BYTES // 2**20} Mo)")
    raw = p.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return parse_csv(raw.decode(enc))
        except UnicodeDecodeError:
            continue
    raise DataError("encodage non reconnu (UTF-8 attendu)")


@dataclass(frozen=True)
class Bin:
    left: float
    right: float
    count: int


def histogram(values: list[float], bins: int = 10) -> list[Bin]:
    """Classes de même largeur entre le min et le max (dernière classe fermée à droite), valeurs finies."""
    data = [v for v in values if math.isfinite(v)]
    if not data:
        return []
    bins = max(1, int(bins))
    lo, hi = min(data), max(data)
    if hi <= lo:  # une seule valeur : une classe de largeur 1 centrée dessus
        return [Bin(lo - 0.5, lo + 0.5, len(data))]
    width = (hi - lo) / bins
    counts = [0] * bins
    for v in data:
        counts[min(bins - 1, int((v - lo) / width))] += 1
    return [Bin(lo + i * width, lo + (i + 1) * width, c) for i, c in enumerate(counts)]


def nice_ticks(lo: float, hi: float, count: int = 5) -> list[float]:
    """Graduations « rondes » (1, 2, 5 × 10ⁿ) couvrant [lo, hi] ; ``count`` est indicatif."""
    if not (math.isfinite(lo) and math.isfinite(hi)):
        return []
    if hi <= lo:
        hi = lo + 1.0
    raw = (hi - lo) / max(1, count)
    mag = 10 ** math.floor(math.log10(raw))
    step = next(s * mag for s in (1, 2, 5, 10) if s * mag >= raw)
    first = math.floor(lo / step) * step
    ticks = []
    t = first
    while t <= hi + step * 1e-9:
        if t >= lo - step * 1e-9:
            ticks.append(round(t, 12))
        t += step
    return ticks
