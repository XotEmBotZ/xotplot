"""Variables and dimensions inspector view with statistical summaries and profile/cross-section plots."""

from __future__ import annotations

import numpy as np
from PyQt6.QtCore import Qt, pyqtSignal
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
    QVBoxLayout,
    QWidget,
)

from xotplot.gui.mpl_canvas import MplCanvasWidget
from xotplot.gui.theme import get_theme_qss


class VariablesInspectorView(QWidget):
    """View providing 5D coordinate controls, variable statistics, slicing options, and profile plots."""

    variable_selected = pyqtSignal(str)
    slice_mode_changed = pyqtSignal(str)
    coordinate_changed = pyqtSignal(dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._dark_mode = True
        self._variables_data = [
            {"name": "gh", "desc": "Geopotential Height", "units": "dam", "min": "492.1", "max": "594.3", "mean": "556.8", "std": "21.4"},
            {"name": "t", "desc": "Temperature", "units": "K", "min": "218.4", "max": "311.2", "mean": "268.5", "std": "18.9"},
            {"name": "u", "desc": "U-Component of Wind", "units": "m/s", "min": "-32.4", "max": "68.2", "mean": "12.7", "std": "14.3"},
            {"name": "v", "desc": "V-Component of Wind", "units": "m/s", "min": "-41.1", "max": "45.0", "mean": "1.8", "std": "11.6"},
            {"name": "q", "desc": "Specific Humidity", "units": "g/kg", "min": "0.01", "max": "18.5", "mean": "3.82", "std": "4.12"},
        ]
        self._current_var = "gh"
        self._current_slice_mode = "Direct Slice"

        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # Splitter dividing controls/table on left and embedded canvas plot on right
        self._splitter = QSplitter(Qt.Orientation.Horizontal, self)

        # Left Container: 5D Coordinates + Variable Table + Slicing Dock
        left_widget = QWidget(self)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.setSpacing(8)

        # 1. Coordinate Axes (5D) Panel
        coords_group = QGroupBox("Coordinate Axes (5D Slicing & Subsetting)", left_widget)
        coords_grid = QGridLayout(coords_group)
        coords_grid.setContentsMargins(8, 8, 8, 8)
        coords_grid.setSpacing(6)

        # Time stepper
        coords_grid.addWidget(QLabel("time (Lead Hour):"), 0, 0)
        self.time_spin = QSpinBox(coords_group)
        self.time_spin.setRange(0, 120)
        self.time_spin.setSingleStep(3)
        self.time_spin.setValue(24)
        self.time_spin.setSuffix(" h")
        coords_grid.addWidget(self.time_spin, 0, 1)

        # isobaricInhPa stepper
        coords_grid.addWidget(QLabel("isobaricInhPa:"), 0, 2)
        self.level_combo = QComboBox(coords_group)
        self.level_combo.addItems(["1000", "925", "850", "700", "500", "300", "250", "200", "100", "50", "10"])
        self.level_combo.setCurrentText("500")
        coords_grid.addWidget(self.level_combo, 0, 3)

        # Ensemble stepper
        coords_grid.addWidget(QLabel("ensemble member:"), 1, 0)
        self.ens_spin = QSpinBox(coords_group)
        self.ens_spin.setRange(0, 50)
        self.ens_spin.setValue(0)
        self.ens_spin.setPrefix("mem_")
        coords_grid.addWidget(self.ens_spin, 1, 1)

        # Spatial bounding box
        coords_grid.addWidget(QLabel("Lat Range [S, N]:"), 2, 0)
        lat_box = QHBoxLayout()
        self.lat_min = QDoubleSpinBox(coords_group)
        self.lat_min.setRange(-90.0, 90.0)
        self.lat_min.setValue(20.0)
        self.lat_max = QDoubleSpinBox(coords_group)
        self.lat_max.setRange(-90.0, 90.0)
        self.lat_max.setValue(60.0)
        lat_box.addWidget(self.lat_min)
        lat_box.addWidget(QLabel("to"))
        lat_box.addWidget(self.lat_max)
        coords_grid.addLayout(lat_box, 2, 1, 1, 3)

        coords_grid.addWidget(QLabel("Lon Range [W, E]:"), 3, 0)
        lon_box = QHBoxLayout()
        self.lon_min = QDoubleSpinBox(coords_group)
        self.lon_min.setRange(-180.0, 180.0)
        self.lon_min.setValue(-130.0)
        self.lon_max = QDoubleSpinBox(coords_group)
        self.lon_max.setRange(-180.0, 180.0)
        self.lon_max.setValue(-60.0)
        lon_box.addWidget(self.lon_min)
        lon_box.addWidget(QLabel("to"))
        lon_box.addWidget(self.lon_max)
        coords_grid.addLayout(lon_box, 3, 1, 1, 3)

        left_layout.addWidget(coords_group)

        # 2. Searchable Variable Table
        table_group = QGroupBox("Variables Catalog & Summary Statistics", left_widget)
        table_layout = QVBoxLayout(table_group)
        table_layout.setContentsMargins(8, 8, 8, 8)
        table_layout.setSpacing(6)

        search_box = QHBoxLayout()
        search_box.addWidget(QLabel("Filter:"))
        self.search_edit = QLineEdit(table_group)
        self.search_edit.setPlaceholderText("Search variable name, desc, units...")
        search_box.addWidget(self.search_edit)
        table_layout.addLayout(search_box)

        self.table = QTableWidget(table_group)
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["Variable", "Description", "Units", "Min", "Max", "Mean", "Std"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self._populate_variable_table()
        table_layout.addWidget(self.table)
        left_layout.addWidget(table_group)

        # 3. Dimension Reduction & Slicing Dock
        reduction_group = QGroupBox("Dimension Reduction & Slicing Operation", left_widget)
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

        # Right Container: Embedded Canvas for 1D profile or 2D zonal cross-section
        right_widget = QWidget(self)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(4, 4, 4, 4)
        right_layout.setSpacing(6)

        top_bar = QHBoxLayout()
        self.plot_title_lbl = QLabel(f"Diagnostic Plot: {self._current_var.upper()} Profile / Cross-Section")
        self.plot_title_lbl.setStyleSheet("font-weight: bold; font-size: 12px;")
        top_bar.addWidget(self.plot_title_lbl)
        top_bar.addStretch()

        self.btn_refresh_plot = QPushButton("Recompute Plot", right_widget)
        self.btn_refresh_plot.setObjectName("primaryAction")
        top_bar.addWidget(self.btn_refresh_plot)
        right_layout.addLayout(top_bar)

        self.canvas_widget = MplCanvasWidget(right_widget, width=6.5, height=5.5)
        right_layout.addWidget(self.canvas_widget, stretch=1)

        self._splitter.addWidget(right_widget)

        # Splitter sizing
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 1)

        main_layout.addWidget(self._splitter)

        # Connections
        self.search_edit.textChanged.connect(self._on_filter_changed)
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)
        self.rb_direct.toggled.connect(self._on_slice_mode_toggled)
        self.rb_zonal.toggled.connect(self._on_slice_mode_toggled)
        self.rb_time.toggled.connect(self._on_slice_mode_toggled)
        self.rb_vert.toggled.connect(self._on_slice_mode_toggled)
        self.btn_refresh_plot.clicked.connect(self._update_plot)

        self.time_spin.valueChanged.connect(self._on_coord_changed)
        self.level_combo.currentTextChanged.connect(self._on_coord_changed)
        self.ens_spin.valueChanged.connect(self._on_coord_changed)
        self.lat_min.valueChanged.connect(self._on_coord_changed)
        self.lat_max.valueChanged.connect(self._on_coord_changed)
        self.lon_min.valueChanged.connect(self._on_coord_changed)
        self.lon_max.valueChanged.connect(self._on_coord_changed)

        # Select first row and render initial plot
        self.table.selectRow(0)
        self._update_plot()

    def _populate_variable_table(self) -> None:
        self.table.setRowCount(len(self._variables_data))
        for row_idx, var in enumerate(self._variables_data):
            self.table.setItem(row_idx, 0, QTableWidgetItem(var["name"]))
            self.table.setItem(row_idx, 1, QTableWidgetItem(var["desc"]))
            self.table.setItem(row_idx, 2, QTableWidgetItem(var["units"]))
            self.table.setItem(row_idx, 3, QTableWidgetItem(var["min"]))
            self.table.setItem(row_idx, 4, QTableWidgetItem(var["max"]))
            self.table.setItem(row_idx, 5, QTableWidgetItem(var["mean"]))
            self.table.setItem(row_idx, 6, QTableWidgetItem(var["std"]))

    def _on_filter_changed(self, text: str) -> None:
        query = text.lower().strip()
        for row in range(self.table.rowCount()):
            matches = False
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and query in item.text().lower():
                    matches = True
                    break
            self.table.setRowHidden(row, not matches)

    def _on_table_selection_changed(self) -> None:
        selected_rows = self.table.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            var_name = self.table.item(row, 0).text()
            self._current_var = var_name
            self.plot_title_lbl.setText(f"Diagnostic Plot: {self._current_var.upper()} ({self._current_slice_mode})")
            self.variable_selected.emit(var_name)
            self._update_plot()

    def _on_slice_mode_toggled(self) -> None:
        if self.rb_direct.isChecked():
            self._current_slice_mode = "Direct Slice"
        elif self.rb_zonal.isChecked():
            self._current_slice_mode = "Zonal Mean"
        elif self.rb_time.isChecked():
            self._current_slice_mode = "Time Mean"
        elif self.rb_vert.isChecked():
            self._current_slice_mode = "Vertical Integral"

        self.plot_title_lbl.setText(f"Diagnostic Plot: {self._current_var.upper()} ({self._current_slice_mode})")
        self.slice_mode_changed.emit(self._current_slice_mode)
        self._update_plot()

    def _on_coord_changed(self) -> None:
        coords = {
            "time": self.time_spin.value(),
            "level": self.level_combo.currentText(),
            "ensemble": self.ens_spin.value(),
            "lat_min": self.lat_min.value(),
            "lat_max": self.lat_max.value(),
            "lon_min": self.lon_min.value(),
            "lon_max": self.lon_max.value(),
        }
        self.coordinate_changed.emit(coords)

    def _update_plot(self) -> None:
        """Plot either a 1D vertical profile or 2D zonal cross-section based on reduction mode."""
        self.canvas_widget.figure.clear()
        ax = self.canvas_widget.figure.add_subplot(111)

        pressure_levels = np.array([1000, 925, 850, 700, 600, 500, 400, 300, 250, 200, 150, 100])

        if self._current_slice_mode in ["Direct Slice", "Vertical Integral"]:
            # 1D Vertical Profile (Log-pressure axis)
            if self._current_var == "gh":
                values = 500.0 - 450.0 * np.log10(pressure_levels / 1000.0) + np.random.normal(0, 1.5, len(pressure_levels))
                unit_label = "Geopotential Height [dam]"
            elif self._current_var == "t":
                values = 288.15 - 6.5 * (1000 - pressure_levels) / 100.0 + np.random.normal(0, 1.0, len(pressure_levels))
                unit_label = "Temperature [K]"
            elif self._current_var in ["u", "v"]:
                values = 5.0 + 35.0 * np.sin((1000 - pressure_levels) / 700 * np.pi) + np.random.normal(0, 1.2, len(pressure_levels))
                unit_label = f"{self._current_var.upper()}-Wind Component [m/s]"
            else:
                values = 14.0 * np.exp(-(1000 - pressure_levels) / 250.0) + np.random.normal(0, 0.2, len(pressure_levels))
                unit_label = "Specific Humidity [g/kg]"

            color = "#38bdf8" if self._dark_mode else "#0284c7"
            ax.plot(values, pressure_levels, marker="o", linewidth=2.0, color=color, label=f"{self._current_var.upper()} Profile")
            ax.set_yscale("log")
            ax.set_ylim(1050, 90)
            ax.set_yticks([1000, 850, 700, 500, 300, 200, 100])
            ax.get_yaxis().set_major_formatter(lambda x, pos: f"{int(x)}")
            ax.set_ylabel("Pressure [hPa]")
            ax.set_xlabel(unit_label)
            ax.set_title(f"1D Vertical Profile: {self._current_var.upper()} @ T+{self.time_spin.value()}h")
            ax.legend(loc="upper right", framealpha=0.3)

        else:
            # 2D Zonal Cross-Section (Latitude vs Pressure)
            lats = np.linspace(self.lat_min.value(), self.lat_max.value(), 30)
            LAT, P = np.meshgrid(lats, pressure_levels)

            if self._current_var == "gh":
                Z = 500 - 400 * np.log10(P / 1000.0) - 0.4 * (LAT - 20)
                label = "Geopotential Height [dam]"
                cmap = "turbo"
            elif self._current_var == "t":
                Z = 288 - 0.05 * (1000 - P) - 0.5 * (LAT - 20)
                label = "Temperature [K]"
                cmap = "coolwarm"
            elif self._current_var in ["u", "v"]:
                Z = 45.0 * np.exp(-((LAT - 35) ** 2) / 150.0) * np.sin((1000 - P) / 800.0 * np.pi)
                label = f"{self._current_var.upper()}-Wind [m/s]"
                cmap = "plasma"
            else:
                Z = 12.0 * np.exp(-((LAT - 25) ** 2) / 250.0) * (P / 1000.0) ** 2
                label = "Specific Humidity [g/kg]"
                cmap = "viridis"

            cf = ax.contourf(LAT, P, Z, levels=12, cmap=cmap)
            cs = ax.contour(LAT, P, Z, levels=12, colors="#ffffff" if self._dark_mode else "#000000", linewidths=0.6, alpha=0.5)
            ax.clabel(cs, inline=True, fontsize=7)

            ax.set_yscale("log")
            ax.set_ylim(1050, 90)
            ax.set_yticks([1000, 850, 700, 500, 300, 200, 100])
            ax.get_yaxis().set_major_formatter(lambda x, pos: f"{int(x)}")
            ax.set_ylabel("Pressure [hPa]")
            ax.set_xlabel("Latitude (°N)")
            ax.set_title(f"2D Zonal Mean Cross-Section: {self._current_var.upper()} (T+{self.time_spin.value()}h)")

            cbar = self.canvas_widget.figure.colorbar(cf, ax=ax, orientation="horizontal", pad=0.16, shrink=0.85)
            cbar.set_label(label, fontsize=8, color="#dfe2ef" if self._dark_mode else "#0f172a")
            cbar.ax.tick_params(colors="#dfe2ef" if self._dark_mode else "#0f172a", labelsize=8)

        self.canvas_widget.apply_theme(self._dark_mode)
        self.canvas_widget.figure.tight_layout()
        self.canvas_widget.canvas.draw_idle()

    def set_theme(self, dark_mode: bool) -> None:
        """Update canvas and UI theme styling."""
        self._dark_mode = dark_mode
        self.canvas_widget.apply_theme(dark_mode)
        self._update_plot()

        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(get_theme_qss(dark_mode))
