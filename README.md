### Features by Release

**v1.0**

* NetCDF & GRIB2 multi-cube file inspection
* Automated coordinate harmonization (lat/lon/time/level)
* Global grid cyclic point padding (1D regular grids)
* 2D horizontal isobaric and surface slicing
* Filled contour maps (`contourf`)
* Fast scalar grid mesh rendering (`pcolormesh`)
* Line contour overlays with auto-labels
* Wind barbs and quiver vectors with automated decimation
* Standard projection support (Plate Carrée, Lambert Conformal, Polar Stereographic)
* Fixed bundled Natural Earth vector boundaries (110m)
* Hardcoded unit conversions (Kelvin to Celsius, Pa to hPa)
* Headless batch plotting via CLI argument parser
* Terminal file and coordinate inspector via Textual TUI
* Dual-stage PyQt6 GUI viewport (fast Plate Carrée preview during scrubbing, high-res Cartopy render on commit)
* Export to high-DPI raster and vector formats (PNG, PDF)

**v1.1**

* Arbitrary vertical cross-sections and transects (pressure-height vs. distance)
* Terrain masking along transects
* Skew-T ln-P thermodynamic soundings and hodographs in a modal window
* Hovmöller space-time diagrams
* Uniform-grid wind streamlines (`streamplot`) with auto-regridding
* 2D curvilinear and rotated-pole grid coordinate transformations
* Safe AST-based derived variable math engine
* Custom user shapefile and GeoJSON vector overlay ingestion

---

### Proposed Architecture

The system uses a **stateless, headless core** driven by a single **Pydantic Plot Specification**, ensuring all rendering logic is completely decoupled from user interfaces.

```
       ┌────────────────────────┐
       │     Incoming Data      │
       │    (GRIB2 / NetCDF)    │
       └───────────┬────────────┘
                   ▼
       ┌────────────────────────┐
       │ Ingestion & Normalizer │  (xarray + cfgrib / netCDF4: coordinate standardizer)
       └───────────┬────────────┘
                   ▼
       ┌────────────────────────┐
       │  Pydantic PlotSpec     │  <── Source of truth for state and overrides
       └───────────┬────────────┘
         ┌─────────┴─────────┐
         ▼                   ▼
    ┌─────────┐         ┌─────────┐
    │ CLI/TUI │         │  PyQt6  │
    │ (Batch/ │         │ (Dual-  │
    │ Textual)│         │  Stage) │
    └────┬────┘         └────┬────┘
         └─────────┬─────────┘
                   ▼
       ┌────────────────────────┐
       │ Stateless Plot Engine  │  (Matplotlib OO-API + Cartopy; QThread worker)
       └───────────┬────────────┘
                   ▼
            Rendered Output

```

1. **Ingestion & Normalizer:** Disambiguates GRIB2 hypercubes using `cfgrib.open_datasets()` and normalizes heterogeneous coordinate naming onto an internal `xarray.Dataset`.
2. **Pydantic PlotSpec:** A serializable schema defining all slicing, projection, styling, and vector properties. It acts as the single protocol shared by the CLI, TUI, and GUI.
3. **Execution Interfaces:**
* **CLI / Textual:** Pure headless execution mapping terminal arguments or interactive inspection selections directly into a `PlotSpec`.
* **PyQt6 GUI:** Dual-stage rendering engine. Slider interactions trigger fast, subsampled 2D mesh updates via Matplotlib blitting; committed releases trigger background `QThread` workers to execute full-resolution Cartopy transformations.


4. **Stateless Plot Engine:** Uses pure object-oriented Matplotlib and Cartopy (no `pyplot` global state) to transform the slice and specification into an image buffer.
