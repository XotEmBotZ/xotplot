"""Variables and dimensions inspector view with hierarchical tree, title configurator, and PlotConfig store."""

from __future__ import annotations

from typing import Any, Optional
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
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
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from xotplot.constants import (
    DEFAULT_GLOBAL_TITLE,
    DEFAULT_SUBTITLE_POST,
    DEFAULT_SUBTITLE_PRE,
    DEFAULT_SUBTITLE_TEMPLATE,
    DEFAULT_VAR_TEMPLATE,
    WIND_BARB_COLORS,
)
from xotplot.engine import get_qt_engine_bridge
from xotplot.engine.plotting.renderer import is_wind_variable
from xotplot.gui.engine_canvas import EngineCanvasWidget
from xotplot.gui.theme import get_theme_qss
from xotplot.spec import (
    DataPlotSpec,
    DataSliceSpec,
    DatasetMetadata,
    GlobalTitleSpec,
    PlotConfig,
    RegionViewSpec,
    VariableTitleSpec,
)


class VariablesInspectorView(QWidget):
    """View providing hierarchical variable tree, statistical summaries, title settings, and PlotConfig store."""

    variable_selected = pyqtSignal(str)
    coordinate_changed = pyqtSignal(dict)
    plot_requested = pyqtSignal(object)  # Emits DataPlotSpec
    plotconfig_changed = pyqtSignal(list)  # Emits list[PlotConfig]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._dark_mode = True
        self._metadata: Optional[DatasetMetadata] = None
        self._current_var = "t2m"
        self._current_level: Optional[float] = None
        self._current_level_type: Optional[str] = "surface"
        self._current_hist_job_id: Optional[str] = None
        self._region_spec_provider: Optional[Any] = None
        self._global_title_provider: Optional[Any] = None

        # Centralized plotconfig list
        self._plot_configs: list[PlotConfig] = []
        self._editing_config_id: Optional[str] = None

        self._engine_bridge = get_qt_engine_bridge()
        self._engine_bridge.job_completed.connect(self._on_engine_job_completed)
        self._engine_bridge.job_failed.connect(self._on_engine_job_failed)

        # Unified debounce timer for plot re-renders across all rapid user inputs
        self._render_debounce_timer = QTimer(self)
        self._render_debounce_timer.setSingleShot(True)
        self._render_debounce_timer.setInterval(450)
        self._render_debounce_timer.timeout.connect(self._update_profile_plot)

        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # Outer Vertical Splitter separating top (Controls + Canvas) and bottom sidebar (PlotConfig list)
        self._v_splitter = QSplitter(Qt.Orientation.Vertical, self)
        self._v_splitter.setHandleWidth(6)
        self._v_splitter.setChildrenCollapsible(False)

        # Top Horizontal Splitter: Left Controls / Tree and Right embedded canvas
        self._h_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self._h_splitter.setHandleWidth(6)
        self._h_splitter.setChildrenCollapsible(False)

        # Left Container with ScrollArea for controls
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setMinimumWidth(260)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(4, 4, 8, 4)
        left_layout.setSpacing(8)

        # 1. Searchable Hierarchical Variable Tree
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
        self.tree.setMinimumHeight(160)
        tree_layout.addWidget(self.tree)
        left_layout.addWidget(tree_group)

        # 2. Variable Text Template Section (1 slot with placeholders; Global Title and Subtitle are in Viewport)
        self.title_group = QGroupBox("Variable Title Configuration", left_widget)
        title_vbox = QVBoxLayout(self.title_group)
        title_vbox.setContentsMargins(8, 8, 8, 8)
        title_vbox.setSpacing(6)

        # Single Slot for Variable Specific Text (with placeholders {name}, {long_name}, {level}, {units})
        row_var_slot = QVBoxLayout()
        lbl_var_header = QLabel("Variable Text Template (1 slot):")
        lbl_var_header.setStyleSheet("font-weight: bold; font-size: 11px;")
        row_var_slot.addWidget(lbl_var_header)

        self.edit_var_template = QLineEdit(self.title_group)
        self.edit_var_template.setText(DEFAULT_VAR_TEMPLATE)
        self.edit_var_template.setPlaceholderText("Placeholders: {name}, {long_name}, {level}, {units}")
        row_var_slot.addWidget(self.edit_var_template)

        lbl_tokens_hint = QLabel("Placeholders: {name} | {long_name} | {level} | {units}")
        lbl_tokens_hint.setStyleSheet("color: #87929a; font-size: 10px;")
        row_var_slot.addWidget(lbl_tokens_hint)
        title_vbox.addLayout(row_var_slot)

        # Live Title & Subtitle Preview computed with Global Viewport settings
        self.lbl_title_preview = QLabel("Title Preview: —", self.title_group)
        self.lbl_title_preview.setStyleSheet(
            "background: rgba(148, 163, 184, 0.15); border-radius: 4px; padding: 4px 6px; font-size: 11px; font-weight: bold;"
        )
        self.lbl_title_preview.setWordWrap(True)
        title_vbox.addWidget(self.lbl_title_preview)

        left_layout.addWidget(self.title_group)

        # 3. Colormap & Plot Styling Controls
        self.plot_ctrl_group = QGroupBox("Plot Styling & Rendering Controls", left_widget)
        plot_ctrl_grid = QGridLayout(self.plot_ctrl_group)
        plot_ctrl_grid.setContentsMargins(8, 8, 8, 8)
        plot_ctrl_grid.setSpacing(6)

        plot_ctrl_grid.addWidget(QLabel("Colormap:"), 0, 0)
        self.combo_cmap = QComboBox(self.plot_ctrl_group)
        self.combo_cmap.addItems([
            "coolwarm", "viridis", "plasma", "magma", "turbo",
            "Blues", "YlGnBu", "Spectral_r", "Greys_r", "cividis"
        ])
        plot_ctrl_grid.addWidget(self.combo_cmap, 0, 1)

        plot_ctrl_grid.addWidget(QLabel("Plot Style:"), 0, 2)
        self.combo_style = QComboBox(self.plot_ctrl_group)
        self.combo_style.addItems(["contourf", "pcolormesh", "contour"])
        plot_ctrl_grid.addWidget(self.combo_style, 0, 3)

        plot_ctrl_grid.addWidget(QLabel("Min Value:"), 1, 0)
        self.spin_vmin = QDoubleSpinBox(self.plot_ctrl_group)
        self.spin_vmin.setRange(-1e9, 1e9)
        self.spin_vmin.setDecimals(2)
        self.spin_vmin.setSpecialValueText("Auto")
        self.spin_vmin.setValue(-1e9)
        plot_ctrl_grid.addWidget(self.spin_vmin, 1, 1)

        plot_ctrl_grid.addWidget(QLabel("Max Value:"), 1, 2)
        self.spin_vmax = QDoubleSpinBox(self.plot_ctrl_group)
        self.spin_vmax.setRange(-1e9, 1e9)
        self.spin_vmax.setDecimals(2)
        self.spin_vmax.setSpecialValueText("Auto")
        self.spin_vmax.setValue(1e9)
        plot_ctrl_grid.addWidget(self.spin_vmax, 1, 3)

        plot_ctrl_grid.addWidget(QLabel("Contour Levels:"), 2, 0)
        self.spin_levels = QSpinBox(self.plot_ctrl_group)
        self.spin_levels.setRange(5, 60)
        self.spin_levels.setValue(15)
        plot_ctrl_grid.addWidget(self.spin_levels, 2, 1)

        self.btn_reset_bounds = QPushButton("Reset Min/Max (Auto)", self.plot_ctrl_group)
        self.btn_reset_bounds.setToolTip("Reset numerical bounds to Auto (data min/max)")
        plot_ctrl_grid.addWidget(self.btn_reset_bounds, 2, 2, 1, 2)

        left_layout.addWidget(self.plot_ctrl_group)

        # 4. Wind Barbs Configuration Panel
        self.wind_barbs_group = QGroupBox("Wind Barbs Configuration", left_widget)
        barbs_layout = QGridLayout(self.wind_barbs_group)
        barbs_layout.setContentsMargins(8, 8, 8, 8)
        barbs_layout.setSpacing(6)

        barbs_layout.addWidget(QLabel("Density (Grid Step):"), 0, 0)
        self.spin_barbs_step = QSpinBox(self.wind_barbs_group)
        self.spin_barbs_step.setRange(1, 40)
        self.spin_barbs_step.setValue(5)
        self.spin_barbs_step.setToolTip("Grid subsampling step interval (1 = dense, 10+ = sparse)")
        barbs_layout.addWidget(self.spin_barbs_step, 0, 1)

        barbs_layout.addWidget(QLabel("Barb Length:"), 0, 2)
        self.spin_barbs_length = QDoubleSpinBox(self.wind_barbs_group)
        self.spin_barbs_length.setRange(2.0, 20.0)
        self.spin_barbs_length.setSingleStep(0.5)
        self.spin_barbs_length.setValue(6.0)
        self.spin_barbs_length.setToolTip("Length scale of wind barbs in points")
        barbs_layout.addWidget(self.spin_barbs_length, 0, 3)

        barbs_layout.addWidget(QLabel("Pivot Point:"), 1, 0)
        self.combo_barbs_pivot = QComboBox(self.wind_barbs_group)
        self.combo_barbs_pivot.addItems(["middle", "tip"])
        self.combo_barbs_pivot.setToolTip("Grid point anchor point: 'middle' or 'tip'")
        barbs_layout.addWidget(self.combo_barbs_pivot, 1, 1)

        barbs_layout.addWidget(QLabel("Barb Color:"), 1, 2)
        self.combo_barbs_color = QComboBox(self.wind_barbs_group)
        for col in WIND_BARB_COLORS:
            self.combo_barbs_color.addItem(col)
        self.combo_barbs_color.setToolTip("Stroke color of wind barbs")
        barbs_layout.addWidget(self.combo_barbs_color, 1, 3)

        self.wind_barbs_group.setVisible(False)
        left_layout.addWidget(self.wind_barbs_group)

        # 5. Push Button: "Add Config"
        action_row = QHBoxLayout()
        self.btn_add_config = QPushButton("Add Config", left_widget)
        self.btn_add_config.setObjectName("primaryAction")
        self.btn_add_config.setToolTip("Push current variable configuration into the centralized PlotConfig store")
        self.btn_add_config.clicked.connect(self._on_add_config_clicked)
        action_row.addWidget(self.btn_add_config)
        left_layout.addLayout(action_row)

        left_layout.addStretch()
        scroll_area.setWidget(left_widget)
        self._h_splitter.addWidget(scroll_area)

        # Right Container: Diagnostic Canvas (Profile / Cross-Section)
        right_widget = QWidget(self)
        right_widget.setMinimumWidth(280)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(4, 4, 4, 4)
        right_layout.setSpacing(6)

        top_bar = QHBoxLayout()
        self.plot_title_lbl = QLabel(f"Field & Distribution: {self._current_var.upper()}")
        self.plot_title_lbl.setStyleSheet("font-weight: bold; font-size: 12px;")
        top_bar.addWidget(self.plot_title_lbl)
        top_bar.addStretch()

        self.btn_toggle_histogram = QPushButton("Map Only", right_widget)
        self.btn_toggle_histogram.setCheckable(True)
        # Default: Map Only checked (hide histogram by default)
        self.btn_toggle_histogram.setChecked(True)
        self.btn_toggle_histogram.setToolTip("Toggle to hide histogram and maximize map viewing space")
        top_bar.addWidget(self.btn_toggle_histogram)

        self.btn_refresh_plot = QPushButton("Recompute Plots", right_widget)
        top_bar.addWidget(self.btn_refresh_plot)
        right_layout.addLayout(top_bar)

        self.canvas_widget = EngineCanvasWidget(right_widget, width=6.5, height=6.0)
        right_layout.addWidget(self.canvas_widget, stretch=1)

        self._h_splitter.addWidget(right_widget)
        self._h_splitter.setStretchFactor(0, 3)
        self._h_splitter.setStretchFactor(1, 2)

        self._v_splitter.addWidget(self._h_splitter)

        # Bottom Sidebar: PlotConfig Store (Centralized List & Editor)
        self._init_bottom_sidebar()
        self._v_splitter.addWidget(self._bottom_sidebar)

        self._v_splitter.setStretchFactor(0, 4)
        self._v_splitter.setStretchFactor(1, 1)

        main_layout.addWidget(self._v_splitter)

        # Signal connections with debouncing across all controls
        self.search_edit.textChanged.connect(self._on_filter_changed)
        self.tree.itemSelectionChanged.connect(self._on_tree_selection_changed)
        self.combo_cmap.currentTextChanged.connect(lambda _: self._on_quick_input_changed())
        self.combo_style.currentTextChanged.connect(lambda _: self._on_quick_input_changed())
        self.spin_vmin.valueChanged.connect(lambda _: self._on_quick_input_changed())
        self.spin_vmax.valueChanged.connect(lambda _: self._on_quick_input_changed())
        self.spin_levels.valueChanged.connect(lambda _: self._on_quick_input_changed())
        self.btn_reset_bounds.clicked.connect(self._on_reset_bounds_clicked)
        self.btn_refresh_plot.clicked.connect(self._on_immediate_refresh_clicked)
        self.btn_toggle_histogram.toggled.connect(lambda _: self._update_profile_plot())
        self.spin_barbs_step.valueChanged.connect(lambda _: self._on_quick_input_changed())
        self.spin_barbs_length.valueChanged.connect(lambda _: self._on_quick_input_changed())
        self.combo_barbs_pivot.currentTextChanged.connect(lambda _: self._on_quick_input_changed())
        self.combo_barbs_color.currentTextChanged.connect(lambda _: self._on_quick_input_changed())

        # Title & Var Template signal connections
        self.edit_var_template.textChanged.connect(self._on_title_setting_changed)

        self._update_title_preview()

    def _init_bottom_sidebar(self) -> None:
        """Initialize the bottom sidebar for viewing, editing, and deleting pushed PlotConfig entries."""
        self._bottom_sidebar = QGroupBox("PlotConfig (Centralized Configuration List)", self)
        sidebar_layout = QVBoxLayout(self._bottom_sidebar)
        sidebar_layout.setContentsMargins(6, 6, 6, 6)
        sidebar_layout.setSpacing(6)

        # Toolbar above table
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        self.btn_update_config = QPushButton("Update Config", self._bottom_sidebar)
        self.btn_update_config.setToolTip("Update selected plotconfig with current UI parameters")
        self.btn_update_config.clicked.connect(self._on_update_config_clicked)
        toolbar.addWidget(self.btn_update_config)

        self.btn_delete_config = QPushButton("Delete Selected", self._bottom_sidebar)
        self.btn_delete_config.setToolTip("Delete selected plotconfig from centralized list")
        self.btn_delete_config.clicked.connect(self._on_delete_config_clicked)
        toolbar.addWidget(self.btn_delete_config)

        self.btn_clear_configs = QPushButton("Clear All", self._bottom_sidebar)
        self.btn_clear_configs.setToolTip("Clear all configurations from PlotConfig list")
        self.btn_clear_configs.clicked.connect(self._on_clear_configs_clicked)
        toolbar.addWidget(self.btn_clear_configs)

        self.btn_plot_config = QPushButton("Plot in Viewport", self._bottom_sidebar)
        self.btn_plot_config.setObjectName("primaryAction")
        self.btn_plot_config.setToolTip("Render selected plotconfig on Spatial Viewport")
        self.btn_plot_config.clicked.connect(self._on_plot_config_clicked)
        toolbar.addWidget(self.btn_plot_config)

        toolbar.addStretch()

        self.lbl_plotconfig_status = QLabel("0 configurations", self._bottom_sidebar)
        self.lbl_plotconfig_status.setStyleSheet("color: #87929a; font-size: 11px;")
        toolbar.addWidget(self.lbl_plotconfig_status)

        sidebar_layout.addLayout(toolbar)

        # Table showing pushed PlotConfig items
        self.config_table = QTableWidget(self._bottom_sidebar)
        self.config_table.setColumnCount(7)
        self.config_table.setHorizontalHeaderLabels([
            "ID", "Variable", "Level", "Style", "Colormap", "Range", "Variable Text"
        ])
        self.config_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.config_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.config_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.config_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.config_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.config_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.config_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.config_table.verticalHeader().setVisible(False)
        self.config_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.config_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.config_table.setMinimumHeight(110)
        self.config_table.itemSelectionChanged.connect(self._on_config_table_selection_changed)
        self.config_table.cellDoubleClicked.connect(lambda row, col: self._on_edit_config_clicked())

        sidebar_layout.addWidget(self.config_table)

    def set_region_spec_provider(self, provider: Any) -> None:
        """Set a callable that returns the current RegionViewSpec from ProjectionRegionView."""
        self._region_spec_provider = provider

    def set_global_title_provider(self, provider: Any) -> None:
        """Set a callable that returns the current GlobalTitleSpec from SpatialViewportView."""
        self._global_title_provider = provider

    def get_plot_configs(self) -> list[PlotConfig]:
        """Return the current centralized PlotConfig list."""
        return list(self._plot_configs)

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
        self.plot_title_lbl.setText(f"Field & Distribution: {self._current_var.upper()}{lvl_txt}")

        is_wind_var = is_wind_variable(self._current_var)
        self.plot_ctrl_group.setVisible(not is_wind_var)
        self.wind_barbs_group.setVisible(is_wind_var)

        self._update_title_preview()
        self.variable_selected.emit(self._current_var)
        self._update_profile_plot()

    def _get_current_var_title_spec(self) -> VariableTitleSpec:
        """Construct VariableTitleSpec from 1 template slot."""
        tpl = self.edit_var_template.text().strip() or DEFAULT_VAR_TEMPLATE
        return VariableTitleSpec(template=tpl)

    def _get_current_global_title_spec(self) -> GlobalTitleSpec:
        """Obtain GlobalTitleSpec from global viewport provider or fallback to defaults."""
        if self._global_title_provider:
            try:
                spec = self._global_title_provider()
                if spec is not None:
                    return spec
            except Exception:
                pass
        return GlobalTitleSpec()

    def _compute_current_title_parts(self) -> tuple[str, str, str]:
        """Compute the common Global Title, formatted Subtitle, and Variable Text."""
        var_spec = self._get_current_var_title_spec()
        global_spec = self._get_current_global_title_spec()

        long_name = None
        units = None
        if self._metadata and self._current_var in self._metadata.variables:
            vinfo = self._metadata.variables[self._current_var]
            long_name = vinfo.long_name
            units = vinfo.units

        var_text = var_spec.format_var_text(
            var_name=self._current_var,
            long_name=long_name,
            level=self._current_level,
            units=units,
        )

        main_title = global_spec.format_title(var_text)
        sub_title = global_spec.format_subtitle(var_text)
        return main_title, sub_title, var_text

    def _update_title_preview(self) -> None:
        """Update live preview text label for title and subtitle immediately."""
        main_title, sub_title, var_text = self._compute_current_title_parts()
        preview_text = f"Title (Common): {main_title}"
        if sub_title:
            preview_text += f"\nSubtitle: {sub_title}"
        else:
            preview_text += f"\nVar Text: {var_text}"
        self.lbl_title_preview.setText(preview_text)

    def _on_title_setting_changed(self) -> None:
        """Handle any title setting changes: update live preview immediately and debounce plot update."""
        self._update_title_preview()
        self._render_debounce_timer.start(500)

    def _on_quick_input_changed(self) -> None:
        """Debounce rapid adjustments on colormap, bounds, spinboxes, and barbs."""
        self._render_debounce_timer.start(350)

    def _on_immediate_refresh_clicked(self) -> None:
        """Cancel debounce and refresh plot immediately."""
        self._render_debounce_timer.stop()
        self._update_profile_plot()

    def _on_reset_bounds_clicked(self) -> None:
        self._render_debounce_timer.stop()
        self.spin_vmin.blockSignals(True)
        self.spin_vmax.blockSignals(True)
        self.spin_vmin.setValue(-1e9)
        self.spin_vmax.setValue(1e9)
        self.spin_vmin.blockSignals(False)
        self.spin_vmax.blockSignals(False)
        self._update_profile_plot()

    def _build_current_plot_config(self, config_id: Optional[str] = None) -> PlotConfig:
        """Assemble current UI parameter state into a validated PlotConfig model."""
        main_title, sub_title, var_text = self._compute_current_title_parts()
        vmin = self.spin_vmin.value() if self.spin_vmin.value() > -1e9 else None
        vmax = self.spin_vmax.value() if self.spin_vmax.value() < 1e9 else None
        is_wind = is_wind_variable(self._current_var)

        kwargs = {}
        if config_id:
            kwargs["id"] = config_id

        return PlotConfig(
            variable=self._current_var,
            level=self._current_level,
            level_type=self._current_level_type,
            plot_type=self.combo_style.currentText(),  # type: ignore[arg-type]
            colormap=self.combo_cmap.currentText(),
            vmin=vmin,
            vmax=vmax,
            num_levels=self.spin_levels.value(),
            is_wind=is_wind,
            barbs_step=self.spin_barbs_step.value(),
            barbs_length=self.spin_barbs_length.value(),
            barbs_pivot=self.combo_barbs_pivot.currentText(),
            barbs_color=self.combo_barbs_color.currentText(),
            var_text_template=self.edit_var_template.text().strip() or DEFAULT_VAR_TEMPLATE,
            computed_var_text=var_text,
            enabled=True,
            **kwargs,
        )

    def _on_add_config_clicked(self) -> None:
        """Push current variable settings to centralized PlotConfig list."""
        cfg = self._build_current_plot_config()
        self._plot_configs.append(cfg)
        self._refresh_plotconfig_table()
        self.plotconfig_changed.emit(self._plot_configs)
        self.lbl_plotconfig_status.setText(f"Added '{cfg.variable}' | Total: {len(self._plot_configs)}")

    def _refresh_plotconfig_table(self) -> None:
        """Synchronize the bottom sidebar table with the current _plot_configs list."""
        self.config_table.blockSignals(True)
        self.config_table.setRowCount(len(self._plot_configs))

        for row, cfg in enumerate(self._plot_configs):
            lvl_str = f"{cfg.level:.0f} hPa" if cfg.level is not None else (cfg.level_type or "surface")
            rng_str = f"[{cfg.vmin:.1f}, {cfg.vmax:.1f}]" if (cfg.vmin is not None and cfg.vmax is not None) else "Auto"

            self.config_table.setItem(row, 0, QTableWidgetItem(cfg.id))
            self.config_table.setItem(row, 1, QTableWidgetItem(cfg.variable))
            self.config_table.setItem(row, 2, QTableWidgetItem(lvl_str))
            self.config_table.setItem(row, 3, QTableWidgetItem(cfg.plot_type))
            self.config_table.setItem(row, 4, QTableWidgetItem(cfg.colormap))
            self.config_table.setItem(row, 5, QTableWidgetItem(rng_str))
            self.config_table.setItem(row, 6, QTableWidgetItem(cfg.computed_var_text))

        self.config_table.blockSignals(False)
        self.lbl_plotconfig_status.setText(f"{len(self._plot_configs)} configurations")

    def _on_config_table_selection_changed(self) -> None:
        selected_rows = self.config_table.selectionModel().selectedRows()
        has_sel = len(selected_rows) > 0
        self.btn_update_config.setEnabled(has_sel)
        self.btn_delete_config.setEnabled(has_sel)
        self.btn_plot_config.setEnabled(has_sel)

    def _on_update_config_clicked(self) -> None:
        """Update selected PlotConfig with the current parameters in the controls."""
        selected_rows = self.config_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        target_id = self._plot_configs[row].id
        updated_cfg = self._build_current_plot_config(config_id=target_id)
        self._plot_configs[row] = updated_cfg
        self._refresh_plotconfig_table()
        self.plotconfig_changed.emit(self._plot_configs)
        self.lbl_plotconfig_status.setText(f"Updated '{target_id}' ({updated_cfg.variable})")

    def _on_edit_config_clicked(self) -> None:
        """Load selected plotconfig back into controls for viewing and adjusting."""
        selected_rows = self.config_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        cfg = self._plot_configs[row]
        self._editing_config_id = cfg.id

        # Update controls
        self.combo_cmap.setCurrentText(cfg.colormap)
        self.combo_style.setCurrentText(cfg.plot_type)
        self.spin_levels.setValue(cfg.num_levels)

        self.spin_vmin.blockSignals(True)
        self.spin_vmax.blockSignals(True)
        self.spin_vmin.setValue(cfg.vmin if cfg.vmin is not None else -1e9)
        self.spin_vmax.setValue(cfg.vmax if cfg.vmax is not None else 1e9)
        self.spin_vmin.blockSignals(False)
        self.spin_vmax.blockSignals(False)

        # Wind controls
        self.spin_barbs_step.setValue(cfg.barbs_step)
        self.spin_barbs_length.setValue(cfg.barbs_length)
        self.combo_barbs_pivot.setCurrentText(cfg.barbs_pivot)
        self.combo_barbs_color.setCurrentText(cfg.barbs_color)

        # Variable title template control
        self.edit_var_template.setText(cfg.var_text_template)

        self._update_title_preview()
        self._update_profile_plot()
        self.lbl_plotconfig_status.setText(f"Loaded '{cfg.id}' ({cfg.variable}) into controls")

    def _on_delete_config_clicked(self) -> None:
        """Delete selected PlotConfig from the centralized list."""
        selected_rows = self.config_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        deleted_id = self._plot_configs[row].id
        del self._plot_configs[row]
        if self._editing_config_id == deleted_id:
            self._editing_config_id = None

        self._refresh_plotconfig_table()
        self.plotconfig_changed.emit(self._plot_configs)
        self.lbl_plotconfig_status.setText(f"Deleted config '{deleted_id}'")

    def _on_clear_configs_clicked(self) -> None:
        """Clear all configurations from PlotConfig list."""
        self._plot_configs.clear()
        self._editing_config_id = None
        self._refresh_plotconfig_table()
        self.plotconfig_changed.emit(self._plot_configs)
        self.lbl_plotconfig_status.setText("Cleared all configurations")

    def _on_plot_config_clicked(self) -> None:
        """Render selected PlotConfig onto Spatial Viewport via plot_requested signal."""
        selected_rows = self.config_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        cfg = self._plot_configs[row]

        region_view = None
        if self._region_spec_provider:
            region_view = self._region_spec_provider()

        dataset_id = self._metadata.dataset_id if self._metadata else None
        global_title_spec = self._get_current_global_title_spec()
        plot_spec = cfg.to_data_plot_spec(
            dataset_id=dataset_id,
            region_view=region_view,
            global_title_spec=global_title_spec,
        )
        self.plot_requested.emit(plot_spec)

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

        is_wind_var = is_wind_variable(self._current_var)
        main_title, sub_title, _ = self._compute_current_title_parts()

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
                "barbs_enabled": is_wind_var,
                "barbs_step": self.spin_barbs_step.value(),
                "barbs_length": self.spin_barbs_length.value(),
                "barbs_pivot": self.combo_barbs_pivot.currentText(),
                "barbs_color": self.combo_barbs_color.currentText(),
                "show_histogram": not self.btn_toggle_histogram.isChecked(),
                "title": main_title,
                "subtitle": sub_title,
            },
            channel="inspector_hist",
            cancel_previous=True,
            width=6.5,
            height=6.0 if not self.btn_toggle_histogram.isChecked() else 5.5,
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
