"""Dark engineering workspace shared by the dashboard and its dialogs."""

from pathlib import Path

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication, QWidget


BACKGROUND = "#303134"
PANEL = "#252629"
PLOT = "#1d1e20"
TEXT = "#e8e9ed"
MUTED = "#b3b7c1"
CYAN = "#39bcf3"
AMBER = "#ffc43d"

STYLESHEET = """
QWidget {
    color: #e8e9ed;
    font-family: "Noto Sans CJK KR", "Noto Sans", sans-serif;
    font-size: 14px;
}
QMainWindow, QDialog { background: #303134; }
QWidget#workspace-shell, QWidget#workspace, QTabWidget::pane { background: #303134; }
QFrame#app-header { background: #233d91; border: none; }
QLabel#app-title { color: #ffffff; font-size: 19px; font-weight: 600; }
QLabel#app-section { color: #dce4ff; font-size: 16px; }
QFrame#sidebar { background: #292a2d; border-right: 1px solid #45474c; }
QLabel#sidebar-title { color: #c5c8d1; font-size: 14px; font-weight: 600; padding: 8px; }
QTreeWidget#navigation {
    background: #292a2d; border: none; outline: none; show-decoration-selected: 1;
}
QTreeWidget#navigation::item { height: 38px; padding-left: 3px; border-left: 3px solid transparent; }
QTreeWidget#navigation::item:hover { background: #363940; }
QTreeWidget#navigation::item:selected { background: #343e55; color: #ffffff; border-left: 3px solid #ffc43d; }
QFrame#workspace-toolbar { background: #35373b; border-bottom: 1px solid #4a4c52; }
QLabel#page-title { font-size: 17px; font-weight: 600; }
QLabel#workspace-device { color: #c7cad2; font-size: 14px; }
QTabWidget::pane { border: none; }
QGroupBox {
    background: #252629; border: 1px solid #4a4c52; border-radius: 0px;
    margin-top: 24px; padding: 12px 10px 10px;
    font-weight: 600;
}
QGroupBox::title { subcontrol-origin: margin; left: 12px; top: 3px; padding: 0px 5px; color: #e8e9ed; }
QLabel[role="metric"] { font-size: 29px; font-weight: 600; background: transparent; }
QLabel[role="metric-caption"] { color: #b3b7c1; font-size: 14px; }
QLabel#session-state { font-size: 18px; font-weight: 600; padding: 2px 0px 6px; }
QLabel#pipeline-event { color: #c5c9d2; font-size: 14px; padding: 7px 0px; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background: #1e1f22; border: 1px solid #565960; border-radius: 0px;
    padding: 6px 8px; min-height: 22px; selection-background-color: #355da4;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus { border: 1px solid #59aaf0; }
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {
    color: #a4a8b2; background: #2c2d31; border-color: #414349;
}
QComboBox::drop-down { width: 24px; border-left: 1px solid #44464d; }
QComboBox::down-arrow { image: url("@ASSETS@/chevron-down.svg"); width: 12px; height: 8px; }
QSpinBox::up-button, QDoubleSpinBox::up-button { subcontrol-origin: border; subcontrol-position: top right; width: 24px; background: #34363c; border-left: 1px solid #555963; }
QSpinBox::down-button, QDoubleSpinBox::down-button { subcontrol-origin: border; subcontrol-position: bottom right; width: 24px; background: #34363c; border-left: 1px solid #555963; }
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow { image: url("@ASSETS@/chevron-up.svg"); width: 10px; height: 6px; }
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow { image: url("@ASSETS@/chevron-down.svg"); width: 10px; height: 6px; }
QComboBox QAbstractItemView { background: #252629; selection-background-color: #35518b; padding: 4px; }
QPushButton {
    background: #383a40; border: 1px solid #5b5e66; border-radius: 0px;
    padding: 7px 14px; min-height: 22px; color: #f0f1f4;
}
QPushButton:hover { background: #454850; border-color: #8c929f; }
QPushButton:pressed { background: #24262b; }
QPushButton:disabled { background: #2e3035; color: #737781; border-color: #42444b; }
QPushButton[role="primary"] { background: #ffc43d; border-color: #ffc43d; color: #1a1b1d; font-weight: 600; }
QPushButton[role="primary"]:hover { background: #ffd46e; border-color: #ffd46e; }
QPushButton[role="primary"]:pressed { background: #e4aa26; }
QPushButton[role="primary"]:disabled { background: #504a37; border-color: #60563b; color: #aaa18a; }
QPushButton[role="stop"]:enabled { background: #713638; border-color: #be6264; color: #ffffff; }
QPushButton[role="stop"]:hover { background: #8e4043; }
QPushButton#console-toggle { text-align: left; background: #35373b; border: none; border-top: 1px solid #50535a; }
QTextEdit, QListWidget, QTableWidget {
    background: #1e1f22; alternate-background-color: #292b30; border: 1px solid #4a4d54;
    selection-background-color: #344c7c; gridline-color: #41434a;
}
QTextEdit#event-console { font-family: "Noto Sans Mono", "DejaVu Sans Mono", monospace; font-size: 14px; border: none; padding: 6px; }
QListWidget::item { padding: 10px; border-bottom: 1px solid #34363b; }
QHeaderView::section { background: #36383e; color: #e8e9ed; padding: 9px; border: none; border-right: 1px solid #4a4c52; border-bottom: 1px solid #4a4c52; }
QTableCornerButton::section { background: #36383e; border: none; }
QScrollArea { background: transparent; border: none; }
QScrollBar:vertical { background: #282a2e; width: 12px; margin: 0; }
QScrollBar::handle:vertical { background: #60646e; min-height: 28px; margin: 2px; }
QScrollBar:horizontal { background: #282a2e; height: 12px; margin: 0; }
QScrollBar::handle:horizontal { background: #60646e; min-width: 28px; margin: 2px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QCheckBox { spacing: 9px; min-height: 30px; }
QCheckBox::indicator { width: 17px; height: 17px; border: 1px solid #747985; background: #222428; }
QCheckBox::indicator:checked { background: #3379cc; border-color: #76b8ff; image: url("@ASSETS@/check.svg"); }
QToolTip { background: #393c43; color: #ffffff; border: 1px solid #696f7b; padding: 8px; font-size: 14px; }
"""


def apply_theme(widget: QWidget) -> None:
    """Use a deterministic palette even on light desktop themes."""
    app = QApplication.instance()
    if app is not None and not app.property("tms-dark-theme"):
        app.setStyle("Fusion")
        palette = QPalette()
        for role, color in (
            (QPalette.ColorRole.Window, BACKGROUND),
            (QPalette.ColorRole.WindowText, TEXT),
            (QPalette.ColorRole.Base, PLOT),
            (QPalette.ColorRole.AlternateBase, PANEL),
            (QPalette.ColorRole.Text, TEXT),
            (QPalette.ColorRole.Button, "#383a40"),
            (QPalette.ColorRole.ButtonText, TEXT),
            (QPalette.ColorRole.Highlight, "#35518b"),
            (QPalette.ColorRole.HighlightedText, "#ffffff"),
            (QPalette.ColorRole.ToolTipBase, "#393c43"),
            (QPalette.ColorRole.ToolTipText, TEXT),
            (QPalette.ColorRole.PlaceholderText, MUTED),
        ):
            palette.setColor(role, QColor(color))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor("#a4a8b2"))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#737781"))
        app.setPalette(palette)
        app.setFont(QFont("Noto Sans CJK KR", 10))
        app.setProperty("tms-dark-theme", True)
    asset_path = (Path(__file__).parent / "assets").as_posix()
    widget.setStyleSheet(STYLESHEET.replace("@ASSETS@", asset_path))
