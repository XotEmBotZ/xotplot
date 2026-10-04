# Meteorological Plotting Implementation & GUI Workflow Specification

**Date**: 2026-10-04  
**Project**: `xotplot`  
**Status**: APPROVED DESIGN / READY FOR IMPLEMENTATION

---

## 1. Overall Sequence & Strategy

Following the approved **GUI Inspector-First** sequence:
1. **Pydantic Data Models**: Add `DataSliceSpec` and `DataPlotSpec` to `src/xotplot/spec.py`.
2. **File Open Entry Point**: Add `File -> Open Dataset...` (`Ctrl+O`) and CLI startup argument (`sys.argv[1]`) to `MainWindow` and `app.py`.
3. **Mediator Signal Architecture**: `MainWindow` mediates dataset lifecycle via PyQt signals (`dataset_loaded`, `slice_selected`, `render_field_requested`).
4. **Hierarchical Tree Inspector**: Restructure `VariablesInspectorView` to present variables grouped by level type:
   - ▾ **Surface & 2D Diagnostic** (`t2m`, `u10`, `v10`, `msl`, `sp`, `tp`, etc.)
   - ▾ **Isobaric Levels (Upper Air)**: Organized by pressure levels (`1000 hPa`, `850 hPa`, `500 hPa`, `250 hPa`, etc.), containing 3D isobaric variables (`t_isobaric`, `u_isobaric`, `v_isobaric`, `gh_isobaric`).
   - ▾ **Soil & Boundary Layers** (`sot_soilLayer`, `vsw_soilLayer`).
5. **Mandatory Colormap & Scale Controls**:
   - Provide user colormap selector (e.g. `viridis`, `coolwarm`, `plasma`, `magma`, `Blues`, `cividis`).
   - Min/Max numerical inputs with an "Auto-Calculate Range" button for convenience.
   - Plot style selector (`contourf`, `pcolormesh`, `contour`).
6. **Engine Field Renderer**:
   - Implement `render_gridded_field(slice_spec, plot_spec, region_spec, figure)` in `src/xotplot/engine/plotting/renderer.py`.
   - Wire `execute_render_job("field", ...)` to slice from `DatasetRegistry` and composite meteorological field underneath/alongside Cartopy borders, coastlines, and graticules.
7. **Spatial Viewport & Inspector Wiring**:
   - Clicking "Plot" or selecting a slice in the inspector transmits `DataPlotSpec` to the Engine.
   - The resulting PNG renders crisply in `EngineCanvasWidget` inside the `Spatial Viewport` on the `#ffffff` canvas.

---

## 2. Pydantic Specifications

```python
class DataSliceSpec(BaseModel):
    """Specification for slicing a 2D horizontal field from a multi-dimensional dataset."""
    variable: str
    level_type: Optional[str] = None   # 'isobaric', 'surface', 'soilLayer'
    level_value: Optional[float] = None  # e.g. 500.0 (in hPa)
    time_index: int = 0


class DataPlotSpec(BaseModel):
    """Complete specification for rendering a meteorological field on a Cartopy canvas."""
    dataset_id: Optional[str] = None
    slice_spec: DataSliceSpec
    plot_type: Literal["contourf", "pcolormesh", "contour"] = "contourf"
    colormap: str = "coolwarm"
    vmin: Optional[float] = None
    vmax: Optional[float] = None
    num_levels: int = 15
    show_colorbar: bool = True
    colorbar_label: Optional[str] = None
```

---

## 3. Communication Contract

```
[User / CLI args]
       │
       ▼
[MainWindow] ─── engine_bridge.open_dataset(path) ───► [Engine Worker]
       │                                                      │
       │ ◄────── DatasetMetadata (34 vars, coords) ───────────┘
       │
       ├──► [VariablesInspectorView.populate_tree(metadata)]
       │             │ (User selects Level/Variable + Colormap)
       │             ▼
       │     slice_selected(DataPlotSpec)
       │             │
       ▼             ▼
[MainWindow] ─── engine_bridge.submit("field", DataPlotSpec) ──► [Engine Worker]
       │                                                              │
       │ ◄──────────────── PNG Bytes ─────────────────────────────────┘
       │
       └──► [SpatialViewportView.display_image(png_bytes)]
```
