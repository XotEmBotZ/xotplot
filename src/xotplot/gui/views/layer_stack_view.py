"""Layer stack and compositing view for meteorological vector and raster overlays."""

from typing import Any, Dict, List, Optional
import numpy as np
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from xotplot.engine import get_qt_engine_bridge
from xotplot.gui.engine_canvas import EngineCanvasWidget


class LayerStackView(QWidget):
    """View managing multi-layer composite overlay, Z-ordering, styling, and vector feature store."""

    layer_changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.dark_mode = True
        self._current_job_id: Optional[str] = None
        self.engine_bridge = get_qt_engine_bridge()
        self.engine_bridge.job_completed.connect(self._on_render_completed)

        # Layer definition schema:
        # id, name, visible, locked, type ('vector', 'contour', 'raster'), fill_mode, color, alpha, stroke_width, contour_intervals
        self._layers: List[Dict[str, Any]] = [
            {
                "id": "severe_outlooks",
                "name": "SPC Severe Outlooks",
                "visible": True,
                "locked": False,
                "type": "vector",
                "fill_mode": "Solid",
                "color": "#e11d48",  # Rose/Red
                "alpha": 0.45,
                "stroke_width": 2.0,
                "contour_intervals": 5,
            },
            {
                "id": "rivers",
                "name": "Major Rivers & Hydro",
                "visible": True,
                "locked": False,
                "type": "vector",
                "fill_mode": "Outline Only",
                "color": "#38bdf8",  # Sky blue
                "alpha": 0.8,
                "stroke_width": 1.5,
                "contour_intervals": 4,
            },
            {
                "id": "us_states",
                "name": "US State Boundaries",
                "visible": True,
                "locked": False,
                "type": "vector",
                "fill_mode": "Outline Only",
                "color": "#94a3b8",  # Muted slate
                "alpha": 0.9,
                "stroke_width": 1.2,
                "contour_intervals": 1,
            },
            {
                "id": "height_contours",
                "name": "500 hPa Geopotential Height",
                "visible": True,
                "locked": False,
                "type": "contour",
                "fill_mode": "Outline Only",
                "color": "#f59e0b",  # Amber
                "alpha": 0.85,
                "stroke_width": 1.6,
                "contour_intervals": 6,
            },
            {
                "id": "radar_reflectivity",
                "name": "Composite Radar Reflectivity",
                "visible": True,
                "locked": False,
                "type": "raster",
                "fill_mode": "Color Filled",
                "color": "#10b981",  # Emerald
                "alpha": 0.65,
                "stroke_width": 1.0,
                "contour_intervals": 10,
            },
        ]

        self._selected_index = 0
        self._init_ui()
        self._populate_table()
        self._sync_inspector()
        self.render_composite()

    def _init_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(8)

        # Left controls panel
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setMinimumWidth(430)
        scroll.setMaximumWidth(500)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(4, 4, 8, 4)
        left_layout.setSpacing(10)

        # 1. Layer Stack Table & Management Buttons
        stack_group = QGroupBox("Z-Order Layer Stack", self)
        stack_layout = QVBoxLayout(stack_group)
        stack_layout.setSpacing(6)

        # Action toolbar for layers
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(4)

        self.btn_move_up = QPushButton("▲ Up")
        self.btn_move_up.setToolTip("Move layer up in Z-stack (draws on top)")
        self.btn_move_up.clicked.connect(self._on_move_up)
        toolbar_layout.addWidget(self.btn_move_up)

        self.btn_move_down = QPushButton("▼ Down")
        self.btn_move_down.setToolTip("Move layer down in Z-stack")
        self.btn_move_down.clicked.connect(self._on_move_down)
        toolbar_layout.addWidget(self.btn_move_down)

        self.btn_duplicate = QPushButton("Duplicate")
        self.btn_duplicate.setToolTip("Duplicate selected layer")
        self.btn_duplicate.clicked.connect(self._on_duplicate)
        toolbar_layout.addWidget(self.btn_duplicate)

        self.btn_remove = QPushButton("Remove")
        self.btn_remove.setToolTip("Remove selected layer")
        self.btn_remove.clicked.connect(self._on_remove)
        toolbar_layout.addWidget(self.btn_remove)

        stack_layout.addLayout(toolbar_layout)

        # Table widget
        self.table = QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Vis", "Lock", "Layer Name", "Type"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setMinimumHeight(170)
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)
        stack_layout.addWidget(self.table)

        left_layout.addWidget(stack_group)

        # 2. Workspace Vector Feature Store
        store_group = QGroupBox("Workspace Vector Feature Store", self)
        store_layout = QVBoxLayout(store_group)
        store_layout.setSpacing(6)

        store_desc = QLabel("Quickly add preset or external vector geographic datasets:")
        store_desc.setStyleSheet("color: #87929a; font-size: 10px;")
        store_layout.addWidget(store_desc)

        store_buttons = QHBoxLayout()
        store_buttons.setSpacing(4)

        self.btn_add_shp = QPushButton("+ Add .shp")
        self.btn_add_shp.setObjectName("primaryAction")
        self.btn_add_shp.clicked.connect(self._on_add_shapefile)
        store_buttons.addWidget(self.btn_add_shp)

        self.btn_add_states = QPushButton("+ US States")
        self.btn_add_states.clicked.connect(lambda: self._add_preset_vector("US States", "#94a3b8"))
        store_buttons.addWidget(self.btn_add_states)

        self.btn_add_outlooks = QPushButton("+ Severe Outlooks")
        self.btn_add_outlooks.clicked.connect(lambda: self._add_preset_vector("Severe Outlooks", "#e11d48"))
        store_buttons.addWidget(self.btn_add_outlooks)

        self.btn_add_rivers = QPushButton("+ Rivers")
        self.btn_add_rivers.clicked.connect(lambda: self._add_preset_vector("Rivers", "#38bdf8"))
        store_buttons.addWidget(self.btn_add_rivers)

        store_layout.addLayout(store_buttons)
        left_layout.addWidget(store_group)

        # 3. Layer Symbology & Attributes Inspector
        insp_group = QGroupBox("Layer Symbology & Attributes Inspector", self)
        insp_layout = QGridLayout(insp_group)
        insp_layout.setSpacing(6)

        self.lbl_active_name = QLabel("Selected Layer: None")
        self.lbl_active_name.setStyleSheet("font-weight: bold; color: #8ed5ff;")
        insp_layout.addWidget(self.lbl_active_name, 0, 0, 1, 2)

        insp_layout.addWidget(QLabel("Fill Mode:"), 1, 0)
        self.combo_fill_mode = QComboBox()
        self.combo_fill_mode.addItems(["Solid", "Outline Only", "Hatched", "Color Filled"])
        self.combo_fill_mode.currentTextChanged.connect(self._on_fill_mode_changed)
        insp_layout.addWidget(self.combo_fill_mode, 1, 1)

        insp_layout.addWidget(QLabel("Layer Color:"), 2, 0)
        color_row = QHBoxLayout()
        self.btn_color_picker = QPushButton()
        self.btn_color_picker.setFixedSize(36, 22)
        self.btn_color_picker.clicked.connect(self._on_pick_color)
        self.lbl_color_hex = QLabel("#ffffff")
        color_row.addWidget(self.btn_color_picker)
        color_row.addWidget(self.lbl_color_hex)
        color_row.addStretch()
        insp_layout.addLayout(color_row, 2, 1)

        insp_layout.addWidget(QLabel("Opacity (Alpha):"), 3, 0)
        alpha_row = QHBoxLayout()
        self.slider_alpha = QSlider(Qt.Orientation.Horizontal)
        self.slider_alpha.setRange(0, 100)
        self.slider_alpha.setValue(80)
        self.slider_alpha.valueChanged.connect(self._on_alpha_slider_changed)
        self.lbl_alpha_val = QLabel("0.80")
        self.lbl_alpha_val.setFixedWidth(35)
        alpha_row.addWidget(self.slider_alpha)
        alpha_row.addWidget(self.lbl_alpha_val)
        insp_layout.addLayout(alpha_row, 3, 1)

        insp_layout.addWidget(QLabel("Stroke Width (pt):"), 4, 0)
        self.spin_stroke = QDoubleSpinBox()
        self.spin_stroke.setRange(0.2, 10.0)
        self.spin_stroke.setSingleStep(0.2)
        self.spin_stroke.setValue(1.5)
        self.spin_stroke.valueChanged.connect(self._on_stroke_changed)
        insp_layout.addWidget(self.spin_stroke, 4, 1)

        insp_layout.addWidget(QLabel("Contour Intervals:"), 5, 0)
        self.spin_intervals = QSpinBox()
        self.spin_intervals.setRange(1, 50)
        self.spin_intervals.setValue(6)
        self.spin_intervals.valueChanged.connect(self._on_intervals_changed)
        insp_layout.addWidget(self.spin_intervals, 5, 1)

        left_layout.addWidget(insp_group)

        # Refresh button
        self.btn_redraw = QPushButton("Apply & Render Stack")
        self.btn_redraw.setObjectName("primaryAction")
        self.btn_redraw.clicked.connect(self.render_composite)
        left_layout.addWidget(self.btn_redraw)

        left_layout.addStretch()
        scroll.setWidget(left_widget)
        main_layout.addWidget(scroll)

        # Right Map Canvas
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)

        self.canvas_widget = EngineCanvasWidget(right_container, width=8.0, height=6.0, dpi=100)
        self.canvas = self.canvas_widget
        right_layout.addWidget(self.canvas_widget)

        self.lbl_status = QLabel("Composite Layer Stack Ready")
        self.lbl_status.setStyleSheet("color: #87929a; font-size: 10px; padding: 2px 4px;")
        right_layout.addWidget(self.lbl_status)

        main_layout.addWidget(right_container, stretch=1)

    def _populate_table(self) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(len(self._layers))

        for row, layer in enumerate(self._layers):
            # Visibility checkbox
            vis_check = QCheckBox()
            vis_check.setChecked(layer["visible"])
            vis_check.stateChanged.connect(lambda state, r=row: self._on_vis_toggled(r, state))
            vis_widget = QWidget()
            vis_box = QHBoxLayout(vis_widget)
            vis_box.addWidget(vis_check)
            vis_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
            vis_box.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(row, 0, vis_widget)

            # Lock checkbox
            lock_check = QCheckBox()
            lock_check.setChecked(layer["locked"])
            lock_check.stateChanged.connect(lambda state, r=row: self._on_lock_toggled(r, state))
            lock_widget = QWidget()
            lock_box = QHBoxLayout(lock_widget)
            lock_box.addWidget(lock_check)
            lock_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lock_box.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(row, 1, lock_widget)

            # Name item
            name_item = QTableWidgetItem(layer["name"])
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, 2, name_item)

            # Type item
            type_item = QTableWidgetItem(layer["type"].capitalize())
            type_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, 3, type_item)

        self.table.blockSignals(False)
        if 0 <= self._selected_index < len(self._layers):
            self.table.selectRow(self._selected_index)

    def _on_vis_toggled(self, row: int, state: int) -> None:
        if 0 <= row < len(self._layers):
            self._layers[row]["visible"] = (state == 2 or state == Qt.CheckState.Checked.value)
            self.render_composite()

    def _on_lock_toggled(self, row: int, state: int) -> None:
        if 0 <= row < len(self._layers):
            self._layers[row]["locked"] = (state == 2 or state == Qt.CheckState.Checked.value)
            if self._selected_index == row:
                self._sync_inspector()

    def _on_table_selection_changed(self) -> None:
        selected_rows = self.table.selectionModel().selectedRows()
        if selected_rows:
            self._selected_index = selected_rows[0].row()
            self._sync_inspector()

    def _sync_inspector(self) -> None:
        if not (0 <= self._selected_index < len(self._layers)):
            self.lbl_active_name.setText("Selected Layer: None")
            return

        layer = self._layers[self._selected_index]
        self.lbl_active_name.setText(f"Selected: {layer['name']} ({layer['type']})")

        # Update controls
        self.combo_fill_mode.blockSignals(True)
        self.combo_fill_mode.setCurrentText(layer.get("fill_mode", "Solid"))
        self.combo_fill_mode.blockSignals(False)

        col = layer.get("color", "#ffffff")
        self.lbl_color_hex.setText(col)
        self.btn_color_picker.setStyleSheet(f"background-color: {col}; border: 1px solid #555; border-radius: 2px;")

        alpha_int = int(round(layer.get("alpha", 0.8) * 100))
        self.slider_alpha.blockSignals(True)
        self.slider_alpha.setValue(alpha_int)
        self.lbl_alpha_val.setText(f"{layer.get('alpha', 0.8):.2f}")
        self.slider_alpha.blockSignals(False)

        self.spin_stroke.blockSignals(True)
        self.spin_stroke.setValue(layer.get("stroke_width", 1.5))
        self.spin_stroke.blockSignals(False)

        self.spin_intervals.blockSignals(True)
        self.spin_intervals.setValue(layer.get("contour_intervals", 6))
        self.spin_intervals.blockSignals(False)

        # Lock disable logic
        is_locked = layer.get("locked", False)
        self.combo_fill_mode.setEnabled(not is_locked)
        self.btn_color_picker.setEnabled(not is_locked)
        self.slider_alpha.setEnabled(not is_locked)
        self.spin_stroke.setEnabled(not is_locked)
        self.spin_intervals.setEnabled(not is_locked)

    def _on_fill_mode_changed(self, mode: str) -> None:
        if 0 <= self._selected_index < len(self._layers):
            self._layers[self._selected_index]["fill_mode"] = mode
            self.render_composite()

    def _on_pick_color(self) -> None:
        if 0 <= self._selected_index < len(self._layers):
            initial = QColor(self._layers[self._selected_index].get("color", "#ffffff"))
            color = QColorDialog.getColor(initial, self, "Select Layer Color")
            if color.isValid():
                hex_str = color.name()
                self._layers[self._selected_index]["color"] = hex_str
                self.lbl_color_hex.setText(hex_str)
                self.btn_color_picker.setStyleSheet(f"background-color: {hex_str}; border: 1px solid #555; border-radius: 2px;")
                self.render_composite()

    def _on_alpha_slider_changed(self, val: int) -> None:
        if 0 <= self._selected_index < len(self._layers):
            alpha = val / 100.0
            self._layers[self._selected_index]["alpha"] = alpha
            self.lbl_alpha_val.setText(f"{alpha:.2f}")
            self.render_composite()

    def _on_stroke_changed(self, val: float) -> None:
        if 0 <= self._selected_index < len(self._layers):
            self._layers[self._selected_index]["stroke_width"] = val
            self.render_composite()

    def _on_intervals_changed(self, val: int) -> None:
        if 0 <= self._selected_index < len(self._layers):
            self._layers[self._selected_index]["contour_intervals"] = val
            self.render_composite()

    def _on_move_up(self) -> None:
        idx = self._selected_index
        if idx > 0:
            self._layers[idx], self._layers[idx - 1] = self._layers[idx - 1], self._layers[idx]
            self._selected_index = idx - 1
            self._populate_table()
            self.render_composite()

    def _on_move_down(self) -> None:
        idx = self._selected_index
        if 0 <= idx < len(self._layers) - 1:
            self._layers[idx], self._layers[idx + 1] = self._layers[idx + 1], self._layers[idx]
            self._selected_index = idx + 1
            self._populate_table()
            self.render_composite()

    def _on_duplicate(self) -> None:
        if 0 <= self._selected_index < len(self._layers):
            orig = self._layers[self._selected_index]
            copy_layer = dict(orig)
            copy_layer["name"] = f"{orig['name']} (Copy)"
            self._layers.insert(self._selected_index + 1, copy_layer)
            self._selected_index += 1
            self._populate_table()
            self.render_composite()

    def _on_remove(self) -> None:
        if 0 <= self._selected_index < len(self._layers):
            if len(self._layers) > 1:
                del self._layers[self._selected_index]
                self._selected_index = max(0, self._selected_index - 1)
                self._populate_table()
                self._sync_inspector()
                self.render_composite()

    def _on_add_shapefile(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Shapefile", "", "Shapefiles (*.shp);;All Files (*)")
        if file_path:
            name = file_path.split("/")[-1].replace(".shp", "")
            self._layers.insert(0, {
                "id": f"shp_{len(self._layers)}",
                "name": f"Shapefile: {name}",
                "visible": True,
                "locked": False,
                "type": "vector",
                "fill_mode": "Outline Only",
                "color": "#a855f7",
                "alpha": 0.85,
                "stroke_width": 1.5,
                "contour_intervals": 1,
            })
            self._selected_index = 0
            self._populate_table()
            self._sync_inspector()
            self.render_composite()

    def _add_preset_vector(self, name: str, default_color: str) -> None:
        new_layer = {
            "id": f"preset_{len(self._layers)}_{name.lower().replace(' ', '_')}",
            "name": name,
            "visible": True,
            "locked": False,
            "type": "vector",
            "fill_mode": "Solid" if "Outlook" in name else "Outline Only",
            "color": default_color,
            "alpha": 0.5 if "Outlook" in name else 0.8,
            "stroke_width": 1.5,
            "contour_intervals": 3,
        }
        self._layers.insert(0, new_layer)
        self._selected_index = 0
        self._populate_table()
        self._sync_inspector()
        self.render_composite()

    def set_theme(self, dark_mode: bool) -> None:
        """Switch dark or light theme colors (canvas always stays in light theme)."""
        self.dark_mode = False
        self.render_composite()

    def render_composite(self) -> None:
        """Render multi-layer composite overlay by delegating to engine process."""
        self._current_job_id = self.engine_bridge.submit(
            "composite",
            {"layers": self._layers},
            channel="composite",
            width=8.0,
            height=6.0,
            dpi=100,
            cancel_previous=True,
        )
        active_count = sum(1 for lyr in self._layers if lyr.get("visible", True))
        self.lbl_status.setText(f"Rendering {active_count} layers | Z-Stack Depth: {len(self._layers)}")
        self.layer_changed.emit()

    def _on_render_completed(self, job_id: str, image_data: bytes) -> None:
        if job_id == self._current_job_id:
            self.canvas_widget.set_image_bytes(image_data)
            active_count = sum(1 for lyr in self._layers if lyr.get("visible", True))
            self.lbl_status.setText(f"Rendered {active_count} layers | Z-Stack Depth: {len(self._layers)}")
