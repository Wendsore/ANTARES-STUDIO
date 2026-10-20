"""Provenance des ressources, inventaire des licences et crédits (master prompt §9.1, AST-03/06).

Logique pure (sans Qt) : utilisée par l'inventaire de la bibliothèque, l'export (fichier de crédits,
avertissements du plan) et le modèle de scène « Crédits ».
"""

from __future__ import annotations

from dataclasses import dataclass

from antares_studio import __version__
from antares_studio.domain.model import Asset, AssetLicense, Project


@dataclass(frozen=True)
class LicenseChoice:
    id: str
    label: str
    attribution_required: bool
    redistribution_allowed: bool


LICENSE_CHOICES: tuple[LicenseChoice, ...] = (
    LicenseChoice("own-work", "Œuvre personnelle (auteur du projet)", False, True),
    LicenseChoice("CC0-1.0", "CC0 1.0 — domaine public volontaire", False, True),
    LicenseChoice("public-domain", "Domaine public", False, True),
    LicenseChoice("CC-BY-4.0", "CC BY 4.0 — attribution", True, True),
    LicenseChoice("CC-BY-SA-4.0", "CC BY-SA 4.0 — attribution, partage identique", True, True),
    LicenseChoice("CC-BY-NC-4.0", "CC BY-NC 4.0 — attribution, pas d'usage commercial", True, True),
    LicenseChoice("proprietary", "Propriétaire / usage personnel — non redistribuable", False, False),
    LicenseChoice("other", "Autre (préciser dans la source)", True, False),
)

STATUS_COMPLETE = "complète"
STATUS_MISSING = "provenance manquante"
STATUS_NOT_REDISTRIBUTABLE = "non redistribuable"

SOFTWARE_CREDITS: tuple[str, ...] = (
    f"Réalisé avec ANTARES Studio {__version__} (Wendsore).",
    "Interface : Qt / PySide6 (LGPL v3). Encodage : FFmpeg (https://ffmpeg.org).",
)


def choice_for(license_id: str) -> LicenseChoice | None:
    return next((c for c in LICENSE_CHOICES if c.id == license_id), None)


def license_status(lic: AssetLicense) -> str:
    """Statut d'une fiche : complète, provenance manquante ou non redistribuable."""
    if not lic.license or not (lic.author or lic.source_url):
        return STATUS_MISSING
    if not lic.redistribution_allowed:
        return STATUS_NOT_REDISTRIBUTABLE
    return STATUS_COMPLETE


def assets_in_use(project: Project) -> dict[str, list[str]]:
    """Identifiant de ressource → libellés des objets/clips qui l'utilisent (toutes scènes)."""
    uses: dict[str, list[str]] = {}
    for scene in project.scenes:
        for node in scene.nodes:
            aid = node.params.get("asset_id")
            if isinstance(aid, str) and aid:
                uses.setdefault(aid, []).append(f"{scene.name} › {node.name}")
        for clip in scene.audio:
            uses.setdefault(clip.asset_id, []).append(f"{scene.name} › ♪ {clip.name or clip.id}")
    return uses


@dataclass(frozen=True)
class InventoryRow:
    asset: Asset
    status: str
    used_by: tuple[str, ...]


def inventory(project: Project) -> list[InventoryRow]:
    """Inventaire déterministe (ordre du projet) des ressources avec statut et usages."""
    uses = assets_in_use(project)
    return [InventoryRow(a, license_status(a.license), tuple(uses.get(a.id, ()))) for a in project.assets]


def provenance_warnings(project: Project, scene_id: str | None = None) -> list[str]:
    """Avertissements pour les ressources utilisées sans fiche complète (AST-03)."""
    uses = assets_in_use(project)
    out: list[str] = []
    for asset in project.assets:
        used = uses.get(asset.id, [])
        if scene_id is not None:
            scene_name = project.scene(scene_id).name
            used = [u for u in used if u.startswith(scene_name + " › ")]
        if not used:
            continue
        status = license_status(asset.license)
        if status == STATUS_MISSING:
            out.append(f"Ressource sans provenance : {asset.path} (utilisée par {', '.join(used)}).")
        elif status == STATUS_NOT_REDISTRIBUTABLE:
            out.append(f"Ressource non redistribuable : {asset.path} — la vidéo ne doit pas être diffusée.")
    return out


def credits_lines(project: Project, include_software: bool = True) -> list[str]:
    """Lignes de crédits : sources scientifiques, ressources tierces (attribution), logiciel."""
    lines: list[str] = []
    meta = project.scientific_metadata
    sources = meta.get("sources", [])
    if isinstance(sources, list) and sources:
        lines.append("Sources scientifiques :")
        for src in sources:
            if not isinstance(src, dict):
                continue
            label = str(src.get("label", "")).strip()
            url = str(src.get("url", "")).strip()
            if label or url:
                lines.append(f"  • {label}{' — ' + url if url else ''}")
    if meta.get("to_scale") is False:
        lines.append("Schéma : distances et tailles non à l'échelle.")
    assets = [a for a in project.assets if a.license.attribution_required or a.license.author]
    if assets:
        lines.append("Ressources :")
        for a in assets:
            lic = a.license
            parts = [a.path.rsplit("/", 1)[-1]]
            if lic.author:
                parts.append(lic.author)
            if lic.license:
                choice = choice_for(lic.license)
                parts.append(choice.label.split(" — ")[0] if choice else lic.license)
            if lic.source_url:
                parts.append(lic.source_url)
            lines.append("  • " + " — ".join(parts))
    if include_software:
        lines.extend(SOFTWARE_CREDITS)
    return lines


def credits_text(project: Project) -> str:
    return "\n".join(credits_lines(project)) + "\n"
