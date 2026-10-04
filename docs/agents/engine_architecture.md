# Plotting Engine Architecture, Multi-Core Pool & Cancellation (`xotplot.engine`)

This document records the stateless rendering engine architecture, multi-core process pool, channel-based cancellation, and communication bridges for `xotplot`.

## Core Principles
1. **Isolated Multi-Core OS Process Pool**: Rendering runs in a pool of isolated worker processes (`multiprocessing.get_context("spawn")`) sized according to available CPU cores (`DEFAULT_ENGINE_WORKERS`). The engine never interferes with GUI, TUI, or CLI event loops.
2. **Channel-Based Instant Job Cancellation**: When a user changes view configuration (e.g. region, projection, or layers), obsolete jobs on that channel are immediately discarded from the queue, and any active worker executing an obsolete job is terminated via `terminate()`. An idle worker immediately begins processing the latest request, freeing CPU cycles and eliminating queue latency.
3. **Double-Render Latency Elimination**: Matplotlib's `bbox_inches="tight"` double-rendering overhead is eliminated in `figure_to_png_bytes`, achieving an instant >2.5x speedup per frame.
4. **Debounced Viewport Inputs**: Continuous micro-events (spinboxes, slider dragging) in views like `ProjectionRegionView` pass through a short single-shot debounce timer (`VIEWPORT_DEBOUNCE_MS`), preventing hundreds of redundant render dispatches.
5. **Real-Time Engine Status Indicator**: `QtEngineBridge` emits `status_changed(bool, int)` to drive the bottom-right status bar indicator (`● IDLE` in green vs `● BUSY (N active)` in orange).
6. **Strict Light Theme Plot Surface**: In accordance with project requirements and `src/xotplot/constants.py`, all plot canvases strictly render with `#ffffff` background.
7. **No GUI Imports in Engine**: The engine module never imports from `xotplot.gui`.

## Module Breakdown

- [`src/xotplot/engine/cartopy_features.py`](file:///home/xotem/projects/xotplot/src/xotplot/engine/cartopy_features.py):
  - Natural Earth feature caching, discovery, downloading, and geometry loading (`load_shapefile_geometries`).
- [`src/xotplot/engine/renderer.py`](file:///home/xotem/projects/xotplot/src/xotplot/engine/renderer.py):
  - Headless rendering routines:
    - `build_crs(proj_spec)`
    - `render_region_plot(spec, figure)`
    - `render_synoptic_field(figure)`
    - `render_layer_composite(layers, figure)`
    - `render_variable_profile(var, time_step, figure)`
    - `render_variable_cross_section(var, time_step, lat_min, lat_max, figure)`
    - `render_diagnostic_plot(var_name, unit_str, preset_name, figure)`
    - `render_colormap_transfer_plot(...)`
  - Serialization: `figure_to_png_bytes(figure, dpi)` without redundant double-render.
  - Dispatcher: `execute_render_job(job_type, params, width, height, dpi) -> bytes`.
- [`src/xotplot/engine/process.py`](file:///home/xotem/projects/xotplot/src/xotplot/engine/process.py):
  - `_engine_worker_main(conn)`: Headless worker loop running in child processes.
  - `EngineProcessPool`: Multi-core pool with `cancel_channel(channel)`, `_terminate_and_respawn(slot)`, and queue management.
  - `QtEngineBridge`: Non-blocking PyQt6 adapter reading results via `multiprocessing.connection.wait` (epoll/select) and emitting `job_completed`, `job_failed`, and `status_changed`.
- [`src/xotplot/gui/engine_canvas.py`](file:///home/xotem/projects/xotplot/src/xotplot/gui/engine_canvas.py):
  - `EngineCanvasWidget`: High-performance widget displaying engine PNG bytes via `QPixmap` on a `#ffffff` canvas.

## GUI Integration
- [`ProjectionRegionView`](file:///home/xotem/projects/xotplot/src/xotplot/gui/views/projection_region_view.py): Continuous spinboxes and sliders debounce through `request_projection_update()`. On update, `apply_projection()` submits to `channel="region"` with `cancel_previous=True`, instantly canceling obsolete renders.
- [`MainWindow`](file:///home/xotem/projects/xotplot/src/xotplot/gui/main_window.py): Status bar connects to `QtEngineBridge.status_changed` to dynamically display `● IDLE` or `● BUSY (N active)`.
