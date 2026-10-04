"""Reusable Matplotlib Canvas widget for PyQt6 with strict light theme plot canvas."""

from pathlib import Path
from typing import Optional
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from xotplot.constants import DEFAULT_PLOT_BG_COLOR, DEFAULT_PLOT_FG_COLOR
from xotplot.engine import render_synoptic_field


class MplCanvasWidget(QWidget):
    """Interactive Matplotlib canvas widget strictly adhering to #ffffff plot canvas."""

    cursor_moved = pyqtSignal(float, float)

    def __init__(self, parent: QWidget | None = None, width: float = 8.0, height: float = 5.0, dpi: int = 100) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.figure = Figure(figsize=(width, height), dpi=dpi)
        self.canvas = FigureCanvasQTAgg(self.figure)
        layout.addWidget(self.canvas)

        self.dark_mode = False
        self.apply_theme(dark_mode=False)
        self.canvas.mpl_connect("motion_notify_event", self._on_motion)

    def apply_theme(self, dark_mode: bool = False) -> None:
        """Apply theme colors (plots strictly remain in light theme #ffffff)."""
        self.dark_mode = False
        bg_color = DEFAULT_PLOT_BG_COLOR
        fg_color = DEFAULT_PLOT_FG_COLOR
        grid_color = "#cbd5e1"

        self.figure.patch.set_facecolor(bg_color)
        for ax in self.figure.axes:
            ax.set_facecolor(bg_color)
            ax.tick_params(colors=fg_color, which="both")
            for spine in ax.spines.values():
                spine.set_color(fg_color)
            ax.xaxis.label.set_color(fg_color)
            ax.yaxis.label.set_color(fg_color)
            ax.title.set_color(fg_color)
            ax.grid(True, color=grid_color, linestyle="--", alpha=0.5)

        self.canvas.draw_idle()

    def _on_motion(self, event) -> None:
        if event.inaxes and event.xdata is not None and event.ydata is not None:
            self.cursor_moved.emit(float(event.xdata), float(event.ydata))

    def plot_synoptic_field(self) -> None:
        """Delegate synoptic plot generation to xotplot.engine."""
        render_synoptic_field(self.figure)
        self.apply_theme(False)
        self.canvas.draw_idle()

    def save_figure(self, path: str | Path, dpi: int = 300) -> None:
        """Save current figure to disk."""
        self.figure.savefig(path, dpi=dpi, bbox_inches="tight")
