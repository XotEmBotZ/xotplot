"""Interactive spatial viewport view module for meteorological visual workflows."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDockWidget,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSlider,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from xotplot.constants import ALL_REGIONS
from xotplot.gui.mpl_canvas import MplCanvasWidget
from xotplot.gui.theme import get_theme_qss



class SpatialViewportView(QWidget):
    """Spatial viewport view hosting MplCanvasWidget, scrubber, mini-toolbar, and CLI/YAML dock."""

    cursor_moved = pyqtSignal(float, float)
    lead_time_changed = pyqtSignal(int)
    extent_reset_requested = pyqtSignal()
    probe_triggered = pyqtSignal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._dark_mode = True
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Vertical splitter separating canvas + controls from the bottom CLI/YAML inspector
        self._splitter = QSplitter(Qt.Orientation.Vertical, self)

        # Upper container: Toolbar + Canvas + Scrubber
        upper_widget = QWidget(self)
        upper_layout = QVBoxLayout(upper_widget)
        upper_layout.setContentsMargins(6, 6, 6, 6)
        upper_layout.setSpacing(6)

        # Mini-toolbar
        self._toolbar_frame = QFrame(upper_widget)
        self._toolbar_frame.setFrameShape(QFrame.Shape.StyledPanel)
        tb_layout = QHBoxLayout(self._toolbar_frame)
        tb_layout.setContentsMargins(6, 4, 6, 4)
        tb_layout.setSpacing(6)

        self._btn_pan = QPushButton("Pan", self._toolbar_frame)
        self._btn_pan.setCheckable(True)
        self._btn_zoom = QPushButton("Zoom", self._toolbar_frame)
        self._btn_zoom.setCheckable(True)
        self._btn_reset = QPushButton("Reset Extent", self._toolbar_frame)
        self._btn_probe = QPushButton("Point Probe", self._toolbar_frame)
        self._btn_probe.setCheckable(True)
        self._btn_export = QPushButton("Export Fig", self._toolbar_frame)
        self._btn_export.setObjectName("primaryAction")

        tb_layout.addWidget(self._btn_pan)
        tb_layout.addWidget(self._btn_zoom)
        tb_layout.addWidget(self._btn_reset)
        tb_layout.addWidget(self._btn_probe)
        tb_layout.addWidget(self._btn_export)

        tb_layout.addWidget(QLabel(" | Region:", self._toolbar_frame))
        self.combo_region = QComboBox(self._toolbar_frame)
        self.combo_region.addItems(list(ALL_REGIONS.keys()))
        tb_layout.addWidget(self.combo_region)
        tb_layout.addStretch()

        self._header_info = QLabel("GFS 0.25°: 500 hPa Geopotential Height & 850 hPa Wind Barbs", self._toolbar_frame)
        self._header_info.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        tb_layout.addWidget(self._header_info)

        upper_layout.addWidget(self._toolbar_frame)

        # Canvas Widget
        self.canvas_widget = MplCanvasWidget(upper_widget)
        upper_layout.addWidget(self.canvas_widget, stretch=1)

        # Forecast Lead-time scrubber slider (0 to 120h, step 3)
        self._scrubber_frame = QFrame(upper_widget)
        self._scrubber_frame.setFrameShape(QFrame.Shape.StyledPanel)
        scrubber_layout = QHBoxLayout(self._scrubber_frame)
        scrubber_layout.setContentsMargins(8, 4, 8, 4)
        scrubber_layout.setSpacing(8)

        lbl_lead = QLabel("Forecast Lead Time:", self._scrubber_frame)
        scrubber_layout.addWidget(lbl_lead)

        self.slider = QSlider(Qt.Orientation.Horizontal, self._scrubber_frame)
        self.slider.setRange(0, 120)
        self.slider.setSingleStep(3)
        self.slider.setPageStep(6)
        self.slider.setTickInterval(6)
        self.slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider.setValue(24)
        scrubber_layout.addWidget(self.slider, stretch=1)

        self.slider_val_lbl = QLabel("+024h (Valid: +24h)", self._scrubber_frame)
        self.slider_val_lbl.setMinimumWidth(130)
        scrubber_layout.addWidget(self.slider_val_lbl)

        upper_layout.addWidget(self._scrubber_frame)

        self._splitter.addWidget(upper_widget)

        # Bottom Inspector: CLI & YAML inspector dock / tabs
        inspector_widget = QWidget(self)
        inspector_layout = QVBoxLayout(inspector_widget)
        inspector_layout.setContentsMargins(6, 4, 6, 6)
        inspector_layout.setSpacing(4)

        self.inspector_tabs = QTabWidget(inspector_widget)

        # Tab 1: Generated CLI Command
        cli_tab = QWidget()
        cli_tab_layout = QVBoxLayout(cli_tab)
        cli_tab_layout.setContentsMargins(4, 4, 4, 4)
        self.cli_text_edit = QPlainTextEdit(cli_tab)
        self.cli_text_edit.setReadOnly(True)
        cli_tab_layout.addWidget(self.cli_text_edit)
        self.inspector_tabs.addTab(cli_tab, "Generated CLI Command")

        # Tab 2: config.yaml
        yaml_tab = QWidget()
        yaml_tab_layout = QVBoxLayout(yaml_tab)
        yaml_tab_layout.setContentsMargins(4, 4, 4, 4)
        self.yaml_text_edit = QPlainTextEdit(yaml_tab)
        self.yaml_text_edit.setReadOnly(True)
        yaml_tab_layout.addWidget(self.yaml_text_edit)
        self.inspector_tabs.addTab(yaml_tab, "config.yaml")

        inspector_layout.addWidget(self.inspector_tabs)
        self._splitter.addWidget(inspector_widget)

        # Set initial splitter proportions (75% top, 25% bottom)
        self._splitter.setStretchFactor(0, 3)
        self._splitter.setStretchFactor(1, 1)

        main_layout.addWidget(self._splitter)

        # Signal connections
        self.canvas_widget.cursor_moved.connect(self._on_canvas_cursor_moved)
        self.slider.valueChanged.connect(self._on_slider_value_changed)
        self._btn_reset.clicked.connect(self._on_reset_extent)
        self._btn_probe.toggled.connect(self._on_probe_toggled)
        self._btn_export.clicked.connect(self._on_export_fig)

        # Initial plot & text generation
        self.canvas_widget.plot_synoptic_field()
        self._update_inspector_texts(24)

    def _on_canvas_cursor_moved(self, lon: float, lat: float) -> None:
        self.cursor_moved.emit(lon, lat)

    def _on_slider_value_changed(self, value: int) -> None:
        # Snap value to nearest multiple of 3
        snapped_val = round(value / 3.0) * 3
        if snapped_val != value:
            self.slider.blockSignals(True)
            self.slider.setValue(snapped_val)
            self.slider.blockSignals(False)
            value = snapped_val

        self.slider_val_lbl.setText(f"+{value:03d}h (Valid: +{value}h)")
        self._update_inspector_texts(value)
        self.lead_time_changed.emit(value)

    def _update_inspector_texts(self, lead_hours: int) -> None:
        cli_cmd = (
            f"xplot render \\\n"
            f"  --input GFS_Global_0p25deg_latest.grib2 \\\n"
            f"  --step {lead_hours} \\\n"
            f"  --var HGT --level 500hPa \\\n"
            f"  --proj LambertConformal --central-lon -95.0 \\\n"
            f"  --extent -130,-60,20,60 \\\n"
            f"  --contourf --cmap turbo --levels 520:595:6 \\\n"
            f"  --wind-barbs UGRD:VGRD@850hPa \\\n"
            f"  --output ./exports/gfs_500hpa_f{lead_hours:03d}.png"
        )
        self.cli_text_edit.setPlainText(cli_cmd)

        yaml_cfg = (
            f"pipeline:\n"
            f"  source:\n"
            f"    dataset: GFS_Global_0p25deg\n"
            f"    lead_time_hours: {lead_hours}\n"
            f"    level: 500hPa\n"
            f"    fields:\n"
            f"      - geopotential_height\n"
            f"      - u_wind\n"
            f"      - v_wind\n"
            f"  spatial:\n"
            f"    projection: LambertConformal\n"
            f"    central_longitude: -95.0\n"
            f"    bounding_box:\n"
            f"      west: -130.0\n"
            f"      east: -60.0\n"
            f"      south: 20.0\n"
            f"      north: 60.0\n"
            f"  render:\n"
            f"    colormap: turbo\n"
            f"    levels: [520, 595, 6]\n"
            f"    barbs_step: 4\n"
            f"    dpi: 300\n"
        )
        self.yaml_text_edit.setPlainText(yaml_cfg)

    def _on_reset_extent(self) -> None:
        self.canvas_widget.plot_synoptic_field()
        self.extent_reset_requested.emit()

    def _on_probe_toggled(self, checked: bool) -> None:
        self.probe_triggered.emit(checked)

    def _on_export_fig(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Figure",
            "synoptic_field.png",
            "PNG Image (*.png);;PDF Document (*.pdf);;SVG Vector (*.svg)",
        )
        if file_path:
            self.canvas_widget.figure.savefig(file_path, dpi=300, bbox_inches="tight")

    def set_theme(self, dark_mode: bool) -> None:
        """Update canvas and UI theme styling."""
        self._dark_mode = dark_mode
        self.canvas_widget.apply_theme(dark_mode)

        # When run standalone or integrated, ensure centralized styling aligns
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(get_theme_qss(dark_mode))
