"""
Interface graphique principale — Thème sombre ultra-professionnel.
Architecture : QMainWindow avec deux panneaux (logs | diagnostic IA).
"""
import os
import threading
import json
from datetime import datetime

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QTextEdit,
    QFrame, QSplitter, QProgressBar, QStatusBar,
    QScrollArea, QSizePolicy, QApplication,
    QListWidget, QListWidgetItem,
)
from PySide6.QtCore import Qt, QThread, Signal, QObject, QTimer, QSize, QPoint
from PySide6.QtGui import (
    QFont, QColor, QTextCharFormat, QSyntaxHighlighter,
    QTextDocument, QPalette, QIcon, QLinearGradient, QGradient,
)
from app.models.log_parser import STM32LogParser

# ──────────────────────────────────────────────
# PALETTE DE COULEURS
# ──────────────────────────────────────────────
C_BG_DEEP    = "#1E1E1E"   # Fond principal (gris sombre)
C_BG_PANEL   = "#181818"   # Fond des panneaux (plus sombre)
C_BG_CARD    = "#252526"   # Fond des cartes / boutons / en-tête
C_BORDER     = "#2D2D2D"   # Bordures
C_ACCENT     = "#00D4FF"   # Bleu cyan (accent principal)
C_ACCENT2    = "#7C3AED"   # Violet (accent secondaire)
C_SUCCESS    = "#3FB950"   # Vert (OK / INFO)
C_WARNING    = "#D29922"   # Jaune (WARNING)
C_ERROR      = "#F85149"   # Rouge (ERROR)
C_TEXT_MAIN  = "#E6EDF3"   # Texte principal
C_TEXT_DIM   = "#8B949E"   # Texte secondaire / grisé
C_HEADER_BG  = "#1E1E1E"   # Fond de l'en-tête


# ──────────────────────────────────────────────
# WORKER — exécute l'analyse dans un thread séparé
# (pour ne pas bloquer l'interface pendant l'IA)
# ──────────────────────────────────────────────
class AnalysisWorker(QObject):
    progress = Signal(int, str)   # (étape 1-4, message)
    finished = Signal(dict)        # résultats complets
    error    = Signal(str)

    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path

    def run(self):
        try:
            from app.controllers.analysis_controller import AnalysisController
            ctrl = AnalysisController()
            result = ctrl.run_full_analysis(
                self.file_path,
                progress_callback=lambda step, msg: self.progress.emit(step, msg)
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


# ──────────────────────────────────────────────
# SYNTAX HIGHLIGHTER — pour le panneau de logs
# ──────────────────────────────────────────────
class LogHighlighter(QSyntaxHighlighter):
    def __init__(self, document: QTextDocument):
        super().__init__(document)

        self.fmt_error   = QTextCharFormat()
        self.fmt_error.setForeground(QColor(C_ERROR))

        self.fmt_warning = QTextCharFormat()
        self.fmt_warning.setForeground(QColor(C_WARNING))

        self.fmt_info    = QTextCharFormat()
        self.fmt_info.setForeground(QColor(C_TEXT_DIM))

        self.fmt_ts      = QTextCharFormat()
        self.fmt_ts.setForeground(QColor(C_ACCENT))

    def highlightBlock(self, text: str):
        # Timestamp au début (ex: 10:42:06)
        import re
        for m in re.finditer(r"^\d{2}:\d{2}:\d{2}", text):
            self.setFormat(m.start(), m.end() - m.start(), self.fmt_ts)

        if "Error:" in text or "ERROR" in text:
            self.setFormat(0, len(text), self.fmt_error)
        elif "Warning:" in text or "WARNING" in text:
            self.setFormat(0, len(text), self.fmt_warning)
        else:
            self.setFormat(0, len(text), self.fmt_info)


# ──────────────────────────────────────────────
# WIDGET — Carte de statistique (chiffre + label)
# ──────────────────────────────────────────────
class StatCard(QFrame):
    def __init__(self, icon: str, value: str, label: str, color: str):
        super().__init__()
        self.setFixedHeight(80)
        self.setStyleSheet(f"""
            QFrame {{
                background: {C_BG_CARD};
                border: 1px solid {C_BORDER};
                border-left: 3px solid {color};
                border-radius: 8px;
            }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 8, 14, 8)
        lay.setSpacing(2)

        top = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(f"color: {color}; font-size: 18px; border: none;")
        self.value_lbl = QLabel(value)
        self.value_lbl.setStyleSheet(f"color: {C_TEXT_MAIN}; font-size: 22px; font-weight: bold; border: none;")
        top.addWidget(icon_lbl)
        top.addStretch()
        top.addWidget(self.value_lbl)

        self.label_lbl = QLabel(label)
        self.label_lbl.setStyleSheet(f"color: {C_TEXT_DIM}; font-size: 11px; border: none;")

        lay.addLayout(top)
        lay.addWidget(self.label_lbl)

    def update_value(self, value: str):
        self.value_lbl.setText(value)


# ──────────────────────────────────────────────
# CUSTOM TITLE BAR (macOS-style dots + center title)
# ──────────────────────────────────────────────
class TitleBar(QFrame):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.setFixedHeight(35)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {C_BG_DEEP};
                border-bottom: 1px solid {C_BORDER};
            }}
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(15, 0, 15, 0)
        lay.setSpacing(8)

        # Boutons de contrôle macOS-style
        self.btn_close = QPushButton()
        self.btn_close.setFixedSize(12, 12)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background-color: #FF5F56;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #E04F47;
            }
        """)
        self.btn_close.clicked.connect(self.parent.close)

        self.btn_min = QPushButton()
        self.btn_min.setFixedSize(12, 12)
        self.btn_min.setCursor(Qt.PointingHandCursor)
        self.btn_min.setStyleSheet("""
            QPushButton {
                background-color: #FFBD2E;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #DCA323;
            }
        """)
        self.btn_min.clicked.connect(self.parent.showMinimized)

        self.btn_max = QPushButton()
        self.btn_max.setFixedSize(12, 12)
        self.btn_max.setCursor(Qt.PointingHandCursor)
        self.btn_max.setStyleSheet("""
            QPushButton {
                background-color: #27C93F;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1EA030;
            }
        """)
        self.btn_max.clicked.connect(self._toggle_maximize)

        lay.addWidget(self.btn_close)
        lay.addWidget(self.btn_min)
        lay.addWidget(self.btn_max)

        lay.addStretch(1)

        # Titre centré
        self.title_lbl = QLabel("STM32 Log Analyzer — Outil IA de diagnostic")
        self.title_lbl.setStyleSheet(f"color: {C_TEXT_MAIN}; font-size: 12px; font-weight: bold;")
        lay.addWidget(self.title_lbl)

        lay.addStretch(1)

        # Espaceur pour équilibrer la barre de titre
        spacer = QWidget()
        spacer.setFixedWidth(52)
        lay.addWidget(spacer)

        # Variables de déplacement de la fenêtre
        self.drag_active = False
        self.drag_position = QPoint()

    def _toggle_maximize(self):
        if self.parent.isMaximized():
            self.parent.showNormal()
        else:
            self.parent.showMaximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_active = True
            self.drag_position = event.globalPosition().toPoint() - self.parent.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.drag_active and event.buttons() == Qt.LeftButton:
            self.parent.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_active = False

    def mouseDoubleClickEvent(self, event):
        self._toggle_maximize()
        event.accept()


# ──────────────────────────────────────────────
# FENÊTRE PRINCIPALE
# ──────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("STM32 Log Analyzer — Outil IA de diagnostic")
        self.setMinimumSize(1280, 800)
        self.setWindowFlags(Qt.FramelessWindowHint) # Fenêtre sans bordures
        self._current_file = None
        self._worker_thread = None
        self.parser = STM32LogParser() # Parser local pour l'affichage direct

        # Création des StatCards en arrière-plan pour éviter de casser des références
        self.stat_lines    = StatCard("📄", "—", "Lignes lues",     C_ACCENT)
        self.stat_errors   = StatCard("❌", "—", "Erreurs détectées", C_ERROR)
        self.stat_warnings = StatCard("⚠️",  "—", "Avertissements",   C_WARNING)
        self.stat_status   = StatCard("🔬", "—", "Statut analyse",   C_ACCENT2)

        self._apply_dark_theme()
        self._build_ui()
        self._refresh_history()

    # ── THÈME GLOBAL ─────────────────────────
    def _apply_dark_theme(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {C_BG_DEEP};
                color: {C_TEXT_MAIN};
                font-family: 'Segoe UI', 'Inter', sans-serif;
                font-size: 13px;
            }}
            QSplitter::handle {{
                background: {C_BORDER};
                width: 1px;
            }}
            QScrollBar:vertical {{
                background: {C_BG_PANEL};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {C_BORDER};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {C_ACCENT};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QStatusBar {{
                background: {C_BG_PANEL};
                color: {C_TEXT_DIM};
                border-top: 1px solid {C_BORDER};
                font-size: 12px;
                padding: 2px 10px;
            }}
        """)

    # ── CONSTRUCTION DE L'UI ─────────────────
    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        root_lay = QVBoxLayout(root)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        # En-tête / Barre de titre macOS-style
        self.title_bar = TitleBar(self)
        root_lay.addWidget(self.title_bar)

        # Barre d'outils
        root_lay.addWidget(self._make_toolbar())

        # Barre de progression (cachée par défaut)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 4)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {C_BG_PANEL};
                border: none;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {C_ACCENT2}, stop:1 {C_ACCENT});
                border-radius: 0px;
            }}
        """)
        self.progress_bar.setVisible(False)
        root_lay.addWidget(self.progress_bar)

        # Splitter central : Historique | Logs bruts | Diagnostic IA
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._make_history_panel())
        splitter.addWidget(self._make_log_panel())
        splitter.addWidget(self._make_diag_panel())
        splitter.setSizes([220, 480, 580])
        root_lay.addWidget(splitter, stretch=1)

        # Status bar
        self.status = QStatusBar()
        self.status.setSizeGripEnabled(True) # Activer la poignée de redimensionnement native
        self.setStatusBar(self.status)
        self.status.showMessage("Prêt  •  Chargez un fichier de log STM32 pour commencer")

        # Raccorder la connexion de statut à l'IHM
        self._status_label = QLabel("🟢 Connecté à l'API Groq")
        self._status_label.setStyleSheet(f"color: {C_TEXT_DIM}; border: none; font-size: 11px;")
        self.status.addWidget(self._status_label)

    # ── BARRE D'OUTILS ───────────────────────
    def _make_toolbar(self) -> QWidget:
        bar = QFrame()
        bar.setFixedHeight(50)
        bar.setStyleSheet(f"""
            QFrame {{
                background: {C_BG_CARD};
                border-bottom: 1px solid {C_BORDER};
            }}
        """)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(15, 5, 15, 5)
        lay.setSpacing(10)

        # Bouton Charger
        self.btn_load = QPushButton("  📁  Charger log")
        self.btn_load.setFixedHeight(34)
        self.btn_load.setCursor(Qt.PointingHandCursor)
        self.btn_load.setStyleSheet(f"""
            QPushButton {{
                background: {C_BG_PANEL};
                color: {C_TEXT_MAIN};
                border: 1px solid {C_BORDER};
                border-radius: 6px;
                padding: 0 12px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: #2D2D2D;
                border-color: {C_ACCENT};
                color: {C_ACCENT};
            }}
            QPushButton:pressed {{
                background: #181818;
            }}
        """)
        self.btn_load.clicked.connect(self._on_load_file)

        # Bouton Analyser (désactivé jusqu'au chargement)
        self.btn_analyze = QPushButton("  ⚙️  Analyser avec IA")
        self.btn_analyze.setFixedHeight(34)
        self.btn_analyze.setEnabled(False)
        self.btn_analyze.setCursor(Qt.PointingHandCursor)
        self.btn_analyze.setStyleSheet(self._btn_primary_style())
        self.btn_analyze.clicked.connect(self._on_analyze)

        # Bouton Export JSON
        self.btn_export = QPushButton("  📥  Exporter JSON")
        self.btn_export.setFixedHeight(34)
        self.btn_export.setEnabled(False)
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.setStyleSheet(f"""
            QPushButton {{
                background: {C_BG_PANEL};
                color: {C_TEXT_MAIN};
                border: 1px solid {C_BORDER};
                border-radius: 6px;
                padding: 0 12px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:enabled:hover {{
                background: #2D2D2D;
                border-color: {C_SUCCESS};
                color: {C_SUCCESS};
            }}
            QPushButton:disabled {{
                background: {C_BG_PANEL};
                color: #555555;
                border: 1px solid {C_BORDER};
            }}
        """)
        self.btn_export.clicked.connect(self._on_open_report)

        # Label fichier sélectionné
        self.lbl_file = QLabel("Aucun fichier sélectionné")
        self.lbl_file.setStyleSheet(f"color: {C_TEXT_DIM}; font-style: italic; border: none; font-size: 11px;")

        lay.addWidget(self.btn_load)
        lay.addWidget(self.btn_analyze)
        lay.addWidget(self.btn_export)
        lay.addWidget(self.lbl_file)
        lay.addStretch()

        # Badges de statistiques à droite
        self.lbl_badge_errors = QLabel("0 erreurs")
        self.lbl_badge_errors.setContentsMargins(10, 4, 10, 4)
        self.lbl_badge_errors.setStyleSheet(f"""
            QLabel {{
                background-color: rgba(248, 81, 73, 0.15);
                border: 1px solid rgba(248, 81, 73, 0.4);
                color: #FF7B72;
                border-radius: 11px;
                font-size: 11px;
                font-weight: bold;
            }}
        """)
        self.lbl_badge_errors.setVisible(False)

        self.lbl_badge_warnings = QLabel("0 warnings")
        self.lbl_badge_warnings.setContentsMargins(10, 4, 10, 4)
        self.lbl_badge_warnings.setStyleSheet(f"""
            QLabel {{
                background-color: rgba(210, 153, 34, 0.15);
                border: 1px solid rgba(210, 153, 34, 0.4);
                color: #F2CC60;
                border-radius: 11px;
                font-size: 11px;
                font-weight: bold;
            }}
        """)
        self.lbl_badge_warnings.setVisible(False)

        self.lbl_badge_board = QLabel("Board: —")
        self.lbl_badge_board.setContentsMargins(10, 4, 10, 4)
        self.lbl_badge_board.setStyleSheet(f"""
            QLabel {{
                background-color: rgba(63, 185, 80, 0.15);
                border: 1px solid rgba(63, 185, 80, 0.4);
                color: #7EE787;
                border-radius: 11px;
                font-size: 11px;
                font-weight: bold;
            }}
        """)
        self.lbl_badge_board.setVisible(False)

        lay.addWidget(self.lbl_badge_errors)
        lay.addWidget(self.lbl_badge_warnings)
        lay.addWidget(self.lbl_badge_board)

        return bar

    def _btn_primary_style(self, enabled=True) -> str:
        return f"""
            QPushButton {{
                background: {C_BG_PANEL};
                color: {C_TEXT_MAIN};
                border: 1px solid {C_BORDER};
                border-radius: 6px;
                padding: 0 12px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover:enabled {{
                background: #2D2D2D;
                border-color: {C_ACCENT};
                color: {C_ACCENT};
            }}
            QPushButton:disabled {{
                background: {C_BG_PANEL};
                color: #555555;
                border: 1px solid {C_BORDER};
            }}
        """

    # ── PANNEAU HISTORIQUE ───────────────────
    def _make_history_panel(self) -> QWidget:
        panel = QFrame()
        panel.setStyleSheet(f"QFrame {{ background: {C_BG_PANEL}; border: none; }}")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # En-tête du panneau Historique
        title_bar = QFrame()
        title_bar.setFixedHeight(38)
        title_bar.setStyleSheet(f"""
            QFrame {{
                background: {C_BG_CARD};
                border-bottom: 1px solid {C_BORDER};
                border-right: 1px solid {C_BORDER};
            }}
        """)
        tb_lay = QHBoxLayout(title_bar)
        tb_lay.setContentsMargins(12, 0, 12, 0)
        lbl = QLabel("⏳  HISTORIQUE")
        lbl.setStyleSheet(f"color: {C_TEXT_DIM}; font-size: 11px; font-weight: bold; letter-spacing: 1.0px; border: none;")
        tb_lay.addWidget(lbl)
        
        btn_refresh = QPushButton("🔄")
        btn_refresh.setFixedSize(20, 20)
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.setStyleSheet(f"QPushButton {{ background: transparent; color: {C_TEXT_DIM}; border: none; font-size: 11px; }} QPushButton:hover {{ color: {C_ACCENT}; }}")
        btn_refresh.clicked.connect(self._refresh_history)
        tb_lay.addStretch()
        tb_lay.addWidget(btn_refresh)
        
        lay.addWidget(title_bar)

        # List Widget
        self.history_list = QListWidget()
        self.history_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {C_BG_DEEP};
                border: none;
                border-right: 1px solid {C_BORDER};
                padding: 5px;
            }}
            QListWidget::item {{
                background-color: {C_BG_PANEL};
                border: 1px solid {C_BORDER};
                border-radius: 6px;
                margin-bottom: 5px;
            }}
            QListWidget::item:hover {{
                background-color: #2C2C2C;
                border-color: {C_ACCENT};
            }}
            QListWidget::item:selected {{
                background-color: #353535;
                border-color: {C_ACCENT2};
            }}
        """)
        self.history_list.itemClicked.connect(self._on_history_clicked)
        lay.addWidget(self.history_list, stretch=1)

        return panel

    def _refresh_history(self):
        """Recherche les fichiers de rapports JSON et met à jour la liste de l'historique."""
        self.history_list.clear()
        output_dir = "output_reports"
        if not os.path.exists(output_dir):
            return

        reports = []
        for filename in os.listdir(output_dir):
            if filename.endswith(".json"):
                path = os.path.join(output_dir, filename)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    meta = data.get("meta", {})
                    source = meta.get("fichier_source", filename)
                    date_str = meta.get("date_generation", "")
                    
                    reports.append({
                        "filename": filename,
                        "path": path,
                        "source": source,
                        "date": date_str,
                        "data": data
                    })
                except:
                    pass

        # Tri des rapports (les plus récents en premier)
        reports.sort(key=lambda x: x["date"], reverse=True)

        for r in reports:
            item = QListWidgetItem()
            self.history_list.addItem(item)

            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.setContentsMargins(8, 6, 8, 6)
            layout.setSpacing(2)

            lbl_title = QLabel(r["source"])
            lbl_title.setStyleSheet(f"font-weight: bold; color: {C_TEXT_MAIN}; font-size: 11px;")
            
            disp_date = r["date"]
            if len(disp_date) >= 16:
                try:
                    dt = datetime.strptime(disp_date, "%Y-%m-%d %H:%M:%S")
                    disp_date = dt.strftime("%d/%m/%Y %H:%M")
                except:
                    pass
            lbl_date = QLabel(disp_date)
            lbl_date.setStyleSheet(f"color: {C_TEXT_DIM}; font-size: 10px;")

            layout.addWidget(lbl_title)
            layout.addWidget(lbl_date)

            item.setSizeHint(widget.sizeHint())
            self.history_list.setItemWidget(item, widget)
            item.setData(Qt.UserRole, r)

    def _on_history_clicked(self, item):
        """Se déclenche lorsqu'on sélectionne un rapport de l'historique."""
        r = item.data(Qt.UserRole)
        if not r:
            return

        data = r["data"]

        # 1. Rendu du diagnostic IA
        self._render_diagnosis(data.get("diagnostic_ia", ""))

        # 2. Mise à jour des badges et statistiques de la toolbar
        stats = data.get("statistiques", {})
        nb_errors = stats.get("erreurs_trouvees", 0)
        nb_warnings = stats.get("warnings_trouves", 0)
        total_lines = stats.get("lignes_totales_lues", 0)

        self.stat_lines.update_value(str(total_lines))
        self.stat_errors.update_value(str(nb_errors))
        self.stat_warnings.update_value(str(nb_warnings))

        if nb_errors == 0:
            self.stat_status.update_value("✅ OK")
        elif nb_errors <= 2:
            self.stat_status.update_value("⚠️ Attention")
        else:
            self.stat_status.update_value("🔴 Critique")

        self.lbl_badge_errors.setText(f"{nb_errors} erreur{'s' if nb_errors > 1 else ''}")
        self.lbl_badge_warnings.setText(f"{nb_warnings} warning{'s' if nb_warnings > 1 else ''}")
        
        meta = data.get("meta", {})
        board_name = meta.get("board", "Inconnu")
        self.lbl_badge_board.setText(f"Board: {board_name}")

        self.lbl_badge_errors.setVisible(True)
        self.lbl_badge_warnings.setVisible(True)
        self.lbl_badge_board.setVisible(True)

        # 3. Chargement du fichier log brut
        source_path = meta.get("fichier_source_complet", "")
        self._current_file = source_path

        if source_path and os.path.exists(source_path):
            try:
                with open(source_path, encoding="utf-8", errors="replace") as f:
                    content = f.read()
                self.log_view.setPlainText(content)
                self.lbl_log_count.setText(f"{content.count(chr(10))+1} lignes")
                self.lbl_file.setText(f"📄  {os.path.basename(source_path)}")
                self.lbl_file.setStyleSheet(f"color: {C_SUCCESS}; font-weight: bold; border: none;")
            except Exception as e:
                self.log_view.setPlainText(f"Erreur de lecture du fichier original : {e}")
        else:
            # Reconstitution si fichier d'origine introuvable
            self.lbl_file.setText(f"📄  {os.path.basename(r['source'])} (Introuvable)")
            self.lbl_file.setStyleSheet(f"color: {C_ERROR}; font-weight: bold; border: none;")
            
            errors_details = data.get("details_erreurs_brutes", [])
            lines = [f"[Fichier log original introuvable : {source_path}]", ""]
            lines.append("Erreurs brutes sauvegardées dans le rapport :")
            for err in errors_details:
                lines.append(f"{err.get('heure', '')} : Error: {err.get('message', '')}")
            self.log_view.setPlainText("\n".join(lines))
            self.lbl_log_count.setText("—")

        self._report_path = r["path"]
        self.btn_export.setEnabled(True)
        self.btn_analyze.setEnabled(True)
        self.status.showMessage(f"Rapport historique chargé : {os.path.basename(r['path'])}")

    # ── PANNEAU GAUCHE : logs bruts ──────────
    def _make_log_panel(self) -> QWidget:
        panel = QFrame()
        panel.setStyleSheet(f"QFrame {{ background: {C_BG_PANEL}; border: none; }}")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Titre du panneau
        title_bar = QFrame()
        title_bar.setFixedHeight(38)
        title_bar.setStyleSheet(f"""
            QFrame {{
                background: {C_BG_CARD};
                border-bottom: 1px solid {C_BORDER};
                border-right: 1px solid {C_BORDER};
            }}
        """)
        tb_lay = QHBoxLayout(title_bar)
        tb_lay.setContentsMargins(16, 0, 16, 0)
        lbl = QLabel("📄  Log brut STM32CubeProgrammer")
        lbl.setStyleSheet(f"color: {C_TEXT_DIM}; font-size: 11px; font-weight: bold; letter-spacing: 0.5px; border: none;")
        tb_lay.addWidget(lbl)
        tb_lay.addStretch()
        self.lbl_log_count = QLabel("")
        self.lbl_log_count.setStyleSheet(f"color: {C_TEXT_DIM}; font-size: 11px; border: none;")
        tb_lay.addWidget(self.lbl_log_count)
        lay.addWidget(title_bar)

        # Zone de texte
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Consolas", 10))
        self.log_view.setStyleSheet(f"""
            QTextEdit {{
                background: {C_BG_DEEP};
                color: {C_TEXT_DIM};
                border: none;
                border-right: 1px solid {C_BORDER};
                padding: 12px 16px;
                selection-background-color: {C_ACCENT2};
            }}
        """)
        self.log_view.setPlaceholderText(
            "Aucun fichier chargé.\n\n"
            "Cliquez sur « Charger log » pour commencer.\n\n"
            "Formats supportés : .log, .txt"
        )
        self._log_highlighter = LogHighlighter(self.log_view.document())
        lay.addWidget(self.log_view, stretch=1)

        return panel

    # ── PANNEAU DROIT : diagnostic IA ────────
    def _make_diag_panel(self) -> QWidget:
        panel = QFrame()
        panel.setStyleSheet(f"QFrame {{ background: {C_BG_PANEL}; border: none; }}")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Titre
        title_bar = QFrame()
        title_bar.setFixedHeight(38)
        title_bar.setStyleSheet(f"""
            QFrame {{
                background: {C_BG_CARD};
                border-bottom: 1px solid {C_BORDER};
            }}
        """)
        tb_lay = QHBoxLayout(title_bar)
        tb_lay.setContentsMargins(16, 0, 16, 0)
        lbl = QLabel("⚙️  Diagnostic IA")
        lbl.setStyleSheet(f"color: {C_TEXT_DIM}; font-size: 11px; font-weight: bold; letter-spacing: 0.5px; border: none;")
        tb_lay.addWidget(lbl)
        tb_lay.addStretch()
        lay.addWidget(title_bar)

        # Zone de diagnostic
        self.diag_view = QTextEdit()
        self.diag_view.setReadOnly(True)
        self.diag_view.setFont(QFont("Segoe UI", 12))
        self.diag_view.setStyleSheet(f"""
            QTextEdit {{
                background: {C_BG_DEEP};
                color: {C_TEXT_MAIN};
                border: none;
                padding: 16px 20px;
                line-height: 1.6;
                selection-background-color: {C_ACCENT2};
            }}
        """)
        self.diag_view.setPlaceholderText(
            "Le diagnostic de l'IA apparaîtra ici après l'analyse...\n\n"
            "L'IA analysera les erreurs et vous fournira :\n"
            "  • Le type et la gravité du problème\n"
            "  • Un résumé clair de la cause\n"
            "  • Des solutions pas-à-pas\n"
            "  • Une vérification matérielle"
        )
        lay.addWidget(self.diag_view, stretch=1)

        return panel

    # ── ÉVÉNEMENTS ───────────────────────────
    def _on_load_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Sélectionner un fichier de log STM32",
            "",
            "Fichiers Log (*.log *.txt);;Tous les fichiers (*)"
        )
        if not path:
            return

        self._current_file = path
        filename = os.path.basename(path)

        # Mise à jour du label fichier
        self.lbl_file.setText(f"📄  {filename}")
        self.lbl_file.setStyleSheet(f"color: {C_SUCCESS}; font-weight: bold; border: none;")

        # Lecture et affichage du contenu brut
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                content = f.read()
            self.log_view.setPlainText(content)
            self.lbl_log_count.setText(f"{content.count(chr(10))+1} lignes")
            
            # Analyse immédiate des métadonnées pour les badges de la toolbar
            entries = self.parser.parse_file(path)
            errors = [e for e in entries if e.level == "ERROR"]
            warnings = [e for e in entries if e.level == "WARNING"]
            
            board_name = "Inconnu"
            for entry in entries:
                if "Board" in entry.raw_line and ":" in entry.raw_line:
                    parts = entry.raw_line.split(":")
                    for i, part in enumerate(parts):
                        if "Board" in part:
                            if i + 1 < len(parts):
                                board_name = parts[i+1].strip()
                                break
                    if board_name != "Inconnu":
                        break
            
            # Mise à jour immédiate des stats et des badges
            self.stat_lines.update_value(str(len(entries)))
            self.stat_errors.update_value(str(len(errors)))
            self.stat_warnings.update_value(str(len(warnings)))
            
            self.lbl_badge_errors.setText(f"{len(errors)} erreur{'s' if len(errors) > 1 else ''}")
            self.lbl_badge_warnings.setText(f"{len(warnings)} warning{'s' if len(warnings) > 1 else ''}")
            self.lbl_badge_board.setText(f"Board: {board_name}")
            
            self.lbl_badge_errors.setVisible(True)
            self.lbl_badge_warnings.setVisible(True)
            self.lbl_badge_board.setVisible(True)
            
        except Exception as e:
            self.log_view.setPlainText(f"Erreur de lecture : {e}")
            self._reset_stats()

        # Réinitialisation du diagnostic et activation bouton analyser
        self.diag_view.clear()
        self.btn_analyze.setEnabled(True)
        self.btn_export.setEnabled(False)
        self.status.showMessage(f"Fichier chargé : {path}")

    def _reset_stats(self):
        self.stat_lines.update_value("—")
        self.stat_errors.update_value("—")
        self.stat_warnings.update_value("—")
        self.stat_status.update_value("—")
        self.lbl_badge_errors.setText("0 erreurs")
        self.lbl_badge_warnings.setText("0 warnings")
        self.lbl_badge_board.setText("Board: —")
        self.lbl_badge_errors.setVisible(False)
        self.lbl_badge_warnings.setVisible(False)
        self.lbl_badge_board.setVisible(False)

    def _on_analyze(self):
        if not self._current_file:
            return

        # Désactivation des boutons pendant l'analyse
        self.btn_analyze.setEnabled(False)
        self.btn_load.setEnabled(False)
        self.btn_export.setEnabled(False)
        self.diag_view.setPlainText("⏳  Analyse en cours...\nL'IA Groq examine vos logs, cela peut prendre quelques secondes.")

        # Barre de progression
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)

        # Lancement du worker dans un thread séparé
        self._worker_thread = QThread()
        self._worker = AnalysisWorker(self._current_file)
        self._worker.moveToThread(self._worker_thread)

        self._worker_thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_analysis_done)
        self._worker.error.connect(self._on_analysis_error)
        self._worker.finished.connect(self._worker_thread.quit)
        self._worker.error.connect(self._worker_thread.quit)

        self._worker_thread.start()

    def _on_progress(self, step: int, message: str):
        self.progress_bar.setValue(step)
        self.status.showMessage(message)

    def _on_analysis_done(self, result: dict):
        self.progress_bar.setValue(4)
        QTimer.singleShot(600, lambda: self.progress_bar.setVisible(False))

        # Mise à jour des stats
        self.stat_lines.update_value(str(result["total_lines"]))
        self.stat_errors.update_value(str(len(result["errors"])))
        self.stat_warnings.update_value(str(len(result["warnings"])))

        nb_errors = len(result["errors"])
        if nb_errors == 0:
            self.stat_status.update_value("✅ OK")
        elif nb_errors <= 2:
            self.stat_status.update_value("⚠️ Attention")
        else:
            self.stat_status.update_value("🔴 Critique")

        # Mise à jour des badges de la toolbar
        self.lbl_badge_errors.setText(f"{nb_errors} erreur{'s' if nb_errors > 1 else ''}")
        self.lbl_badge_warnings.setText(f"{len(result['warnings'])} warning{'s' if len(result['warnings']) > 1 else ''}")
        self.lbl_badge_board.setText(f"Board: {result.get('board', 'Inconnu')}")
        self.lbl_badge_errors.setVisible(True)
        self.lbl_badge_warnings.setVisible(True)
        self.lbl_badge_board.setVisible(True)

        # Affichage du diagnostic
        self._render_diagnosis(result["ai_diagnosis"])

        # Stockage du chemin du rapport
        self._report_path = result["report_path"]

        # Rafraîchir l'historique pour inclure la nouvelle analyse
        self._refresh_history()

        # Réactivation des boutons
        self.btn_analyze.setEnabled(True)
        self.btn_load.setEnabled(True)
        self.btn_export.setEnabled(True)
        self.status.showMessage(
            f"✅  Analyse terminée  •  Rapport : {os.path.basename(self._report_path)}"
        )

    def _on_analysis_error(self, error_msg: str):
        self.progress_bar.setVisible(False)
        self.diag_view.setPlainText(f"❌  ERREUR D'ANALYSE\n\n{error_msg}")
        self.btn_analyze.setEnabled(True)
        self.btn_load.setEnabled(True)
        self.status.showMessage(f"Erreur : {error_msg[:80]}")

    def _render_diagnosis(self, text: str):
        """Affiche le diagnostic avec mise en forme HTML riche."""
        lines = text.strip().split("\n")
        
        # Dictionnaire pour mapper les chiffres aux puces de chiffres romains/arabes cerclés
        num_map = {
            "1": "❶", "2": "❷", "3": "❸", "4": "❹", "5": "❺",
            "6": "❻", "7": "❼", "8": "❽", "9": "❾", "10": "❿"
        }
        
        html_parts = [f"""
            <div style="
                font-family: 'Segoe UI', 'Inter', sans-serif;
                font-size: 13px;
                color: {C_TEXT_MAIN};
                line-height: 1.6;
            ">
        """]

        in_solutions = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith("TYPE:"):
                # Récupération du type et du titre
                content = line.replace("TYPE:", "", 1).strip()
                parts = content.split(" - ", 1)
                severity = "CRITIQUE"
                title = content
                if len(parts) == 2:
                    severity = parts[0].strip()
                    title = parts[1].strip()
                
                severity_color = C_ERROR if severity.upper() == "CRITIQUE" else C_WARNING
                severity_bg = "rgba(248, 81, 73, 0.15)" if severity.upper() == "CRITIQUE" else "rgba(210, 153, 34, 0.15)"
                
                html_parts.append(f"""
                    <div style="color: {C_TEXT_DIM}; font-size: 10px; font-weight: bold; margin-top: 10px; margin-bottom: 6px; letter-spacing: 1px;">TYPE D'ERREUR</div>
                    <div style="margin-bottom: 15px; padding: 2px 0;">
                        <span style="background-color: {severity_bg}; color: {severity_color}; border: 1px solid {severity_color}; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: bold; margin-right: 10px;">{severity}</span>
                        <span style="color: {C_TEXT_MAIN}; font-size: 14px; font-weight: bold;">{title}</span>
                    </div>
                """)
                
            elif line.startswith("RESUME:"):
                summary_text = line.replace("RESUME:", "", 1).strip()
                html_parts.append(f"""
                    <div style="color: {C_TEXT_DIM}; font-size: 10px; font-weight: bold; margin-top: 15px; margin-bottom: 6px; letter-spacing: 1px;">RÉSUMÉ</div>
                    <div style="color: {C_TEXT_MAIN}; font-size: 13px; font-weight: bold; line-height: 1.5; margin-bottom: 15px;">
                        {summary_text}
                    </div>
                """)
                
            elif line.startswith("SOLUTIONS:"):
                in_solutions = True
                html_parts.append(f"""
                    <div style="color: {C_TEXT_DIM}; font-size: 10px; font-weight: bold; margin-top: 15px; margin-bottom: 8px; letter-spacing: 1px;">ÉTAPES DE RÉSOLUTION</div>
                """)
                
            elif in_solutions and (line.startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.", "10.")) or (line[0].isdigit() and line[1] == '.')):
                parts = line.split(".", 1)
                num = parts[0].strip()
                step_text = parts[1].strip()
                circled_num = num_map.get(num, num)
                
                html_parts.append(f"""
                    <div style="margin-bottom: 8px; line-height: 1.5;">
                        <span style="color: #00D4FF; font-size: 16px; font-weight: bold; margin-right: 8px; font-family: 'Segoe UI Symbol', sans-serif;">{circled_num}</span>
                        <span style="color: {C_TEXT_MAIN}; font-size: 12px;">{step_text}</span>
                    </div>
                """)
                
            elif line.startswith("VÉRIFICATION MATÉRIELLE:") or line.startswith("VERIFICATION MATERIELLE:"):
                in_solutions = False
                check_text = line.replace("VÉRIFICATION MATÉRIELLE:", "", 1).replace("VERIFICATION MATERIELLE:", "", 1).strip()
                
                color = C_WARNING
                if check_text.upper().startswith("OUI"):
                    color = C_ERROR
                elif check_text.upper().startswith("NON"):
                    color = C_WARNING  # Orange comme sur le mockup
                
                html_parts.append(f"""
                    <div style="color: {C_TEXT_DIM}; font-size: 10px; font-weight: bold; margin-top: 18px; margin-bottom: 6px; letter-spacing: 1px;">VÉRIFICATION MATÉRIELLE REQUISE</div>
                    <div style="color: {color}; font-size: 12px; font-weight: bold; padding: 2px 0;">
                        ⚠️ {check_text}
                    </div>
                """)
            else:
                html_parts.append(f"<div style='color: {C_TEXT_DIM}; margin-bottom: 4px; font-size: 12px;'>{line}</div>")

        html_parts.append("</div>")
        self.diag_view.setHtml("".join(html_parts))

    def _on_open_report(self):
        """Ouvre le dossier contenant le dernier rapport généré."""
        if hasattr(self, "_report_path") and self._report_path:
            folder = os.path.dirname(os.path.abspath(self._report_path))
            os.startfile(folder)
