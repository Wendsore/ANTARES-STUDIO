"""Centre d'aide : sommaire, recherche plein texte, rubriques Markdown locales, navigation et liens.

Hors ligne : les rubriques viennent de ``resources/help`` (voir ``antares_studio.help.topics``). Les
liens web s'ouvrent dans le navigateur du système ; les liens entre rubriques restent dans la fenêtre.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QSize, Qt, QUrl, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QDesktopServices,
    QFont,
    QImage,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
    QTextFrameFormat,
    QTextLength,
    QTextTable,
)
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSplitter,
    QTextBrowser,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from antares_studio.app import icons, theme
from antares_studio.help import topics

TOPIC_ROLE = Qt.ItemDataRole.UserRole + 1


def style_help_document(doc: QTextDocument) -> None:
    """Met en forme un document issu du Markdown : titres aérés, interligne, tableaux lisibles."""
    p = theme.active()
    doc.setDocumentMargin(22)
    cursor = QTextCursor(doc)
    block = doc.begin()
    while block.isValid():
        fmt = block.blockFormat()
        level = fmt.headingLevel()
        cursor.setPosition(block.position())
        if level:
            fmt.setTopMargin({1: 4, 2: 22, 3: 16}.get(level, 12))
            fmt.setBottomMargin(8 if level == 1 else 6)
            cursor.setBlockFormat(fmt)
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
            ch = QTextCharFormat()
            ch.setForeground(QBrush(QColor(p.accent if level == 1 else p.text)))
            ch.setFontPointSize(theme.scaled_pt({1: 20, 2: 15, 3: 12.5}.get(level, 12)))
            ch.setFontWeight(QFont.Weight.Bold)
            cursor.mergeCharFormat(ch)
        elif cursor.currentTable() is None:
            fmt.setLineHeight(135, 1)  # 1 = QTextBlockFormat.LineHeightTypes.ProportionalHeight
            if fmt.bottomMargin() < 6:
                fmt.setBottomMargin(6)
            cursor.setBlockFormat(fmt)
        block = block.next()
    for frame in doc.rootFrame().childFrames():
        if isinstance(frame, QTextTable):
            _style_table(frame)


def _style_table(table: QTextTable) -> None:
    p = theme.active()
    fmt = table.format()
    fmt.setBorder(1)
    fmt.setBorderBrush(QBrush(QColor(p.border)))
    fmt.setBorderStyle(QTextFrameFormat.BorderStyle.BorderStyle_Solid)
    fmt.setCellPadding(6)
    fmt.setCellSpacing(0)
    fmt.setTopMargin(6)
    fmt.setBottomMargin(10)
    fmt.setWidth(QTextLength(QTextLength.Type.PercentageLength, 100))
    table.setFormat(fmt)
    for col in range(table.columns()):
        cell = table.cellAt(0, col)
        cf = cell.format()
        cf.setBackground(QBrush(QColor(p.raised)))
        cell.setFormat(cf)


class HelpBrowser(QTextBrowser):
    """Affiche une rubrique ; les images sont mises à la largeur de la fenêtre."""

    def loadResource(self, rtype: int, name: QUrl | str) -> Any:  # noqa: N802 (API Qt)
        if rtype == int(QTextDocument.ResourceType.ImageResource.value):
            path = topics.HELP_DIR / (name.toString() if isinstance(name, QUrl) else str(name))
            if path.is_file() and topics.HELP_DIR in path.resolve().parents:
                img = QImage(str(path))
                max_w = max(200, self.viewport().width() - 60)
                if img.width() > max_w:
                    img = img.scaledToWidth(max_w, Qt.TransformationMode.SmoothTransformation)
                return img
            return None
        return super().loadResource(rtype, name)


class HelpCenter(QDialog):
    """Fenêtre d'aide non modale. ``extra`` fournit les sections dynamiques (raccourcis…)."""

    topicShown = Signal(str)

    def __init__(self, extra: Callable[[], dict[str, str]] | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("help_center")
        self.setWindowTitle("Centre d'aide — ANTARES Studio")
        self.setWindowIcon(icons.app_icon())
        self.setModal(False)
        self.resize(1080, 760)
        self._extra = extra or (lambda: {})
        self._history: list[str] = []
        self._pos = -1
        self.current_topic = ""

        top = QHBoxLayout()
        self.back_btn = QToolButton()
        self.back_btn.setIcon(icons.icon("chevron-left"))
        self.back_btn.setToolTip("Rubrique précédente (Alt+←)")
        self.back_btn.setShortcut("Alt+Left")
        self.back_btn.clicked.connect(self.back)
        self.fwd_btn = QToolButton()
        self.fwd_btn.setIcon(icons.icon("chevron-right"))
        self.fwd_btn.setToolTip("Rubrique suivante (Alt+→)")
        self.fwd_btn.setShortcut("Alt+Right")
        self.fwd_btn.clicked.connect(self.forward)
        self.home_btn = QToolButton()
        self.home_btn.setIcon(icons.icon("house"))
        self.home_btn.setToolTip("Bienvenue")
        self.home_btn.clicked.connect(lambda: self.show_topic(topics.DEFAULT_TOPIC))
        self.search = QLineEdit()
        self.search.setObjectName("help_search")
        self.search.setPlaceholderText("Rechercher dans l'aide (ex. : orbite, sous-titres, export)…")
        self.search.setClearButtonEnabled(True)
        self.search.addAction(icons.icon("search"), QLineEdit.ActionPosition.LeadingPosition)
        self.search.textChanged.connect(self._on_search)
        for w in (self.back_btn, self.fwd_btn, self.home_btn):
            w.setIconSize(QSize(20, 20))
            top.addWidget(w)
        top.addWidget(self.search, 1)

        self.tree = QTreeWidget()
        self.tree.setObjectName("help_tree")
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(14)
        self.tree.itemActivated.connect(self._on_item)
        self.tree.itemClicked.connect(self._on_item)
        self.results_label = QLabel("")
        self.results_label.setProperty("role", "hint")
        self.results_label.setWordWrap(True)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.addWidget(self.results_label)
        ll.addWidget(self.tree, 1)

        self.browser = HelpBrowser()
        self.browser.setObjectName("help_browser")
        self.browser.setOpenLinks(False)
        self.browser.anchorClicked.connect(self._on_link)

        split = QSplitter()
        split.addWidget(left)
        split.addWidget(self.browser)
        split.setStretchFactor(1, 1)
        split.setSizes([290, 790])

        lay = QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(split, 1)
        self._fill_tree()
        self._update_nav()

    # --- sommaire et recherche ------------------------------------------------------------------
    def _fill_tree(self) -> None:
        self.tree.clear()
        self.results_label.setText("")
        self.results_label.setVisible(False)
        for section, items in topics.sections():
            head = QTreeWidgetItem([section])
            head.setFlags(Qt.ItemFlag.ItemIsEnabled)
            f = head.font(0)
            f.setBold(True)
            head.setFont(0, f)
            self.tree.addTopLevelItem(head)
            for t in items:
                child = QTreeWidgetItem([t.title])
                child.setData(0, TOPIC_ROLE, t.id)
                head.addChild(child)
            head.setExpanded(True)
        self._select_current()

    def _on_search(self, text: str) -> None:
        q = text.strip()
        if len(q) < 2:
            self._fill_tree()
            return
        results = topics.search(q, self._extra())
        self.tree.clear()
        self.results_label.setVisible(True)
        if not results:
            self.results_label.setText(f"Aucune rubrique ne contient « {q} ». Essayez un mot plus court.")
            return
        self.results_label.setText(f"{len(results)} rubrique(s) pour « {q} » :")
        for t, _score in results:
            item = QTreeWidgetItem([t.title])
            item.setData(0, TOPIC_ROLE, t.id)
            item.setToolTip(0, topics.snippet(t.id, q))
            self.tree.addTopLevelItem(item)
        first = self.tree.topLevelItem(0)
        if first is not None:
            self.tree.setCurrentItem(first)

    def _on_item(self, item: QTreeWidgetItem, _col: int = 0) -> None:
        topic_id = item.data(0, TOPIC_ROLE)
        if topic_id:
            self.show_topic(str(topic_id))

    def _select_current(self) -> None:
        it = self._find_item(self.current_topic)
        if it is not None:
            self.tree.blockSignals(True)
            self.tree.setCurrentItem(it)
            self.tree.blockSignals(False)

    def _find_item(self, topic_id: str) -> QTreeWidgetItem | None:
        stack = [self.tree.topLevelItem(i) for i in range(self.tree.topLevelItemCount())]
        while stack:
            it = stack.pop()
            if it is None:
                continue
            if it.data(0, TOPIC_ROLE) == topic_id:
                return it
            stack.extend(it.child(i) for i in range(it.childCount()))
        return None

    # --- affichage et navigation ----------------------------------------------------------------
    def show_topic(self, topic_id: str, record: bool = True) -> None:
        if topic_id not in topics.TOPICS_BY_ID:
            topic_id = topics.DEFAULT_TOPIC
        md = topics.topic_markdown(topic_id, self._extra())
        self.browser.document().clear()
        self.browser.setMarkdown(md)
        style_help_document(self.browser.document())
        self.browser.verticalScrollBar().setValue(0)
        self.current_topic = topic_id
        if record:
            del self._history[self._pos + 1 :]
            self._history.append(topic_id)
            self._pos = len(self._history) - 1
        self._select_current()
        self._update_nav()
        self.topicShown.emit(topic_id)

    def back(self) -> None:
        if self._pos > 0:
            self._pos -= 1
            self.show_topic(self._history[self._pos], record=False)

    def forward(self) -> None:
        if self._pos + 1 < len(self._history):
            self._pos += 1
            self.show_topic(self._history[self._pos], record=False)

    def _update_nav(self) -> None:
        self.back_btn.setEnabled(self._pos > 0)
        self.fwd_btn.setEnabled(self._pos + 1 < len(self._history))

    def _on_link(self, url: QUrl) -> None:
        if url.scheme() in ("http", "https", "mailto"):
            QDesktopServices.openUrl(url)
            return
        target = url.path().rsplit("/", 1)[-1].removesuffix(".md")
        if target in topics.TOPICS_BY_ID:
            self.show_topic(target)

    def restyle(self) -> None:
        """Après un changement de thème : icônes et mise en forme de la rubrique courante."""
        self.back_btn.setIcon(icons.icon("chevron-left"))
        self.fwd_btn.setIcon(icons.icon("chevron-right"))
        self.home_btn.setIcon(icons.icon("house"))
        if self.current_topic:
            self.show_topic(self.current_topic, record=False)
