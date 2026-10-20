# ADR-0003 — Provenance des ressources, inventaire des licences et crédits

**Date :** 2026-10-21 — **Statut :** accepté — **Phase :** 5

## Contexte

Le master prompt (§9.1, Gate 5, Gate 6) exige : provenance et licence visibles pour chaque ressource,
aucun élément non redistribuable dans un export diffusé, crédits/attribution présents dans les sorties,
avertissement d'échelle dans les modèles schématiques, sources des constantes affichées (SCI-07/08).
Le schéma v1 (ADR-0002) porte déjà `Asset.license` (auteur, source, licence, attribution, redistribution,
date de vérification) et `Project.scientific_metadata` (représentation, échelle, notes, sources).

## Décision

1. **Fiche de provenance à l'import** (`ProvenanceDialog`) proposée après chaque import d'image ou d'audio
   depuis l'interface, annulable (« Plus tard ») : l'import n'est jamais bloqué, mais la ressource reste
   « provenance manquante ». Liste fermée de licences courantes (œuvre personnelle, CC0, domaine public,
   CC BY/BY-SA/BY-NC 4.0, propriétaire, autre) qui pré-remplit « attribution requise » et
   « redistribution autorisée ».
2. **Statut calculé, jamais stocké** (`resources/licenses.py`, logique pure) : `complète`,
   `provenance manquante` (pas de licence, ou ni auteur ni source), `non redistribuable`. L'inventaire
   (onglet « Ressources » de la bibliothèque, dialogue « Inventaire des licences et crédits ») liste statut
   et usages (scène › objet/clip).
3. **Avertissements à l'export, pas de blocage** : `build_render_plan` ajoute un avertissement par
   ressource **utilisée** sans provenance ou non redistribuable ; l'export reste possible (usage en classe
   hors diffusion), l'avertissement figure dans le manifest.
4. **Crédits générés depuis le projet** (`credits_lines`) : sources scientifiques, mention « non à
   l'échelle » si `to_scale` est faux, ressources avec attribution requise ou auteur renseigné, puis
   logiciel (ANTARES Studio, Qt/PySide6 LGPL v3, FFmpeg). Écrits à chaque export dans
   `<vidéo>.credits.txt` et dans le manifest ; le modèle de scène « Crédits » les met en image.
5. **Avertissement d'échelle = objet dédié** : nouveau type `callout` (encadré texte avec fond, bordure,
   marge), utilisé par les trois modèles scientifiques et par `Objet > Avertissement d'échelle`, placé
   sous l'image au-dessus de la bande réservée aux sous-titres ; l'action force `to_scale = false`.
6. **Favoris de la bibliothèque** persistés dans les préférences locales (QSettings), pas dans le projet :
   ils appartiennent à l'utilisateur, pas au document.

## Alternatives écartées

- Bloquer l'export quand une ressource est non redistribuable : trop rigide pour l'usage pédagogique
  local ; remplacé par un avertissement explicite.
- Stocker le statut de licence dans le fichier projet : redondant et source d'incohérences.
- Filtre `drawtext` de FFmpeg pour les crédits : dépend de la build (fontconfig) ; la scène « Crédits »
  utilise le painter partagé.
- Packs d'icônes tiers : aucun pack redistribuable vérifié n'a été intégré ; la géométrie générative
  locale (formes, encadrés, modèles) reste la solution sans ressource tierce (master prompt §9.1).

## Conséquences

- Schéma v1 inchangé (champs déjà prévus) ; anciens projets lisibles sans migration.
- Tests : AST-03, AST-05, AST-06, SCI-07, SCI-08 et parcours P1 complet (Gate 5) automatisés.
- Reste à décider par le propriétaire : licence du produit ANTARES (R-002) et build FFmpeg distribuée.
