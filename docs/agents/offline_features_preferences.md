# Cartopy Feature Offline Policy & Download Preferences

## Architecture & Policy

### 1. Offline-First Skipping Guarantee
- Automatic background downloading of Cartopy Natural Earth shapefiles is **strictly disabled** during startup and map redraws.
- Handled by [`src/xotplot/gui/cartopy_features.py`](file:///home/xotem/projects/xotplot/src/xotplot/gui/cartopy_features.py):
  - `is_feature_cached(category, layer, resolution)` inspects local disk directories (`~/.local/share/cartopy` and `repo_data_dir`) without executing any network calls.
  - `get_cached_feature(...)` returns `None` if the shapefile is missing locally, causing the render pipeline to safely skip that layer.
- **Cold startup test passed**: When the entire Cartopy cache is cleared, the application launches instantly with zero exceptions and zero network downloads.

### 2. Preference Dialog & Download Manager
- Implemented in [`src/xotplot/gui/preferences_dialog.py`](file:///home/xotem/projects/xotplot/src/xotplot/gui/preferences_dialog.py) (`CartopyPreferencesDialog`):
  - Accessible via `Edit -> Feature Download Preferences...` (`Ctrl+,`) or the `⚙ Manage Downloads & Offline Cache...` button in the `Projection & Region` dock.
  - **Dynamic Cache Directory**: Allows changing the Cartopy cache root directory (`📁 Change Cache Directory...`), updating `cartopy.config["data_dir"]` dynamically and reflecting current status immediately.
  - Matrix table showing all feature layers (`Coastlines`, `Country Borders`, `State / Provinces`, `Rivers`, `Lakes`) across resolutions (`110m`, `50m`, `10m`) with `✓ Cached` or `Missing` indicators.
  - **Deselected Uncached Options by Default**: All uncached options in both the preference download manager matrix and the main `Projection & Region` layer checkboxes (`Coastlines`, `Borders`, `States`, `Rivers`, `Lakes`) are unchecked/deselected by default if their local shapefiles are absent and no custom shapefile override is set.
  - **Selective Download**: Checkboxes allow user to download only the specific features and resolutions they want.
  - **Cache Eraser**: `Delete All Cartopy Cache` button wipes all downloaded shapefiles from disk for testing or freeing space.

