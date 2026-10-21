"""Mini-langage de formules rendu localement, sans LaTeX ni exécution (master prompt §6.1 « fallback »).

Syntaxe (sous-ensemble inspiré de LaTeX, jamais interprété comme du code) :
``x^{2}``, ``a_{n}``, ``\\frac{a}{b}``, ``\\sqrt{x}``, ``\\vec{v}``, ``\\alpha`` … (lettres grecques),
``\\cdot \\times \\pm \\le \\ge \\ne \\to \\infty \\approx \\sum \\int \\partial \\degree``, ``{...}`` groupe.
Une commande inconnue est conservée en texte littéral et signalée dans les diagnostics ; une accolade
non fermée est tolérée (fermeture implicite) et signalée.
"""

from __future__ import annotations

from dataclasses import dataclass, field

SYMBOLS: dict[str, str] = {
    "alpha": "α",
    "beta": "β",
    "gamma": "γ",
    "delta": "δ",
    "epsilon": "ε",
    "zeta": "ζ",
    "eta": "η",
    "theta": "θ",
    "iota": "ι",
    "kappa": "κ",
    "lambda": "λ",
    "mu": "μ",
    "nu": "ν",
    "xi": "ξ",
    "pi": "π",
    "rho": "ρ",
    "sigma": "σ",
    "tau": "τ",
    "upsilon": "υ",
    "phi": "φ",
    "chi": "χ",
    "psi": "ψ",
    "omega": "ω",
    "Gamma": "Γ",
    "Delta": "Δ",
    "Theta": "Θ",
    "Lambda": "Λ",
    "Xi": "Ξ",
    "Pi": "Π",
    "Sigma": "Σ",
    "Phi": "Φ",
    "Psi": "Ψ",
    "Omega": "Ω",
    "cdot": "·",
    "times": "×",
    "pm": "±",
    "le": "≤",
    "ge": "≥",
    "ne": "≠",
    "to": "→",
    "infty": "∞",
    "approx": "≈",
    "sum": "∑",
    "int": "∫",
    "partial": "∂",
    "degree": "°",
    "propto": "∝",
    "nabla": "∇",
    "leftarrow": "←",
    "rightarrow": "→",
    "equiv": "≡",
    "sim": "∼",
    "ldots": "…",
    "cdots": "⋯",
}
_COMMANDS_WITH_ARGS = {"frac": 2, "sqrt": 1, "vec": 1, "hat": 1, "bar": 1, "text": 1}


@dataclass
class Node:
    """Nœud de mise en page : kind ∈ text | row | sup | sub | frac | sqrt | vec | hat | bar."""

    kind: str
    text: str = ""
    children: list[Node] = field(default_factory=list)


@dataclass(frozen=True)
class Formula:
    root: Node
    diagnostics: tuple[str, ...]

    def plain(self) -> str:
        """Transcription linéaire (accessibilité, tests, sous-titres)."""
        return _plain(self.root)


def _plain(n: Node) -> str:
    if n.kind == "text":
        return n.text
    parts = [_plain(c) for c in n.children]
    if n.kind == "frac":
        return f"({parts[0]})/({parts[1]})"
    if n.kind == "sqrt":
        return f"√({parts[0]})"
    if n.kind == "sup":
        return f"^({parts[0]})"
    if n.kind == "sub":
        return f"_({parts[0]})"
    if n.kind in ("vec", "hat", "bar"):
        return f"{n.kind}({parts[0]})"
    return "".join(parts)


class _Parser:
    def __init__(self, src: str):
        self.s = src
        self.i = 0
        self.diag: list[str] = []

    def parse(self) -> Node:
        row = self.parse_row(stop_at_brace=False)
        if self.i < len(self.s):  # accolade fermante orpheline
            self.diag.append(f"accolade fermante inattendue à la position {self.i}")
            self.i += 1
            rest = self.parse()
            row.children.extend(rest.children)
        return row

    def parse_row(self, stop_at_brace: bool) -> Node:
        row = Node("row")
        buf = ""

        def flush() -> None:
            nonlocal buf
            if buf:
                row.children.append(Node("text", buf))
                buf = ""

        while self.i < len(self.s):
            ch = self.s[self.i]
            if ch == "}":
                if stop_at_brace:
                    self.i += 1
                    flush()
                    return row
                flush()
                return row  # géré par l'appelant
            if ch == "{":
                flush()
                self.i += 1
                row.children.append(self.parse_row(stop_at_brace=True))
                continue
            if ch in "^_":
                flush()
                self.i += 1
                arg = self.parse_arg()
                row.children.append(Node("sup" if ch == "^" else "sub", children=[arg]))
                continue
            if ch == "\\":
                flush()
                row.children.append(self.parse_command())
                continue
            buf += ch
            self.i += 1
        if stop_at_brace:
            self.diag.append("accolade non fermée (fermée implicitement)")
        flush()
        return row

    def parse_arg(self) -> Node:
        if self.i < len(self.s) and self.s[self.i] == "{":
            self.i += 1
            return self.parse_row(stop_at_brace=True)
        if self.i < len(self.s) and self.s[self.i] == "\\":
            return self.parse_command()
        if self.i < len(self.s):
            ch = self.s[self.i]
            self.i += 1
            return Node("text", ch)
        self.diag.append("argument manquant après ^ ou _")
        return Node("text", "")

    def parse_command(self) -> Node:
        self.i += 1  # '\\'
        j = self.i
        while j < len(self.s) and self.s[j].isalpha():
            j += 1
        name = self.s[self.i : j]
        if not name:  # '\{', '\\' : littéral ; '\,' '\;' '\:' : espace fine ; '\!' : rien
            ch = self.s[self.i] if self.i < len(self.s) else "\\"
            self.i = min(len(self.s), self.i + 1)
            if ch in ",;:":
                return Node("text", " ")
            if ch == "!":
                return Node("text", "")
            return Node("text", ch)
        self.i = j
        if name in SYMBOLS:
            return Node("text", SYMBOLS[name])
        if name in _COMMANDS_WITH_ARGS:
            n_args = _COMMANDS_WITH_ARGS[name]
            args = [self.parse_arg() for _ in range(n_args)]
            if name == "text":
                return Node("text", _plain(args[0]))
            return Node(name, children=args)
        self.diag.append(f"commande inconnue \\{name} conservée en texte")
        return Node("text", "\\" + name)


def parse_formula(source: str) -> Formula:
    """Analyse ``source`` ; ne lève jamais : les anomalies deviennent des diagnostics."""
    p = _Parser(source or "")
    root = p.parse()
    return Formula(root, tuple(p.diag))
