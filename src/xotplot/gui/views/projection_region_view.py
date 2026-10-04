"""Cartopy projection and coordinate reference system configuration view."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from xotplot.constants import (
    ALL_REGIONS,
    CRS_CARDS,
    DEFAULT_BORDER_COLOR,
    DEFAULT_COAST_COLOR,
    DEFAULT_GRID_COLOR,
    DEFAULT_LAKE_COLOR,
    DEFAULT_PLOT_BG_COLOR,
    DEFAULT_PLOT_FG_COLOR,
    DEFAULT_RIVER_COLOR,
    DEFAULT_SHP_COLOR,
    DEFAULT_STATE_COLOR,
    PROJECTION_ACTIVE_BG,
    PROJECTION_ACTIVE_BORDER,
    PROJECTION_ACTIVE_FG,
    REGION_CATEGORIES,
    VIEWPORT_DEBOUNCE_MS,
)
from xotplot.engine import get_qt_engine_bridge, is_feature_cached
from xotplot.gui.engine_canvas import EngineCanvasWidget
from xotplot.gui.preferences_dialog import CartopyPreferencesDialog
from xotplot.spec import (
    CustomShapefileSpec,
    ExtentSpec,
    FeatureLayerSpec,
    FeaturesSpec,
    GraticuleSpec,
    ProjectionSpec,
    RegionViewSpec,
)


class ProjectionRegionView(QWidget):
    """Granular Cartopy configuration view for Projection & Region with extensive border/feature controls."""

    projection_changed = pyqtSignal(dict)

    CRS_CARDS = CRS_CARDS
    EXTENT_PRESETS = ALL_REGIONS

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.dark_mode = False
        self._current_crs_id = "LambertConformal"
        self._card_buttons: Dict[str, QPushButton] = {}
        self._custom_shapefiles: List[Dict[str, Any]] = []

        # Color defaults from centralized constants
        self._coast_color = DEFAULT_COAST_COLOR
        self._border_color = DEFAULT_BORDER_COLOR
        self._state_color = DEFAULT_STATE_COLOR
        self._river_color = DEFAULT_RIVER_COLOR
        self._lake_color = DEFAULT_LAKE_COLOR
        self._grid_color = DEFAULT_GRID_COLOR
        self._shp_color = DEFAULT_SHP_COLOR

        # Dedicated custom shapefile paths per feature
        self._custom_shp_coast: Optional[str] = None
        self._custom_shp_borders: Optional[str] = None
        self._custom_shp_states: Optional[str] = None
        self._custom_shp_rivers: Optional[str] = None
        self._custom_shp_lakes: Optional[str] = None

        self._current_job_id: Optional[str] = None
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(VIEWPORT_DEBOUNCE_MS)
        self._debounce_timer.timeout.connect(self.apply_projection)

        self.engine_bridge = get_qt_engine_bridge()
        self.engine_bridge.job_completed.connect(self._on_render_completed)

        self._init_ui()
        self._sync_feature_checkboxes_with_cache()
        self.apply_projection()


    def _init_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(8)

        # Left control panel inside scroll area
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setMinimumWidth(440)
        scroll.setMaximumWidth(520)

        panel_container = QWidget()
        panel_layout = QVBoxLayout(panel_container)
        panel_layout.setContentsMargins(4, 4, 8, 4)
        panel_layout.setSpacing(10)

        # ---------------------------------------------------------------------
        # 1. Region Extent Presets & Bounding Box (First Option)
        # ---------------------------------------------------------------------
        extent_group = QGroupBox("1. Region Extent & Bounding Box", self)
        extent_layout = QVBoxLayout(extent_group)
        extent_layout.setSpacing(6)

        cat_row = QHBoxLayout()
        cat_row.addWidget(QLabel("Category:"))
        self.combo_category = QComboBox()
        self.combo_category.addItem("All Categories")
        self.combo_category.addItems(list(REGION_CATEGORIES.keys()))
        self.combo_category.currentTextChanged.connect(self._on_category_changed)
        cat_row.addWidget(self.combo_category)
        extent_layout.addLayout(cat_row)

        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Region:"))
        self.combo_preset = QComboBox()
        self._populate_region_combo()
        self.combo_preset.currentTextChanged.connect(self._on_preset_changed)
        preset_row.addWidget(self.combo_preset)
        extent_layout.addLayout(preset_row)

        # Initialize to first India region
        first_region = list(self.EXTENT_PRESETS.keys())[0]
        init_w, init_e, init_s, init_n = self.EXTENT_PRESETS[first_region]

        bbox_grid = QGridLayout()
        bbox_grid.setSpacing(4)
        bbox_grid.addWidget(QLabel("West (Lon):"), 0, 0)
        self.spin_west = QDoubleSpinBox()
        self.spin_west.setRange(-180.0, 180.0)
        self.spin_west.setValue(init_w)
        self.spin_west.valueChanged.connect(self.request_projection_update)
        bbox_grid.addWidget(self.spin_west, 0, 1)

        bbox_grid.addWidget(QLabel("East (Lon):"), 0, 2)
        self.spin_east = QDoubleSpinBox()
        self.spin_east.setRange(-180.0, 180.0)
        self.spin_east.setValue(init_e)
        self.spin_east.valueChanged.connect(self.request_projection_update)
        bbox_grid.addWidget(self.spin_east, 0, 3)

        bbox_grid.addWidget(QLabel("South (Lat):"), 1, 0)
        self.spin_south = QDoubleSpinBox()
        self.spin_south.setRange(-90.0, 90.0)
        self.spin_south.setValue(init_s)
        self.spin_south.valueChanged.connect(self.request_projection_update)
        bbox_grid.addWidget(self.spin_south, 1, 1)

        bbox_grid.addWidget(QLabel("North (Lat):"), 1, 2)
        self.spin_north = QDoubleSpinBox()
        self.spin_north.setRange(-90.0, 90.0)
        self.spin_north.setValue(init_n)
        self.spin_north.valueChanged.connect(self.request_projection_update)
        bbox_grid.addWidget(self.spin_north, 1, 3)

        extent_layout.addLayout(bbox_grid)
        panel_layout.addWidget(extent_group)

        # ---------------------------------------------------------------------
        # 2. Cartopy CRS Library Grid Cards
        # ---------------------------------------------------------------------
        curr_crs = next((c for c in self.CRS_CARDS if c["id"] == self._current_crs_id), None)
        title_suffix = f" — Active: {curr_crs['name']} [{curr_crs['code'].upper()}]" if curr_crs else ""
        self.crs_group = QGroupBox(f"2. Cartopy CRS Library{title_suffix}", self)
        crs_grid = QGridLayout(self.crs_group)
        crs_grid.setSpacing(6)

        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)

        for idx, crs_info in enumerate(self.CRS_CARDS):
            row = idx // 2
            col = idx % 2
            is_active = (crs_info["id"] == self._current_crs_id)
            prefix = "● " if is_active else ""
            card_btn = QPushButton(f"{prefix}{crs_info['name']}\n[{crs_info['code'].upper()}]")
            card_btn.setCheckable(True)
            card_btn.setToolTip(crs_info["desc"])
            card_btn.setMinimumHeight(44)
            card_btn.setStyleSheet(f"""
                QPushButton {{
                    text-align: center;
                    font-size: 11px;
                    border: 1px solid #3e484f;
                    border-radius: 4px;
                    padding: 4px;
                }}
                QPushButton:checked, QPushButton[activeCard="true"] {{
                    background-color: {PROJECTION_ACTIVE_BG};
                    color: {PROJECTION_ACTIVE_FG};
                    border: 2px solid {PROJECTION_ACTIVE_BORDER};
                    font-weight: bold;
                }}
            """)
            if is_active:
                card_btn.setChecked(True)
                card_btn.setProperty("activeCard", True)

            card_btn.clicked.connect(lambda checked, cid=crs_info["id"]: self._on_select_crs(cid))
            self._btn_group.addButton(card_btn, idx)
            self._card_buttons[crs_info["id"]] = card_btn
            crs_grid.addWidget(card_btn, row, col)

        panel_layout.addWidget(self.crs_group)

        # ---------------------------------------------------------------------
        # 3. Projection Parameters
        # ---------------------------------------------------------------------
        param_group = QGroupBox("3. Projection Parameters", self)
        param_layout = QGridLayout(param_group)
        param_layout.setSpacing(6)

        param_layout.addWidget(QLabel("Central Longitude:"), 0, 0)
        self.spin_central_lon = QDoubleSpinBox()
        self.spin_central_lon.setRange(-180.0, 180.0)
        self.spin_central_lon.setSingleStep(5.0)
        self.spin_central_lon.setValue(82.5)
        self.spin_central_lon.valueChanged.connect(self.request_projection_update)
        param_layout.addWidget(self.spin_central_lon, 0, 1)

        param_layout.addWidget(QLabel("Central Latitude:"), 1, 0)
        self.spin_central_lat = QDoubleSpinBox()
        self.spin_central_lat.setRange(-90.0, 90.0)
        self.spin_central_lat.setSingleStep(5.0)
        self.spin_central_lat.setValue(22.0)
        self.spin_central_lat.valueChanged.connect(self.request_projection_update)
        param_layout.addWidget(self.spin_central_lat, 1, 1)

        self.lbl_sp1 = QLabel("Std Parallel 1:")
        self.spin_sp1 = QDoubleSpinBox()
        self.spin_sp1.setRange(-90.0, 90.0)
        self.spin_sp1.setSingleStep(1.0)
        self.spin_sp1.setValue(12.0)
        self.spin_sp1.valueChanged.connect(self.request_projection_update)
        param_layout.addWidget(self.lbl_sp1, 2, 0)
        param_layout.addWidget(self.spin_sp1, 2, 1)

        self.lbl_sp2 = QLabel("Std Parallel 2:")
        self.spin_sp2 = QDoubleSpinBox()
        self.spin_sp2.setRange(-90.0, 90.0)
        self.spin_sp2.setSingleStep(1.0)
        self.spin_sp2.setValue(28.0)
        self.spin_sp2.valueChanged.connect(self.request_projection_update)
        param_layout.addWidget(self.lbl_sp2, 3, 0)
        param_layout.addWidget(self.spin_sp2, 3, 1)

        panel_layout.addWidget(param_group)

        # ---------------------------------------------------------------------
        # 4. Granular Borders & Features Controls (All Cartopy Options)
        # ---------------------------------------------------------------------
        feat_group = QGroupBox("4. Cartopy Borders & Feature Layer Config", self)
        feat_layout = QGridLayout(feat_group)
        feat_layout.setSpacing(6)

        # Download Preferences Dialog Trigger
        self.btn_prefs = QPushButton("⚙ Manage Downloads & Offline Cache...")
        self.btn_prefs.clicked.connect(self._open_preferences_dialog)
        feat_layout.addWidget(self.btn_prefs, 0, 0, 1, 3)

        # Feature Scale / Resolution
        feat_layout.addWidget(QLabel("Natural Earth Scale:"), 1, 0)
        self.combo_scale = QComboBox()
        self.combo_scale.addItems(["110m (Coarse)", "50m (Medium)", "10m (High-Res)"])
        self.combo_scale.setCurrentIndex(1)  # 50m default
        self.combo_scale.currentIndexChanged.connect(self._on_scale_changed)
        feat_layout.addWidget(self.combo_scale, 1, 1, 1, 2)

        # Coastlines
        self.chk_coast = QCheckBox("Coastlines")
        self.chk_coast.stateChanged.connect(self.apply_projection)
        feat_layout.addWidget(self.chk_coast, 2, 0)


        self.spin_coast_width = QDoubleSpinBox()
        self.spin_coast_width.setRange(0.2, 5.0)
        self.spin_coast_width.setSingleStep(0.2)
        self.spin_coast_width.setValue(1.0)
        self.spin_coast_width.valueChanged.connect(self.request_projection_update)
        feat_layout.addWidget(self.spin_coast_width, 2, 1)

        coast_btn_layout = QHBoxLayout()
        self.btn_coast_col = QPushButton("Color")
        self.btn_coast_col.clicked.connect(lambda: self._pick_color("_coast_color", self.btn_coast_col))
        coast_btn_layout.addWidget(self.btn_coast_col)

        self.btn_coast_shp = QPushButton("📁 .shp")
        self.btn_coast_shp.setToolTip("Set custom shapefile for Coastlines (overrides Natural Earth)")
        self.btn_coast_shp.clicked.connect(lambda: self._pick_feature_shapefile("_custom_shp_coast", self.btn_coast_shp))
        coast_btn_layout.addWidget(self.btn_coast_shp)
        feat_layout.addLayout(coast_btn_layout, 2, 2)

        # Country Borders
        self.chk_borders = QCheckBox("Country Borders")
        self.chk_borders.stateChanged.connect(self.apply_projection)
        feat_layout.addWidget(self.chk_borders, 3, 0)

        self.combo_border_style = QComboBox()
        self.combo_border_style.addItems(["Dashed (--)", "Solid (-)", "Dotted (:)"])
        self.combo_border_style.currentIndexChanged.connect(self.apply_projection)
        feat_layout.addWidget(self.combo_border_style, 3, 1)

        border_btn_layout = QHBoxLayout()
        self.btn_border_col = QPushButton("Color")
        self.btn_border_col.clicked.connect(lambda: self._pick_color("_border_color", self.btn_border_col))
        border_btn_layout.addWidget(self.btn_border_col)

        self.btn_border_shp = QPushButton("📁 .shp")
        self.btn_border_shp.setToolTip("Set custom shapefile for Country Borders (overrides Natural Earth)")
        self.btn_border_shp.clicked.connect(lambda: self._pick_feature_shapefile("_custom_shp_borders", self.btn_border_shp))
        border_btn_layout.addWidget(self.btn_border_shp)
        feat_layout.addLayout(border_btn_layout, 3, 2)

        # State / Province Subdivisions
        self.chk_states = QCheckBox("State / Provinces")
        self.chk_states.setChecked(False)
        self.chk_states.stateChanged.connect(self.apply_projection)
        feat_layout.addWidget(self.chk_states, 4, 0)

        self.spin_state_width = QDoubleSpinBox()
        self.spin_state_width.setRange(0.2, 3.0)
        self.spin_state_width.setValue(0.5)
        self.spin_state_width.valueChanged.connect(self.request_projection_update)
        feat_layout.addWidget(self.spin_state_width, 4, 1)

        state_btn_layout = QHBoxLayout()
        self.btn_state_col = QPushButton("Color")
        self.btn_state_col.clicked.connect(lambda: self._pick_color("_state_color", self.btn_state_col))
        state_btn_layout.addWidget(self.btn_state_col)

        self.btn_state_shp = QPushButton("📁 .shp")
        self.btn_state_shp.setToolTip("Set custom shapefile for States / Provinces (overrides Natural Earth)")
        self.btn_state_shp.clicked.connect(lambda: self._pick_feature_shapefile("_custom_shp_states", self.btn_state_shp))
        state_btn_layout.addWidget(self.btn_state_shp)
        feat_layout.addLayout(state_btn_layout, 4, 2)

        # Rivers & Hydrography
        self.chk_rivers = QCheckBox("Rivers")
        self.chk_rivers.setChecked(False)
        self.chk_rivers.stateChanged.connect(self.apply_projection)
        feat_layout.addWidget(self.chk_rivers, 5, 0)

        self.spin_river_width = QDoubleSpinBox()
        self.spin_river_width.setRange(0.2, 3.0)
        self.spin_river_width.setValue(0.6)
        self.spin_river_width.valueChanged.connect(self.request_projection_update)
        feat_layout.addWidget(self.spin_river_width, 5, 1)

        river_btn_layout = QHBoxLayout()
        self.btn_river_col = QPushButton("Color")
        self.btn_river_col.clicked.connect(lambda: self._pick_color("_river_color", self.btn_river_col))
        river_btn_layout.addWidget(self.btn_river_col)

        self.btn_river_shp = QPushButton("📁 .shp")
        self.btn_river_shp.setToolTip("Set custom shapefile for Rivers (overrides Natural Earth)")
        self.btn_river_shp.clicked.connect(lambda: self._pick_feature_shapefile("_custom_shp_rivers", self.btn_river_shp))
        river_btn_layout.addWidget(self.btn_river_shp)
        feat_layout.addLayout(river_btn_layout, 5, 2)

        # Lakes
        self.chk_lakes = QCheckBox("Lakes Outline")
        self.chk_lakes.setChecked(False)
        self.chk_lakes.stateChanged.connect(self.apply_projection)
        feat_layout.addWidget(self.chk_lakes, 6, 0)

        self.spin_lake_width = QDoubleSpinBox()
        self.spin_lake_width.setRange(0.2, 3.0)
        self.spin_lake_width.setValue(0.6)
        self.spin_lake_width.valueChanged.connect(self.request_projection_update)
        feat_layout.addWidget(self.spin_lake_width, 6, 1)

        lake_btn_layout = QHBoxLayout()
        self.btn_lake_col = QPushButton("Color")
        self.btn_lake_col.clicked.connect(lambda: self._pick_color("_lake_color", self.btn_lake_col))
        lake_btn_layout.addWidget(self.btn_lake_col)

        self.btn_lake_shp = QPushButton("📁 .shp")
        self.btn_lake_shp.setToolTip("Set custom shapefile for Lakes (overrides Natural Earth)")
        self.btn_lake_shp.clicked.connect(lambda: self._pick_feature_shapefile("_custom_shp_lakes", self.btn_lake_shp))
        lake_btn_layout.addWidget(self.btn_lake_shp)
        feat_layout.addLayout(lake_btn_layout, 6, 2)

        panel_layout.addWidget(feat_group)

        # ---------------------------------------------------------------------
        # 5. Custom Shapefiles Management (Import, Style, Toggle)
        # ---------------------------------------------------------------------
        shp_group = QGroupBox("5. Custom Shapefiles (.shp)", self)
        shp_layout = QVBoxLayout(shp_group)
        shp_layout.setSpacing(6)

        shp_top_row = QHBoxLayout()
        self.btn_add_shp = QPushButton("+ Add Shapefile...")
        self.btn_add_shp.setObjectName("primaryAction")
        self.btn_add_shp.clicked.connect(self._on_add_shapefile)
        shp_top_row.addWidget(self.btn_add_shp)

        self.btn_remove_shp = QPushButton("Remove")
        self.btn_remove_shp.clicked.connect(self._on_remove_shapefile)
        shp_top_row.addWidget(self.btn_remove_shp)
        shp_layout.addLayout(shp_top_row)

        self.list_shapefiles = QListWidget()
        self.list_shapefiles.setMaximumHeight(90)
        shp_layout.addWidget(self.list_shapefiles)

        # Shapefile line width & color
        shp_opts = QHBoxLayout()
        shp_opts.addWidget(QLabel("Stroke Width:"))
        self.spin_shp_width = QDoubleSpinBox()
        self.spin_shp_width.setRange(0.2, 6.0)
        self.spin_shp_width.setValue(1.2)
        self.spin_shp_width.valueChanged.connect(self.request_projection_update)
        shp_opts.addWidget(self.spin_shp_width)

        self.btn_shp_color = QPushButton("Pick Color")
        self._shp_color = "#e11d48"  # Rose red default for custom shapefiles
        self.btn_shp_color.clicked.connect(self._pick_shp_color)
        shp_opts.addWidget(self.btn_shp_color)
        shp_layout.addLayout(shp_opts)

        panel_layout.addWidget(shp_group)

        # ---------------------------------------------------------------------
        # 6. Graticules, Ticks & Gridlines Inspector
        # ---------------------------------------------------------------------
        grat_group = QGroupBox("6. Graticules & Gridlines Inspector", self)
        grat_layout = QGridLayout(grat_group)
        grat_layout.setSpacing(6)

        self.chk_gridlines = QCheckBox("Enable Graticule Gridlines")
        self.chk_gridlines.setChecked(True)
        self.chk_gridlines.stateChanged.connect(self.apply_projection)
        grat_layout.addWidget(self.chk_gridlines, 0, 0, 1, 2)

        self.chk_labels = QCheckBox("Draw Coordinate Labels")
        self.chk_labels.setChecked(True)
        self.chk_labels.stateChanged.connect(self.apply_projection)
        grat_layout.addWidget(self.chk_labels, 1, 0, 1, 2)

        grat_layout.addWidget(QLabel("Line Style:"), 2, 0)
        self.combo_linestyle = QComboBox()
        self.combo_linestyle.addItems(["Dashed (--)", "Solid (-)", "Dotted (:)"])
        self.combo_linestyle.currentIndexChanged.connect(self.apply_projection)
        grat_layout.addWidget(self.combo_linestyle, 2, 1)

        grat_layout.addWidget(QLabel("Lon Step (°):"), 3, 0)
        self.spin_lon_step = QDoubleSpinBox()
        self.spin_lon_step.setRange(0.5, 60.0)
        self.spin_lon_step.setValue(5.0)
        self.spin_lon_step.valueChanged.connect(self.request_projection_update)
        grat_layout.addWidget(self.spin_lon_step, 3, 1)

        grat_layout.addWidget(QLabel("Lat Step (°):"), 4, 0)
        self.spin_lat_step = QDoubleSpinBox()
        self.spin_lat_step.setRange(0.5, 60.0)
        self.spin_lat_step.setValue(5.0)
        self.spin_lat_step.valueChanged.connect(self.request_projection_update)
        grat_layout.addWidget(self.spin_lat_step, 4, 1)

        grat_layout.addWidget(QLabel("Grid Color & Alpha:"), 5, 0)
        grat_tools = QHBoxLayout()
        self.btn_grid_col = QPushButton("Grid Color")
        self.btn_grid_col.clicked.connect(lambda: self._pick_color("_grid_color", self.btn_grid_col))
        grat_tools.addWidget(self.btn_grid_col)

        self.slider_grid_alpha = QSlider(Qt.Orientation.Horizontal)
        self.slider_grid_alpha.setRange(10, 100)
        self.slider_grid_alpha.setValue(60)
        self.slider_grid_alpha.valueChanged.connect(self.request_projection_update)
        grat_tools.addWidget(self.slider_grid_alpha)
        grat_layout.addLayout(grat_tools, 5, 1)

        panel_layout.addWidget(grat_group)

        scroll.setWidget(panel_container)
        main_layout.addWidget(scroll)

        # Right side: Mpl Canvas
        right_container = QWidget(self)
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)

        self.canvas_widget = EngineCanvasWidget(right_container, width=8.0, height=6.0, dpi=100)
        self.canvas = self.canvas_widget
        right_layout.addWidget(self.canvas_widget)

        self.lbl_info = QLabel("Cartopy Projection Mesh Ready")
        self.lbl_info.setStyleSheet("color: #87929a; font-size: 10px; padding: 2px 4px;")
        right_layout.addWidget(self.lbl_info)

        main_layout.addWidget(right_container, stretch=1)

    def _pick_color(self, attr_name: str, btn: QPushButton) -> None:
        curr_hex = getattr(self, attr_name, "#000000")
        col = QColorDialog.getColor()
        if col.isValid():
            setattr(self, attr_name, col.name())
            btn.setStyleSheet(f"background-color: {col.name()};")
            self.apply_projection()

    def _pick_shp_color(self) -> None:
        col = QColorDialog.getColor()
        if col.isValid():
            self._shp_color = col.name()
            self.btn_shp_color.setStyleSheet(f"background-color: {col.name()};")
            self.apply_projection()

    def _pick_feature_shapefile(self, attr_name: str, btn: QPushButton) -> None:
        """Select a custom shapefile overriding a specific natural earth feature."""
        curr_val = getattr(self, attr_name, None)
        if curr_val:
            # If already set, clicking allows clearing or re-selecting
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Change or Clear Custom Feature Shapefile", "", "Shapefiles (*.shp);;GeoPackage (*.gpkg);;All Files (*)"
            )
            if file_path:
                setattr(self, attr_name, file_path)
                btn.setText(f"✓ {Path(file_path).stem[:6]}")
                btn.setStyleSheet("background-color: #0284c7; color: white;")
            else:
                setattr(self, attr_name, None)
                btn.setText("📁 .shp")
                btn.setStyleSheet("")
        else:
            default_dir = str(Path.home() / "Downloads") if (Path.home() / "Downloads").exists() else str(Path.home())
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Custom Feature Shapefile", default_dir, "Shapefiles (*.shp);;GeoPackage (*.gpkg);;All Files (*)"
            )
            if file_path:
                setattr(self, attr_name, file_path)
                btn.setText(f"✓ {Path(file_path).stem[:6]}")
                btn.setStyleSheet("background-color: #0284c7; color: white;")

        self.apply_projection()

    def _on_add_shapefile(self) -> None:
        default_dir = str(Path.home() / "Downloads") if (Path.home() / "Downloads").exists() else str(Path.home())
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Shapefile",
            default_dir,
            "Shapefiles (*.shp);;GeoPackage (*.gpkg);;All Files (*)",
        )
        if file_path:
            p = Path(file_path)
            item = QListWidgetItem(f"✓ {p.name}")
            item.setData(Qt.ItemDataRole.UserRole, file_path)
            self.list_shapefiles.addItem(item)
            self._custom_shapefiles.append({"path": file_path, "name": p.name, "enabled": True})
            self.apply_projection()

    def _on_remove_shapefile(self) -> None:
        row = self.list_shapefiles.currentRow()
        if row >= 0:
            item = self.list_shapefiles.takeItem(row)
            path = item.data(Qt.ItemDataRole.UserRole)
            self._custom_shapefiles = [s for s in self._custom_shapefiles if s["path"] != path]
            self.apply_projection()

    def _on_select_crs(self, crs_id: str) -> None:
        self._current_crs_id = crs_id
        for cid, btn in self._card_buttons.items():
            is_active = (cid == crs_id)
            btn.setChecked(is_active)
            btn.setProperty("activeCard", is_active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            crs_meta = next((c for c in self.CRS_CARDS if c["id"] == cid), None)
            if crs_meta:
                prefix = "● " if is_active else ""
                btn.setText(f"{prefix}{crs_meta['name']}\n[{crs_meta['code'].upper()}]")

        # Contextual enables for projection controls
        curr = next((c for c in self.CRS_CARDS if c["id"] == crs_id), None)
        if curr:
            if hasattr(self, "crs_group"):
                self.crs_group.setTitle(f"2. Cartopy CRS Library — Active: {curr['name']} [{curr['code'].upper()}]")
            self.lbl_sp1.setEnabled(curr["has_parallels"])
            self.spin_sp1.setEnabled(curr["has_parallels"])
            self.lbl_sp2.setEnabled(curr["has_parallels"])
            self.spin_sp2.setEnabled(curr["has_parallels"])
            self.spin_central_lat.setEnabled(curr["has_lat"])

        self.apply_projection()

    def _populate_region_combo(self) -> None:
        selected_cat = getattr(self, "combo_category", None)
        cat_text = selected_cat.currentText() if selected_cat is not None else "All Categories"

        self.combo_preset.blockSignals(True)
        self.combo_preset.clear()

        if cat_text in REGION_CATEGORIES:
            regions = list(REGION_CATEGORIES[cat_text].keys())
        else:
            regions = list(self.EXTENT_PRESETS.keys())

        self.combo_preset.addItems(regions)
        self.combo_preset.blockSignals(False)

    def _on_category_changed(self, category_name: str) -> None:
        self._populate_region_combo()
        if self.combo_preset.count() > 0:
            self._on_preset_changed(self.combo_preset.currentText())

    def _on_preset_changed(self, preset_name: str) -> None:
        coords = None
        if preset_name in self.EXTENT_PRESETS:
            coords = self.EXTENT_PRESETS[preset_name]
        else:
            cat_text = self.combo_category.currentText()
            if cat_text in REGION_CATEGORIES and preset_name in REGION_CATEGORIES[cat_text]:
                coords = REGION_CATEGORIES[cat_text][preset_name]

        if coords is not None:
            w, e, s, n = coords
            self.spin_west.blockSignals(True)
            self.spin_east.blockSignals(True)
            self.spin_south.blockSignals(True)
            self.spin_north.blockSignals(True)
            self.spin_west.setValue(w)
            self.spin_east.setValue(e)
            self.spin_south.setValue(s)
            self.spin_north.setValue(n)
            self.spin_west.blockSignals(False)
            self.spin_east.blockSignals(False)
            self.spin_south.blockSignals(False)
            self.spin_north.blockSignals(False)

            # Auto-align central lon/lat to the center of bounding box
            c_lon = ((w + e) / 2.0) if w <= e else (((w + e + 360) / 2.0) % 360 - 180)
            c_lat = (s + n) / 2.0
            self.spin_central_lon.setValue(round(c_lon, 1))
            self.spin_central_lat.setValue(round(c_lat, 1))

            self.apply_projection()

    def get_selected_crs(self) -> Any:
        return build_crs(self.to_spec().projection)

    def _on_scale_changed(self) -> None:
        self._sync_feature_checkboxes_with_cache()
        self.apply_projection()

    def _sync_feature_checkboxes_with_cache(self) -> None:
        """Deselect all feature checkboxes whose Natural Earth shapefiles are not cached locally."""
        scale_map = {"110m (Coarse)": "110m", "50m (Medium)": "50m", "10m (High-Res)": "10m"}
        chosen_scale = scale_map.get(self.combo_scale.currentText(), "50m")

        features_info = [
            (self.chk_coast, "physical", "coastline", self._custom_shp_coast),
            (self.chk_borders, "cultural", "admin_0_countries", self._custom_shp_borders),
            (self.chk_states, "cultural", "admin_1_states_provinces_lines", self._custom_shp_states),
            (self.chk_rivers, "physical", "rivers_lake_centerlines", self._custom_shp_rivers),
            (self.chk_lakes, "physical", "lakes", self._custom_shp_lakes),
        ]

        for chk, cat, layer, custom_shp in features_info:
            has_custom = custom_shp and Path(custom_shp).exists()
            cached = is_feature_cached(cat, layer, chosen_scale)
            # If not cached and no custom shapefile override, deselect it
            if not cached and not has_custom:
                chk.blockSignals(True)
                chk.setChecked(False)
                chk.blockSignals(False)
            elif cached and not has_custom:
                # Default essential layers (Coastlines & Borders) to checked if available
                if chk in (self.chk_coast, self.chk_borders):
                    chk.blockSignals(True)
                    chk.setChecked(True)
                    chk.blockSignals(False)

    def _open_preferences_dialog(self) -> None:
        """Open the Cartopy Feature Preferences dialog to manage and download features."""
        dialog = CartopyPreferencesDialog(self)
        dialog.features_updated.connect(self._sync_feature_checkboxes_with_cache)
        dialog.features_updated.connect(self.apply_projection)
        dialog.exec()


    def set_theme(self, dark_mode: bool) -> None:
        """Plot canvas always stays in light theme."""
        self.dark_mode = False
        self.apply_projection()

    def request_projection_update(self) -> None:
        """Debounce rapid spinbox and slider updates before dispatching render to engine."""
        self._debounce_timer.start()

    def apply_projection(self) -> None:
        """Render the map projection canvas by delegating to the separate engine process."""
        self._debounce_timer.stop()
        spec = self.to_spec()
        self._current_job_id = self.engine_bridge.submit(
            "region",
            spec.model_dump(mode="json"),
            channel="region",
            width=8.0,
            height=6.0,
            dpi=100,
            cancel_previous=True,
        )

        w, e, s, n = spec.extent.as_tuple()
        self.lbl_info.setText(
            f"CRS: {spec.projection.crs_id} | Extent: [{w:.1f}°, {e:.1f}°, {s:.1f}°, {n:.1f}°] | "
            f"Scale: {spec.features.scale} | Custom Shp: {len(spec.custom_shapefiles)}"
        )

        # Emit change signal
        self.projection_changed.emit({
            "crs_id": spec.projection.crs_id,
            "central_longitude": spec.projection.central_longitude,
            "central_latitude": spec.projection.central_latitude,
            "extent": (w, e, s, n),
            "custom_shapefiles": [str(s.path) for s in spec.custom_shapefiles],
        })

    def _on_render_completed(self, job_id: str, image_data: bytes) -> None:
        if job_id == self._current_job_id:
            self.canvas_widget.set_image_bytes(image_data)

    def to_spec(self) -> RegionViewSpec:
        """Export current view state to a validated RegionViewSpec Pydantic model."""
        scale_map = {"110m (Coarse)": "110m", "50m (Medium)": "50m", "10m (High-Res)": "10m"}
        chosen_scale = scale_map.get(self.combo_scale.currentText(), "50m")

        border_style_map = {"Dashed (--)": "--", "Solid (-)": "-", "Dotted (:)": ":"}
        b_style = border_style_map.get(self.combo_border_style.currentText(), "--")
        g_style = border_style_map.get(self.combo_linestyle.currentText(), "--")

        features_spec = FeaturesSpec(
            scale=chosen_scale,
            coastlines=FeatureLayerSpec(
                enabled=self.chk_coast.isChecked(),
                color=self._coast_color,
                linewidth=self.spin_coast_width.value(),
                linestyle="-",
                custom_shapefile=Path(self._custom_shp_coast) if self._custom_shp_coast else None,
            ),
            borders=FeatureLayerSpec(
                enabled=self.chk_borders.isChecked(),
                color=self._border_color,
                linewidth=0.8,
                linestyle=b_style,
                custom_shapefile=Path(self._custom_shp_borders) if self._custom_shp_borders else None,
            ),
            states=FeatureLayerSpec(
                enabled=self.chk_states.isChecked(),
                color=self._state_color,
                linewidth=self.spin_state_width.value(),
                linestyle=":",
                custom_shapefile=Path(self._custom_shp_states) if self._custom_shp_states else None,
            ),
            rivers=FeatureLayerSpec(
                enabled=self.chk_rivers.isChecked(),
                color=self._river_color,
                linewidth=self.spin_river_width.value(),
                linestyle="-",
                custom_shapefile=Path(self._custom_shp_rivers) if self._custom_shp_rivers else None,
            ),
            lakes=FeatureLayerSpec(
                enabled=self.chk_lakes.isChecked(),
                color=self._lake_color,
                linewidth=self.spin_lake_width.value(),
                linestyle="-",
                custom_shapefile=Path(self._custom_shp_lakes) if self._custom_shp_lakes else None,
            ),
        )

        custom_shps = [
            CustomShapefileSpec(
                path=Path(s["path"]),
                name=s.get("name", Path(s["path"]).name),
                enabled=s.get("enabled", True),
                color=self._shp_color,
                linewidth=self.spin_shp_width.value(),
            )
            for s in self._custom_shapefiles
        ]

        graticules_spec = GraticuleSpec(
            enabled=self.chk_gridlines.isChecked(),
            draw_labels=self.chk_labels.isChecked(),
            linestyle=g_style,
            lon_step=self.spin_lon_step.value(),
            lat_step=self.spin_lat_step.value(),
            color=self._grid_color,
            alpha=self.slider_grid_alpha.value() / 100.0,
        )

        return RegionViewSpec(
            category=self.combo_category.currentText(),
            preset_name=self.combo_preset.currentText(),
            extent=ExtentSpec(
                west=self.spin_west.value(),
                east=self.spin_east.value(),
                south=self.spin_south.value(),
                north=self.spin_north.value(),
            ),
            projection=ProjectionSpec(
                crs_id=self._current_crs_id,
                central_longitude=self.spin_central_lon.value(),
                central_latitude=self.spin_central_lat.value(),
                standard_parallels=(self.spin_sp1.value(), self.spin_sp2.value()),
            ),
            features=features_spec,
            custom_shapefiles=custom_shps,
            graticules=graticules_spec,
        )

    def apply_spec(self, spec: RegionViewSpec) -> None:
        """Apply a validated RegionViewSpec to configure UI widgets and redraw."""
        # 1. Category & Preset
        cat_idx = self.combo_category.findText(spec.category)
        if cat_idx >= 0:
            self.combo_category.blockSignals(True)
            self.combo_category.setCurrentIndex(cat_idx)
            self._populate_region_combo()
            self.combo_category.blockSignals(False)

        preset_idx = self.combo_preset.findText(spec.preset_name)
        if preset_idx >= 0:
            self.combo_preset.blockSignals(True)
            self.combo_preset.setCurrentIndex(preset_idx)
            self.combo_preset.blockSignals(False)

        # 2. Extent
        self.spin_west.blockSignals(True)
        self.spin_east.blockSignals(True)
        self.spin_south.blockSignals(True)
        self.spin_north.blockSignals(True)
        self.spin_west.setValue(spec.extent.west)
        self.spin_east.setValue(spec.extent.east)
        self.spin_south.setValue(spec.extent.south)
        self.spin_north.setValue(spec.extent.north)
        self.spin_west.blockSignals(False)
        self.spin_east.blockSignals(False)
        self.spin_south.blockSignals(False)
        self.spin_north.blockSignals(False)

        # 3. Projection
        self._current_crs_id = spec.projection.crs_id
        for cid, btn in self._card_buttons.items():
            is_active = (cid == self._current_crs_id)
            btn.setChecked(is_active)
            btn.setProperty("activeCard", is_active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            crs_meta = next((c for c in self.CRS_CARDS if c["id"] == cid), None)
            if crs_meta:
                prefix = "● " if is_active else ""
                btn.setText(f"{prefix}{crs_meta['name']}\n[{crs_meta['code'].upper()}]")

        curr = next((c for c in self.CRS_CARDS if c["id"] == self._current_crs_id), None)
        if curr and hasattr(self, "crs_group"):
            self.crs_group.setTitle(f"2. Cartopy CRS Library — Active: {curr['name']} [{curr['code'].upper()}]")

        self.spin_central_lon.blockSignals(True)
        self.spin_central_lat.blockSignals(True)
        self.spin_sp1.blockSignals(True)
        self.spin_sp2.blockSignals(True)
        self.spin_central_lon.setValue(spec.projection.central_longitude)
        self.spin_central_lat.setValue(spec.projection.central_latitude)
        self.spin_sp1.setValue(spec.projection.standard_parallels[0])
        self.spin_sp2.setValue(spec.projection.standard_parallels[1])
        self.spin_central_lon.blockSignals(False)
        self.spin_central_lat.blockSignals(False)
        self.spin_sp1.blockSignals(False)
        self.spin_sp2.blockSignals(False)

        # 4. Features
        scale_rev_map = {"110m": 0, "50m": 1, "10m": 2}
        self.combo_scale.setCurrentIndex(scale_rev_map.get(spec.features.scale, 1))

        self.chk_coast.setChecked(spec.features.coastlines.enabled)
        self.spin_coast_width.setValue(spec.features.coastlines.linewidth)
        self._coast_color = spec.features.coastlines.color
        self._custom_shp_coast = str(spec.features.coastlines.custom_shapefile) if spec.features.coastlines.custom_shapefile else None

        self.chk_borders.setChecked(spec.features.borders.enabled)
        self._border_color = spec.features.borders.color
        self._custom_shp_borders = str(spec.features.borders.custom_shapefile) if spec.features.borders.custom_shapefile else None

        self.chk_states.setChecked(spec.features.states.enabled)
        self.spin_state_width.setValue(spec.features.states.linewidth)
        self._state_color = spec.features.states.color
        self._custom_shp_states = str(spec.features.states.custom_shapefile) if spec.features.states.custom_shapefile else None

        self.chk_rivers.setChecked(spec.features.rivers.enabled)
        self.spin_river_width.setValue(spec.features.rivers.linewidth)
        self._river_color = spec.features.rivers.color
        self._custom_shp_rivers = str(spec.features.rivers.custom_shapefile) if spec.features.rivers.custom_shapefile else None

        self.chk_lakes.setChecked(spec.features.lakes.enabled)
        self.spin_lake_width.setValue(spec.features.lakes.linewidth)
        self._lake_color = spec.features.lakes.color
        self._custom_shp_lakes = str(spec.features.lakes.custom_shapefile) if spec.features.lakes.custom_shapefile else None

        # 5. Custom shapefiles
        self.list_shapefiles.clear()
        self._custom_shapefiles = []
        for s in spec.custom_shapefiles:
            p_str = str(s.path)
            self._custom_shapefiles.append({"path": p_str, "name": s.name or Path(p_str).name, "enabled": s.enabled})
            item = QListWidgetItem(f"✓ {s.name or Path(p_str).name}")
            item.setData(Qt.ItemDataRole.UserRole, p_str)
            self.list_shapefiles.addItem(item)
            self._shp_color = s.color
            self.spin_shp_width.setValue(s.linewidth)

        # 6. Graticules
        self.chk_gridlines.setChecked(spec.graticules.enabled)
        self.chk_labels.setChecked(spec.graticules.draw_labels)
        self.spin_lon_step.setValue(spec.graticules.lon_step)
        self.spin_lat_step.setValue(spec.graticules.lat_step)
        self._grid_color = spec.graticules.color
        self.slider_grid_alpha.setValue(int(spec.graticules.alpha * 100))

        self.apply_projection()


# Backward compatibility alias
ProjectionCartopyView = ProjectionRegionView

