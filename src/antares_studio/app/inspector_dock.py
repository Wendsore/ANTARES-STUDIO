"""Inspecteur contextuel : éditeurs typés issus du catalogue, bouton « image clé » par propriété animable."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from antares_studio.app import theme
from antares_studio.app.document import ProjectDocument
from antares_studio.domain.colors import format_color, is_color, parse_color
from antares_studio.domain.commands import (
    RemoveKeyframe,
    RemoveTrack,
    SetKeyframe,
    SetProjectMetadata,
    SetSceneProperty,
)
from antares_studio.domain.kinds import BASE_LABELS, KINDS, ParamSpec
from antares_studio.domain.model import Node
from antares_studio.domain.properties import is_animatable
from antares_studio.timeline.evaluator import NodeState

# Paramètres « ressource » : (type de ressource proposé, libellé de l'absence de choix)
ASSET_PARAMS: dict[str, tuple[str, str]] = {
    "params.asset_id": ("image", "(aucune image)"),
    "params.data_asset_id": ("data", "(aucun fichier CSV)"),
    "params.sequence_asset_id": ("sequence", "(aucune séquence)"),
    "params.model_asset_id": ("model", "(aucun modèle 3D)"),
}


class ColorButton(QPushButton):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._value = "#FFFFFF"
        self.setFixedWidth(110)
        self.clicked.connect(self._pick)
        self.changed: list[Any] = []

    def value(self) -> str:
        return self._value

    def set_value(self, v: str) -> None:
        if not is_color(v):
            v = "#FFFFFF"
        self._value = v.upper()
        r, g, b, a = parse_color(self._value)
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        # les couleurs du projet sont #RRGGBB[AA] ; le CSS de Qt lirait #AARRGGBB : on passe par rgba()
        fg = theme.active().text if a < 0.4 else "#000000" if lum > 0.55 else "#FFFFFF"
        self.setText("Transparent" if a == 0 else self._value)
        self.setToolTip(f"{self._value} — clic : choisir une couleur (transparence comprise)")
        border = theme.active().control_border
        rgba = f"rgba({round(r * 255)}, {round(g * 255)}, {round(b * 255)}, {round(a * 255)})"
        self.setStyleSheet(
            f"background-color: {rgba}; color: {fg}; border: 1px solid {border};"
            " border-radius: 5px; padding: 3px 6px;"
        )

    def _pick(self) -> None:
        r, g, b, a = parse_color(self._value)
        initial = QColor()
        initial.setRgbF(r, g, b, a)
        color = QColorDialog.getColor(
            initial, self, "Choisir une couleur", QColorDialog.ColorDialogOption.ShowAlphaChannel
        )
        if color.isValid():
            self.set_value(format_color((color.redF(), color.greenF(), color.blueF(), color.alphaF())))
            for cb in self.changed:
                cb(self._value)


def common_properties(nodes: list[Node]) -> list[tuple[str, str, ParamSpec]]:
    """Propriétés éditables ensemble : transformation, apparence, puis paramètres et style partagés.

    Un paramètre de style ou de paramétrage est commun s'il existe, avec le même type, dans le catalogue
    de chacun des types d'objets sélectionnés (ex. « Remplissage » d'un cercle et d'un rectangle).
    """
    out: list[tuple[str, str, ParamSpec]] = [
        ("rotation_deg", BASE_LABELS["rotation_deg"], ParamSpec("r", "float", 0.0)),
        ("scale.x", BASE_LABELS["scale.x"], ParamSpec("sx", "float", 1.0, min=0.01)),
        ("scale.y", BASE_LABELS["scale.y"], ParamSpec("sy", "float", 1.0, min=0.01)),
        ("opacity", BASE_LABELS["opacity"], ParamSpec("o", "float", 1.0, min=0.0, max=1.0)),
        ("z_index", "Ordre (plan)", ParamSpec("z", "int", 0)),
        ("visible", BASE_LABELS["visible"], ParamSpec("v", "bool", True)),
        ("locked", "Verrouillé", ParamSpec("l", "bool", False)),
    ]
    specs = [KINDS[n.kind] for n in nodes if n.kind in KINDS]
    if not specs or len(specs) != len(nodes):
        return out
    for group in ("style", "params"):
        first = specs[0].style if group == "style" else specs[0].params
        for ps in first:
            if ps.type not in ("float", "int", "bool", "color"):
                continue
            if all(
                any(
                    o.name == ps.name and o.type == ps.type
                    for o in (s.style if group == "style" else s.params)
                )
                for s in specs[1:]
            ):
                out.append((f"{group}.{ps.name}", ps.label or ps.name, ps))
    return out


class InspectorDock(QWidget):
    def __init__(self, document: ProjectDocument, parent: QWidget | None = None):
        super().__init__(parent)
        self.document = document
        self._editors: dict[str, QWidget] = {}
        self._key_buttons: dict[str, QToolButton] = {}
        self._node_id: str | None = None
        self._multi_ids: list[str] = []  # sélection multiple : édition commune
        self._mixed_labels: dict[str, QLabel] = {}
        self._updating = False
        self.sources_button: QPushButton | None = None
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        outer.addWidget(self.scroll_area)
        self.body = QWidget()
        self.scroll_area.setWidget(self.body)
        self.form = QFormLayout(self.body)
        self.form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        document.selectionChanged.connect(lambda _s: self.rebuild())
        document.changed.connect(self.refresh_values)
        document.frameChanged.connect(lambda _f: self.refresh_values())
        document.sceneChanged.connect(lambda _s: self.rebuild())
        self.rebuild()

    # --- construction -----------------------------------------------------
    def _clear(self) -> None:
        while self.form.rowCount():
            self.form.removeRow(0)
        self._editors.clear()
        self._key_buttons.clear()
        self._mixed_labels.clear()
        self._multi_ids = []

    def rebuild(self) -> None:
        self._clear()
        sel = self.document.selected_nodes
        scene = self.document.scene
        if scene is None:
            return
        if len(sel) != 1:
            self._node_id = None
            if len(sel) > 1:
                self._build_multi_form(sel)
            else:
                self._build_scene_form(sel)
            return
        node = sel[0]
        self._node_id = node.id
        spec = KINDS.get(node.kind)
        title = QLabel(f"<b>{spec.label if spec else node.kind}</b>")
        self.form.addRow(title)
        self._add_editor("name", "Nom", ParamSpec("name", "str", node.name), node)
        self._add_editor("position.x", BASE_LABELS["position.x"], ParamSpec("x", "float", 0.0), node)
        self._add_editor("position.y", BASE_LABELS["position.y"], ParamSpec("y", "float", 0.0), node)
        self._add_editor("rotation_deg", BASE_LABELS["rotation_deg"], ParamSpec("r", "float", 0.0), node)
        self._add_editor("scale.x", BASE_LABELS["scale.x"], ParamSpec("sx", "float", 1.0, min=0.01), node)
        self._add_editor("scale.y", BASE_LABELS["scale.y"], ParamSpec("sy", "float", 1.0, min=0.01), node)
        self._add_editor(
            "opacity", BASE_LABELS["opacity"], ParamSpec("o", "float", 1.0, min=0.0, max=1.0), node
        )
        self._add_editor("z_index", "Ordre (plan)", ParamSpec("z", "int", 0), node)
        self._add_editor("visible", BASE_LABELS["visible"], ParamSpec("v", "bool", True), node)
        self._add_editor("locked", "Verrouillé", ParamSpec("l", "bool", False), node)
        if spec is not None:
            if spec.params:
                self.form.addRow(QLabel("<b>Paramètres</b>"))
                for ps in spec.params:
                    self._add_editor(f"params.{ps.name}", ps.label or ps.name, ps, node)
            if spec.style:
                self.form.addRow(QLabel("<b>Style</b>"))
                for ps in spec.style:
                    self._add_editor(f"style.{ps.name}", ps.label or ps.name, ps, node)
        self.refresh_values()

    def _build_multi_form(self, sel: list[Node]) -> None:
        """Propriétés communes à tous les objets sélectionnés ; une modification s'applique à chacun."""
        self._multi_ids = [n.id for n in sel]
        self.form.addRow(QLabel(f"<b>{len(sel)} objets sélectionnés</b>"))
        hint = QLabel(
            "Les modifications s'appliquent à tous (un seul Ctrl+Z les annule). « ≠ » : valeurs différentes."
        )
        hint.setWordWrap(True)
        hint.setProperty("role", "hint")
        self.form.addRow(hint)
        for path, label, spec in common_properties(sel):
            editor = self._make_editor(path, spec)
            mixed = QLabel("")
            mixed.setToolTip("Les objets sélectionnés ont des valeurs différentes")
            row = QWidget()
            lay = QHBoxLayout(row)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.addWidget(editor, 1)
            lay.addWidget(mixed)
            self._editors[path] = editor
            self._mixed_labels[path] = mixed
            self.form.addRow(label + " :", row)
        self.refresh_values()

    def _refresh_multi(self) -> None:
        scene = self.document.scene
        state = self.document.state()
        if scene is None or state is None:
            return
        nodes = [n for n in (scene.find_node(i) for i in self._multi_ids) if n is not None]
        if len(nodes) != len(self._multi_ids):
            self.rebuild()
            return
        self._updating = True
        try:
            for path, editor in self._editors.items():
                values = []
                for n in nodes:
                    try:
                        st: NodeState | None = state.node(n.id)
                    except KeyError:
                        st = None
                    values.append(self._current_value(n, st, path))
                self._set_editor(editor, values[0])
                self._mixed_labels[path].setText("≠" if any(v != values[0] for v in values) else "")
        finally:
            self._updating = False

    def _build_scene_form(self, sel: list[Node]) -> None:
        scene = self.document.scene
        if scene is None:
            return
        self.form.addRow(QLabel(f"<b>Scène : {scene.name}</b>"))
        name = QLineEdit(scene.name)
        name.editingFinished.connect(lambda: self._scene_attr("name", name.text().strip() or scene.name))
        self.form.addRow("Nom :", name)
        dur = QSpinBox()
        dur.setRange(1, 1_000_000)
        dur.setValue(scene.duration_frames)
        dur.setSuffix(" images")
        fps = float(self.document.project.canvas.fps)
        dur.setToolTip(f"{scene.duration_frames / fps:.2f} s à {fps:g} images/s")
        dur.editingFinished.connect(lambda: self._scene_attr("duration_frames", dur.value()))
        self.form.addRow("Durée :", dur)
        bg = ColorButton()
        bg.set_value(scene.background)
        bg.changed.append(lambda v: self._scene_attr("background", v))
        self.form.addRow("Fond :", bg)
        from antares_studio.rendering.transitions import TRANSITION_LABELS

        kind = QComboBox()
        kind.setObjectName("scene_transition")
        for k, label in TRANSITION_LABELS.items():
            kind.addItem(label, k)
        kind.setCurrentIndex(max(0, kind.findData(scene.transition.kind)))
        kind.setToolTip(
            "Entrée de la scène depuis la dernière image de la scène précédente (du noir pour la première)"
        )
        tr_dur = QSpinBox()
        tr_dur.setObjectName("scene_transition_duration")
        tr_dur.setRange(1, 600)
        tr_dur.setValue(scene.transition.duration_frames)
        tr_dur.setSuffix(" images")
        tr_dur.setToolTip(f"{scene.transition.duration_frames / fps:.2f} s ; prise sur le début de la scène")
        tr_dur.setEnabled(scene.transition.kind != "none")

        def set_transition() -> None:
            from antares_studio.domain.model import SceneTransition

            new = SceneTransition(str(kind.currentData()), int(tr_dur.value()))
            tr_dur.setEnabled(new.kind != "none")
            self._scene_attr("transition", new)

        kind.currentIndexChanged.connect(lambda _i: set_transition())
        tr_dur.editingFinished.connect(set_transition)
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(kind, 1)
        lay.addWidget(tr_dur)
        self.form.addRow("Transition :", row)
        c = self.document.project.canvas
        self.form.addRow(QLabel(f"Canevas : {c.width} × {c.height} px, {float(c.fps):g} images/s"))
        self._build_metadata_form()
        hint = QLabel("Sélectionnez un objet pour modifier ses propriétés.")
        hint.setWordWrap(True)
        self.form.addRow(hint)

    def _build_metadata_form(self) -> None:
        """Métadonnées scientifiques du projet (SCI-07/08) : représentation, échelle, notes, sources."""
        meta = self.document.project.scientific_metadata
        self.form.addRow(QLabel("<b>Métadonnées scientifiques</b>"))
        repr_box = QComboBox()
        # distinction du master prompt §9.3 : schématique / modélisation / simulation / données mesurées
        repr_box.addItem("Schématique (visuel arbitraire)", "schematic")
        repr_box.addItem("Modélisation (hypothèses explicites)", "model")
        repr_box.addItem("Simulation numérique (algorithme, pas, erreurs)", "simulation")
        repr_box.addItem("Données mesurées (source, incertitude)", "data")
        repr_box.addItem("À l'échelle", "to_scale")
        repr_box.addItem("Mixte (préciser dans les notes)", "mixed")
        idx = repr_box.findData(str(meta.get("representation", "schematic")))
        repr_box.setCurrentIndex(max(0, idx))
        repr_box.currentIndexChanged.connect(
            lambda _i: self._meta("representation", str(repr_box.currentData()))
        )
        self.form.addRow("Représentation :", repr_box)
        to_scale = QCheckBox("Distances et tailles à l'échelle")
        to_scale.setChecked(bool(meta.get("to_scale", False)))
        to_scale.setToolTip("Décoché : un avertissement « non à l'échelle » est attendu dans la vidéo.")
        to_scale.toggled.connect(lambda on: self._meta("to_scale", bool(on)))
        self.form.addRow("", to_scale)
        notes = QLineEdit(str(meta.get("notes", "")))
        notes.setPlaceholderText("Simplifications, hypothèses…")
        notes.editingFinished.connect(lambda: self._meta("notes", notes.text().strip()))
        self.form.addRow("Notes :", notes)
        sources = meta.get("sources", [])
        n = len(sources) if isinstance(sources, list) else 0
        self.sources_button = QPushButton(f"Sources… ({n})")
        self.sources_button.setToolTip(
            "\n".join(
                f"{s.get('label', '')} {s.get('url', '')}".strip()
                for s in (sources if isinstance(sources, list) else [])
                if isinstance(s, dict)
            )
            or "Aucune source référencée"
        )
        self.sources_button.clicked.connect(self._edit_sources)
        self.form.addRow("Sources :", self.sources_button)

    def _refresh_metadata(self) -> None:
        button = getattr(self, "sources_button", None)
        if button is None:
            return
        sources = self.document.project.scientific_metadata.get("sources", [])
        n = len(sources) if isinstance(sources, list) else 0
        try:
            button.setText(f"Sources… ({n})")
        except RuntimeError:  # bouton détruit par une reconstruction du formulaire
            self.sources_button = None

    def _data_columns(self) -> list[str]:
        """Noms de colonnes du CSV lié au graphique sélectionné (vide si aucune donnée)."""
        scene = self.document.scene
        node = scene.find_node(self._node_id) if scene and self._node_id else None
        if node is None or node.kind != "chart":
            return []
        path = self.document.resolve_asset(str(node.params.get("data_asset_id", "")))
        if path is None:
            return []
        from antares_studio.science.data import DataError, load_csv

        try:
            return [c.name for c in load_csv(path).columns]
        except (DataError, OSError):
            return []

    def _meta(self, key: str, value: Any) -> None:
        if self.document.project.scientific_metadata.get(key) == value:
            return
        self.document.push(SetProjectMetadata(key, value))

    def _edit_sources(self) -> None:
        from antares_studio.app.provenance_dialog import SourcesDialog

        SourcesDialog(self.document, self).exec()
        self.rebuild()

    def _scene_attr(self, attr: str, value: Any) -> None:
        scene = self.document.scene
        if scene is None or getattr(scene, attr) == value:
            return
        self.document.push(SetSceneProperty(scene.id, attr, value))

    def _add_editor(self, path: str, label: str, spec: ParamSpec, node: Node) -> None:
        editor = self._make_editor(path, spec)
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(editor, 1)
        if is_animatable(node, path):
            key = QToolButton()
            key.setText("◆")
            key.setCheckable(True)
            key.setToolTip(
                "Image clé à l'image courante (clic : poser/retirer ; clic droit : supprimer l'animation)"
            )
            key.setFixedWidth(24)
            key.clicked.connect(lambda _c=False, p=path: self._toggle_key(p))
            key.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            key.customContextMenuRequested.connect(lambda _pos, p=path: self._remove_track(p))
            self._key_buttons[path] = key
            lay.addWidget(key)
        self._editors[path] = editor
        self.form.addRow(label + " :", row)

    def _make_editor(self, path: str, spec: ParamSpec) -> QWidget:
        t = spec.type
        if t == "float":
            sb = QDoubleSpinBox()
            sb.setRange(spec.min if spec.min is not None else -1e6, spec.max if spec.max is not None else 1e6)
            sb.setDecimals(2)
            sb.setSingleStep(0.1 if path.startswith("scale") or path == "opacity" else 1.0)
            sb.setKeyboardTracking(False)
            sb.valueChanged.connect(lambda v, p=path: self._commit(p, float(v)))
            return sb
        if t == "int":
            sb2 = QSpinBox()
            sb2.setRange(
                int(spec.min) if spec.min is not None else -100000,
                int(spec.max) if spec.max is not None else 100000,
            )
            sb2.setKeyboardTracking(False)
            sb2.valueChanged.connect(lambda v, p=path: self._commit(p, int(v)))
            return sb2
        if t == "bool":
            cb = QCheckBox()
            cb.toggled.connect(lambda v, p=path: self._commit(p, bool(v)))
            return cb
        if t == "color":
            btn = ColorButton()
            btn.changed.append(lambda v, p=path: self._commit(p, v))
            return btn
        if t == "vec2":
            w = QWidget()
            lay = QHBoxLayout(w)
            lay.setContentsMargins(0, 0, 0, 0)
            xs, ys = QDoubleSpinBox(), QDoubleSpinBox()
            for s in (xs, ys):
                s.setRange(-1e6, 1e6)
                s.setDecimals(1)
                s.setKeyboardTracking(False)
                lay.addWidget(s)
            xs.valueChanged.connect(lambda _v, p=path: self._commit(p, [xs.value(), ys.value()]))
            ys.valueChanged.connect(lambda _v, p=path: self._commit(p, [xs.value(), ys.value()]))
            w.setProperty("xs", xs)
            w.setProperty("ys", ys)
            return w
        if spec.choices:
            choice = QComboBox()
            for value, text in spec.choices:
                choice.addItem(text, value)
            choice.currentIndexChanged.connect(lambda _i, p=path: self._commit(p, choice.currentData()))
            return choice
        if path == "params.text":
            te = QPlainTextEdit()
            te.setMaximumHeight(80)
            te.textChanged.connect(lambda p=path: self._commit_text(p, te))
            return te
        if path == "params.align":
            combo = QComboBox()
            combo.addItem("Centré", "center")
            combo.addItem("Gauche", "left")
            combo.addItem("Droite", "right")
            combo.currentIndexChanged.connect(lambda _i, p=path: self._commit(p, combo.currentData()))
            return combo
        if path in ASSET_PARAMS:
            combo = QComboBox()
            wanted, empty = ASSET_PARAMS[path]
            combo.addItem(empty, "")
            for a in self.document.project.assets:
                if a.kind == wanted:
                    combo.addItem(a.path, a.id)
            combo.currentIndexChanged.connect(lambda _i, p=path: self._commit(p, combo.currentData()))
            return combo
        if path in ("params.x_column", "params.y_column"):
            combo = QComboBox()
            combo.setEditable(True)
            for name in self._data_columns():
                combo.addItem(name, name)
            combo.currentTextChanged.connect(lambda text, p=path: self._commit(p, text))
            return combo
        if t == "points":
            lab = QLabel("(édition des sommets : version ultérieure)")
            return lab
        le = QLineEdit()
        le.editingFinished.connect(lambda p=path: self._commit(p, le.text()))
        return le

    # --- synchronisation --------------------------------------------------
    def refresh_values(self) -> None:
        if self._multi_ids:
            self._refresh_multi()
            return
        if self._node_id is None:
            self._refresh_metadata()
            return
        scene = self.document.scene
        state = self.document.state()
        if scene is None or state is None:
            return
        node = scene.find_node(self._node_id)
        if node is None:
            self.rebuild()
            return
        if node.kind == "chart":
            # les colonnes dépendent du CSV lié : reconstruire quand les données arrivent ou changent
            combo = self._editors.get("params.x_column")
            if isinstance(combo, QComboBox):
                cols = self._data_columns()
                current = [combo.itemText(i) for i in range(combo.count())]
                if cols != current:
                    self.rebuild()
                    return
        try:
            st: NodeState | None = state.node(node.id)
        except KeyError:
            st = None
        self._updating = True
        try:
            for path, editor in self._editors.items():
                value = self._current_value(node, st, path)
                self._set_editor(editor, value)
            for path, btn in self._key_buttons.items():
                track = scene.track_for(node.id, path)
                has_track = track is not None and bool(track.keyframes)
                on_key = has_track and any(k.frame == self.document.frame for k in track.keyframes)  # type: ignore[union-attr]
                btn.setChecked(on_key)
                color = (
                    theme.KEYFRAME_SELECTED.name()
                    if on_key
                    else theme.KEYFRAME.name()
                    if has_track
                    else theme.TEXT_MUTED.name()
                )
                btn.setStyleSheet(f"color: {color}; font-weight: bold;")
        finally:
            self._updating = False

    def _current_value(self, node: Node, st: NodeState | None, path: str) -> Any:
        if st is not None:
            if path == "position.x":
                return st.position[0]
            if path == "position.y":
                return st.position[1]
            if path == "rotation_deg":
                return st.rotation_deg
            if path == "scale.x":
                return st.scale[0]
            if path == "scale.y":
                return st.scale[1]
            if path == "opacity":
                return st.opacity
            if path.startswith("params."):
                return st.params.get(path[7:])
            if path.startswith("style."):
                return st.style.get(path[6:])
        if path == "name":
            return node.name
        if path == "visible":
            return node.visible
        if path == "locked":
            return node.locked
        if path == "z_index":
            return node.z_index
        from antares_studio.domain.properties import get_property

        try:
            return get_property(node, path)
        except KeyError:
            return None

    def _set_editor(self, editor: QWidget, value: Any) -> None:
        if isinstance(editor, QDoubleSpinBox):
            if value is not None:
                editor.setValue(float(value))
        elif isinstance(editor, QSpinBox):
            if value is not None:
                editor.setValue(int(value))
        elif isinstance(editor, QCheckBox):
            editor.setChecked(bool(value))
        elif isinstance(editor, ColorButton):
            editor.set_value(str(value) if value else "#FFFFFF")
        elif isinstance(editor, QPlainTextEdit):
            if editor.toPlainText() != str(value or ""):
                editor.setPlainText(str(value or ""))
        elif isinstance(editor, QComboBox):
            idx = editor.findData(value)
            if idx < 0 and editor.isEditable():
                editor.setCurrentText(str(value or ""))
            else:
                editor.setCurrentIndex(max(0, idx))
        elif isinstance(editor, QLineEdit):
            editor.setText(str(value or ""))
        elif editor.property("xs") is not None and isinstance(value, list) and len(value) == 2:
            editor.property("xs").setValue(float(value[0]))
            editor.property("ys").setValue(float(value[1]))

    def _commit(self, path: str, value: Any) -> None:
        if self._updating:
            return
        scene = self.document.scene
        if scene is None:
            return
        if self._multi_ids:
            try:
                with self.document.macro(f"Modifier {len(self._multi_ids)} objets"):
                    for nid in self._multi_ids:
                        if scene.find_node(nid) is not None:
                            self.document.set_node_property(nid, path, value)
            except ValueError:
                self.refresh_values()
            return
        if self._node_id is None:
            return
        node = scene.find_node(self._node_id)
        if node is None:
            return
        try:
            self.document.set_node_property(node.id, path, value)
        except ValueError:
            self.refresh_values()

    def _commit_text(self, path: str, editor: QPlainTextEdit) -> None:
        if self._updating:
            return
        self._commit(path, editor.toPlainText())

    def _toggle_key(self, path: str) -> None:
        scene = self.document.scene
        if scene is None or self._node_id is None:
            return
        node = scene.find_node(self._node_id)
        if node is None:
            return
        track = scene.track_for(node.id, path)
        frame = self.document.frame
        if track is not None and any(k.frame == frame for k in track.keyframes):
            self.document.push(RemoveKeyframe(scene.id, node.id, path, frame))
        else:
            state = self.document.state()
            st = state.node(node.id) if state else None
            value = self._current_value(node, st, path)
            self.document.push(SetKeyframe(scene.id, node.id, path, frame, value))

    def _remove_track(self, path: str) -> None:
        scene = self.document.scene
        if scene is None or self._node_id is None:
            return
        if scene.track_for(self._node_id, path) is not None:
            self.document.push(RemoveTrack(scene.id, self._node_id, path))
