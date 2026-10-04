"""CLI & Batch Rendering Engine View for automated meteorological plot production."""

from __future__ import annotations

import glob
import os
from pathlib import Path
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from xotplot.gui.theme import get_theme_qss


class CliBatchEngineView(QWidget):
    """CLI discovery engine, workflow presets, backend target selector, and batch execution view."""

    batch_started = pyqtSignal(list, dict)  # list of files, execution config
    batch_finished = pyqtSignal(int)        # number of files rendered

    PRESETS = {
        "CONUS Severe Synoptic": {
            "dataset": "GFS 0.25° Synoptic",
            "format": "PNG",
            "dpi": 300,
            "extent": "-125,-66,24,50",
            "projection": "LambertConformal",
            "colormap": "turbo",
            "fields": ["500hPa HGT", "850hPa Wind Barbs", "Surface MSLP"],
        },
        "ECMWF 2m Temp": {
            "dataset": "ECMWF IFS 0.1°",
            "format": "WebP",
            "dpi": 300,
            "extent": "-140,-50,15,65",
            "projection": "PlateCarree",
            "colormap": "cmo.thermal",
            "fields": ["2m Temperature (TMP2m)", "10m Wind Vectors"],
        },
        "GOES Mesoscale Sector (Animation)": {
            "dataset": "GOES-16 ABI Ch13 Clean IR",
            "format": "MP4",
            "dpi": 150,
            "extent": "-105,-85,28,45",
            "projection": "Geostationary",
            "colormap": "plasma",
            "fields": ["Brightness Temperature (Tb)", "GLM Lightning Density"],
        },
    }

    BACKENDS = [
        ("Multiprocessing Pool", "Local multiprocessing worker pool with concurrent CPUs"),
        ("Headless CLI", "Single-process lightweight CLI invocations (xvfb/headless)"),
        ("Slurm Cluster", "Distributed HPC cluster submission via sbatch array jobs"),
        ("Cron Daemon", "Automated recurring background scheduler integration"),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._dark_mode = True
        self._matched_files: list[str] = []
        self._simulated_progress_step = 0
        self._sim_timer = QTimer(self)
        self._sim_timer.timeout.connect(self._advance_batch_simulation)

        self._init_ui()
        self._apply_preset("CONUS Severe Synoptic")
        self._on_search_clicked()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # Main splitter dividing Configuration (Left) and File Discovery/Console (Right)
        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)

        # ================= LEFT SIDEBAR (Config & Specs) =================
        left_scroll = QScrollArea(self.splitter)
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_scroll.setMinimumWidth(400)

        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(4, 4, 8, 4)
        left_layout.setSpacing(10)

        # 1. Workflow Presets & Render Specs
        preset_box = QGroupBox("Workflow Presets & Render Specs", left_container)
        preset_layout = QGridLayout(preset_box)
        preset_layout.setSpacing(6)

        preset_layout.addWidget(QLabel("Preset:"), 0, 0)
        self.combo_preset = QComboBox(preset_box)
        self.combo_preset.addItems(list(self.PRESETS.keys()))
        self.combo_preset.currentTextChanged.connect(self._apply_preset)
        preset_layout.addWidget(self.combo_preset, 0, 1)

        preset_layout.addWidget(QLabel("Output Format:"), 1, 0)
        self.combo_format = QComboBox(preset_box)
        self.combo_format.addItems(["PNG", "WebP", "MP4"])
        self.combo_format.currentTextChanged.connect(self._update_cli_preview)
        preset_layout.addWidget(self.combo_format, 1, 1)

        preset_layout.addWidget(QLabel("Render DPI:"), 2, 0)
        self.spin_dpi = QSpinBox(preset_box)
        self.spin_dpi.setRange(72, 600)
        self.spin_dpi.setValue(300)
        self.spin_dpi.setSingleStep(50)
        self.spin_dpi.valueChanged.connect(self._update_cli_preview)
        preset_layout.addWidget(self.spin_dpi, 2, 1)

        preset_layout.addWidget(QLabel("Bounding Extent:"), 3, 0)
        self.txt_extent = QLineEdit("-125,-66,24,50", preset_box)
        self.txt_extent.textChanged.connect(self._update_cli_preview)
        preset_layout.addWidget(self.txt_extent, 3, 1)

        preset_layout.addWidget(QLabel("Projection:"), 4, 0)
        self.combo_proj = QComboBox(preset_box)
        self.combo_proj.addItems(["LambertConformal", "PlateCarree", "Orthographic", "Geostationary"])
        self.combo_proj.currentTextChanged.connect(self._update_cli_preview)
        preset_layout.addWidget(self.combo_proj, 4, 1)

        left_layout.addWidget(preset_box)

        # 2. Target Execution Backend Selector
        backend_box = QGroupBox("Target Execution Backend", left_container)
        backend_layout = QVBoxLayout(backend_box)
        backend_layout.setSpacing(6)

        self.backend_btn_group = QButtonGroup(backend_box)
        self.backend_radios: list[QRadioButton] = []

        for i, (backend_name, backend_desc) in enumerate(self.BACKENDS):
            radio = QRadioButton(backend_name, backend_box)
            if i == 0:
                radio.setChecked(True)
            self.backend_btn_group.addButton(radio, i)
            self.backend_radios.append(radio)

            radio_container = QVBoxLayout()
            radio_container.setSpacing(1)
            radio_container.addWidget(radio)

            desc_lbl = QLabel(f"  {backend_desc}", backend_box)
            desc_lbl.setStyleSheet("color: #87929a; font-size: 9px;")
            radio_container.addWidget(desc_lbl)
            backend_layout.addLayout(radio_container)

        self.backend_btn_group.idToggled.connect(self._on_backend_changed)

        # Worker count / Cluster partitions
        worker_layout = QHBoxLayout()
        self.lbl_workers = QLabel("Concurrency Workers / Jobs:", backend_box)
        self.spin_workers = QSpinBox(backend_box)
        self.spin_workers.setRange(1, 128)
        self.spin_workers.setValue(8)
        self.spin_workers.valueChanged.connect(self._update_cli_preview)
        worker_layout.addWidget(self.lbl_workers)
        worker_layout.addWidget(self.spin_workers)
        backend_layout.addLayout(worker_layout)

        left_layout.addWidget(backend_box)

        # 3. Batch Actions (Validation & Trigger)
        action_box = QGroupBox("Batch Engine Execution", left_container)
        act_layout = QVBoxLayout(action_box)
        act_layout.setSpacing(6)

        self.btn_validate_syntax = QPushButton("Validate Syntax & Specs", action_box)
        self.btn_validate_syntax.clicked.connect(self._on_validate_syntax)
        act_layout.addWidget(self.btn_validate_syntax)

        self.lbl_validation_status = QLabel("Status: Ready for validation", action_box)
        self.lbl_validation_status.setStyleSheet("color: #87929a; font-weight: 500;")
        act_layout.addWidget(self.lbl_validation_status)

        self.btn_run_batch = QPushButton("Execute Batch Pipeline", action_box)
        self.btn_run_batch.setObjectName("primaryAction")
        self.btn_run_batch.clicked.connect(self._on_execute_batch)
        act_layout.addWidget(self.btn_run_batch)

        # Progress bar
        self.progress_bar = QProgressBar(action_box)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        act_layout.addWidget(self.progress_bar)

        left_layout.addWidget(action_box)
        left_layout.addStretch()

        left_scroll.setWidget(left_container)
        self.splitter.addWidget(left_scroll)

        # ================= RIGHT SIDE (Discovery & Logs) =================
        right_container = QWidget(self.splitter)
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(4, 4, 4, 4)
        right_layout.setSpacing(6)

        # File Discovery Wildcard / Glob Engine
        discovery_box = QGroupBox("File Discovery Engine (Glob / Wildcard Pattern)", right_container)
        disc_layout = QVBoxLayout(discovery_box)
        disc_layout.setSpacing(6)

        # Input row
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Pattern:"))

        self.txt_pattern = QLineEdit("data/**/*.grib2, *.nc", discovery_box)
        search_row.addWidget(self.txt_pattern, stretch=1)

        self.btn_browse = QPushButton("Browse...", discovery_box)
        self.btn_browse.clicked.connect(self._on_browse_dir)
        search_row.addWidget(self.btn_browse)

        self.btn_scan = QPushButton("Discover Files", discovery_box)
        self.btn_scan.clicked.connect(self._on_search_clicked)
        search_row.addWidget(self.btn_scan)

        disc_layout.addLayout(search_row)

        # File match table with status badges
        self.file_table = QTableWidget(0, 4, discovery_box)
        self.file_table.setHorizontalHeaderLabels(["Filename", "Size", "Format", "Status"])
        self.file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.file_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.file_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.file_table.verticalHeader().setVisible(False)
        self.file_table.setAlternatingRowColors(True)
        disc_layout.addWidget(self.file_table, stretch=1)

        right_layout.addWidget(discovery_box, stretch=3)

        # Generated Headless CLI Command / Script Output Box
        output_box = QGroupBox("Generated CLI Command & Execution Telemetry", right_container)
        out_layout = QVBoxLayout(output_box)
        out_layout.setSpacing(4)

        self.txt_cli_preview = QPlainTextEdit(output_box)
        self.txt_cli_preview.setReadOnly(True)
        out_layout.addWidget(self.txt_cli_preview)

        right_layout.addWidget(output_box, stretch=2)

        self.splitter.addWidget(right_container)
        self.splitter.setStretchFactor(0, 2)
        self.splitter.setStretchFactor(1, 3)

        main_layout.addWidget(self.splitter)

    # --- Presets & Handlers ---

    def _apply_preset(self, preset_name: str) -> None:
        if preset_name not in self.PRESETS:
            return
        cfg = self.PRESETS[preset_name]

        self.combo_format.blockSignals(True)
        self.spin_dpi.blockSignals(True)
        self.combo_proj.blockSignals(True)
        self.txt_extent.blockSignals(True)

        idx_fmt = self.combo_format.findText(cfg["format"])
        if idx_fmt >= 0:
            self.combo_format.setCurrentIndex(idx_fmt)

        self.spin_dpi.setValue(cfg["dpi"])
        self.txt_extent.setText(cfg["extent"])

        idx_proj = self.combo_proj.findText(cfg["projection"])
        if idx_proj >= 0:
            self.combo_proj.setCurrentIndex(idx_proj)

        self.combo_format.blockSignals(False)
        self.spin_dpi.blockSignals(False)
        self.combo_proj.blockSignals(False)
        self.txt_extent.blockSignals(False)

        self._update_cli_preview()

    def _on_backend_changed(self) -> None:
        selected_backend = self._get_active_backend()
        if "Slurm" in selected_backend:
            self.lbl_workers.setText("Slurm Tasks (--ntasks):")
        elif "Cron" in selected_backend:
            self.lbl_workers.setText("Schedule Interval (Hours):")
        else:
            self.lbl_workers.setText("Concurrency Workers / Jobs:")
        self._update_cli_preview()

    def _get_active_backend(self) -> str:
        active_id = self.backend_btn_group.checkedId()
        if 0 <= active_id < len(self.BACKENDS):
            return self.BACKENDS[active_id][0]
        return "Multiprocessing Pool"

    def _on_browse_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Select Data Directory", os.getcwd())
        if directory:
            self.txt_pattern.setText(f"{directory}/**/*.grib2")
            self._on_search_clicked()

    def _on_search_clicked(self) -> None:
        """Scan filesystem or populate mock meteorological files matching pattern."""
        raw_pattern = self.txt_pattern.text().strip()
        patterns = [p.strip() for p in raw_pattern.split(",") if p.strip()]

        found_files: list[str] = []
        for pat in patterns:
            found = glob.glob(pat, recursive=True)
            found_files.extend(found)

        # If no local files found on disk matching the pattern, supply standard realistic GFS/ECMWF demo batch list
        if not found_files:
            demo_files = [
                ("GFS_Global_0p25deg_20261004_00z_f000.grib2", "142 MB", "GRIB2", "Ready"),
                ("GFS_Global_0p25deg_20261004_00z_f006.grib2", "142 MB", "GRIB2", "Ready"),
                ("GFS_Global_0p25deg_20261004_00z_f012.grib2", "142 MB", "GRIB2", "Ready"),
                ("GFS_Global_0p25deg_20261004_00z_f018.grib2", "142 MB", "GRIB2", "Ready"),
                ("GFS_Global_0p25deg_20261004_00z_f024.grib2", "142 MB", "GRIB2", "Ready"),
                ("ECMWF_IFS_oper_20261004_12z_step00.nc", "88 MB", "NetCDF4", "Ready"),
                ("ECMWF_IFS_oper_20261004_12z_step06.nc", "88 MB", "NetCDF4", "Ready"),
                ("ECMWF_IFS_oper_20261004_12z_step12.nc", "88 MB", "NetCDF4", "Ready"),
            ]
            self.file_table.setRowCount(len(demo_files))
            self._matched_files = [f[0] for f in demo_files]
            for row, (name, size, fmt, status) in enumerate(demo_files):
                self._set_table_row(row, name, size, fmt, status)
        else:
            self._matched_files = found_files[:100]  # Cap at 100 for responsive display
            self.file_table.setRowCount(len(self._matched_files))
            for row, path in enumerate(self._matched_files):
                p = Path(path)
                try:
                    size_mb = f"{p.stat().st_size / (1024 * 1024):.1f} MB"
                except Exception:
                    size_mb = "N/A"
                fmt = "GRIB2" if p.suffix.lower() in [".grib2", ".grb2"] else "NetCDF"
                self._set_table_row(row, p.name, size_mb, fmt, "Ready")

        self._update_cli_preview()

    def _set_table_row(self, row: int, filename: str, size: str, fmt: str, status: str) -> None:
        item_name = QTableWidgetItem(filename)
        item_size = QTableWidgetItem(size)
        item_fmt = QTableWidgetItem(fmt)
        item_status = QTableWidgetItem(status)

        item_size.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item_fmt.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        # Style badges
        if status == "Ready":
            item_status.setForeground(QColor("#38bdf8" if self._dark_mode else "#0284c7"))
        elif status == "Processing":
            item_status.setForeground(QColor("#f59e0b" if self._dark_mode else "#d97706"))
        elif status == "Completed":
            item_status.setForeground(QColor("#10b981" if self._dark_mode else "#059669"))
        elif status == "Failed":
            item_status.setForeground(QColor("#ef4444" if self._dark_mode else "#dc2626"))

        self.file_table.setItem(row, 0, item_name)
        self.file_table.setItem(row, 1, item_size)
        self.file_table.setItem(row, 2, item_fmt)
        self.file_table.setItem(row, 3, item_status)

    def _on_validate_syntax(self) -> None:
        extent_parts = self.txt_extent.text().split(",")
        if len(extent_parts) != 4:
            self.lbl_validation_status.setText("Status: Invalid extent format (must be west,east,south,north)")
            self.lbl_validation_status.setStyleSheet("color: #ef4444; font-weight: bold;")
            return

        try:
            [float(p) for p in extent_parts]
        except ValueError:
            self.lbl_validation_status.setText("Status: Invalid numerical coordinate in extent")
            self.lbl_validation_status.setStyleSheet("color: #ef4444; font-weight: bold;")
            return

        n_files = len(self._matched_files)
        self.lbl_validation_status.setText(f"Status: Validated OK ({n_files} files ready for pipeline)")
        self.lbl_validation_status.setStyleSheet("color: #10b981; font-weight: bold;")

    def _update_cli_preview(self) -> None:
        backend = self._get_active_backend()
        preset = self.combo_preset.currentText()
        fmt = self.combo_format.currentText().lower()
        dpi = self.spin_dpi.value()
        extent = self.txt_extent.text().strip()
        proj = self.combo_proj.currentText()
        workers = self.spin_workers.value()
        pattern = self.txt_pattern.text().strip()

        if "Slurm" in backend:
            cmd = (
                f"#!/bin/bash\n"
                f"#SBATCH --job-name=xotplot_batch\n"
                f"#SBATCH --ntasks={workers}\n"
                f"#SBATCH --cpus-per-task=2\n"
                f"#SBATCH --time=02:00:00\n"
                f"#SBATCH --output=logs/xotplot_%A_%a.log\n\n"
                f"srun xplot batch \\\n"
                f"  --pattern \"{pattern}\" \\\n"
                f"  --preset \"{preset}\" \\\n"
                f"  --format {fmt} --dpi {dpi} \\\n"
                f"  --proj {proj} --extent {extent} \\\n"
                f"  --output-dir ./renders/slurm/"
            )
        elif "Cron" in backend:
            cmd = (
                f"# Cron Schedule definition (every {workers}h)\n"
                f"0 */{workers} * * * /usr/local/bin/xplot batch "
                f"--pattern \"{pattern}\" "
                f"--format {fmt} --dpi {dpi} "
                f"--preset \"{preset}\" "
                f"--output-dir /var/www/weather_portal/renders/ >> /var/log/xotplot_cron.log 2>&1"
            )
        elif "Headless CLI" in backend:
            cmd = (
                f"xplot batch \\\n"
                f"  --pattern \"{pattern}\" \\\n"
                f"  --backend headless \\\n"
                f"  --format {fmt} --dpi {dpi} \\\n"
                f"  --proj {proj} --extent {extent} \\\n"
                f"  --preset \"{preset}\" \\\n"
                f"  --output-dir ./renders/batch/"
            )
        else:  # Multiprocessing Pool
            cmd = (
                f"xplot batch \\\n"
                f"  --pattern \"{pattern}\" \\\n"
                f"  --workers {workers} \\\n"
                f"  --format {fmt} --dpi {dpi} \\\n"
                f"  --proj {proj} --extent {extent} \\\n"
                f"  --preset \"{preset}\" \\\n"
                f"  --output-dir ./renders/concurrency/"
            )

        self.txt_cli_preview.setPlainText(cmd)

    def _on_execute_batch(self) -> None:
        """Trigger simulated batch rendering execution."""
        if not self._matched_files:
            self._on_search_clicked()

        self._on_validate_syntax()
        self.btn_run_batch.setEnabled(False)
        self.btn_run_batch.setText("Rendering in Progress...")
        self.progress_bar.setValue(0)
        self._simulated_progress_step = 0

        # Mark all files Processing
        for row in range(self.file_table.rowCount()):
            item = self.file_table.item(row, 3)
            if item:
                item.setText("Processing")
                item.setForeground(QColor("#f59e0b" if self._dark_mode else "#d97706"))

        config = {
            "backend": self._get_active_backend(),
            "preset": self.combo_preset.currentText(),
            "format": self.combo_format.currentText(),
            "dpi": self.spin_dpi.value(),
            "extent": self.txt_extent.text(),
            "workers": self.spin_workers.value(),
        }
        self.batch_started.emit(self._matched_files, config)
        self._sim_timer.start(120)

    def _advance_batch_simulation(self) -> None:
        self._simulated_progress_step += 1
        n_rows = self.file_table.rowCount()
        total_steps = max(1, n_rows * 2)
        pct = min(100, int((self._simulated_progress_step / total_steps) * 100))
        self.progress_bar.setValue(pct)

        # Incrementally mark table items Completed
        finished_rows = min(n_rows, self._simulated_progress_step // 2)
        for r in range(finished_rows):
            item = self.file_table.item(r, 3)
            if item and item.text() != "Completed":
                item.setText("Completed")
                item.setForeground(QColor("#10b981" if self._dark_mode else "#059669"))

        if pct >= 100:
            self._sim_timer.stop()
            self.btn_run_batch.setEnabled(True)
            self.btn_run_batch.setText("Execute Batch Pipeline")
            self.lbl_validation_status.setText(f"Status: Batch rendering finished ({n_rows} artifacts produced)")
            self.lbl_validation_status.setStyleSheet("color: #10b981; font-weight: bold;")
            self.batch_finished.emit(n_rows)

    def set_theme(self, dark_mode: bool) -> None:
        """Apply theme mode to child widgets and badges."""
        self._dark_mode = dark_mode
        # Refresh table badge colors
        for r in range(self.file_table.rowCount()):
            item = self.file_table.item(r, 3)
            if item:
                text = item.text()
                if text == "Ready":
                    item.setForeground(QColor("#38bdf8" if dark_mode else "#0284c7"))
                elif text == "Processing":
                    item.setForeground(QColor("#f59e0b" if dark_mode else "#d97706"))
                elif text == "Completed":
                    item.setForeground(QColor("#10b981" if dark_mode else "#059669"))
                elif text == "Failed":
                    item.setForeground(QColor("#ef4444" if dark_mode else "#dc2626"))

        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(get_theme_qss(dark_mode))
