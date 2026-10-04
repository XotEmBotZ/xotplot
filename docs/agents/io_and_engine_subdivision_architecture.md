# Architectural Specification & Decisions Report: Engine Subdivisions (IO & Plotting)

**Date**: 2026-10-04  
**Project**: `xotplot`  
**Status**: APPROVED DESIGN / READY FOR IMPLEMENTATION

---

## 1. Executive Summary & Change Request

In accordance with explicit architectural decisions and the latest design change request:
1. **Engine Process Subdivisions**: The headless Engine process pool is subdivided into two primary domain subsystems:
   - `xotplot.engine.io`: Dataset ingestion, format sniffing, GRIB2 hypercube merging, coordinate canonicalization, and in-memory lazy dataset registry.
   - `xotplot.engine.plotting`: Headless Matplotlib/Cartopy rendering, projection building, raster/contour generation, and figure-to-PNG byte serialization.
2. **Unified Data Format**: A single canonical `xarray.Dataset` schema with lazy chunks (`dask`), strictly standardized coordinates (`lat`, `lon`, `time`, `level`), and normalized longitude bounds (`[-180, 180)`).
3. **Fail-Fast & Zero UI Blocking**: The entire IO ingestion, indexing, and rendering pipelines run strictly inside the isolated Engine process pool (`EngineProcessPool`). Only lightweight Pydantic metadata and serialized PNG bytes cross the inter-process boundary to the GUI/TUI/CLI.

---

## 2. Complete Summary of All Discussed Decisions

| Decision Topic | Selected Option | Rationale & Behavioral Rules |
| :--- | :--- | :--- |
| **Operating Mode** | `CODER` | Strict adherence to instructions, simple fail-fast code, no unrequested features, zero auto-commits. |
| **Engine Organization** | Subdivided into `plotting` & `io` | Most compute and data operations remain centralized in the Engine process pool, separating data ingestion from visual rendering. |
| **Coordinate Normalization** | Single Unified Canonical Schema | Coordinates and dimensions renamed to canonical lowercase: `lat`, `lon`, `time`, `level`. Downstream plotting code never checks alternate names like `latitude` or `nav_lat`. |
| **Coordinate Ranges & Sorting** | Ascending `lat` (`-90` to `90`) and `lon` (`-180` to `180`) | Standard Cartopy/GIS alignment. Longitudes wrapped into `[-180, 180)` and sorted ascending. |
| **GRIB2 Hypercube Splitting** | Merged Unified Dataset via Pre-Inspection | Multiple GRIB2 hypercubes (surface, isobaric, height) are inspected and merged into a single `xr.Dataset`. |
| **Variable Naming Convention** | Systematic Level-Type Suffixing | 3D isobaric variables named e.g. `t_isobaric` (with canonical `level` dimension in hPa), surface variables named `t_surface` or standard `t2m`. Zero namespace collisions. |
| **Format Detection** | Magic Bytes Sniffing + User Override | Fast check on first 8 bytes (`b"GRIB"`, HDF5/NetCDF, `.zgroup`/`zarr.json` directory) with file extension fallback, plus explicit `format_override` parameter. |
| **Engine IPC Protocol** | Pydantic-Validated Models | Strict models (`OpenDatasetRequest`, `DatasetMetadata`, `VariableInfo`, `CoordinateInfo`) defined in `src/xotplot/spec.py`. |
| **Dataset Lifecycle in Engine** | Multi-Dataset Registry | Engine maintains a dataset registry keyed by `dataset_id`, tracks an active dataset pointer, and supports explicit `close_dataset(id)` to prevent file descriptor leaks. |
| **Dependency Stack** | Standard Scientific Stack | `xarray`, `dask`, `cfgrib`, `eccodes`, `netcdf4`, `zarr` managed via `uv add`. |

---

## 3. Package & Directory Restructuring

```
src/xotplot/
├── spec.py                  # Single source of truth for Pydantic specs (PlotSpec, DatasetMetadata, etc.)
├── constants.py             # Default colors, ports, worker counts, coordinate names
├── io/                      # Public/Engine shared ingestion models & format detectors
│   ├── __init__.py          # Exports canonical open/metadata interfaces
│   ├── detector.py          # Magic-byte and path sniffing (GRIB2, NetCDF4, Zarr)
│   └── canonical.py         # Coordinate canonicalization & range normalization
├── engine/                  # Headless multiprocessing subsystem
│   ├── __init__.py          # High-level engine client & bridge exports
│   ├── process.py           # Multi-core process pool, IPC dispatch, QtEngineBridge
│   ├── io/                  # Engine IO subsystem
│   │   ├── __init__.py
│   │   ├── registry.py      # DatasetRegistry (dataset_id -> xr.Dataset, active pointer)
│   │   ├── grib.py          # GRIB2 multi-message inspector, hypercube merger
│   │   ├── netcdf.py        # NetCDF4 opener with Dask chunks
│   │   └── zarr.py          # Zarr group opener
│   └── plotting/            # Engine Plotting subsystem
│       ├── __init__.py
│       ├── renderer.py      # Matplotlib/Cartopy render routines
│       └── cartopy_features.py # Natural Earth & shapefile geometry loading
```

---

## 4. Full Specification (Pydantic Models in `src/xotplot/spec.py`)

### 4.1 Ingestion & IO Models

```python
from typing import Annotated, Any, Dict, List, Literal, Optional, Tuple
from pydantic import BaseModel, Field

SupportedFormat = Literal["auto", "grib2", "netcdf4", "zarr"]

class OpenDatasetRequest(BaseModel):
    """Request sent across IPC to open a dataset inside the Engine process pool."""
    file_path: str
    format_override: SupportedFormat = "auto"
    dataset_id: Optional[str] = None  # Auto-generated UUID if omitted


class VariableInfo(BaseModel):
    """Metadata descriptor for an individual data variable."""
    name: str
    dimensions: List[str]
    shape: List[int]
    dtype: str
    units: Optional[str] = None
    long_name: Optional[str] = None
    standard_name: Optional[str] = None
    level_type: Optional[str] = None  # e.g., 'isobaric', 'surface', 'heightAboveGround'


class CoordinateInfo(BaseModel):
    """Metadata descriptor for a canonical coordinate axis."""
    name: str  # 'lat', 'lon', 'time', 'level'
    dimensions: List[str]
    size: int
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    units: Optional[str] = None
    discrete_values: Optional[List[float]] = None  # e.g. isobaric levels [1000, 850, 500, ...]


class DatasetMetadata(BaseModel):
    """Complete metadata serialized from Engine to GUI/TUI/CLI upon dataset open."""
    dataset_id: str
    file_path: str
    detected_format: str
    variables: Dict[str, VariableInfo]
    coordinates: Dict[str, CoordinateInfo]
    global_attrs: Dict[str, Any] = Field(default_factory=dict)
```

### 4.2 Plotting & Rendering Models (Extending Existing `spec.py`)

```python
class DataPlotSpec(BaseModel):
    """Specification for rendering gridded data onto the map canvas."""
    dataset_id: Optional[str] = None  # Defaults to active dataset
    variable: str
    level_index: Optional[int] = None
    level_value: Optional[float] = None
    time_index: int = 0
    plot_type: Literal["contour", "contourf", "pcolormesh", "quiver", "streamplot"] = "contourf"
    colormap: str = "viridis"
    num_levels: int = 15
    vmin: Optional[float] = None
    vmax: Optional[float] = None
```

---

## 5. Engine Worker IPC Protocol Commands

The worker process main loop (`_engine_worker_main` in `src/xotplot/engine/process.py`) supports the following commands dispatched across isolated processes:

1. `{"command": "io_open", "request": OpenDatasetRequest.model_dump()}`
   - Action: Sniffs format, invokes format-specific Engine IO reader, standardizes coordinates to canonical schema, registers `xr.Dataset` into `DatasetRegistry`.
   - Returns: `{"success": True, "metadata": DatasetMetadata.model_dump()}`
2. `{"command": "io_close", "dataset_id": str}`
   - Action: Closes file handles, evicts dataset from registry.
   - Returns: `{"success": True}`
3. `{"command": "io_set_active", "dataset_id": str}`
   - Action: Points active dataset pointer to specified ID.
   - Returns: `{"success": True}`
4. `{"command": "render", "job_id": str, "job_type": str, "params": dict, ...}`
   - Action: Slices requested variable/level/time from registered active dataset and renders headless Matplotlib/Cartopy plot to PNG bytes.
   - Returns: `{"success": True, "image_data": bytes}`
5. `{"command": "shutdown"}`
   - Action: Closes all open datasets and cleanly exits process.

---

## 6. Execution Plan & Next Steps

1. Add required scientific packages (`xarray`, `dask`, `cfgrib`, `eccodes`, `netcdf4`, `zarr`) using `uv add`.
2. Implement format sniffer in `src/xotplot/io/detector.py` and coordinate normalizer in `src/xotplot/io/canonical.py`.
3. Implement `src/xotplot/engine/io/` subsystem with `DatasetRegistry` and GRIB2/NetCDF4/Zarr loaders.
4. Restructure `src/xotplot/engine/plotting/` preserving existing render routines and Cartopy shapefile features.
5. Update `src/xotplot/engine/process.py` to route IO requests to `engine.io` and plot requests to `engine.plotting`.
6. Write unit and regression tests validating ingestion of the sample file `~/Downloads/20261002000000-0h-oper-fc.grib2`.
