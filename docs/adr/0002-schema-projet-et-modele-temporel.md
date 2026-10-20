# ADR-0002 — Schéma de projet v1, temps canonique en frames et évaluateur pur

**Date :** 2026-10-20 — **Statut :** acceptée

## Contexte

Le master prompt (§3.4, §6.1) impose : IDs stables, version de schéma, pas de chemin absolu, temps canonique quantifié, désérialisation sans exécution de code, sauvegarde atomique, et un évaluateur `evaluate(project, scene_id, t) -> SceneState` commun à la prévisualisation et à l'export.

## Décisions

1. **Format de projet** : un **dossier** `Nom.antares/` (pas d'archive) contenant `project.json`, `assets/`, `audio/`, `licenses/`, `autosaves/`, `cache/`, `renders/`. Un dossier est lisible par l'utilisateur, robuste aux interruptions (remplacement atomique de `project.json` seul) et évite les attaques ZIP-slip à l'ouverture. Un export/import en archive `.antares.zip` pourra être ajouté plus tard avec contrôle de traversée.
2. **Temps canonique** : entiers de **frames** ; la cadence est un rationnel `fps_num/fps_den` (30/1 par défaut). Les secondes ne servent qu'à l'affichage et à l'audio ; conversion `frame = round(t * fps)`.
3. **Modèle** : `Project{schema_version, project_id, title, locale, canvas, scenes[], assets[], scientific_metadata}` ; `Scene{id, name, duration_frames, background, nodes[], tracks[]}` ; `Node{id, kind, name, parent_id, position, rotation_deg, scale, opacity, visible, locked, z_index, style{}, params{}}` ; `Track{target_id, property, keyframes[{frame, value, easing}]}`. Les propriétés animables sont adressées par chemin pointé (`position.x`, `opacity`, `style.fill`, `params.radius`).
4. **Interpolation** : `step`, `linear`, `ease_in`, `ease_out`, `ease_in_out` (cubique) ; couleurs en RGBA linéaire par composante ; angles interpolés **tels quels** (pas de plus-court-arc) pour qu'un tour complet 0→360 reste un tour (convention documentée dans `timeline/evaluator.py`) ; booléens en `step`.
5. **Collisions de keyframes** : deux clés à la même frame → la dernière écrite remplace la précédente (normalisation à l'insertion) ; avant la première clé, valeur de la première ; après la dernière, valeur de la dernière.
6. **Évaluateur pur** : `evaluate(project, scene_id, frame)` retourne un `SceneState` immuable (liste de `NodeState` avec transformation monde et propriétés résolues, triés par `z_index` puis ordre de déclaration). Aucune dépendance Qt ; parent cyclique détecté et rejeté à la validation.
7. **Sérialisation** : `json` standard uniquement, validation stricte à la lecture (types, finitude, unicité des IDs, références), aucun `pickle`, `eval`, `exec`. Les erreurs produisent `ProjectFormatError` avec le chemin JSON fautif.
8. **Persistance** : écriture dans un fichier temporaire du même dossier puis `os.replace` ; sauvegarde de l'ancien `project.json` dans `autosaves/` avant migration ; autosave périodique dans `autosaves/` sans toucher au fichier principal.

## Conséquences

- Les tests TIM-01…12 et MOD-01…12 deviennent écrivables sans Qt.
- La prévisualisation et l'export consomment le même `SceneState` ; les écarts ne peuvent être que de rasterisation.
- Les presets (Phase 3) sont des générateurs de keyframes, donc entièrement représentables dans ce schéma.
