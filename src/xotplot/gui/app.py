"""Application entrypoint for the PyQt6 GUI."""

import sys
from PyQt6.QtWidgets import QApplication

from xotplot.gui.main_window import MainWindow


def run_app(argv: list[str] | None = None) -> int:
    """Initialize and run the PyQt6 application."""
    app = QApplication(argv if argv is not None else sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
