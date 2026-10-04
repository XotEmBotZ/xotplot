# Projection & Region View Updates

## Modifications
1. **Renamed Screen**:
   - Renamed from `Projection & Cartopy` to **`Projection & Region`** across navigation aside docks, window titles, and menus.

2. **Reordered Left Control Panel**:
   - **`1. Region Extent & Bounding Box`** is now the **first option** at the top of the panel.
   - Followed by `2. Cartopy CRS Library` and `3. Projection Parameters`.
   - Defaults to `India & Subcontinent` category and `India (National Subcontinent)` region `[68.0°E, 97.5°E, 6.5°N, 37.5°N]`.

3. **Line-Only Coastline Vectors**:
   - Completely removed land and sea background color fills (`cfeature.LAND` and ocean blue fill removed).
   - Rendered with a clean, unshaded white canvas (`#ffffff`), crisp dark-slate coastlines (`#334155`), and subtle dashed national borders.
