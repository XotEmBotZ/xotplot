"""Dask Compute telemetry and distributed processing configuration view."""

from __future__ import annotations

import math
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class WorkerCardWidget(QFrame):
    """Widget presenting CPU % and RAM usage gauges for an individual Dask worker process."""

    def __init__(self, worker_id: int, host: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.worker_id = worker_id
        self.host = host
        self.setObjectName("workerCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # Worker header row
        hdr = QHBoxLayout()
        self.title_lbl = QLabel(f"Worker {self.worker_id}")
        self.title_lbl.setStyleSheet("font-weight: bold; font-size: 11px;")
        hdr.addWidget(self.title_lbl)

        self.status_dot = QLabel("● Active")
        self.status_dot.setStyleSheet("color: #38bdf8; font-size: 9px; font-weight: bold;")
        hdr.addStretch()
        hdr.addWidget(self.status_dot)
        layout.addLayout(hdr)

        self.host_lbl = QLabel(f"{self.host} • 4 threads")
        self.host_lbl.setStyleSheet("color: #87929a; font-size: 9px;")
        layout.addWidget(self.host_lbl)

        # CPU Progress gauge
        cpu_box = QHBoxLayout()
        cpu_tag = QLabel("CPU")
        cpu_tag.setFixedWidth(28)
        cpu_tag.setStyleSheet("font-size: 9px; color: #87929a;")
        cpu_box.addWidget(cpu_tag)

        self.cpu_bar = QProgressBar()
        self.cpu_bar.setRange(0, 100)
        self.cpu_bar.setValue(25 + (self.worker_id * 9) % 65)
        self.cpu_bar.setFixedHeight(12)
        self.cpu_bar.setTextVisible(True)
        self.cpu_bar.setFormat("%v%")
        cpu_box.addWidget(self.cpu_bar)
        layout.addLayout(cpu_box)

        # RAM Progress gauge
        ram_box = QHBoxLayout()
        ram_tag = QLabel("RAM")
        ram_tag.setFixedWidth(28)
        ram_tag.setStyleSheet("font-size: 9px; color: #87929a;")
        ram_box.addWidget(ram_tag)

        self.ram_bar = QProgressBar()
        self.ram_bar.setRange(0, 100)
        ram_pct = 35 + (self.worker_id * 7) % 50
        self.ram_bar.setValue(ram_pct)
        self.ram_bar.setFixedHeight(12)
        self.ram_bar.setTextVisible(True)
        self.ram_bar.setFormat(f"%v% ({(ram_pct * 16 / 100):.1f}/16GB)")
        ram_box.addWidget(self.ram_bar)
        layout.addLayout(ram_box)

    def update_metrics(self, cpu_val: int, ram_gb: float, max_gb: float = 16.0) -> None:
        """Update CPU and RAM usage gauges."""
        self.cpu_bar.setValue(cpu_val)
        ram_pct = int(min(100.0, (ram_gb / max_gb) * 100.0))
        self.ram_bar.setValue(ram_pct)
        self.ram_bar.setFormat(f"{ram_pct}% ({ram_gb:.1f}/{max_gb:.0f}GB)")


class ComputeDaskView(QWidget):
    """View managing Dask cluster telemetry, chunk configuration, and task graph DAG progression."""

    chunk_config_changed = pyqtSignal(dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("computeDaskView")
        self._dark_mode = True

        self._init_ui()
        self._update_chunk_memory_preview()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # ================= 1. Header: Cluster Status & Telemetry Metrics =================
        header_group = QGroupBox("Dask Distributed Cluster Status & Telemetry")
        header_layout = QGridLayout(header_group)
        header_layout.setContentsMargins(10, 8, 10, 8)
        header_layout.setHorizontalSpacing(16)
        header_layout.setVerticalSpacing(4)

        # Scheduler Address
        self.sched_lbl = QLabel("Scheduler Address:")
        self.sched_lbl.setStyleSheet("font-weight: bold; color: #87929a;")
        self.sched_val = QLabel("tcp://127.0.0.1:8786 (Active)")
        self.sched_val.setStyleSheet("color: #38bdf8; font-weight: bold;")
        header_layout.addWidget(self.sched_lbl, 0, 0)
        header_layout.addWidget(self.sched_val, 0, 1)

        # Active Tasks Gauge / Metric
        self.tasks_lbl = QLabel("Active Tasks:")
        self.tasks_lbl.setStyleSheet("font-weight: bold; color: #87929a;")
        self.tasks_val = QLabel("42 / 576 tasks running (7.3%)")
        self.tasks_val.setStyleSheet("color: #8ed5ff; font-weight: bold;")
        header_layout.addWidget(self.tasks_lbl, 0, 2)
        header_layout.addWidget(self.tasks_val, 0, 3)

        # Memory Throughput
        self.thru_lbl = QLabel("Memory Throughput:")
        self.thru_lbl.setStyleSheet("font-weight: bold; color: #87929a;")
        self.thru_val = QLabel("1.42 GB/s I/O • 34.2 GB / 128 GB Total")
        self.thru_val.setStyleSheet("color: #51cf66; font-weight: bold;")
        header_layout.addWidget(self.thru_lbl, 1, 0)
        header_layout.addWidget(self.thru_val, 1, 1)

        # Cluster Dashboard URL & Action
        self.dash_lbl = QLabel("Dashboard:")
        self.dash_lbl.setStyleSheet("font-weight: bold; color: #87929a;")
        self.dash_val = QLabel("http://127.0.0.1:8787/status")
        self.dash_val.setStyleSheet("color: #dfe2ef; text-decoration: underline;")
        header_layout.addWidget(self.dash_lbl, 1, 2)
        header_layout.addWidget(self.dash_val, 1, 3)

        main_layout.addWidget(header_group)

        # ================= 2. Task Graph DAG Progression Timeline =================
        dag_group = QGroupBox("Task Graph DAG Progression Timeline")
        dag_layout = QVBoxLayout(dag_group)
        dag_layout.setContentsMargins(10, 8, 10, 8)
        dag_layout.setSpacing(6)

        # Visual pipeline stage boxes
        pipeline_box = QHBoxLayout()
        pipeline_box.setSpacing(6)

        self.dag_stages = [
            {"name": "1. I/O Read (Zarr / GRIB)", "status": "Finished (128/128)", "pct": 100, "color": "#51cf66"},
            {"name": "2. MetPy Diagnostic Calc", "status": "Running (42/128)", "pct": 33, "color": "#38bdf8"},
            {"name": "3. Spatial Interpolation", "status": "Pending (0/128)", "pct": 0, "color": "#87929a"},
            {"name": "4. Matplotlib Render", "status": "Queued", "pct": 0, "color": "#87929a"},
        ]

        self.stage_widgets = []
        for i, stage in enumerate(self.dag_stages):
            card = QFrame()
            card.setFrameShape(QFrame.Shape.StyledPanel)
            card.setObjectName(f"dagStageCard_{i}")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(6, 4, 6, 4)
            card_layout.setSpacing(2)

            name_lbl = QLabel(stage["name"])
            name_lbl.setStyleSheet(f"font-weight: bold; font-size: 10px; color: {stage['color']};")
            card_layout.addWidget(name_lbl)

            stat_lbl = QLabel(stage["status"])
            stat_lbl.setStyleSheet("font-size: 9px; color: #87929a;")
            card_layout.addWidget(stat_lbl)

            pbar = QProgressBar()
            pbar.setFixedHeight(8)
            pbar.setTextVisible(False)
            pbar.setRange(0, 100)
            pbar.setValue(stage["pct"])
            card_layout.addWidget(pbar)

            pipeline_box.addWidget(card)
            self.stage_widgets.append((name_lbl, stat_lbl, pbar))

            if i < len(self.dag_stages) - 1:
                arrow = QLabel("➔")
                arrow.setStyleSheet("font-weight: bold; font-size: 14px; color: #87929a;")
                pipeline_box.addWidget(arrow)

        dag_layout.addLayout(pipeline_box)
        main_layout.addWidget(dag_group)

        # ================= 3. Multidimensional Chunk Size Optimizer =================
        chunk_group = QGroupBox("Multidimensional Chunk Size Optimizer (Xarray / Dask)")
        chunk_layout = QHBoxLayout(chunk_group)
        chunk_layout.setContentsMargins(10, 8, 10, 8)
        chunk_layout.setSpacing(12)

        # Spinboxes for dimensions
        dims_layout = QGridLayout()
        dims_layout.setSpacing(6)

        dims_layout.addWidget(QLabel("Time Chunk:"), 0, 0)
        self.time_spin = QSpinBox()
        self.time_spin.setRange(1, 1000)
        self.time_spin.setValue(1)
        self.time_spin.valueChanged.connect(self._update_chunk_memory_preview)
        dims_layout.addWidget(self.time_spin, 0, 1)

        dims_layout.addWidget(QLabel("Isobaric (Level):"), 0, 2)
        self.level_spin = QSpinBox()
        self.level_spin.setRange(1, 100)
        self.level_spin.setValue(1)
        self.level_spin.valueChanged.connect(self._update_chunk_memory_preview)
        dims_layout.addWidget(self.level_spin, 0, 3)

        dims_layout.addWidget(QLabel("Latitude Chunk:"), 1, 0)
        self.lat_spin = QSpinBox()
        self.lat_spin.setRange(16, 4000)
        self.lat_spin.setSingleStep(64)
        self.lat_spin.setValue(360)
        self.lat_spin.valueChanged.connect(self._update_chunk_memory_preview)
        dims_layout.addWidget(self.lat_spin, 1, 1)

        dims_layout.addWidget(QLabel("Longitude Chunk:"), 1, 2)
        self.lon_spin = QSpinBox()
        self.lon_spin.setRange(16, 8000)
        self.lon_spin.setSingleStep(64)
        self.lon_spin.setValue(720)
        self.lon_spin.valueChanged.connect(self._update_chunk_memory_preview)
        dims_layout.addWidget(self.lon_spin, 1, 3)

        chunk_layout.addLayout(dims_layout)

        # Chunk memory preview badge and recommendation
        badge_box = QVBoxLayout()
        badge_box.setSpacing(4)

        badge_header = QLabel("Chunk Memory Footprint:")
        badge_header.setStyleSheet("font-weight: bold; font-size: 10px; color: #87929a;")
        badge_box.addWidget(badge_header)

        self.chunk_badge = QLabel("1.98 MB / chunk")
        self.chunk_badge.setObjectName("chunkMemoryBadge")
        self.chunk_badge.setStyleSheet(
            "background-color: #004965; color: #8ed5ff; font-weight: bold; font-size: 12px; padding: 4px 10px; border-radius: 3px; border: 1px solid #38bdf8;"
        )
        badge_box.addWidget(self.chunk_badge)

        self.chunk_rec_lbl = QLabel("Optimal size target: 50MB - 150MB per chunk")
        self.chunk_rec_lbl.setStyleSheet("font-size: 9px; color: #87929a;")
        badge_box.addWidget(self.chunk_rec_lbl)

        chunk_layout.addLayout(badge_box)

        # Optimize Button
        opt_box = QVBoxLayout()
        self.auto_opt_btn = QPushButton("Auto Optimize (100MB)")
        self.auto_opt_btn.setObjectName("primaryAction")
        self.auto_opt_btn.clicked.connect(self._auto_optimize_chunks)
        opt_box.addWidget(self.auto_opt_btn)

        self.apply_chunks_btn = QPushButton("Apply to Dataset")
        self.apply_chunks_btn.clicked.connect(self._emit_chunk_config)
        opt_box.addWidget(self.apply_chunks_btn)
        chunk_layout.addLayout(opt_box)

        main_layout.addWidget(chunk_group)

        # ================= 4. Worker Processes Inspector (8 Workers) =================
        worker_group = QGroupBox("Worker Processes Inspector (8 Distributed Workers)")
        worker_main_layout = QVBoxLayout(worker_group)
        worker_main_layout.setContentsMargins(6, 6, 6, 6)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        worker_container = QWidget()
        self.worker_grid = QGridLayout(worker_container)
        self.worker_grid.setContentsMargins(4, 4, 4, 4)
        self.worker_grid.setSpacing(8)

        self.workers: list[WorkerCardWidget] = []
        for i in range(8):
            host = f"node-{(i // 4) + 1}.cluster.local:878{i}"
            w = WorkerCardWidget(worker_id=i, host=host, parent=worker_container)
            row = i // 4
            col = i % 4
            self.worker_grid.addWidget(w, row, col)
            self.workers.append(w)

        scroll_area.setWidget(worker_container)
        worker_main_layout.addWidget(scroll_area)
        main_layout.addWidget(worker_group, stretch=1)

    def _update_chunk_memory_preview(self) -> None:
        """Calculate uncompressed float32 chunk memory usage and update badge."""
        t = self.time_spin.value()
        z = self.level_spin.value()
        y = self.lat_spin.value()
        x = self.lon_spin.value()

        elements = t * z * y * x
        bytes_total = elements * 4  # float32 = 4 bytes
        mb = bytes_total / (1024 * 1024)

        if mb < 1.0:
            badge_text = f"{bytes_total / 1024:.1f} KB / chunk ({elements:,} items)"
            border_color = "#38bdf8"
            bg_color = "#00354a" if self._dark_mode else "#e0f2fe"
            fg_color = "#8ed5ff" if self._dark_mode else "#0284c7"
            self.chunk_rec_lbl.setText("Warning: Chunks may be too small (< 10 MB overhead)")
        elif mb > 300.0:
            badge_text = f"{mb:.1f} MB / chunk ({elements:,} items)"
            border_color = "#ff6b6b"
            bg_color = "#4a0000" if self._dark_mode else "#fee2e2"
            fg_color = "#ff8787" if self._dark_mode else "#b91c1c"
            self.chunk_rec_lbl.setText("Warning: Chunks exceed recommended memory limit (> 300 MB)")
        else:
            badge_text = f"{mb:.2f} MB / chunk ({elements:,} items)"
            border_color = "#51cf66"
            bg_color = "#003b14" if self._dark_mode else "#dcfce7"
            fg_color = "#69db7c" if self._dark_mode else "#15803d"
            self.chunk_rec_lbl.setText("Optimal chunk size range for distributed Dask cluster")

        self.chunk_badge.setText(badge_text)
        self.chunk_badge.setStyleSheet(
            f"background-color: {bg_color}; color: {fg_color}; font-weight: bold; font-size: 11px; padding: 4px 10px; border-radius: 3px; border: 1px solid {border_color};"
        )

    def _auto_optimize_chunks(self) -> None:
        """Calculate balanced chunk dimensions targeting ~100MB per float32 chunk."""
        # 100 MB / 4 bytes = 25,000,000 floats
        # with time=1, isobaric=1 -> lat * lon = 25,000,000
        # for roughly 1:2 aspect ratio: lat=3500, lon=7000
        self.time_spin.setValue(1)
        self.level_spin.setValue(1)
        self.lat_spin.setValue(1024)
        self.lon_spin.setValue(2048)
        self._update_chunk_memory_preview()

    def _emit_chunk_config(self) -> None:
        """Emit signal with selected chunk configuration dictionary."""
        config = {
            "time": self.time_spin.value(),
            "isobaric": self.level_spin.value(),
            "lat": self.lat_spin.value(),
            "lon": self.lon_spin.value(),
        }
        self.chunk_config_changed.emit(config)

    def set_theme(self, dark_mode: bool) -> None:
        """Apply dark or light theme colors to view elements."""
        self._dark_mode = dark_mode
        self._update_chunk_memory_preview()

        # Update DAG stage widgets styling if needed
        for i, (name_lbl, stat_lbl, _) in enumerate(self.stage_widgets):
            stage = self.dag_stages[i]
            stat_color = "#87929a" if dark_mode else "#64748b"
            stat_lbl.setStyleSheet(f"font-size: 9px; color: {stat_color};")
