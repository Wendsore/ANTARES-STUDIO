"""Tutoriels interactifs : étapes guidées vérifiées sur l'état réel du projet (aucune dépendance Qt).

Chaque étape décrit une action à faire dans l'interface et, quand c'est possible, une **vérification**
``check(ctx, base)`` : ``ctx`` est l'état courant, ``base`` l'état au début de l'étape. L'étape est validée
dès que la vérification est vraie, ce qui interdit de « valider » une étape déjà vraie au départ (on
compare toujours à ``base``). Une étape sans vérification se valide avec le bouton « Suivant ».

L'état d'interface utile (zoom, lecture en cours, recherche dans la bibliothèque…) est fourni par la
fenêtre principale dans ``ctx.ui`` ; les clés sont listées dans ``UI_KEYS``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from antares_studio.domain.model import Node, Project, Scene

UI_KEYS = (
    "library_query",  # str : texte de recherche de la bibliothèque
    "zoom",  # float : zoom du canevas
    "playing",  # bool : lecture en cours
    "auto_key",  # bool : « Clé auto » coché
    "safe_zones",  # bool : zones sûres affichées
    "grid",  # bool : grille affichée
    "palette_used",  # int : nombre d'ouvertures de la recherche de commandes
    "help_opened",  # int : nombre d'ouvertures du centre d'aide
    "inventory_opened",  # int : nombre d'ouvertures de l'inventaire des licences
    "exports",  # int : nombre d'exports réussis dans la session
    "full_exports",  # int : nombre d'exports « toutes les scènes » réussis
)


@dataclass(frozen=True)
class TutorialContext:
    project: Project
    scene_id: str
    selection: tuple[str, ...] = ()
    frame: int = 0
    saved: bool = False  # projet enregistré dans un dossier et sans modification en attente
    has_folder: bool = False  # projet associé à un dossier .antares
    ui: dict[str, Any] = field(default_factory=dict)

    @property
    def scene(self) -> Scene | None:
        return next((s for s in self.project.scenes if s.id == self.scene_id), None)

    def nodes(self, kind: str | None = None) -> list[Node]:
        scene = self.scene
        if scene is None:
            return []
        return [n for n in scene.nodes if kind is None or n.kind == kind]

    def all_nodes(self) -> list[Node]:
        return [n for s in self.project.scenes for n in s.nodes]

    def node(self, node_id: str) -> Node | None:
        return next((n for n in self.all_nodes() if n.id == node_id), None)

    def keyframe_count(self) -> int:
        return sum(len(t.keyframes) for s in self.project.scenes for t in s.tracks)

    def keyframe_frames(self) -> list[tuple[str, str, int]]:
        return sorted(
            (t.target_id, t.property, k.frame)
            for s in self.project.scenes
            for t in s.tracks
            for k in t.keyframes
        )

    def tracked(self, prop_prefix: str, kind: str | None = None) -> list[str]:
        """Identifiants des objets (de ``kind``) qui ont une piste animée dont la propriété commence ainsi."""
        out = []
        for s in self.project.scenes:
            for t in s.tracks:
                if not t.property.startswith(prop_prefix) or not t.keyframes:
                    continue
                n = s.find_node(t.target_id)
                if n is not None and (kind is None or n.kind == kind):
                    out.append(n.id)
        return out

    def u(self, key: str, default: Any = None) -> Any:
        return self.ui.get(key, default)


Check = Callable[[TutorialContext, TutorialContext], bool]


@dataclass(frozen=True)
class Step:
    title: str
    body: str  # Markdown
    check: Check | None = None
    target: str = ""  # nom d'objet Qt du widget à mettre en évidence (« Montre-moi »)
    action: str = ""  # action proposée par un bouton : voir ``ACTIONS``
    hint: str = ""  # aide supplémentaire si l'utilisateur bloque


ACTIONS: dict[str, str] = {
    "import_example_csv": "Importer le fichier d'exemple (planètes, NASA)",
    "open_help": "Ouvrir la rubrique d'aide",
}


@dataclass(frozen=True)
class Tutorial:
    id: str
    title: str
    minutes: int
    summary: str
    steps: tuple[Step, ...]
    setup_template: str | None = None  # None : projet courant ; "" : projet vide ; sinon id de modèle
    help_topic: str = ""


# --- vérifications réutilisables --------------------------------------------------------------------
def _count(kind: str | None = None) -> Check:
    return lambda c, b: len(c.nodes(kind)) > len(b.nodes(kind))


def _changed(attr: str, kinds: tuple[str, ...] = ()) -> Check:
    """Vrai si un objet présent au début de l'étape a changé ``attr`` (``position``, ``params.radius``…)."""

    def get(n: Node) -> Any:
        if attr.startswith("params."):
            return n.params.get(attr[7:])
        if attr.startswith("style."):
            return n.style.get(attr[6:])
        return getattr(n, attr)

    def check(c: TutorialContext, b: TutorialContext) -> bool:
        before = {n.id: get(n) for n in b.all_nodes() if not kinds or n.kind in kinds}
        return any(n.id in before and get(n) != before[n.id] for n in c.all_nodes())

    return check


def _any(*checks: Check) -> Check:
    return lambda c, b: any(ch(c, b) for ch in checks)


def _ui_increased(key: str) -> Check:
    return lambda c, b: int(c.u(key, 0) or 0) > int(b.u(key, 0) or 0)


def _scene_added(name_part: str) -> Check:
    def check(c: TutorialContext, b: TutorialContext) -> bool:
        before = {s.id for s in b.project.scenes}
        return any(s.id not in before and name_part.casefold() in s.name.casefold() for s in c.project.scenes)

    return check


def _selected(c: TutorialContext, b: TutorialContext) -> bool:
    return bool(c.selection) and c.selection != b.selection


def _frame_moved(c: TutorialContext, b: TutorialContext) -> bool:
    return c.frame != b.frame


def _zoom_changed(c: TutorialContext, b: TutorialContext) -> bool:
    return abs(float(c.u("zoom", 1.0)) - float(b.u("zoom", 1.0))) > 1e-6


def _saved(c: TutorialContext, b: TutorialContext) -> bool:
    return c.saved


def _text_edited(c: TutorialContext, b: TutorialContext) -> bool:
    return any(
        n.kind == "text" and str(n.params.get("text", "")) not in ("", "Texte") for n in c.nodes("text")
    )


def _renamed(c: TutorialContext, b: TutorialContext) -> bool:
    before = {n.id: n.name for n in b.all_nodes()}
    return any(n.id in before and n.name != before[n.id] for n in c.all_nodes())


def _hidden_or_locked(c: TutorialContext, b: TutorialContext) -> bool:
    before = {n.id: (n.visible, n.locked) for n in b.all_nodes()}
    return any(n.id in before and (n.visible, n.locked) != before[n.id] for n in c.all_nodes())


def _tracked(prop: str, minimum_keys: int = 2) -> Check:
    """Vrai si une piste dont la propriété commence par ``prop`` a gagné des clés et en compte au moins
    ``minimum_keys`` (une animation prédéfinie vient d'être appliquée, par exemple)."""

    def keys(ctx: TutorialContext) -> dict[tuple[str, str], int]:
        return {
            (t.target_id, t.property): len(t.keyframes)
            for s in ctx.project.scenes
            for t in s.tracks
            if t.property.startswith(prop)
        }

    def check(c: TutorialContext, b: TutorialContext) -> bool:
        before = keys(b)
        return any(n >= minimum_keys and n > before.get(k, 0) for k, n in keys(c).items())

    return check


def _keys_added(c: TutorialContext, b: TutorialContext) -> bool:
    return c.keyframe_count() > b.keyframe_count()


def _key_moved(c: TutorialContext, b: TutorialContext) -> bool:
    return c.keyframe_count() == b.keyframe_count() and c.keyframe_frames() != b.keyframe_frames()


def _key_removed(c: TutorialContext, b: TutorialContext) -> bool:
    return c.keyframe_count() < b.keyframe_count()


def _audio_added(c: TutorialContext, b: TutorialContext) -> bool:
    return sum(len(s.audio) for s in c.project.scenes) > sum(len(s.audio) for s in b.project.scenes)


def _audio_adjusted(c: TutorialContext, b: TutorialContext) -> bool:
    before = {
        a.id: (a.offset_frames, a.gain, a.fade_in_seconds, a.fade_out_seconds, a.muted)
        for s in b.project.scenes
        for a in s.audio
    }
    return any(
        a.id in before
        and (a.offset_frames, a.gain, a.fade_in_seconds, a.fade_out_seconds, a.muted) != before[a.id]
        for s in c.project.scenes
        for a in s.audio
    )


def _subtitle_added(c: TutorialContext, b: TutorialContext) -> bool:
    return sum(len(s.subtitles) for s in c.project.scenes) > sum(len(s.subtitles) for s in b.project.scenes)


def _subtitle_edited(c: TutorialContext, b: TutorialContext) -> bool:
    before = {x.id: x.text for s in b.project.scenes for x in s.subtitles}
    return any(
        x.text.strip() and x.text != "Nouveau sous-titre" and before.get(x.id) != x.text
        for s in c.project.scenes
        for x in s.subtitles
    )


def _metadata_changed(key: str) -> Check:
    return lambda c, b: c.project.scientific_metadata.get(key) != b.project.scientific_metadata.get(key)


def _sources_added(c: TutorialContext, b: TutorialContext) -> bool:
    return len(c.project.scientific_metadata.get("sources", [])) > len(
        b.project.scientific_metadata.get("sources", [])
    )


def _formula_edited(c: TutorialContext, b: TutorialContext) -> bool:
    return any(str(n.params.get("text", "")) not in ("", "E = m c^{2}") for n in c.nodes("formula"))


def _chart_with_data(c: TutorialContext, b: TutorialContext) -> bool:
    before = {n.id for n in b.all_nodes() if n.kind == "chart" and n.params.get("data_asset_id")}
    return any(
        n.kind == "chart" and n.params.get("data_asset_id") and n.id not in before for n in c.all_nodes()
    )


def _image_added(c: TutorialContext, b: TutorialContext) -> bool:
    before = {n.id for n in b.all_nodes() if n.kind == "image" and n.params.get("asset_id")}
    return any(n.kind == "image" and n.params.get("asset_id") and n.id not in before for n in c.all_nodes())


def _provenance_completed(c: TutorialContext, b: TutorialContext) -> bool:
    from antares_studio.resources.licenses import STATUS_COMPLETE, license_status

    before = {a.id: license_status(a.license) for a in b.project.assets}
    return any(
        license_status(a.license) == STATUS_COMPLETE and before.get(a.id) != STATUS_COMPLETE
        for a in c.project.assets
    )


# --- catalogue -----------------------------------------------------------------------------------
TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        "interface",
        "1. Découvrir l'espace de travail",
        5,
        "Repérer les panneaux, zoomer, parcourir le temps et trouver n'importe quelle commande.",
        setup_template="moon_phases",
        help_topic="interface",
        steps=(
            Step(
                "Bienvenue",
                "Ce tutoriel a ouvert un projet d'exemple, **Phases de la Lune**, sans toucher à vos "
                "fichiers. Chaque étape se valide toute seule dès que vous avez fait l'action ; "
                "**Montre-moi** fait clignoter l'endroit concerné.\n\n"
                "Cliquez sur **Suivant** pour commencer.",
            ),
            Step(
                "La Bibliothèque",
                "À gauche, la **Bibliothèque** contient les objets, les animations, les modèles et les "
                "ressources du projet. Tapez **cercle** dans son champ de recherche.",
                check=lambda c, b: "cercle" in str(c.u("library_query", "")).casefold(),
                target="library_search",
            ),
            Step(
                "Le canevas",
                "Au centre, le **canevas** montre l'image exactement comme dans la vidéo exportée. "
                "Zoomez avec la **molette** de la souris au-dessus du canevas (ou **Ctrl + +**).",
                check=_zoom_changed,
                target="canvas",
                hint="Ctrl+0 ajuste la vue à la fenêtre ; clic molette ou Alt + glisser pour se déplacer.",
            ),
            Step(
                "Sélectionner un objet",
                "Cliquez sur la **Terre** (le disque bleu) dans le canevas, ou sur son nom dans le panneau "
                "**Scènes et objets**. L'**Inspecteur**, à droite, affiche alors ses propriétés.",
                check=_selected,
                target="layers_tree",
            ),
            Step(
                "Parcourir le temps",
                "En bas, la **Timeline** montre les images clés (losanges). Cliquez ou glissez dans la "
                "règle graduée pour déplacer la **tête de lecture** rouge.",
                check=_frame_moved,
                target="timeline_view",
            ),
            Step(
                "Lire l'animation",
                "Appuyez sur **Espace** (ou le bouton **Lecture**) : la Lune tourne autour de la Terre. "
                "Appuyez de nouveau sur Espace pour mettre en pause.",
                check=lambda c, b: bool(c.u("playing")),
                target="timeline_play",
            ),
            Step(
                "Trouver une commande",
                "Appuyez sur **Ctrl+K** : la **recherche de commandes** liste toutes les actions du "
                "logiciel avec leur raccourci. Tapez quelques lettres puis Entrée, ou Échap pour fermer.",
                check=_ui_increased("palette_used"),
            ),
            Step(
                "L'aide est toujours là",
                "**F1** ouvre le **Centre d'aide** à la rubrique du panneau où vous êtes. Ouvrez-le "
                "maintenant pour terminer ce tutoriel.",
                check=_ui_increased("help_opened"),
                action="open_help",
            ),
        ),
    ),
    Tutorial(
        "premiere-scene",
        "2. Créer votre première scène",
        10,
        "Ajouter des formes et du texte, les déplacer, les colorer, les organiser et enregistrer.",
        setup_template="",
        help_topic="objets",
        steps=(
            Step(
                "Ajouter un cercle",
                "Un projet vide a été créé. Dans la Bibliothèque, onglet **Objets**, **double-cliquez** sur "
                "**Cercle** : il apparaît au centre de la vue.",
                check=_count("circle"),
                target="library_tabs",
                hint="On peut aussi passer par le menu Objet > Cercle.",
            ),
            Step(
                "Déplacer l'objet",
                "Glissez le cercle avec la souris. Pour un réglage fin, utilisez les **flèches du clavier** "
                "(Maj + flèche = 10 px).",
                check=_changed("position"),
                target="canvas",
            ),
            Step(
                "Changer sa taille",
                "Tirez une **poignée carrée** blanche du cadre de sélection (Maj garde les proportions), ou "
                "modifiez le **Rayon** dans l'Inspecteur.",
                check=_any(_changed("scale"), _changed("params.radius")),
                target="inspector",
            ),
            Step(
                "Changer sa couleur",
                "Dans l'Inspecteur, section **Style**, cliquez sur la case **Remplissage** et choisissez une "
                "couleur.",
                check=_changed("style.fill"),
                target="inspector",
            ),
            Step(
                "Ajouter un texte",
                "Ajoutez un **Texte** depuis la Bibliothèque, puis **double-cliquez** dessus dans le canevas "
                "pour écrire votre titre.",
                check=_count("text"),
                target="library_tabs",
            ),
            Step(
                "Écrire le titre",
                "Écrivez le texte de votre titre (double-clic sur le texte, ou champ **Texte** de "
                "l'Inspecteur).",
                check=lambda c, b: _text_edited(c, b) and _changed("params.text", ("text",))(c, b),
                target="inspector",
            ),
            Step(
                "Dupliquer",
                "Sélectionnez le cercle et appuyez sur **Ctrl+D** : une copie décalée est créée.",
                check=_count(None),
            ),
            Step(
                "Renommer",
                "Dans **Scènes et objets**, double-cliquez sur le nom d'un objet pour le renommer "
                "(par exemple « Soleil »). Des noms clairs facilitent la suite.",
                check=_renamed,
                target="layers_tree",
            ),
            Step(
                "Masquer ou verrouiller",
                "Dans la même liste, cochez la colonne **œil** pour masquer un objet, ou **cadenas** pour "
                "le protéger des clics involontaires.",
                check=_hidden_or_locked,
                target="layers_tree",
            ),
            Step(
                "Enregistrer",
                "**Ctrl+S** enregistre le projet dans un dossier `.antares` (images, sons et sauvegardes "
                "automatiques y sont rangés). Choisissez un nom et un emplacement.",
                check=_saved,
                hint="Ctrl+Z annule n'importe quelle étape précédente ; Ctrl+Y la rétablit.",
            ),
        ),
    ),
    Tutorial(
        "animer",
        "3. Animer sans programmer",
        10,
        "Appliquer des animations toutes faites, poser des images clés et les modifier dans la timeline.",
        setup_template="",
        help_topic="animations",
        steps=(
            Step(
                "Un objet à animer",
                "Ajoutez une **Étoile** (ou n'importe quelle forme) depuis la Bibliothèque.",
                check=_count(None),
                target="library_tabs",
            ),
            Step(
                "Le faire apparaître",
                "Objet sélectionné, ouvrez l'onglet **Animations** de la Bibliothèque et double-cliquez sur "
                "**Apparition**. Réglez la durée, puis **Appliquer**.",
                check=_tracked("opacity"),
                target="library_tabs",
            ),
            Step(
                "Le mettre en orbite",
                "Toujours sur le même objet, appliquez **Orbite schématique** : choisissez le centre, le "
                "rayon, le nombre de tours et le sens. Le bouton « Utiliser la position actuelle… » calcule "
                "rayon et phase depuis la position de l'objet.",
                check=_tracked("position", 3),
            ),
            Step(
                "Vérifier",
                "Appuyez sur **Espace** pour lire l'animation.",
                check=lambda c, b: bool(c.u("playing")),
                target="timeline_play",
            ),
            Step(
                "Une image clé à la main",
                "Mettez en pause, déplacez la tête de lecture, puis cliquez sur le **losange ◆** à côté de "
                "**Rotation** dans l'Inspecteur pour poser une image clé. Changez de moment, modifiez la "
                "rotation : avec **Clé auto** coché dans la Timeline, la clé est posée automatiquement.",
                check=_keys_added,
                target="inspector",
            ),
            Step(
                "Déplacer une clé",
                "Dans la Timeline, **glissez un losange** vers la gauche ou la droite pour changer le "
                "moment de l'image clé.",
                check=_key_moved,
                target="timeline_view",
            ),
            Step(
                "Supprimer une clé",
                "Cliquez sur un losange pour le sélectionner (il devient orange) puis appuyez sur **Suppr**.",
                check=_key_removed,
                target="timeline_view",
                hint="Clic droit sur le losange de l'Inspecteur : supprime l'animation de la propriété.",
            ),
        ),
    ),
    Tutorial(
        "narration",
        "4. Ajouter la voix et les sous-titres",
        8,
        "Importer une narration enregistrée, la caler, puis écrire des sous-titres lisibles.",
        setup_template="intro",
        help_topic="narration",
        steps=(
            Step(
                "Enregistrer d'abord",
                "Le son est copié dans le dossier du projet : enregistrez ce projet d'exemple (**Ctrl+S**).",
                check=lambda c, b: c.has_folder,
            ),
            Step(
                "Importer la narration",
                "Ouvrez l'onglet **Narration** (à côté de la Timeline) puis **Importer une narration…**. "
                "Choisissez un fichier WAV, MP3, OGG, FLAC ou M4A : par exemple votre voix enregistrée "
                "avec le dictaphone du téléphone. Vous pouvez aussi cliquer sur **Enregistrer au micro…**.",
                check=_audio_added,
                target="narration_import",
                hint="Pas de fichier sous la main ? **Enregistrer au micro…** enregistre votre voix.",
            ),
            Step(
                "Caler et régler le son",
                "Glissez le clip audio dans la Timeline, ou changez dans le tableau son **début**, son "
                "**gain** ou ses **fondus**.",
                check=_audio_adjusted,
                target="narration_table",
            ),
            Step(
                "Écrire un sous-titre",
                "Onglet **Sous-titres** : placez la tête de lecture puis **Ajouter à l'image courante**.",
                check=_subtitle_added,
                target="subtitles_add",
            ),
            Step(
                "Le texte du sous-titre",
                "Double-cliquez dans la colonne **Texte** du tableau et écrivez la phrase prononcée ; "
                "ajustez **Début** et **Fin**. Les problèmes (chevauchement, ligne trop longue) s'affichent "
                "sous le tableau.",
                check=_subtitle_edited,
                target="subtitles_table",
            ),
            Step(
                "Zones sûres",
                "Activez **Affichage > Zones sûres (sous-titres)** : les cadres pointillés montrent la "
                "zone que les téléphones et téléviseurs ne rognent pas.",
                check=lambda c, b: bool(c.u("safe_zones")),
            ),
        ),
    ),
    Tutorial(
        "science",
        "5. Une scène scientifique rigoureuse",
        12,
        "Orbite de Kepler, équation, graphique de données réelles, sources et avertissement d'échelle.",
        setup_template="",
        help_topic="rigueur-scientifique",
        steps=(
            Step(
                "Ajouter le modèle Kepler",
                "Bibliothèque, onglet **Modèles** : double-cliquez sur **Orbite de Kepler**. Une nouvelle "
                "scène est créée : planète sur une ellipse, Soleil au foyer, vitesse plus grande au "
                "périhélie.",
                check=_scene_added("Kepler"),
                target="library_tabs",
            ),
            Step(
                "Écrire une équation",
                "Ajoutez un objet **Équation (formule)** (catégorie Maths) et remplacez la formule dans "
                "l'Inspecteur, par exemple `T^{2} = \\frac{4 \\pi^{2}}{G M} a^{3}`.",
                check=_formula_edited,
                target="inspector",
                hint="La syntaxe complète est dans l'aide, rubrique « Équations ».",
            ),
            Step(
                "Enregistrer le projet",
                "Les données importées sont copiées dans le dossier du projet : enregistrez (**Ctrl+S**).",
                check=lambda c, b: c.has_folder,
            ),
            Step(
                "Tracer des données réelles",
                "Menu **Objet > Importer des données (CSV) en graphique…** et choisissez un CSV, ou "
                "utilisez le bouton ci-dessous pour importer l'exemple fourni : distance et période des "
                "huit planètes (NASA). La fiche de provenance s'ouvre ensuite : déjà remplie pour "
                "l'exemple ; pour vos fichiers, indiquez l'auteur, la source et la licence.",
                check=_chart_with_data,
                action="import_example_csv",
            ),
            Step(
                "Animer la courbe",
                "Graphique sélectionné, appliquez l'animation **Tracer la courbe** : la courbe se dessine "
                "progressivement.",
                check=_tracked("params.progress"),
                target="library_tabs",
            ),
            Step(
                "Dire ce que montre la scène",
                "Cliquez sur le fond du canevas (aucun objet sélectionné) : l'Inspecteur affiche les "
                "**Métadonnées scientifiques**. Choisissez la **Représentation** qui correspond.",
                check=_metadata_changed("representation"),
                target="inspector",
            ),
            Step(
                "Citer ses sources",
                "Toujours dans les métadonnées, bouton **Sources…** : ajoutez au moins une source (titre, "
                "lien ou référence). Elles apparaissent dans les crédits.",
                check=_sources_added,
                target="inspector",
            ),
            Step(
                "Prévenir le spectateur",
                "Menu **Objet > Avertissement d'échelle** ajoute l'encadré « distances et tailles non à "
                "l'échelle ». Indispensable dès qu'un schéma déforme les proportions.",
                check=_count("callout"),
            ),
        ),
    ),
    Tutorial(
        "ressources",
        "6. Images, provenance et crédits",
        8,
        "Importer une image, documenter sa licence et produire des crédits exacts.",
        setup_template=None,
        help_topic="provenance-et-licences",
        steps=(
            Step(
                "Importer une image",
                "Menu **Objet > Importer une image…** (Ctrl+I) : PNG, JPEG, SVG, BMP ou WebP. Le projet doit "
                "être enregistré : ANTARES le propose sinon.",
                check=_image_added,
            ),
            Step(
                "Documenter la provenance",
                "La **fiche de provenance** s'ouvre : auteur, source (lien), licence. Complétez-la. "
                "« Plus tard » la laisse en « provenance manquante » : double-clic dans l'onglet "
                "**Ressources** de la Bibliothèque pour y revenir.",
                check=_provenance_completed,
                target="library_tabs",
            ),
            Step(
                "Contrôler l'inventaire",
                "**Fichier > Inventaire des licences et crédits…** liste chaque ressource, son statut et le "
                "texte des crédits.",
                check=_ui_increased("inventory_opened"),
            ),
            Step(
                "Ajouter la scène de crédits",
                "Onglet **Modèles** : double-cliquez sur **Crédits**. La scène reprend les sources et les "
                "ressources documentées.",
                check=_scene_added("Crédits"),
                target="library_tabs",
            ),
        ),
    ),
    Tutorial(
        "exporter",
        "7. Exporter la vidéo",
        6,
        "Produire un brouillon rapide, puis la vidéo complète avec ses sous-titres et ses crédits.",
        setup_template=None,
        help_topic="export-video",
        steps=(
            Step(
                "Un brouillon rapide",
                "**Fichier > Exporter la vidéo…** (Ctrl+E), profil **Brouillon 720p**, puis **Exporter**. "
                "La progression s'affiche ; « Annuler l'export » n'abandonne aucun fichier partiel.",
                check=_ui_increased("exports"),
                hint="Si FFmpeg est introuvable : Aide > Diagnostics… puis Aide > Chemin de FFmpeg…",
            ),
            Step(
                "La vidéo complète",
                "Exportez de nouveau en cochant **Toutes les scènes à la suite (vidéo complète)** et le "
                "profil **Final 1080p**.",
                check=_ui_increased("full_exports"),
            ),
            Step(
                "Les fichiers produits",
                "À côté de la vidéo : `.srt` (sous-titres), `.credits.txt` (crédits) et `.manifest.json` "
                "(description du rendu). Publiez la vidéo avec ses crédits. Bravo, vous connaissez tout le "
                "parcours !",
            ),
        ),
    ),
)

TUTORIALS_BY_ID: dict[str, Tutorial] = {t.id: t for t in TUTORIALS}


class TutorialRun:
    """Déroulé d'un tutoriel : étape courante, état de référence et validation automatique."""

    def __init__(self, tutorial: Tutorial, context: TutorialContext):
        self.tutorial = tutorial
        self.index = 0
        self.base = context
        self.completed: set[int] = set()

    @property
    def step(self) -> Step:
        return self.tutorial.steps[self.index]

    @property
    def finished(self) -> bool:
        return len(self.completed) == len(self.tutorial.steps) or (
            self.index == len(self.tutorial.steps) - 1 and self.index in self.completed
        )

    def update(self, context: TutorialContext) -> bool:
        """Évalue l'étape courante ; ``True`` si elle vient d'être validée."""
        step = self.step
        if self.index in self.completed or step.check is None:
            return False
        try:
            ok = bool(step.check(context, self.base))
        except (KeyError, AttributeError, TypeError, ValueError):
            ok = False
        if ok:
            self.completed.add(self.index)
        return ok

    def go(self, index: int, context: TutorialContext) -> None:
        self.index = max(0, min(index, len(self.tutorial.steps) - 1))
        self.base = context

    def next(self, context: TutorialContext) -> None:
        if self.step.check is None:
            self.completed.add(self.index)
        self.go(self.index + 1, context)
