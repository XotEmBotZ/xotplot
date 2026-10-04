"""Lightweight canvas widget for displaying plot images rendered by the engine process."""

from pathlib import Path
from typing import Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QResizeEvent
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from xotplot.constants import DEFAULT_PLOT_BG_COLOR


class EngineCanvasWidget(QWidget):
    """Plot canvas widget displaying headless engine renders on a strict #ffffff canvas."""

    cursor_moved = pyqtSignal(float, float)

    def __init__(self, parent: Optional[QWidget] = None, width: float = 8.0, height: float = 6.0, dpi: int = 100) -> None:
        super().__init__(parent)
        self._raw_bytes: Optional[bytes] = None
        self._pixmap: Optional[QPixmap] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._image_label = QLabel(self)
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setStyleSheet(f"background-color: {DEFAULT_PLOT_BG_COLOR};")
        layout.addWidget(self._image_label)

        self.setStyleSheet(f"background-color: {DEFAULT_PLOT_BG_COLOR};")
        self.setMouseTracking(True)

    @property
    def current_image_bytes(self) -> Optional[bytes]:
        return self._raw_bytes

    def set_image_bytes(self, data: bytes) -> None:
        """Update canvas display with fresh PNG bytes rendered by the engine."""
        self._raw_bytes = data
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            self._pixmap = pixmap
            self._update_display()

    def _update_display(self) -> None:
        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._image_label.setPixmap(scaled)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._update_display()

    def save_figure(self, path: str | Path) -> None:
        """Save the current rendered figure to disk."""
        if self._raw_bytes:
            Path(path).write_bytes(self._raw_bytes)

    def apply_theme(self, dark_mode: bool = False) -> None:
        """Plots always strictly remain on light theme #ffffff canvas."""
        self.setStyleSheet(f"background-color: {DEFAULT_PLOT_BG_COLOR};")
        self._image_label.setStyleSheet(f"background-color: {DEFAULT_PLOT_BG_COLOR};")
