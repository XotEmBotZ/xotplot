"""Variables and dimensions inspector view with hierarchical tree and plotting controls."""

from __future__ import annotations

from typing import Optional
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from xotplot.engine import (
    get_qt_engine_bridge,
    render_variable_cross_section,
    render_variable_profile,
)
from xotplot.gui.engine_canvas import EngineCanvasWidget
from xotplot.gui.theme import get_theme_qss
from xotplot.spec import DataPlotSpec, DataSliceSpec, DatasetMetadata, RegionViewSpec


class VariablesInspectorView(QWidget):
    """View providing hierarchical variable tree, statistical summaries, colormap controls, and plot requests."""

    variable_selected = pyqtSignal(str)
    slice_mode_changed = pyqtSignal(str)
    coordinate_changed = pyqtSignal(dict)
    plot_requested = pyqtSignal(object)  # Emits DataPlotSpec

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._dark_mode = True
        self._metadata: Optional[DatasetMetadata] = None
        self._current_var = "t2m"
        self._current_level: Optional[float] = None
        self._current_level_type: Optional[str] = "surface"
        self._current_slice_mode = "Direct Slice"
        self._current_hist_job_id: Optional[str] = None
        self._region_spec_provider: Optional[Any] = None

        self._engine_bridge = get_qt_engine_bridge()
        self._engine_bridge.job_completed.connect(self._on_engine_job_completed)
        self._engine_bridge.job_failed.connect(self._on_engine_job_failed)

        # Debounce timer for typing into numerical bounds spinboxes
        self._bounds_debounce_timer = QTimer(self)
        self._bounds_debounce_timer.setSingleShot(True)
        self._bounds_debounce_timer.setInterval(400)
        self._bounds_debounce_timer.timeout.connect(self._update_profile_plot)

        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # Splitter dividing controls/tree on left and embedded canvas plot on right
        self._splitter = QSplitter(Qt.Orientation.Horizontal, self)

        # Left Container: Tree + Colormap/Plot controls + Slicing Dock
        left_widget = QWidget(self)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.setSpacing(8)

        # 1. Searchable Hierarchical Variable Tree (Option 3)
        tree_group = QGroupBox("Variables Catalog (Grouped by Level Type)", left_widget)
        tree_layout = QVBoxLayout(tree_group)
        tree_layout.setContentsMargins(8, 8, 8, 8)
        tree_layout.setSpacing(6)

        search_box = QHBoxLayout()
        search_box.addWidget(QLabel("Filter:"))
        self.search_edit = QLineEdit(tree_group)
        self.search_edit.setPlaceholderText("Filter variables or levels...")
        search_box.addWidget(self.search_edit)
        tree_layout.addLayout(search_box)

        self.tree = QTreeWidget(tree_group)
        self.tree.setHeaderLabels(["Parameter / Level", "Dimensions", "Units", "Long Name"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.header().setStretchLastSection(True)
        tree_layout.addWidget(self.tree)
        left_layout.addWidget(tree_group, stretch=2)

        # 2. Mandatory Colormap & Plot Styling Controls (Option 3)
        plot_ctrl_group = QGroupBox("Plot Styling & Rendering Controls", left_widget)
        plot_ctrl_grid = QGridLayout(plot_ctrl_group)
        plot_ctrl_grid.setContentsMargins(8, 8, 8, 8)
        plot_ctrl_grid.setSpacing(6)

        # Colormap picker
        plot_ctrl_grid.addWidget(QLabel("Colormap:"), 0, 0)
        self.combo_cmap = QComboBox(plot_ctrl_group)
        self.combo_cmap.addItems([
            "coolwarm", "viridis", "plasma", "magma", "turbo",
            "Blues", "YlGnBu", "Spectral_r", "Greys_r", "cividis"
        ])
        plot_ctrl_grid.addWidget(self.combo_cmap, 0, 1)

        # Plot Style (contourf, pcolormesh, contour)
        plot_ctrl_grid.addWidget(QLabel("Plot Style:"), 0, 2)
        self.combo_style = QComboBox(plot_ctrl_group)
        self.combo_style.addItems(["contourf", "pcolormesh", "contour"])
        plot_ctrl_grid.addWidget(self.combo_style, 0, 3)

        # Min / Max numerical bounds
        plot_ctrl_grid.addWidget(QLabel("Min Value:"), 1, 0)
        self.spin_vmin = QDoubleSpinBox(plot_ctrl_group)
        self.spin_vmin.setRange(-1e9, 1e9)
        self.spin_vmin.setDecimals(2)
        self.spin_vmin.setSpecialValueText("Auto")
        self.spin_vmin.setValue(-1e9)
        plot_ctrl_grid.addWidget(self.spin_vmin, 1, 1)

        plot_ctrl_grid.addWidget(QLabel("Max Value:"), 1, 2)
        self.spin_vmax = QDoubleSpinBox(plot_ctrl_group)
        self.spin_vmax.setRange(-1e9, 1e9)
        self.spin_vmax.setDecimals(2)
        self.spin_vmax.setSpecialValueText("Auto")
        self.spin_vmax.setValue(1e9)
        plot_ctrl_grid.addWidget(self.spin_vmax, 1, 3)

        # Contour levels count & buttons
        plot_ctrl_grid.addWidget(QLabel("Contour Levels:"), 2, 0)
        self.spin_levels = QSpinBox(plot_ctrl_group)
        self.spin_levels.setRange(5, 60)
        self.spin_levels.setValue(15)
        plot_ctrl_grid.addWidget(self.spin_levels, 2, 1)

        self.btn_reset_bounds = QPushButton("Reset Min/Max (Auto)", plot_ctrl_group)
        self.btn_reset_bounds.setObjectName("primaryAction")
        self.btn_reset_bounds.setToolTip("Reset numerical bounds to Auto (data min/max)")
        plot_ctrl_grid.addWidget(self.btn_reset_bounds, 2, 2, 1, 2)

        left_layout.addWidget(plot_ctrl_group)

        # 3. Dimension Reduction & Slicing Dock
        reduction_group = QGroupBox("Dimension Reduction & Profile Slicing", left_widget)
        reduction_layout = QHBoxLayout(reduction_group)
        reduction_layout.setContentsMargins(8, 8, 8, 8)
        reduction_layout.setSpacing(10)

        self.rb_direct = QRadioButton("Direct Slice", reduction_group)
        self.rb_direct.setChecked(True)
        self.rb_zonal = QRadioButton("Zonal Mean (d/dλ)", reduction_group)
        self.rb_time = QRadioButton("Time Mean (d/dt)", reduction_group)
        self.rb_vert = QRadioButton("Vertical Integral (∫dp)", reduction_group)

        reduction_layout.addWidget(self.rb_direct)
        reduction_layout.addWidget(self.rb_zonal)
        reduction_layout.addWidget(self.rb_time)
        reduction_layout.addWidget(self.rb_vert)

        left_layout.addWidget(reduction_group)
        self._splitter.addWidget(left_widget)

        # Right Container: Diagnostic Canvas (Profile / Cross-Section)
        right_widget = QWidget(self)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(4, 4, 4, 4)
        right_layout.setSpacing(6)

        top_bar = QHBoxLayout()
        self.plot_title_lbl = QLabel(f"Field & Distribution: {self._current_var.upper()}")
        self.plot_title_lbl.setStyleSheet("font-weight: bold; font-size: 12px;")
        top_bar.addWidget(self.plot_title_lbl)
        top_bar.addStretch()

        self.btn_refresh_plot = QPushButton("Recompute Plots", right_widget)
        top_bar.addWidget(self.btn_refresh_plot)
        right_layout.addLayout(top_bar)

        self.canvas_widget = EngineCanvasWidget(right_widget, width=6.5, height=6.0)
        right_layout.addWidget(self.canvas_widget, stretch=1)

        self._splitter.addWidget(right_widget)

        # Sizing
        self._splitter.setStretchFactor(0, 3)
        self._splitter.setStretchFactor(1, 2)

        main_layout.addWidget(self._splitter)

        # Signal connections
        self.search_edit.textChanged.connect(self._on_filter_changed)
        self.tree.itemSelectionChanged.connect(self._on_tree_selection_changed)
        self.combo_cmap.currentTextChanged.connect(lambda _: self._update_profile_plot())
        self.combo_style.currentTextChanged.connect(lambda _: self._update_profile_plot())
        self.spin_vmin.valueChanged.connect(self._on_bounds_spin_changed)
        self.spin_vmax.valueChanged.connect(self._on_bounds_spin_changed)
        self.spin_levels.valueChanged.connect(lambda _: self._update_profile_plot())
        self.btn_reset_bounds.clicked.connect(self._on_reset_bounds_clicked)
        self.btn_refresh_plot.clicked.connect(self._update_profile_plot)
        self.rb_direct.toggled.connect(self._on_slice_mode_toggled)
        self.rb_zonal.toggled.connect(self._on_slice_mode_toggled)
        self.rb_time.toggled.connect(self._on_slice_mode_toggled)
        self.rb_vert.toggled.connect(self._on_slice_mode_toggled)

    def set_region_spec_provider(self, provider: Any) -> None:
        """Set a callable that returns the current RegionViewSpec from ProjectionRegionView."""
        self._region_spec_provider = provider

    def load_dataset_metadata(self, meta: DatasetMetadata) -> None:
        """Populate the hierarchical variable tree from real DatasetMetadata."""
        self._metadata = meta
        self.tree.clear()

        # Category root items
        surface_root = QTreeWidgetItem(self.tree, ["Surface & 2D Diagnostic", "", "", ""])
        isobaric_root = QTreeWidgetItem(self.tree, ["Isobaric Levels (Upper Air)", "", "", ""])
        soil_root = QTreeWidgetItem(self.tree, ["Soil & Subsurface Layers", "", "", ""])
        other_root = QTreeWidgetItem(self.tree, ["Other Variables", "", "", ""])

        # Fetch isobaric levels list if available
        iso_levels = [1000.0, 850.0, 500.0, 300.0, 250.0]
        if "level" in meta.coordinates and meta.coordinates["level"].discrete_values:
            iso_levels = sorted(meta.coordinates["level"].discrete_values, reverse=True)

        # Create level child nodes under Isobaric root
        level_nodes: dict[float, QTreeWidgetItem] = {}
        for lvl in iso_levels:
            lvl_node = QTreeWidgetItem(isobaric_root, [f"{lvl:.0f} hPa Level", "", "", f"Isobaric Surface {lvl} hPa"])
            level_nodes[lvl] = lvl_node

        # Populate variables into appropriate categories
        for vname, vinfo in meta.variables.items():
            dims_str = f"({', '.join(vinfo.dimensions)})"
            units_str = vinfo.units or ""
            desc_str = vinfo.long_name or ""

            if "level" in vinfo.dimensions:
                # Add variable under each isobaric level node
                for lvl, l_node in level_nodes.items():
                    var_item = QTreeWidgetItem(l_node, [vname, dims_str, units_str, desc_str])
                    var_item.setData(0, Qt.ItemDataRole.UserRole, {
                        "var": vname,
                        "level": lvl,
                        "level_type": "isobaric",
                    })
            elif "soilLayer" in vinfo.dimensions:
                var_item = QTreeWidgetItem(soil_root, [vname, dims_str, units_str, desc_str])
                var_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "var": vname,
                    "level": None,
                    "level_type": "soilLayer",
                })
            elif len(vinfo.dimensions) <= 3:
                var_item = QTreeWidgetItem(surface_root, [vname, dims_str, units_str, desc_str])
                var_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "var": vname,
                    "level": None,
                    "level_type": "surface",
                })
            else:
                var_item = QTreeWidgetItem(other_root, [vname, dims_str, units_str, desc_str])
                var_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "var": vname,
                    "level": None,
                    "level_type": "other",
                })

        surface_root.setExpanded(True)
        isobaric_root.setExpanded(True)
        if iso_levels and iso_levels[0] in level_nodes:
            level_nodes[iso_levels[0]].setExpanded(True)

        # Select first surface variable
        if surface_root.childCount() > 0:
            self.tree.setCurrentItem(surface_root.child(0))

    def _on_filter_changed(self, text: str) -> None:
        """Filter tree items by query text."""
        query = text.lower().strip()
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            self._filter_tree_item(top, query)

    def _filter_tree_item(self, item: QTreeWidgetItem, query: str) -> bool:
        matches = any(query in item.text(col).lower() for col in range(item.columnCount()))
        child_matches = False
        for c in range(item.childCount()):
            child = item.child(c)
            if self._filter_tree_item(child, query):
                child_matches = True

        visible = matches or child_matches or (not query)
        item.setHidden(not visible)
        if child_matches and query:
            item.setExpanded(True)
        return visible

    def _on_tree_selection_changed(self) -> None:
        selected = self.tree.selectedItems()
        if not selected:
            return

        item = selected[0]
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        self._current_var = data["var"]
        self._current_level = data["level"]
        self._current_level_type = data["level_type"]

        lvl_txt = f" ({self._current_level:.0f} hPa)" if self._current_level is not None else ""
        self.plot_title_lbl.setText(f"Diagnostic Plot: {self._current_var.upper()}{lvl_txt} ({self._current_slice_mode})")
        self.variable_selected.emit(self._current_var)
        self._update_profile_plot()

    def _on_bounds_spin_changed(self) -> None:
        """Debounce numerical bounds adjustments to avoid recalculating while typing."""
        self._bounds_debounce_timer.start()

    def _on_reset_bounds_clicked(self) -> None:
        """Reset both min and max to Auto (-1e9 and 1e9), triggering immediate redraw."""
        self._bounds_debounce_timer.stop()
        self.spin_vmin.blockSignals(True)
        self.spin_vmax.blockSignals(True)
        self.spin_vmin.setValue(-1e9)
        self.spin_vmax.setValue(1e9)
        self.spin_vmin.blockSignals(False)
        self.spin_vmax.blockSignals(False)
        self._update_profile_plot()

    def _on_plot_to_viewport_clicked(self) -> None:
        """Emit DataPlotSpec to MainWindow to render the selected field on the map viewport."""
        vmin = self.spin_vmin.value() if self.spin_vmin.value() > -1e9 else None
        vmax = self.spin_vmax.value() if self.spin_vmax.value() < 1e9 else None

        slice_spec = DataSliceSpec(
            variable=self._current_var,
            level_type=self._current_level_type,
            level_value=self._current_level,
            time_index=0,
        )

        plot_spec = DataPlotSpec(
            dataset_id=self._metadata.dataset_id if self._metadata else None,
            slice_spec=slice_spec,
            plot_type=self.combo_style.currentText(),  # type: ignore[arg-type]
            colormap=self.combo_cmap.currentText(),
            vmin=vmin,
            vmax=vmax,
            num_levels=self.spin_levels.value(),
            show_colorbar=True,
            region_view=RegionViewSpec(),
        )

        self.plot_requested.emit(plot_spec)

    def _on_slice_mode_toggled(self) -> None:
        if self.rb_direct.isChecked():
            self._current_slice_mode = "Direct Slice"
        elif self.rb_zonal.isChecked():
            self._current_slice_mode = "Zonal Mean"
        elif self.rb_time.isChecked():
            self._current_slice_mode = "Time Mean"
        elif self.rb_vert.isChecked():
            self._current_slice_mode = "Vertical Integral"

        lvl_txt = f" ({self._current_level:.0f} hPa)" if self._current_level is not None else ""
        self.plot_title_lbl.setText(f"Field & Distribution: {self._current_var.upper()}{lvl_txt} ({self._current_slice_mode})")
        self.slice_mode_changed.emit(self._current_slice_mode)
        self._update_profile_plot()

    def _update_profile_plot(self) -> None:
        """Render stacked 2D plot (top) and distribution histogram (bottom) via engine."""
        vmin = self.spin_vmin.value() if self.spin_vmin.value() > -1e9 else None
        vmax = self.spin_vmax.value() if self.spin_vmax.value() < 1e9 else None

        reg_spec_dict = None
        if self._region_spec_provider is not None:
            try:
                reg_spec = self._region_spec_provider()
                if reg_spec is not None:
                    reg_spec_dict = reg_spec.model_dump()
            except Exception:
                reg_spec_dict = None

        self._current_hist_job_id = self._engine_bridge.submit(
            job_type="slice_histogram",
            params={
                "var_name": self._current_var,
                "level_val": self._current_level,
                "dataset_id": self._metadata.dataset_id if self._metadata else None,
                "plot_type": self.combo_style.currentText(),
                "colormap": self.combo_cmap.currentText(),
                "vmin": vmin,
                "vmax": vmax,
                "num_levels": self.spin_levels.value(),
                "region_spec": reg_spec_dict,
            },
            channel="inspector_hist",
            cancel_previous=True,
            width=6.5,
            height=6.0,
        )

    def _on_engine_job_completed(self, job_id: str, image_data: bytes) -> None:
        if job_id == self._current_hist_job_id:
            self.canvas_widget.set_image_bytes(image_data)

    def _on_engine_job_failed(self, job_id: str, error_msg: str) -> None:
        if job_id == self._current_hist_job_id:
            self.plot_title_lbl.setText(f"Plot Error: {error_msg[:60]}")

    def set_theme(self, dark_mode: bool) -> None:
        """Update canvas and UI theme styling."""
        self._dark_mode = dark_mode
        self.canvas_widget.apply_theme(dark_mode)
        self._update_profile_plot()

        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(get_theme_qss(dark_mode))
