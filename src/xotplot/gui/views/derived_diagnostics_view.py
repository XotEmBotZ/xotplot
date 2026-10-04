"""Derived Diagnostics view with MetPy presets, formula editor, stencils, and preview canvas."""

from __future__ import annotations

import numpy as np
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from xotplot.engine import render_diagnostic_plot
from xotplot.gui.mpl_canvas import MplCanvasWidget


class DerivedDiagnosticsView(QWidget):
    """View for configuring, editing, and previewing derived meteorological diagnostics."""

    diagnostic_evaluated = pyqtSignal(str, str)  # preset/expr name, status message

    PRESETS = {
        "Relative Vorticity": {
            "formula": "d(VGRD)/dx - d(UGRD)/dy",
            "desc": "Vertical component of curl of horizontal velocity: ζ = ∂v/∂x - ∂u/∂y",
            "inputs": ["UGRD", "VGRD"],
            "unit": "10⁻⁵ s⁻¹",
        },
        "Theta-E (Equivalent Potential Temp)": {
            "formula": "TMP * (1000 / PRES) ** 0.286 * exp(2500000 * QVAPOR / (1004 * TMP))",
            "desc": "Equivalent potential temperature indicating moist atmospheric instability.",
            "inputs": ["TMP", "PRES", "QVAPOR"],
            "unit": "K",
        },
        "Bulk Shear 0-6km": {
            "formula": "sqrt((UGRD[6km] - UGRD[sfc])**2 + (VGRD[6km] - VGRD[sfc])**2)",
            "desc": "Kinematic deep-layer vector difference assessing severe thunderstorm organization.",
            "inputs": ["UGRD", "VGRD", "HGT"],
            "unit": "m/s",
        },
        "Frontogenesis (Petterssen 2D)": {
            "formula": "-0.5 * |∇θ| * ((∂u/∂x - ∂v/∂y)*cos(2ψ) + (∂v/∂x + ∂u/∂y)*sin(2ψ))",
            "desc": "Kinematic 2D frontogenesis function tracking baroclinic tightening.",
            "inputs": ["TMP", "UGRD", "VGRD", "PRES"],
            "unit": "K / (100 km · 3 h)",
        },
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("derivedDiagnosticsView")
        self._dark_mode = True

        self._init_ui()
        self._load_presets()
        self.update_preview()

    def _init_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setObjectName("diagSplitter")
        main_layout.addWidget(splitter)

        # ---------------- Left Control Panel ----------------
        control_panel = QWidget()
        control_layout = QVBoxLayout(control_panel)
        control_layout.setContentsMargins(4, 4, 4, 4)
        control_layout.setSpacing(8)

        # 1. Preset Library Group
        preset_group = QGroupBox("MetPy Diagnostic Presets Library")
        preset_layout = QVBoxLayout(preset_group)
        preset_layout.setSpacing(4)

        self.preset_list = QListWidget()
        self.preset_list.setObjectName("presetList")
        self.preset_list.setFixedHeight(120)
        self.preset_list.itemSelectionChanged.connect(self._on_preset_selected)
        preset_layout.addWidget(self.preset_list)

        self.preset_desc_lbl = QLabel("Select a preset diagnostic above.")
        self.preset_desc_lbl.setWordWrap(True)
        self.preset_desc_lbl.setStyleSheet("color: #87929a; font-size: 10px;")
        preset_layout.addWidget(self.preset_desc_lbl)
        control_layout.addWidget(preset_group)

        # 2. Formula Editor Group
        expr_group = QGroupBox("Formula Expression Editor")
        expr_layout = QVBoxLayout(expr_group)
        expr_layout.setSpacing(6)

        # Parameter tags quick insert buttons
        tags_layout = QHBoxLayout()
        tags_layout.setSpacing(4)
        tag_label = QLabel("Quick Insert:")
        tag_label.setStyleSheet("font-weight: bold; font-size: 10px;")
        tags_layout.addWidget(tag_label)

        self.tag_buttons = []
        for tag in ["+ TMP", "+ UGRD", "+ VGRD", "+ PRES", "+ HGT"]:
            btn = QPushButton(tag)
            btn.setObjectName("tagInsertBtn")
            btn.setFixedHeight(22)
            btn.setToolTip(f"Insert parameter tag '{tag[2:]}' into formula")
            btn.clicked.connect(lambda _, t=tag[2:]: self._insert_tag(t))
            self.tag_buttons.append(btn)
            tags_layout.addWidget(btn)
        tags_layout.addStretch()
        expr_layout.addLayout(tags_layout)

        # Formula text area
        self.formula_edit = QPlainTextEdit()
        self.formula_edit.setObjectName("formulaEditor")
        self.formula_edit.setPlaceholderText("Enter custom diagnostic formula or derivative expression...")
        self.formula_edit.setFixedHeight(75)
        expr_layout.addWidget(self.formula_edit)

        # Output variable name and units row
        meta_row = QHBoxLayout()
        meta_row.addWidget(QLabel("Output Var:"))
        self.output_var_input = QLineEdit("DIAG_OUT")
        self.output_var_input.setFixedWidth(110)
        meta_row.addWidget(self.output_var_input)

        meta_row.addWidget(QLabel("Units:"))
        self.unit_input = QLineEdit("auto")
        self.unit_input.setFixedWidth(100)
        meta_row.addWidget(self.unit_input)
        meta_row.addStretch()
        expr_layout.addLayout(meta_row)

        control_layout.addWidget(expr_group)

        # 3. Spatial Stencils and Grid Metrics Group
        stencil_group = QGroupBox("Spatial Stencils & Grid Metric Options")
        stencil_layout = QGridLayout(stencil_group)
        stencil_layout.setSpacing(6)

        stencil_layout.addWidget(QLabel("Difference Stencil:"), 0, 0)
        self.stencil_combo = QComboBox()
        self.stencil_combo.addItems([
            "Centered (2nd-Order Finite Difference)",
            "Compact Pade (4th-Order High Resolution)",
            "Forward / Backward (Boundary Adaptive)",
            "Central 4th-Order Stencil",
        ])
        stencil_layout.addWidget(self.stencil_combo, 0, 1)

        stencil_layout.addWidget(QLabel("Metric Scaling:"), 1, 0)
        self.metric_combo = QComboBox()
        self.metric_combo.addItems([
            "cos(lat) Spherical Metric Correction",
            "Cartesian Equal-Area dx/dy",
            "Lambert Conformal Map-Factor (m_x, m_y)",
            "Polar Stereographic True Metric",
        ])
        stencil_layout.addWidget(self.metric_combo, 1, 1)

        stencil_layout.addWidget(QLabel("Smoothing / Filter:"), 2, 0)
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "None (Raw Diagnostic)",
            "Gaussian Filter (σ = 1.0 grid points)",
            "9-Point Spatial Smoother (Shuman)",
            "Tukey Spectral Window",
        ])
        stencil_layout.addWidget(self.filter_combo, 2, 1)
        control_layout.addWidget(stencil_group)

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self.compute_btn = QPushButton("Calculate Diagnostic")
        self.compute_btn.setObjectName("primaryAction")
        self.compute_btn.clicked.connect(self.update_preview)
        btn_row.addWidget(self.compute_btn)

        self.reset_btn = QPushButton("Reset Expression")
        self.reset_btn.clicked.connect(self._reset_expression)
        btn_row.addWidget(self.reset_btn)

        control_layout.addLayout(btn_row)
        control_layout.addStretch()

        splitter.addWidget(control_panel)

        # ---------------- Right Canvas Preview Panel ----------------
        preview_panel = QFrame()
        preview_panel.setFrameShape(QFrame.Shape.StyledPanel)
        preview_layout = QVBoxLayout(preview_panel)
        preview_layout.setContentsMargins(6, 6, 6, 6)
        preview_layout.setSpacing(4)

        header_row = QHBoxLayout()
        self.preview_title = QLabel("Computed Diagnostic Field Preview")
        self.preview_title.setStyleSheet("font-weight: bold; font-size: 12px; color: #8ed5ff;")
        header_row.addWidget(self.preview_title)

        header_row.addStretch()
        self.stats_badge = QLabel("Min: -14.2 | Max: +18.5 | Mean: +1.2")
        self.stats_badge.setStyleSheet("color: #87929a; font-size: 10px; background-color: #181b25; padding: 2px 6px; border-radius: 2px;")
        header_row.addWidget(self.stats_badge)
        preview_layout.addLayout(header_row)

        self.canvas_widget = MplCanvasWidget(self, width=7.0, height=5.0)
        preview_layout.addWidget(self.canvas_widget)

        splitter.addWidget(preview_panel)
        splitter.setSizes([450, 750])

    def _load_presets(self) -> None:
        """Populate preset list widget."""
        self.preset_list.clear()
        for name in self.PRESETS:
            item = QListWidgetItem(name)
            self.preset_list.addItem(item)
        if self.preset_list.count() > 0:
            self.preset_list.setCurrentRow(0)

    def _on_preset_selected(self) -> None:
        """Handle selection of a preset item."""
        current_item = self.preset_list.currentItem()
        if not current_item:
            return
        preset_name = current_item.text()
        info = self.PRESETS.get(preset_name, {})
        self.formula_edit.setPlainText(info.get("formula", ""))
        self.preset_desc_lbl.setText(f"{info.get('desc', '')} [Inputs: {', '.join(info.get('inputs', []))}]")
        self.unit_input.setText(info.get("unit", "auto"))

        slug = "".join(c if c.isalnum() else "_" for c in preset_name).upper().strip("_")
        self.output_var_input.setText(slug[:12])
        self.update_preview()

    def _insert_tag(self, tag: str) -> None:
        """Insert variable tag at cursor position in formula editor."""
        self.formula_edit.insertPlainText(tag)
        self.formula_edit.setFocus()

    def _reset_expression(self) -> None:
        """Reset formula editor to currently selected preset."""
        self._on_preset_selected()

    def set_theme(self, dark_mode: bool) -> None:
        """Apply dark or light theme colors to embedded widgets and canvas."""
        self._dark_mode = dark_mode
        self.canvas_widget.apply_theme(dark_mode)

        stats_bg = "#181b25" if dark_mode else "#f1f5f9"
        stats_fg = "#87929a" if dark_mode else "#64748b"
        title_fg = "#8ed5ff" if dark_mode else "#0284c7"

        self.stats_badge.setStyleSheet(
            f"color: {stats_fg}; font-size: 10px; background-color: {stats_bg}; padding: 2px 6px; border-radius: 2px;"
        )
        self.preview_title.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {title_fg};")
        self.update_preview()

    def update_preview(self) -> None:
        """Render computed diagnostic field contours on Matplotlib canvas."""
        current_item = self.preset_list.currentItem()
        preset_name = current_item.text() if current_item else "Custom Formula"
        var_name = self.output_var_input.text().strip() or "DIAGNOSTIC"
        unit_str = self.unit_input.text().strip() or "-"
        stencil_str = self.stencil_combo.currentText().split("(")[0].strip()
        metric_str = self.metric_combo.currentText().split("(")[0].strip()

        # Build synthetic preview grid
        lons = np.linspace(-125, -65, 60)
        lats = np.linspace(22, 52, 45)
        X, Y = np.meshgrid(lons, lats)

        # Synthesize atmospheric diagnostic fields based on active preset
        if "Vorticity" in preset_name:
            field = 10 * np.sin(np.radians((X + 100) * 4)) * np.cos(np.radians((Y - 35) * 6)) + 2.5 * np.cos(np.radians(X * 2))
            cmap = "PuOr_r"
            title = f"Relative Vorticity (ζ) [{unit_str}] — Stencil: {stencil_str}"
        elif "Theta-E" in preset_name:
            field = 300 + (Y - 22) * 2.2 + 18 * np.sin(np.radians((X + 90) * 3)) * np.exp(-((Y - 32) ** 2) / 60)
            cmap = "turbo"
            title = f"Equivalent Potential Temperature (θ_e) [{unit_str}]"
        elif "Shear" in preset_name:
            field = 15 + 20 * np.sin(np.radians(Y * 2.5)) ** 2 + 8 * np.cos(np.radians(X * 3))
            cmap = "plasma"
            title = f"Bulk Wind Shear 0-6km Vector Difference [{unit_str}]"
        elif "Frontogenesis" in preset_name:
            shear_zone = np.exp(-((Y - (38 + 5 * np.sin(np.radians(X * 2.5)))) ** 2) / 12)
            field = shear_zone * 4.8 * np.cos(np.radians((X + 85) * 5))
            cmap = "seismic"
            title = f"2D Petterssen Frontogenesis [{unit_str}] — {metric_str}"
        else:
            field = 10 * np.sin(np.radians(X * 2)) * np.cos(np.radians(Y * 2))
            cmap = "viridis"
            title = f"Custom Diagnostic: {var_name} [{unit_str}]"

        f_min, f_max, f_mean = float(np.min(field)), float(np.max(field)), float(np.mean(field))
        self.stats_badge.setText(f"Min: {f_min:+.2f} | Max: {f_max:+.2f} | Mean: {f_mean:+.2f} {unit_str}")

        render_diagnostic_plot(
            var_name=var_name,
            unit_str=unit_str,
            preset_name=preset_name,
            figure=self.canvas_widget.figure,
        )
        self.canvas_widget.apply_theme(self._dark_mode)
        self.canvas_widget.canvas.draw_idle()

        self.diagnostic_evaluated.emit(preset_name, f"Calculated {var_name} successfully")
