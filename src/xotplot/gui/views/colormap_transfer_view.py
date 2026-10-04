"""Colormap & Transfer Function Curve Editor View for meteorological workflows."""

from __future__ import annotations

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.colors import (
    BoundaryNorm,
    Colormap,
    LinearSegmentedColormap,
    LogNorm,
    Normalize,
    TwoSlopeNorm,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from xotplot.gui.mpl_canvas import MplCanvasWidget
from xotplot.gui.theme import get_theme_qss

# Register custom meteorological colormaps if not present in Matplotlib
_CUSTOM_COLORMAPS: dict[str, list[str]] = {
    "cmo.thermal": [
        "#040314",
        "#1c0d45",
        "#420a68",
        "#6b116f",
        "#932667",
        "#b74251",
        "#d56637",
        "#e98e26",
        "#f4ba3e",
        "#f2e661",
        "#fcffa4",
    ],
    "radar_nws": [
        "#00eaff",
        "#00a0ff",
        "#0000f6",
        "#00e000",
        "#00a000",
        "#006000",
        "#ffff00",
        "#e7c000",
        "#ff9000",
        "#ff0000",
        "#d00000",
        "#a00000",
        "#ff00ff",
        "#9900ee",
        "#ffffff",
    ],
}

for name, hex_colors in _CUSTOM_COLORMAPS.items():
    if name not in plt.colormaps():
        cmap_obj = LinearSegmentedColormap.from_list(name, hex_colors, N=256)
        matplotlib.colormaps.register(cmap_obj, name=name)


class ColormapCard(QFrame):
    """Visual preview card for a colormap registry item."""

    clicked = pyqtSignal(str)

    def __init__(self, name: str, display_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.name = name
        self.display_name = display_name
        self._selected = False

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel(self.display_name, self)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 11px;")
        header_layout.addWidget(self.title_label)

        self.tag_label = QLabel(self.name, self)
        self.tag_label.setStyleSheet("color: #87929a; font-size: 9px;")
        self.tag_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header_layout.addWidget(self.tag_label)

        layout.addLayout(header_layout)

        # Gradient preview bar
        self.preview_label = QLabel(self)
        self.preview_label.setFixedHeight(18)
        self.preview_label.setScaledContents(True)
        layout.addWidget(self.preview_label)

        self._render_gradient()

    def _render_gradient(self) -> None:
        try:
            cmap = matplotlib.colormaps[self.name]
        except KeyError:
            cmap = matplotlib.colormaps["viridis"]

        width = 160
        height = 16
        vals = np.linspace(0, 1, width)
        rgba = cmap(vals)  # (width, 4) in [0, 1]
        rgba_bytes = (rgba * 255).astype(np.uint8)

        # Create QImage from RGBA data
        img_data = np.tile(rgba_bytes, (height, 1, 1))  # (height, width, 4)
        qimg = QImage(
            img_data.data,
            width,
            height,
            width * 4,
            QImage.Format.Format_RGBA8888,
        )
        self.preview_label.setPixmap(QPixmap.fromImage(qimg.copy()))

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        if selected:
            self.setStyleSheet(
                "QFrame { border: 2px solid #38bdf8; background-color: #1a2333; border-radius: 4px; }"
            )
        else:
            self.setStyleSheet(
                "QFrame { border: 1px solid #262a34; background-color: #0a0e17; border-radius: 4px; }"
                "QFrame:hover { border: 1px solid #38bdf8; }"
            )

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.name)
        super().mousePressEvent(event)


class ColormapTransferView(QWidget):
    """Colormap registry, transfer function curve editor, normalization, and colorbar settings."""

    colormap_changed = pyqtSignal(str)
    normalization_changed = pyqtSignal(object)  # matplotlib Normalize object

    CARDS_DATA = [
        ("viridis", "Viridis (Perceptual)"),
        ("turbo", "Turbo (Rainbow)"),
        ("plasma", "Plasma (Thermal High)"),
        ("coolwarm", "CoolWarm (Diverging)"),
        ("cmo.thermal", "CMO Thermal (Ocean/Temp)"),
        ("radar_nws", "Radar NWS (Reflectivity)"),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._dark_mode = True
        self._current_cmap = "turbo"
        self._card_widgets: dict[str, ColormapCard] = {}

        # Synthetic atmospheric data for histogram and preview
        rng = np.random.default_rng(42)
        syn1 = rng.normal(loc=12.0, scale=8.0, size=5000)
        syn2 = rng.normal(loc=32.0, scale=6.0, size=3500)
        self._data_sample = np.clip(np.concatenate([syn1, syn2]), -20.0, 50.0)

        self._init_ui()
        self._select_colormap("turbo")
        self._update_plot()

    def _init_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # Horizontal Splitter: Left Sidebar (Registry + Config) | Right (MplCanvas Transfer & Preview)
        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)

        # Left Scroll Area containing controls
        left_scroll = QScrollArea(self.splitter)
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_scroll.setMinimumWidth(380)

        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(4, 4, 8, 4)
        left_layout.setSpacing(10)

        # 1. Colormap Registry Cards Group
        registry_box = QGroupBox("Colormap Registry", left_container)
        reg_layout = QVBoxLayout(registry_box)
        reg_layout.setSpacing(6)

        for cmap_name, display_title in self.CARDS_DATA:
            card = ColormapCard(cmap_name, display_title, registry_box)
            card.clicked.connect(self._select_colormap)
            self._card_widgets[cmap_name] = card
            reg_layout.addWidget(card)

        # Invert Colormap checkbox
        self.chk_invert = QCheckBox("Invert Colormap (_r)", registry_box)
        self.chk_invert.toggled.connect(self._on_invert_toggled)
        reg_layout.addWidget(self.chk_invert)

        left_layout.addWidget(registry_box)

        # 2. Transfer Function Curve Controls Group
        curve_box = QGroupBox("Transfer Function Curve Control", left_container)
        curve_layout = QGridLayout(curve_box)
        curve_layout.setSpacing(6)

        curve_layout.addWidget(QLabel("Curve Shape:"), 0, 0)
        self.combo_curve = QComboBox(curve_box)
        self.combo_curve.addItems(["Linear", "Gamma (Power Law)", "Sigmoid (S-Curve)", "Step Quantized"])
        self.combo_curve.currentIndexChanged.connect(self._on_curve_type_changed)
        curve_layout.addWidget(self.combo_curve, 0, 1)

        curve_layout.addWidget(QLabel("Gamma / Exponent:"), 1, 0)
        gamma_sub = QHBoxLayout()
        self.slider_gamma = QSlider(Qt.Orientation.Horizontal, curve_box)
        self.slider_gamma.setRange(20, 300)  # 0.2 to 3.0
        self.slider_gamma.setValue(100)      # 1.0
        self.slider_gamma.valueChanged.connect(self._on_gamma_slider_changed)
        gamma_sub.addWidget(self.slider_gamma)

        self.spin_gamma = QDoubleSpinBox(curve_box)
        self.spin_gamma.setRange(0.2, 3.0)
        self.spin_gamma.setSingleStep(0.05)
        self.spin_gamma.setValue(1.0)
        self.spin_gamma.valueChanged.connect(self._on_gamma_spin_changed)
        gamma_sub.addWidget(self.spin_gamma)
        curve_layout.addLayout(gamma_sub, 1, 1)

        curve_layout.addWidget(QLabel("Center Shift (Bias):"), 2, 0)
        self.slider_bias = QSlider(Qt.Orientation.Horizontal, curve_box)
        self.slider_bias.setRange(-50, 50)
        self.slider_bias.setValue(0)
        self.slider_bias.valueChanged.connect(self._on_bias_changed)
        curve_layout.addWidget(self.slider_bias, 2, 1)

        left_layout.addWidget(curve_box)

        # 3. Discretization & Normalization Levels Generator
        norm_box = QGroupBox("Discretization & Normalization Levels", left_container)
        norm_layout = QGridLayout(norm_box)
        norm_layout.setSpacing(6)

        norm_layout.addWidget(QLabel("Normalization:"), 0, 0)
        self.combo_norm = QComboBox(norm_box)
        self.combo_norm.addItems(["Linear", "BoundaryNorm (Discretized)", "LogNorm", "TwoSlopeNorm (Diverging)"])
        self.combo_norm.currentIndexChanged.connect(self._on_norm_type_changed)
        norm_layout.addWidget(self.combo_norm, 0, 1)

        # Min / Max / Step controls
        norm_layout.addWidget(QLabel("Range (Min / Max):"), 1, 0)
        range_sub = QHBoxLayout()
        self.spin_min = QDoubleSpinBox(norm_box)
        self.spin_min.setRange(-1000.0, 1000.0)
        self.spin_min.setValue(-10.0)
        self.spin_min.valueChanged.connect(self._on_range_changed)
        range_sub.addWidget(self.spin_min)

        self.spin_max = QDoubleSpinBox(norm_box)
        self.spin_max.setRange(-1000.0, 1000.0)
        self.spin_max.setValue(45.0)
        self.spin_max.valueChanged.connect(self._on_range_changed)
        range_sub.addWidget(self.spin_max)
        norm_layout.addLayout(range_sub, 1, 1)

        norm_layout.addWidget(QLabel("Levels / Step:"), 2, 0)
        levels_sub = QHBoxLayout()
        self.spin_step = QDoubleSpinBox(norm_box)
        self.spin_step.setRange(0.1, 100.0)
        self.spin_step.setValue(5.0)
        self.spin_step.valueChanged.connect(self._on_step_changed)
        levels_sub.addWidget(self.spin_step)

        self.lbl_nlevels = QLabel("12 bins", norm_box)
        self.lbl_nlevels.setStyleSheet("color: #87929a;")
        levels_sub.addWidget(self.lbl_nlevels)
        norm_layout.addLayout(levels_sub, 2, 1)

        # Quick min:max:step input string
        norm_layout.addWidget(QLabel("Levels Expression:"), 3, 0)
        expr_sub = QHBoxLayout()
        self.txt_expr = QLineEdit("-10:45:5", norm_box)
        self.btn_apply_expr = QPushButton("Apply", norm_box)
        self.btn_apply_expr.clicked.connect(self._apply_expr_string)
        expr_sub.addWidget(self.txt_expr)
        expr_sub.addWidget(self.btn_apply_expr)
        norm_layout.addLayout(expr_sub, 3, 1)

        # TwoSlopeNorm center
        self.lbl_center = QLabel("Center Point:")
        norm_layout.addWidget(self.lbl_center, 4, 0)
        self.spin_center = QDoubleSpinBox(norm_box)
        self.spin_center.setRange(-1000.0, 1000.0)
        self.spin_center.setValue(0.0)
        self.spin_center.valueChanged.connect(self._on_range_changed)
        norm_layout.addWidget(self.spin_center, 4, 1)

        left_layout.addWidget(norm_box)

        # 4. Colorbar Customization Options
        cbar_box = QGroupBox("Colorbar Customization", left_container)
        cbar_layout = QGridLayout(cbar_box)
        cbar_layout.setSpacing(6)

        cbar_layout.addWidget(QLabel("Orientation:"), 0, 0)
        orient_sub = QHBoxLayout()
        self.radio_horiz = QRadioButton("Horizontal", cbar_box)
        self.radio_horiz.setChecked(True)
        self.radio_vert = QRadioButton("Vertical", cbar_box)
        orient_group = QButtonGroup(cbar_box)
        orient_group.addButton(self.radio_horiz)
        orient_group.addButton(self.radio_vert)
        self.radio_horiz.toggled.connect(self._update_plot)
        orient_sub.addWidget(self.radio_horiz)
        orient_sub.addWidget(self.radio_vert)
        cbar_layout.addLayout(orient_sub, 0, 1)

        cbar_layout.addWidget(QLabel("Shrink Fraction:"), 1, 0)
        self.spin_shrink = QDoubleSpinBox(cbar_box)
        self.spin_shrink.setRange(0.1, 1.0)
        self.spin_shrink.setSingleStep(0.05)
        self.spin_shrink.setValue(0.85)
        self.spin_shrink.valueChanged.connect(self._update_plot)
        cbar_layout.addWidget(self.spin_shrink, 1, 1)

        cbar_layout.addWidget(QLabel("Aspect Ratio:"), 2, 0)
        self.spin_aspect = QSpinBox(cbar_box)
        self.spin_aspect.setRange(5, 60)
        self.spin_aspect.setValue(24)
        self.spin_aspect.valueChanged.connect(self._update_plot)
        cbar_layout.addWidget(self.spin_aspect, 2, 1)

        cbar_layout.addWidget(QLabel("Colorbar Label:"), 3, 0)
        self.txt_cbar_label = QLineEdit("Surface Air Temperature [°C]", cbar_box)
        self.txt_cbar_label.textChanged.connect(self._update_plot)
        cbar_layout.addWidget(self.txt_cbar_label, 3, 1)

        left_layout.addWidget(cbar_box)
        left_layout.addStretch()

        left_scroll.setWidget(left_container)
        self.splitter.addWidget(left_scroll)

        # Right side: MplCanvasWidget plotting data histogram and transfer curve
        right_container = QWidget(self.splitter)
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(4, 4, 4, 4)
        right_layout.setSpacing(6)

        # Canvas widget
        self.canvas_widget = MplCanvasWidget(right_container, width=7.0, height=5.5)
        right_layout.addWidget(self.canvas_widget, stretch=1)

        # Bottom summary status label
        self.status_bar_lbl = QLabel(
            "Colormap: turbo | Norm: BoundaryNorm | Gamma: 1.00", right_container
        )
        self.status_bar_lbl.setStyleSheet("color: #87929a; padding: 2px;")
        right_layout.addWidget(self.status_bar_lbl)

        self.splitter.addWidget(right_container)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)

        main_layout.addWidget(self.splitter)

    # --- Slots & Handlers ---

    def _select_colormap(self, cmap_name: str) -> None:
        self._current_cmap = cmap_name
        for name, card in self._card_widgets.items():
            card.set_selected(name == cmap_name)
        self.colormap_changed.emit(self._get_active_cmap_name())
        self._update_plot()

    def _on_invert_toggled(self, checked: bool) -> None:
        self.colormap_changed.emit(self._get_active_cmap_name())
        self._update_plot()

    def _get_active_cmap_name(self) -> str:
        base = self._current_cmap
        return f"{base}_r" if self.chk_invert.isChecked() else base

    def _on_curve_type_changed(self, index: int) -> None:
        self._update_plot()

    def _on_gamma_slider_changed(self, val: int) -> None:
        gamma = val / 100.0
        self.spin_gamma.blockSignals(True)
        self.spin_gamma.setValue(gamma)
        self.spin_gamma.blockSignals(False)
        self._update_plot()

    def _on_gamma_spin_changed(self, val: float) -> None:
        self.slider_gamma.blockSignals(True)
        self.slider_gamma.setValue(int(round(val * 100)))
        self.slider_gamma.blockSignals(False)
        self._update_plot()

    def _on_bias_changed(self, val: int) -> None:
        self._update_plot()

    def _on_norm_type_changed(self, index: int) -> None:
        norm_type = self.combo_norm.currentText()
        is_twoslope = "TwoSlopeNorm" in norm_type
        self.lbl_center.setVisible(is_twoslope)
        self.spin_center.setVisible(is_twoslope)
        self._update_plot()

    def _on_range_changed(self) -> None:
        if self.spin_max.value() <= self.spin_min.value():
            self.spin_max.setValue(self.spin_min.value() + 1.0)
        self._sync_expr_box()
        self._update_plot()

    def _on_step_changed(self) -> None:
        self._sync_expr_box()
        self._update_plot()

    def _sync_expr_box(self) -> None:
        vmin = self.spin_min.value()
        vmax = self.spin_max.value()
        step = self.spin_step.value()
        self.txt_expr.setText(f"{vmin:g}:{vmax:g}:{step:g}")
        nbins = max(1, int(np.round((vmax - vmin) / step)))
        self.lbl_nlevels.setText(f"{nbins} bins")

    def _apply_expr_string(self) -> None:
        expr = self.txt_expr.text().strip()
        parts = expr.split(":")
        if len(parts) == 3:
            try:
                vmin, vmax, step = float(parts[0]), float(parts[1]), float(parts[2])
                if vmax > vmin and step > 0:
                    self.spin_min.blockSignals(True)
                    self.spin_max.blockSignals(True)
                    self.spin_step.blockSignals(True)
                    self.spin_min.setValue(vmin)
                    self.spin_max.setValue(vmax)
                    self.spin_step.setValue(step)
                    self.spin_min.blockSignals(False)
                    self.spin_max.blockSignals(False)
                    self.spin_step.blockSignals(False)
                    self._sync_expr_box()
                    self._update_plot()
            except ValueError:
                pass

    def get_norm(self) -> Normalize:
        """Construct the matplotlib Normalize object based on UI settings."""
        norm_type = self.combo_norm.currentText()
        vmin = self.spin_min.value()
        vmax = self.spin_max.value()
        step = self.spin_step.value()

        if "BoundaryNorm" in norm_type:
            boundaries = np.arange(vmin, vmax + step * 0.5, step)
            if len(boundaries) < 2:
                boundaries = np.array([vmin, vmax])
            return BoundaryNorm(boundaries, ncolors=256, clip=True)
        elif "LogNorm" in norm_type:
            safe_vmin = max(0.01, vmin)
            safe_vmax = max(safe_vmin * 1.1, vmax)
            return LogNorm(vmin=safe_vmin, vmax=safe_vmax, clip=True)
        elif "TwoSlopeNorm" in norm_type:
            vcenter = self.spin_center.value()
            if not (vmin < vcenter < vmax):
                vcenter = (vmin + vmax) / 2.0
            return TwoSlopeNorm(vcenter=vcenter, vmin=vmin, vmax=vmax)
        else:
            return Normalize(vmin=vmin, vmax=vmax, clip=True)

    def _update_plot(self) -> None:
        """Plot the data distribution histogram alongside the interactive transfer function curve."""
        cmap_name = self._get_active_cmap_name()
        try:
            cmap = matplotlib.colormaps[cmap_name]
        except KeyError:
            cmap = matplotlib.colormaps["viridis"]

        norm = self.get_norm()
        self.normalization_changed.emit(norm)

        gamma = self.spin_gamma.value()
        bias = self.slider_bias.value() / 100.0  # -0.5 to +0.5
        curve_type = self.combo_curve.currentText()

        vmin = self.spin_min.value()
        vmax = self.spin_max.value()

        # Canvas drawing
        fig = self.canvas_widget.figure
        fig.clear()

        # Create two subplots: Top = Histogram + Transfer Curve, Bottom = 2D Sample Swatch + Colorbar
        gs = fig.add_gridspec(2, 1, height_ratios=[1.6, 1.0], hspace=0.35)
        ax_hist = fig.add_subplot(gs[0])
        ax_swatch = fig.add_subplot(gs[1])

        # 1. Histogram of data distribution
        counts, bin_edges = np.histogram(self._data_sample, bins=45)
        bin_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])
        norm_counts = counts / (np.max(counts) if np.max(counts) > 0 else 1)

        bar_color = "#38bdf8" if self._dark_mode else "#0284c7"
        ax_hist.bar(
            bin_centers,
            norm_counts,
            width=(bin_edges[1] - bin_edges[0]) * 0.9,
            alpha=0.35,
            color=bar_color,
            label="Data Frequency",
        )

        # 2. Transfer function curve
        x_norm = np.linspace(0.0, 1.0, 200)
        x_data = vmin + x_norm * (vmax - vmin)

        if "Sigmoid" in curve_type:
            k = 10.0 * gamma
            x_shifted = x_norm - 0.5 - bias
            y_transfer = 1.0 / (1.0 + np.exp(-k * x_shifted))
            y_transfer = (y_transfer - y_transfer.min()) / (y_transfer.max() - y_transfer.min() + 1e-9)
        elif "Step" in curve_type:
            n_steps = max(3, int(np.round((vmax - vmin) / max(0.1, self.spin_step.value()))))
            y_transfer = np.floor(x_norm * n_steps) / n_steps
        else:
            # Linear / Gamma power-law with center bias
            x_adj = np.clip(x_norm + bias, 0.0, 1.0)
            y_transfer = np.power(x_adj, gamma)

        ax_hist.plot(
            x_data,
            y_transfer,
            color="#f59e0b" if self._dark_mode else "#d97706",
            linewidth=2.2,
            label="Transfer Function T(x)",
        )

        # Vertical guide lines for vmin, vmax
        ax_hist.axvline(vmin, color="#ef4444", linestyle=":", alpha=0.7, label=f"vmin ({vmin:g})")
        ax_hist.axvline(vmax, color="#10b981", linestyle=":", alpha=0.7, label=f"vmax ({vmax:g})")
        if "TwoSlopeNorm" in self.combo_norm.currentText():
            ax_hist.axvline(self.spin_center.value(), color="#a855f7", linestyle="--", alpha=0.7, label="vcenter")

        ax_hist.set_title(
            f"Histogram & Transfer Curve [{self.combo_curve.currentText()} γ={gamma:.2f}]",
            fontsize=10,
            pad=6,
        )
        ax_hist.set_ylabel("Normalized Response / Density", fontsize=8)
        ax_hist.set_ylim(-0.05, 1.1)
        ax_hist.set_xlim(min(vmin - 5, float(self._data_sample.min())), max(vmax + 5, float(self._data_sample.max())))
        ax_hist.legend(loc="upper left", fontsize=7, framealpha=0.4)

        # 3. 2D Synthetic Sample Swatch mapped with colormap & norm
        x_grid = np.linspace(vmin, vmax, 120)
        y_grid = np.linspace(-1, 1, 30)
        X, Y = np.meshgrid(x_grid, y_grid)
        Z = X + 0.15 * (vmax - vmin) * np.sin(Y * np.pi)

        im = ax_swatch.pcolormesh(X, Y, Z, cmap=cmap, norm=norm, shading="auto")
        ax_swatch.set_yticks([])
        ax_swatch.set_xlabel("Physical Variable Domain", fontsize=8)

        # 4. Colorbar customization options
        orientation = "horizontal" if self.radio_horiz.isChecked() else "vertical"
        shrink_val = self.spin_shrink.value()
        aspect_val = self.spin_aspect.value()
        cbar_lbl = self.txt_cbar_label.text()

        fg_color = "#dfe2ef" if self._dark_mode else "#0f172a"

        cbar = fig.colorbar(
            im,
            ax=ax_swatch,
            orientation=orientation,
            shrink=shrink_val,
            aspect=aspect_val,
            pad=0.25 if orientation == "horizontal" else 0.05,
        )
        cbar.set_label(cbar_lbl, fontsize=8, color=fg_color)
        cbar.ax.tick_params(colors=fg_color, labelsize=7)

        self.canvas_widget.apply_theme(self._dark_mode)
        self.canvas_widget.canvas.draw_idle()

        norm_name = self.combo_norm.currentText().split()[0]
        self.status_bar_lbl.setText(
            f"Colormap: {cmap_name} | Norm: {norm_name} [{vmin:g} : {vmax:g}] | "
            f"Gamma: {gamma:.2f} | Bins: {self.lbl_nlevels.text()}"
        )

    def set_theme(self, dark_mode: bool) -> None:
        """Apply theme update across subwidgets and Matplotlib canvas."""
        self._dark_mode = dark_mode
        for card in self._card_widgets.values():
            card.set_selected(card.name == self._current_cmap)
        self.canvas_widget.apply_theme(dark_mode)
        self._update_plot()

        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(get_theme_qss(dark_mode))
