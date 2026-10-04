# Meteorological Region Domain Specifications & Hierarchy

## Priority Ordering
The region presets are organized with **India and India-focused meteorological regions at the top**, followed by the requested global, oceanic, and continental sub-regions.

## Region Categories (`src/xotplot/gui/regions.py`)

1. **India & Subcontinent (Priority 1 - Default)**:
   - India (National Subcontinent) `[68.0°E, 97.5°E, 6.5°N, 37.5°N]`
   - India & Indian Ocean `[50.0°E, 110.0°E, -15.0°N, 40.0°N]`
   - North India & Himalayas `[70.0°E, 92.0°E, 24.0°N, 37.5°N]`
   - South India & Peninsula `[72.0°E, 85.0°E, 6.5°N, 20.0°N]`
   - Bay of Bengal `[80.0°E, 100.0°E, 5.0°N, 23.0°N]`
   - Arabian Sea `[55.0°E, 77.0°E, 5.0°N, 25.0°N]`

2. **Tropical & Equatorial**:
   - India, Indian Ocean, Tropical Pacific, Tropical Atlantic, Western Atlantic, Western Pacific, Central Pacific, Eastern Pacific, Southwest Pacific, Southeast Pacific, Caribbean, Southern Africa, Northern Africa.

3. **US & North America**:
   - CONUS, North America, Pacific Northwest, Northern Plains, Northeast, Western US, Central Plains, Eastern US, Southwest, Southern Plains, Southeast, Alaska, Hawaii, Western Canada, Canada, Southeast Canada.

4. **World & Hemispheres**:
   - World, Northern Hemisphere, Southern Hemisphere, Asia, East Asia, Europe, South America, Middle East, Australia, New Zealand.

5. **Ocean Basins**:
   - Indian Ocean, North Pacific, Western Pacific, Central Pacific, Eastern Pacific, Southwest Pacific, Southeast Pacific, Pacific Basin, Tropical Pacific, North Atlantic, Tropical Atlantic, Western Atlantic, Caribbean.

6. **Globe Views**:
   - Pacific Globe, Atlantic Globe, Arctic Globe, Antarctic Globe.

## UI Integration
- [`src/xotplot/gui/views/projection_region_view.py`](file:///home/xotem/projects/xotplot/src/xotplot/gui/views/projection_region_view.py):
  - Category selector with `India & Subcontinent` loaded first.
  - Region selector defaults to `India (National Subcontinent)` `[68.0, 97.5, 6.5, 37.5]`.
  - Auto-centers central longitude and latitude upon selecting any domain.
- [`src/xotplot/gui/views/spatial_viewport_view.py`](file:///home/xotem/projects/xotplot/src/xotplot/gui/views/spatial_viewport_view.py):
  - Mini-toolbar includes a quick `Region` dropdown with India at the top of the list.
