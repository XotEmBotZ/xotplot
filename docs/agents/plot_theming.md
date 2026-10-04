# Plot Theming Specification

## Enforced Constraint
All Matplotlib plot canvases are **strictly locked to light theme** (`#ffffff` canvas background, `#0f172a` labels/text, `#cbd5e1` gridlines) regardless of whether the user sets the application shell to Dark Mode or Light Mode.

## Affected Canvas Widgets
1. [`src/xotplot/gui/mpl_canvas.py`](file:///home/xotem/projects/xotplot/src/xotplot/gui/mpl_canvas.py):
   - `MplCanvasWidget.apply_theme()` enforces `bg_color="#ffffff"`, `fg_color="#0f172a"`, and `grid_color="#cbd5e1"`.
   - Used by Spatial Viewport, Variables & Dimensions, Colormap Transfer, and Derived Diagnostics.
2. [`src/xotplot/gui/views/projection_region_view.py`](file:///home/xotem/projects/xotplot/src/xotplot/gui/views/projection_region_view.py):
   - `ProjectionRegionView.apply_projection()` figure background locked to `#ffffff` and graticules to `#94a3b8`.
3. [`src/xotplot/gui/views/layer_stack_view.py`](file:///home/xotem/projects/xotplot/src/xotplot/gui/views/layer_stack_view.py):
   - `LayerStackView.render_composite()` figure and axes background locked to `#ffffff` and text to `#0f172a`.
