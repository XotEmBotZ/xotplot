"""Main window for xotplot meteorological workbench linking all reference views."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from xotplot.constants import (
    STATUS_BUSY_COLOR,
    STATUS_BUSY_TEXT,
    STATUS_IDLE_COLOR,
    STATUS_IDLE_TEXT,
    VIEW_NAMES,
)
from xotplot.engine import get_qt_engine_bridge
from xotplot.gui.theme import get_theme_qss
from xotplot.gui.views import (
    CliBatchEngineView,
    ColormapTransferView,
    ComputeDaskView,
    DerivedDiagnosticsView,
    LayerStackView,
    ProjectionRegionView,
    SpatialViewportView,
    VariablesInspectorView,
)


class MainWindow(QMainWindow):
    """Integrated xotplot Meteorological Visualization & Workflow Engine MainWindow."""

    VIEW_NAMES = VIEW_NAMES


    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("xotplot — Meteorological Visualization & Workflow Engine [PyQt6 / Matplotlib Core]")
        self.resize(1440, 900)

        self._dark_mode = True

        self._init_menu_bar()
        self._init_tool_bar()
        self._init_central_ui()
        self._init_status_bar()

        # Connect signals
        self._nav_list.currentRowChanged.connect(self._on_view_changed)

        # Apply initial theme
        self._apply_theme(self._dark_mode)

    def _init_menu_bar(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        open_action = QAction("&Open Data...", self)
        open_action.setShortcut(QKeySequence("Ctrl+O"))
        open_action.triggered.connect(lambda: self._status_bar.showMessage("Open Data triggered", 2000))
        file_menu.addAction(open_action)

        export_action = QAction("&Export Figure...", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(lambda: self._status_bar.showMessage("Export Figure triggered", 2000))
        file_menu.addAction(export_action)

        file_menu.addSeparator()
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        edit_menu = menubar.addMenu("&Edit")
        edit_menu.addAction("Reset Defaults")
        prefs_action = QAction("&Feature Download Preferences...", self)
        prefs_action.setShortcut(QKeySequence("Ctrl+,"))
        prefs_action.triggered.connect(self._open_cartopy_preferences)
        edit_menu.addAction(prefs_action)

        view_menu = menubar.addMenu("&View")
        self._theme_action = QAction("&Dark Mode", self, checkable=True)
        self._theme_action.setChecked(True)
        self._theme_action.setShortcut(QKeySequence("Ctrl+T"))
        self._theme_action.triggered.connect(self._on_toggle_theme)
        view_menu.addAction(self._theme_action)

        view_menu.addSeparator()
        for i, name in enumerate(self.VIEW_NAMES):
            act = QAction(f"Show {name}", self)
            act.triggered.connect(lambda checked, idx=i: self._nav_list.setCurrentRow(idx))
            view_menu.addAction(act)

        menubar.addMenu("&Layer")
        menubar.addMenu("&Projection")
        menubar.addMenu("&Colormap")
        menubar.addMenu("&CLI Export")
        menubar.addMenu("&Tools")
        menubar.addMenu("&Window")
        menubar.addMenu("&Help")

    def _init_tool_bar(self) -> None:
        toolbar = QToolBar("Main Controls", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        btn_open = QPushButton("Open Data")
        btn_open.clicked.connect(lambda: self._status_bar.showMessage("Open Data clicked", 2000))
        toolbar.addWidget(btn_open)

        btn_preview = QPushButton("Preview")
        btn_preview.clicked.connect(lambda: self._status_bar.showMessage("Preview clicked", 2000))
        toolbar.addWidget(btn_preview)

        btn_render = QPushButton("Render")
        btn_render.setObjectName("primaryAction")
        btn_render.clicked.connect(lambda: self._status_bar.showMessage("Render clicked", 2000))
        toolbar.addWidget(btn_render)

        toolbar.addSeparator()

        self._theme_btn = QPushButton("Toggle Light/Dark")
        self._theme_btn.clicked.connect(lambda: self._set_theme(not self._dark_mode))
        toolbar.addWidget(self._theme_btn)

        toolbar.addSeparator()

        lbl_backend = QLabel(" BACKEND: Qt6Agg | DPI: 192 | CACHE: 1.4 GB / 8.0 GB ")
        toolbar.addWidget(lbl_backend)

    def _init_central_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal, central_widget)

        # Left Nav Aside
        left_aside = QWidget()
        left_aside.setMinimumWidth(220)
        left_aside.setMaximumWidth(280)
        aside_layout = QVBoxLayout(left_aside)
        aside_layout.setContentsMargins(6, 6, 6, 6)
        aside_layout.setSpacing(4)

        aside_hdr = QLabel("WORKBENCH DOCKS")
        aside_hdr.setStyleSheet("font-weight: bold; color: #87929a; font-size: 10px; padding: 4px;")
        aside_layout.addWidget(aside_hdr)

        self._nav_list = QListWidget()
        self._nav_list.addItems(self.VIEW_NAMES)
        self._nav_list.setCurrentRow(0)
        aside_layout.addWidget(self._nav_list, stretch=1)

        # Loaded Dataset card at bottom of aside
        ds_card = QWidget()
        ds_card_layout = QVBoxLayout(ds_card)
        ds_card_layout.setContentsMargins(6, 6, 6, 6)
        ds_card_layout.setSpacing(2)
        lbl_ds_title = QLabel("LOADED DATASET: GFS (NETCDF4)")
        lbl_ds_title.setStyleSheet("font-size: 9px; font-weight: bold; color: #10b981;")
        lbl_ds_name = QLabel("gfs.t00z.pgrb2.0p25.f024")
        lbl_ds_name.setStyleSheet("font-family: monospace; font-size: 10px;")
        lbl_ds_meta = QLabel("721x1440 pts | 148.2 MB")
        lbl_ds_meta.setStyleSheet("font-size: 9px; color: #87929a;")

        ds_card_layout.addWidget(lbl_ds_title)
        ds_card_layout.addWidget(lbl_ds_name)
        ds_card_layout.addWidget(lbl_ds_meta)
        aside_layout.addWidget(ds_card)

        splitter.addWidget(left_aside)

        # Right View Stack
        self._view_stack = QStackedWidget()

        # Instantiate all 8 reference views
        self._view_spatial = SpatialViewportView()
        self._view_variables = VariablesInspectorView()
        self._view_projection = ProjectionRegionView()
        self._view_layers = LayerStackView()
        self._view_colormap = ColormapTransferView()
        self._view_cli_batch = CliBatchEngineView()
        self._view_diagnostics = DerivedDiagnosticsView()
        self._view_compute = ComputeDaskView()

        self._views_list = [
            self._view_spatial,
            self._view_variables,
            self._view_projection,
            self._view_layers,
            self._view_colormap,
            self._view_cli_batch,
            self._view_diagnostics,
            self._view_compute,
        ]

        for v in self._views_list:
            self._view_stack.addWidget(v)

        splitter.addWidget(self._view_stack)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter)

    def _init_status_bar(self) -> None:
        self._status_bar = QStatusBar(self)
        self.setStatusBar(self._status_bar)

        self._lbl_idle = QLabel(STATUS_IDLE_TEXT)
        self._lbl_idle.setStyleSheet(f"color: {STATUS_IDLE_COLOR}; font-weight: bold;")
        self._status_bar.addPermanentWidget(self._lbl_idle)

        self._engine_bridge = get_qt_engine_bridge()
        self._engine_bridge.status_changed.connect(self._on_engine_status_changed)

    def _on_engine_status_changed(self, is_busy: bool, active_jobs: int) -> None:
        if is_busy:
            text = f"{STATUS_BUSY_TEXT} ({active_jobs} active)"
            self._lbl_idle.setText(text)
            self._lbl_idle.setStyleSheet(f"color: {STATUS_BUSY_COLOR}; font-weight: bold;")
        else:
            self._lbl_idle.setText(STATUS_IDLE_TEXT)
            self._lbl_idle.setStyleSheet(f"color: {STATUS_IDLE_COLOR}; font-weight: bold;")

    def _on_view_changed(self, index: int) -> None:
        if 0 <= index < len(self._views_list):
            self._view_stack.setCurrentIndex(index)
            self._status_bar.showMessage(f"Active Workbench View: {self.VIEW_NAMES[index]}", 1500)

    def _on_toggle_theme(self, checked: bool) -> None:
        self._set_theme(checked)

    def _set_theme(self, dark_mode: bool) -> None:
        self._dark_mode = dark_mode
        self._theme_action.setChecked(dark_mode)
        self._theme_action.setText("&Dark Mode" if dark_mode else "&Light Mode")
        self._apply_theme(dark_mode)

    def _apply_theme(self, dark_mode: bool) -> None:
        qss = get_theme_qss(dark_mode)
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(qss)

        # Notify child views to update their Matplotlib figures and custom styles
        for v in self._views_list:
            if hasattr(v, "set_theme"):
                v.set_theme(dark_mode)

        self._status_bar.showMessage(f"Applied {'Dark' if dark_mode else 'Light'} theme", 2000)

    def _open_cartopy_preferences(self) -> None:
        """Open Cartopy feature preferences and download manager dialog."""
        from xotplot.gui.preferences_dialog import CartopyPreferencesDialog

        dialog = CartopyPreferencesDialog(self)
        dialog.features_updated.connect(self._view_projection.apply_projection)
        dialog.exec()
