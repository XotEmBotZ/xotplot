"""Dual-stage viewport widget for fast preview and high-resolution renders."""

from pathlib import Path
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ViewportWidget(QWidget):
    """Viewport widget supporting dual-stage preview and full render."""

    render_requested = pyqtSignal()
    point_inspected = pyqtSignal(float, float, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Outer Frame
        self._frame = QFrame(self)
        self._frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame_layout = QVBoxLayout(self._frame)
        frame_layout.setContentsMargins(8, 8, 8, 8)
        frame_layout.setSpacing(6)

        # Top HUD / Toolbar
        top_hud = QHBoxLayout()

        # Mini toolbar
        self._pan_btn = QPushButton("Pan")
        self._zoom_btn = QPushButton("Zoom")
        self._reset_btn = QPushButton("Reset Extent")
        self._probe_btn = QPushButton("Probe")
        self._export_btn = QPushButton("Export Fig")
        self._export_btn.setObjectName("primaryAction")

        top_hud.addWidget(self._pan_btn)
        top_hud.addWidget(self._zoom_btn)
        top_hud.addWidget(self._reset_btn)
        top_hud.addWidget(self._probe_btn)
        top_hud.addWidget(self._export_btn)
        top_hud.addStretch()

        # Header HUD
        self._header_info = QLabel("GFS 0.25°: 500 hPa Geopotential Height & 850 hPa Wind Barbs\nInit: 2024-10-28 12Z | Valid: 2024-10-29 12Z (+24h)")
        self._header_info.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top_hud.addWidget(self._header_info)

        frame_layout.addLayout(top_hud)

        # SVG or Canvas Area
        svg_path = Path(__file__).parent / "sample_chart.svg"
        if svg_path.exists():
            self._svg_widget = QSvgWidget(str(svg_path), self._frame)
            frame_layout.addWidget(self._svg_widget, stretch=1)
        else:
            self._display = QLabel("Interactive Spatial Viewport\n[Cartopy / Plate Carrée Preview & High-Res Commit]", self._frame)
            self._display.setAlignment(Qt.AlignmentFlag.AlignCenter)
            frame_layout.addWidget(self._display, stretch=1)

        # Bottom HUD: Colormap bar
        cmap_box = QFrame(self._frame)
        cmap_box.setFrameShape(QFrame.Shape.StyledPanel)
        cmap_layout = QVBoxLayout(cmap_box)
        cmap_layout.setContentsMargins(6, 4, 6, 4)

        cmap_title = QHBoxLayout()
        cmap_title.addWidget(QLabel("Colormap: <b>turbo</b> (Perceptually Uniform Spectral)"))
        cmap_title.addStretch()
        cmap_title.addWidget(QLabel("Geopotential Height [dam] | Intervals: 8 | Min: 520 / Max: 590"))
        cmap_layout.addLayout(cmap_title)

        # Gradient bar
        grad_bar = QFrame(cmap_box)
        grad_bar.setFixedHeight(12)
        grad_bar.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #30123b, stop:0.14 #4145ab, stop:0.28 #468dfc, stop:0.42 #28d7b3, stop:0.57 #a4fc3c, stop:0.71 #fbbe22, stop:0.85 #e9430c, stop:1.0 #7a0403); border-radius: 2px;")
        cmap_layout.addWidget(grad_bar)

        ticks_layout = QHBoxLayout()
        for tick in ["528", "534", "540", "546", "552", "558", "564", "570", "576", "582", "588"]:
            lbl = QLabel(tick)
            lbl.setStyleSheet("font-family: monospace; font-size: 10px;")
            ticks_layout.addWidget(lbl)
            if tick != "588":
                ticks_layout.addStretch()
        cmap_layout.addLayout(ticks_layout)

        frame_layout.addWidget(cmap_box)
        layout.addWidget(self._frame)
