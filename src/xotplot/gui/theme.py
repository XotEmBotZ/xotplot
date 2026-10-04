"""Dark and light theme styles for xotplot PyQt6 GUI."""

DARK_THEME = """
QWidget {
    background-color: #0f131c;
    color: #dfe2ef;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 11px;
    selection-background-color: #38bdf8;
    selection-color: #001e2c;
}

QMainWindow, QDialog {
    background-color: #0f131c;
}

QMenuBar {
    background-color: #181b25;
    color: #dfe2ef;
    border-bottom: 1px solid #262a34;
    padding: 2px;
}

QMenuBar::item {
    background: transparent;
    padding: 3px 8px;
    border-radius: 2px;
}

QMenuBar::item:selected {
    background-color: #31353f;
    color: #8ed5ff;
}

QMenu {
    background-color: #181b25;
    color: #dfe2ef;
    border: 1px solid #3e484f;
    padding: 4px;
}

QMenu::item {
    padding: 4px 18px;
    border-radius: 2px;
}

QMenu::item:selected {
    background-color: #31353f;
    color: #8ed5ff;
}

QToolBar {
    background-color: #1c1f29;
    border-bottom: 1px solid #262a34;
    padding: 4px;
    spacing: 4px;
}

QToolButton {
    background-color: #262a34;
    color: #dfe2ef;
    border: 1px solid #3e484f;
    border-radius: 2px;
    padding: 4px 8px;
    font-size: 11px;
}

QToolButton:hover {
    background-color: #353943;
    border-color: #8ed5ff;
}

QToolButton:pressed {
    background-color: #004965;
    color: #8ed5ff;
}

QPushButton {
    background-color: #262a34;
    color: #dfe2ef;
    border: 1px solid #3e484f;
    border-radius: 2px;
    padding: 4px 10px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #353943;
    border-color: #8ed5ff;
}

QPushButton:pressed {
    background-color: #004965;
    color: #8ed5ff;
}

QPushButton:disabled {
    background-color: #181b25;
    color: #87929a;
    border-color: #262a34;
}

QPushButton:checked, QPushButton[activeCard="true"] {
    background-color: #0284c7;
    color: #ffffff;
    border: 2px solid #38bdf8;
    font-weight: bold;
}

QPushButton#primaryAction {
    background-color: #004965;
    color: #8ed5ff;
    border: 1px solid #38bdf8;
    font-weight: 600;
}

QPushButton#primaryAction:hover {
    background-color: #00668a;
    color: #ffffff;
}

QDockWidget {
    color: #dfe2ef;
    font-weight: bold;
    titlebar-close-icon: url(none);
    titlebar-normal-icon: url(none);
}

QDockWidget::title {
    background: #1c1f29;
    padding: 6px;
    border-bottom: 1px solid #262a34;
    text-align: left;
}

QTabWidget::pane {
    border: 1px solid #262a34;
    background-color: #181b25;
}

QTabBar::tab {
    background-color: #181b25;
    color: #87929a;
    padding: 6px 12px;
    border-bottom: 2px solid transparent;
}

QTabBar::tab:selected {
    color: #8ed5ff;
    border-bottom: 2px solid #8ed5ff;
    background-color: #262a34;
}

QTabBar::tab:hover:!selected {
    color: #dfe2ef;
    background-color: #1c1f29;
}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #0a0e17;
    color: #dfe2ef;
    border: 1px solid #3e484f;
    border-radius: 2px;
    padding: 3px 6px;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #38bdf8;
}

QComboBox::drop-down {
    border: none;
    width: 16px;
}

QTreeWidget, QListWidget, QTextEdit, QPlainTextEdit {
    background-color: #0a0e17;
    color: #dfe2ef;
    border: 1px solid #262a34;
    border-radius: 2px;
}

QTreeWidget::item, QListWidget::item {
    padding: 3px;
}

QTreeWidget::item:selected, QListWidget::item:selected {
    background-color: #262a34;
    color: #8ed5ff;
}

QSlider::groove:horizontal {
    height: 4px;
    background: #262a34;
    border-radius: 2px;
}

QSlider::sub-page:horizontal {
    background: #38bdf8;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    background: #8ed5ff;
    border: 1px solid #00354a;
    width: 12px;
    margin-top: -4px;
    margin-bottom: -4px;
    border-radius: 6px;
}

QSlider::handle:horizontal:hover {
    background: #c4e7ff;
}

QStatusBar {
    background-color: #0a0e17;
    color: #87929a;
    border-top: 1px solid #262a34;
}

QStatusBar QLabel {
    color: #87929a;
    padding: 0 4px;
}

QGroupBox {
    border: 1px solid #262a34;
    border-radius: 3px;
    margin-top: 8px;
    padding-top: 10px;
    font-weight: 600;
    color: #87929a;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 8px;
    padding: 0 4px;
}
"""

LIGHT_THEME = """
QWidget {
    background-color: #f8fafc;
    color: #0f172a;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 11px;
    selection-background-color: #0284c7;
    selection-color: #ffffff;
}

QMainWindow, QDialog {
    background-color: #f8fafc;
}

QMenuBar {
    background-color: #f1f5f9;
    color: #0f172a;
    border-bottom: 1px solid #cbd5e1;
    padding: 2px;
}

QMenuBar::item {
    background: transparent;
    padding: 3px 8px;
    border-radius: 2px;
}

QMenuBar::item:selected {
    background-color: #e2e8f0;
    color: #0284c7;
}

QMenu {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    padding: 4px;
}

QMenu::item {
    padding: 4px 18px;
    border-radius: 2px;
}

QMenu::item:selected {
    background-color: #e0f2fe;
    color: #0284c7;
}

QToolBar {
    background-color: #f1f5f9;
    border-bottom: 1px solid #cbd5e1;
    padding: 4px;
    spacing: 4px;
}

QToolButton {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 2px;
    padding: 4px 8px;
    font-size: 11px;
}

QToolButton:hover {
    background-color: #e2e8f0;
    border-color: #0284c7;
}

QToolButton:pressed {
    background-color: #e0f2fe;
    color: #0284c7;
}

QPushButton {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 2px;
    padding: 4px 10px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #f1f5f9;
    border-color: #0284c7;
}

QPushButton:pressed {
    background-color: #e0f2fe;
    color: #0284c7;
}

QPushButton:disabled {
    background-color: #f8fafc;
    color: #94a3b8;
    border-color: #e2e8f0;
}

QPushButton:checked, QPushButton[activeCard="true"] {
    background-color: #0284c7;
    color: #ffffff;
    border: 2px solid #0369a1;
    font-weight: bold;
}

QPushButton#primaryAction {
    background-color: #0284c7;
    color: #ffffff;
    border: 1px solid #0369a1;
    font-weight: 600;
}

QPushButton#primaryAction:hover {
    background-color: #0369a1;
}

QDockWidget {
    color: #0f172a;
    font-weight: bold;
    titlebar-close-icon: url(none);
    titlebar-normal-icon: url(none);
}

QDockWidget::title {
    background: #f1f5f9;
    padding: 6px;
    border-bottom: 1px solid #cbd5e1;
    text-align: left;
}

QTabWidget::pane {
    border: 1px solid #cbd5e1;
    background-color: #ffffff;
}

QTabBar::tab {
    background-color: #f1f5f9;
    color: #64748b;
    padding: 6px 12px;
    border-bottom: 2px solid transparent;
}

QTabBar::tab:selected {
    color: #0284c7;
    border-bottom: 2px solid #0284c7;
    background-color: #ffffff;
}

QTabBar::tab:hover:!selected {
    color: #0f172a;
    background-color: #e2e8f0;
}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 2px;
    padding: 3px 6px;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #0284c7;
}

QComboBox::drop-down {
    border: none;
    width: 16px;
}

QTreeWidget, QListWidget, QTextEdit, QPlainTextEdit {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 2px;
}

QTreeWidget::item, QListWidget::item {
    padding: 3px;
}

QTreeWidget::item:selected, QListWidget::item:selected {
    background-color: #e0f2fe;
    color: #0284c7;
}

QSlider::groove:horizontal {
    height: 4px;
    background: #e2e8f0;
    border-radius: 2px;
}

QSlider::sub-page:horizontal {
    background: #0284c7;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    background: #0284c7;
    border: 1px solid #0369a1;
    width: 12px;
    margin-top: -4px;
    margin-bottom: -4px;
    border-radius: 6px;
}

QSlider::handle:horizontal:hover {
    background: #0369a1;
}

QStatusBar {
    background-color: #f1f5f9;
    color: #64748b;
    border-top: 1px solid #cbd5e1;
}

QStatusBar QLabel {
    color: #64748b;
    padding: 0 4px;
}

QGroupBox {
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    margin-top: 8px;
    padding-top: 10px;
    font-weight: 600;
    color: #64748b;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 8px;
    padding: 0 4px;
}
"""


def get_theme_qss(dark_mode: bool) -> str:
    """Return QSS stylesheet string for the requested theme."""
    return DARK_THEME if dark_mode else LIGHT_THEME
