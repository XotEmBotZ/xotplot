"""Reusable Matplotlib Canvas widget for PyQt6 with dark/light theme support."""

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QVBoxLayout, QWidget


class MplCanvasWidget(QWidget):
    """Interactive Matplotlib canvas widget with theme styling and cursor coordinates."""

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
        """Apply theme colors to the figure and axes (plots always remain in light theme)."""
        # User constraint: plots are ALWAYS in light theme
        self.dark_mode = False
        bg_color = "#ffffff"
        fg_color = "#0f172a"
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
        """Plot a synthetic meteorological geopotential height contour and wind field."""
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        x = np.linspace(-130, -60, 45)
        y = np.linspace(20, 60, 35)
        X, Y = np.meshgrid(x, y)

        # Synthetic 500 hPa Geopotential Height field (dam)
        Z = 570 - 0.7 * (Y - 20) + 12 * np.sin(np.radians(X * 2.5)) * np.cos(np.radians((Y - 40) * 3))

        cmap = "turbo"
        levels = np.arange(520, 595, 6)
        cf = ax.contourf(X, Y, Z, levels=levels, cmap=cmap, alpha=0.9)
        cs = ax.contour(X, Y, Z, levels=levels, colors="#1e293b", linewidths=0.8, alpha=0.7)
        ax.clabel(cs, inline=True, fontsize=8, fmt="%d dam")

        # Wind barbs
        step = 4
        X_sub = X[::step, ::step]
        Y_sub = Y[::step, ::step]
        dZ_dy, dZ_dx = np.gradient(Z)
        u = -dZ_dy[::step, ::step] * 15
        v = dZ_dx[::step, ::step] * 15
        ax.barbs(X_sub, Y_sub, u, v, length=5, color="#0284c7")

        # Centers
        ax.text(-95, 42, "L 540", color="#dc2626", fontsize=11, fontweight="bold", ha="center")
        ax.text(-75, 30, "H 588", color="#16a34a", fontsize=11, fontweight="bold", ha="center")

        ax.set_title("GFS 0.25°: 500 hPa Geopotential Height & Wind", fontsize=11)
        ax.set_xlabel("Longitude (°E)", fontsize=9)
        ax.set_ylabel("Latitude (°N)", fontsize=9)

        cbar = self.figure.colorbar(cf, ax=ax, orientation="horizontal", pad=0.14, shrink=0.8)
        cbar.set_label("Geopotential Height [dam]", fontsize=8, color="#0f172a")
        cbar.ax.tick_params(colors="#0f172a", labelsize=8)

        self.apply_theme(False)
        self.figure.tight_layout()
        self.canvas.draw_idle()
