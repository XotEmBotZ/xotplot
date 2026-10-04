# PlotConfig & Title Customization Architecture

## Overview
The Variables & Dimensions Inspector view (`VariablesInspectorView`) provides meteorological variable inspection, single-slot template formatting for variable-specific descriptions, common global plot titles, and a centralized `PlotConfig` store managed via a bottom sidebar.

## Data Schemas (`src/xotplot/spec.py`)

### 1. `VariableTitleSpec`
Provides a single template slot for variable-specific text using tokens/placeholders:
- Supported placeholders:
  - `{name}` / `{var}` / `{var_name}`: canonical variable identifier (e.g. `t2m`, `u10`, `gh`)
  - `{long_name}`: descriptive meteorological title (e.g. `2-metre Temperature`, `Geopotential Height`)
  - `{level}`: isobaric pressure or vertical coordinate (e.g. `850 hPa`)
  - `{units}`: parameter unit string (e.g. `K`, `m/s`, `dam`, `gpm`)
- Automatically purges dangling formatting artifacts if a token (such as level or units) is absent.

### 2. `GlobalTitleSpec`
Enforces common global titles and formatted subtitles following `(pre - var title - post)` formatting:
- Configured globally in `SpatialViewportView` (not per-variable):
  - `title`: Common global title string (e.g., `GFS 0.25° Synoptic Analysis`). Common across all plots and independent of variable specifics.
  - `subtitle_pre`: Prefix for the subtitle (e.g., `Valid: 12Z`).
  - `subtitle_post`: Suffix for the subtitle (e.g., `Forecast T+24h`).
  - `subtitle_enabled`: Boolean flag.
- Subtitle automatically incorporates the evaluated variable-specific text slot into the `(pre - var title - post)` format.

### 3. `PlotConfig`
A single Pydantic model representing each plot layer/variable pushed to the centralized `PlotConfig` store:
- `id`: Unique identifier (e.g., `cfg_a1b2c3`)
- `variable`: Parameter name (`str`)
- `level`, `level_type`: Pressure/vertical level
- `plot_type`: `contourf`, `pcolormesh`, or `contour`
- `colormap`: Matplotlib colormap (`str`)
- `vmin`, `vmax`: Numerical bounds
- `num_levels`: Count of contour intervals
- `is_wind`: Meteorological wind barb flag
- `barbs_step`, `barbs_length`, `barbs_pivot`, `barbs_color`: Wind barb parameters
- `var_text_template`: Template string for 1 variable slot (e.g. `{long_name} ({name}) @ {level} [{units}]`)
- `computed_var_text`: Evaluated variable text slot for this variable
- `enabled`: Boolean active layer flag
- `to_data_plot_spec(dataset_id, region_view, global_title_spec)`: Directly serializes into an executable `DataPlotSpec` for the headless render engine using the global title spec.

## GUI Integration

1. **Global Title in Viewport (`SpatialViewportView`)**:
   - Common Global Title: `QLineEdit`
   - Subtitle Pre / Post: `QLineEdit` inputs
   - Subtitle Checkbox: `QCheckBox`
   - Emits `global_title_changed` signal and provides `get_global_title_spec()`.

2. **Variables Inspector View (`VariablesInspectorView`)**:
   - Single Variable Slot: `QLineEdit` (`edit_var_template`) with live placeholder expansion.
   - Real-time Title & Subtitle Preview label debounced for engine redraws, dynamically resolving global title from the viewport provider.
   - `Add Config` button pushes the active configuration into the centralized `_plot_configs` list.

3. **Bottom Sidebar**:
   - Dedicated `QGroupBox` anchored via vertical splitter at the base of the view.
   - Interactive table detailing `ID`, `Variable`, `Level`, `Style`, `Colormap`, `Range`, and `Variable Text`.
   - Double-clicking any row loads its configuration into the controls for quick inspection or adjustment.
   - Actions:
     - `Update Config`: Updates the selected `PlotConfig` item in-place with the current parameter state.
     - `Delete Selected`: Deletes selected configuration from the store.
     - `Clear All`: Empties the store.
     - `Plot in Viewport`: Emits `plot_requested` signal with `DataPlotSpec` to render immediately.

4. **Live Replot in Viewport upon Global Title Changes**:
   - When global title, subtitle pre/post, or subtitle checkbox is modified in `SpatialViewportView`, changes are debounced via `_title_debounce_timer`.
   - `MainWindow._on_global_title_changed` automatically re-evaluates the active field specification and triggers background asynchronous re-rendering directly on the Viewport canvas.

4. **Map Only Default**:
   - Map Only (`btn_toggle_histogram`) is checked by default to maximize map viewing area while keeping the histogram toggle available on demand.

5. **Right-Side Vertical Color Scale**:
   - Meteorological 2D slice maps render the level/value colormap scale vertically on the right side of the plot axes (`orientation="vertical"`, `pad=0.03`, `fraction=0.046`, `aspect=25`), keeping horizontal axis space clear for geographic coordinate labels and titles.

6. **Non-Blocking Asynchronous Engine & Unified Input Debounce**:
   - All interactive controls (title text edits, variable template inputs, colormap and styling combos, numerical bounds, contour levels, wind barbs) are wired into a single unified debounce timer (`_render_debounce_timer`, 450-500ms).
   - Typing updates the title preview instantly on the GUI thread without triggering rendering.
   - When jobs are cancelled upon new submissions, the process pool tags cancelled jobs and discards their completion payloads asynchronously, eliminating blocking process kills or synchronous pipe reads on the UI thread.
