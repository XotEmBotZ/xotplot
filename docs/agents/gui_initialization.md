# GUI Architecture & Initialization

## Overview
Initialized the foundational PyQt6 desktop GUI module in `src/xotplot/gui/` adhering to the `pyqt6-ui-development-rules` skill and the dual-stage viewport specification from `README.md`.

## Components
- [`src/xotplot/gui/viewport.py`](file:///home/xotem/projects/xotplot/src/xotplot/gui/viewport.py): `ViewportWidget` representing the render area for fast subsampled preview (Plate Carrée) and high-resolution Cartopy commits.
- [`src/xotplot/gui/main_window.py`](file:///home/xotem/projects/xotplot/src/xotplot/gui/main_window.py): `MainWindow` managing layouts, status bar, and dual-stage slider interaction (`sliderMoved` -> preview, `sliderReleased` -> commit).
- [`src/xotplot/gui/app.py`](file:///home/xotem/projects/xotplot/src/xotplot/gui/app.py): Application entrypoint `run_app()`.
- [`src/xotplot/gui/__init__.py`](file:///home/xotem/projects/xotplot/src/xotplot/gui/__init__.py): Module exports.

## Dependencies Added
- `PyQt6` (via `uv add PyQt6`).
