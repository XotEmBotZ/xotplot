"""Application entrypoint for the PyQt6 GUI."""

import sys
from PyQt6.QtWidgets import QApplication

from xotplot.gui.main_window import MainWindow


def run_app(argv: list[str] | None = None) -> int:
    """Initialize and run the PyQt6 application."""
    from PyQt6.QtCore import QTimer

    args = argv if argv is not None else sys.argv
    app = QApplication(args)
    window = MainWindow()
    window.show()

    # If a file path was passed on CLI, load it asynchronously once GUI is painted
    if len(args) > 1 and not args[1].startswith("-"):
        file_arg = args[1]
        QTimer.singleShot(50, lambda: window.load_dataset(file_arg))

    return app.exec()
