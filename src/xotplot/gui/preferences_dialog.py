"""Preferences dialog to manage and download Cartopy Natural Earth features."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from xotplot.constants import FEATURE_REGISTRY, RESOLUTIONS
from xotplot.gui.cartopy_features import (
    clear_cartopy_cache,
    download_feature,
    get_cartopy_data_dir,
    is_feature_cached,
    set_cartopy_data_dir,
)


class CartopyPreferencesDialog(QDialog):
    """Dialog allowing user to view cached features, selectively download them, or clear cache."""

    features_updated = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Cartopy Feature Preferences & Download Manager")
        self.resize(680, 480)

        self._init_ui()
        self._refresh_status_table()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header description
        info_group = QGroupBox("Offline-First Policy", self)
        info_layout = QVBoxLayout(info_group)
        lbl_desc = QLabel(
            "xotplot enforces a strict <b>Offline-First</b> policy: features are <b>never</b> "
            "downloaded automatically in the background or during startup.<br>"
            "If a feature is not downloaded, it is safely skipped. Use this dialog to selectively "
            "download the features and resolutions you need."
        )
        lbl_desc.setWordWrap(True)
        info_layout.addWidget(lbl_desc)

        cache_row = QHBoxLayout()
        self.lbl_cache_path = QLabel(f"<b>Cache Directory:</b> <code>{get_cartopy_data_dir()}</code>")
        self.lbl_cache_path.setWordWrap(True)
        cache_row.addWidget(self.lbl_cache_path, stretch=1)

        self.btn_change_cache = QPushButton("📁 Change Cache Directory...")
        self.btn_change_cache.clicked.connect(self._on_change_cache_dir)
        cache_row.addWidget(self.btn_change_cache)
        info_layout.addLayout(cache_row)
        layout.addWidget(info_group)

        # Feature matrix table
        self.table = QTableWidget(len(FEATURE_REGISTRY), 4, self)
        self.table.setHorizontalHeaderLabels(["Feature", "110m (Coarse)", "50m (Medium)", "10m (High-Res)"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        # Progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Actions row
        btn_row = QHBoxLayout()

        self.btn_download_selected = QPushButton("Download Selected")
        self.btn_download_selected.setObjectName("primaryAction")
        self.btn_download_selected.clicked.connect(self._on_download_selected)
        btn_row.addWidget(self.btn_download_selected)

        self.btn_refresh = QPushButton("Refresh Status")
        self.btn_refresh.clicked.connect(self._refresh_status_table)
        btn_row.addWidget(self.btn_refresh)

        self.btn_clear_cache = QPushButton("Delete All Cartopy Cache")
        self.btn_clear_cache.setStyleSheet("color: #ff6b6b;")
        self.btn_clear_cache.clicked.connect(self._on_clear_cache)
        btn_row.addWidget(self.btn_clear_cache)

        btn_row.addStretch()

        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.accept)
        btn_row.addWidget(self.btn_close)

        layout.addLayout(btn_row)

    def _refresh_status_table(self) -> None:
        """Populate the table showing which features are cached vs missing."""
        self._checkbox_matrix = {}

        for row_idx, feat in enumerate(FEATURE_REGISTRY):
            name_item = QTableWidgetItem(f"{feat['name']} ({feat['layer']})")
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(row_idx, 0, name_item)

            for col_idx, res in enumerate(RESOLUTIONS, start=1):
                cached = is_feature_cached(feat["category"], feat["layer"], res)

                cell_widget = QWidget()
                cell_layout = QHBoxLayout(cell_widget)
                cell_layout.setContentsMargins(4, 2, 4, 2)
                cell_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

                chk = QCheckBox()
                chk.setEnabled(not cached)
                chk.setChecked(False)  # Deselected by default


                status_lbl = QLabel("✓ Cached" if cached else "Missing")
                status_lbl.setStyleSheet("color: #10b981; font-weight: bold;" if cached else "color: #87929a;")

                cell_layout.addWidget(chk)
                cell_layout.addWidget(status_lbl)

                self.table.setCellWidget(row_idx, col_idx, cell_widget)
                self._checkbox_matrix[(feat["id"], res)] = (chk, feat, res, cached)

    def _on_download_selected(self) -> None:
        """Download features checked by the user."""
        items_to_download = [
            (feat, res)
            for (chk, feat, res, cached) in self._checkbox_matrix.values()
            if chk.isChecked() and not cached
        ]

        if not items_to_download:
            QMessageBox.information(self, "Download Manager", "No missing features selected for download.")
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(items_to_download))
        self.progress_bar.setValue(0)

        success = 0
        for idx, (feat, res) in enumerate(items_to_download):
            try:
                download_feature(feat["category"], feat["layer"], res)
                success += 1
            except Exception as e:
                pass
            self.progress_bar.setValue(idx + 1)

        self.progress_bar.setVisible(False)
        self._refresh_status_table()
        self.features_updated.emit()
        QMessageBox.information(self, "Download Manager", f"Successfully downloaded {success} feature(s).")

    def _on_clear_cache(self) -> None:
        """Confirm and delete all cartopy cache."""
        reply = QMessageBox.question(
            self,
            "Confirm Delete Cache",
            "Are you sure you want to delete all cached Cartopy shapefiles?\n"
            "Features will be skipped during rendering until downloaded again.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            deleted_count = clear_cartopy_cache()
            self._refresh_status_table()
            self.features_updated.emit()
            QMessageBox.information(self, "Cache Cleared", f"Removed {deleted_count} cached file(s).")

    def _on_change_cache_dir(self) -> None:
        """Allow user to select a new directory for Cartopy feature downloads and cache."""
        chosen_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Cartopy Cache Directory",
            str(get_cartopy_data_dir()),
        )
        if chosen_dir:
            set_cartopy_data_dir(chosen_dir)
            self.lbl_cache_path.setText(f"<b>Cache Directory:</b> <code>{get_cartopy_data_dir()}</code>")
            self._refresh_status_table()
            self.features_updated.emit()
            QMessageBox.information(
                self,
                "Cache Directory Updated",
                f"Cartopy cache directory successfully changed to:\n{chosen_dir}",
            )

