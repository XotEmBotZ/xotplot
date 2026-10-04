"""Centralized constants, default assumptions, and configuration presets for xotplot."""

from pathlib import Path

# =============================================================================
# GUI Workbench Navigation & View Architecture
# =============================================================================
VIEW_NAMES: list[str] = [
    "Spatial Viewport (2D/3D)",
    "Variables & Dimensions",
    "Projection & Region",
    "Layer Stack & Features",
    "Colormap Transfer",
    "CLI & Batch Engine",
    "Derived Diagnostics",
    "Compute & Dask Engine",
]

# =============================================================================
# Cartopy CRS Projections Registry
# =============================================================================
CRS_CARDS: list[dict[str, str | bool]] = [
    {
        "id": "LambertConformal",
        "name": "Lambert Conformal",
        "code": "lcc",
        "desc": "Conformal conic projection optimal for middle latitudes and synoptic weather maps.",
        "has_parallels": True,
        "has_lat": True,
        "has_lon": True,
    },
    {
        "id": "PlateCarree",
        "name": "Plate Carrée",
        "code": "eqc",
        "desc": "Equirectangular geographic lat/lon projection.",
        "has_parallels": False,
        "has_lat": False,
        "has_lon": True,
    },
    {
        "id": "Mercator",
        "name": "Mercator",
        "code": "merc",
        "desc": "Conformal cylindrical projection standard for marine navigation & tropical storms.",
        "has_parallels": False,
        "has_lat": True,
        "has_lon": True,
    },
    {
        "id": "NorthPolarStereo",
        "name": "North Polar Stereo",
        "code": "npstere",
        "desc": "Conformal azimuthal projection centered on North Pole.",
        "has_parallels": False,
        "has_lat": True,
        "has_lon": True,
    },
    {
        "id": "Orthographic",
        "name": "Orthographic",
        "code": "ortho",
        "desc": "Perspective view of the globe from infinite space.",
        "has_parallels": False,
        "has_lat": True,
        "has_lon": True,
    },
    {
        "id": "Robinson",
        "name": "Robinson",
        "code": "robin",
        "desc": "Pseudocylindrical compromise projection for global mosaics.",
        "has_parallels": False,
        "has_lat": False,
        "has_lon": True,
    },
]

# =============================================================================
# Geographic Regions & Domains Presets (India-First Hierarchy)
# Format: (West Lon, East Lon, South Lat, North Lat)
# =============================================================================
REGION_CATEGORIES: dict[str, dict[str, tuple[float, float, float, float]]] = {
    "India & Subcontinent": {
        "India (National Subcontinent)": (68.0, 97.5, 6.5, 37.5),
        "India & Indian Ocean": (50.0, 110.0, -15.0, 40.0),
        "North India & Himalayas": (70.0, 92.0, 24.0, 37.5),
        "South India & Peninsula": (72.0, 85.0, 6.5, 20.0),
        "Bay of Bengal": (80.0, 100.0, 5.0, 23.0),
        "Arabian Sea": (55.0, 77.0, 5.0, 25.0),
    },
    "Tropical & Equatorial": {
        "India": (68.0, 97.5, 6.5, 37.5),
        "Indian Ocean": (40.0, 120.0, -35.0, 30.0),
        "Tropical Pacific": (130.0, -70.0, -25.0, 25.0),
        "Tropical Atlantic": (-60.0, 20.0, -20.0, 25.0),
        "Western Atlantic": (-85.0, -40.0, 10.0, 45.0),
        "Western Pacific": (110.0, 160.0, -10.0, 35.0),
        "Central Pacific": (160.0, -140.0, -20.0, 25.0),
        "Eastern Pacific": (-140.0, -75.0, -20.0, 25.0),
        "Southwest Pacific": (140.0, -170.0, -50.0, 0.0),
        "Southeast Pacific": (-140.0, -70.0, -55.0, 0.0),
        "Caribbean": (-90.0, -55.0, 10.0, 28.0),
        "Southern Africa": (10.0, 55.0, -35.0, -5.0),
        "Northern Africa": (-20.0, 55.0, 10.0, 38.0),
    },
    "US & North America": {
        "CONUS": (-125.0, -66.5, 20.0, 50.0),
        "North America": (-170.0, -50.0, 15.0, 75.0),
        "Pacific Northwest": (-125.0, -111.0, 42.0, 49.5),
        "Northern Plains": (-105.0, -90.0, 40.0, 49.5),
        "Northeast": (-82.0, -67.0, 38.0, 47.5),
        "Western US": (-125.0, -102.0, 31.0, 49.5),
        "Central Plains": (-104.0, -89.0, 33.0, 44.0),
        "Eastern US": (-90.0, -67.0, 25.0, 48.0),
        "Southwest": (-122.0, -103.0, 31.0, 42.0),
        "Southern Plains": (-104.0, -93.0, 26.0, 37.0),
        "Southeast": (-92.0, -75.0, 24.5, 37.0),
        "Alaska": (-175.0, -130.0, 50.0, 72.0),
        "Hawaii": (-161.0, -154.0, 18.5, 22.5),
        "Western Canada": (-140.0, -100.0, 48.0, 70.0),
        "Canada": (-142.0, -52.0, 42.0, 83.0),
        "Southeast Canada": (-95.0, -55.0, 42.0, 60.0),
    },
    "World & Hemispheres": {
        "World": (-180.0, 180.0, -85.0, 85.0),
        "Northern Hemisphere": (-180.0, 180.0, 0.0, 90.0),
        "Southern Hemisphere": (-180.0, 180.0, -90.0, 0.0),
        "Asia": (40.0, 150.0, 0.0, 75.0),
        "East Asia": (95.0, 150.0, 15.0, 55.0),
        "Europe": (-15.0, 45.0, 34.0, 72.0),
        "South America": (-85.0, -30.0, -56.0, 15.0),
        "Middle East": (30.0, 65.0, 12.0, 42.0),
        "Australia": (110.0, 155.0, -45.0, -10.0),
        "New Zealand": (165.0, 180.0, -48.0, -34.0),
    },
    "Ocean Basins": {
        "Indian Ocean": (40.0, 120.0, -45.0, 25.0),
        "North Pacific": (120.0, -110.0, 15.0, 65.0),
        "Western Pacific": (100.0, 160.0, -10.0, 45.0),
        "Central Pacific": (160.0, -140.0, -15.0, 40.0),
        "Eastern Pacific": (-140.0, -75.0, -10.0, 45.0),
        "Southwest Pacific": (140.0, -160.0, -50.0, 0.0),
        "Southeast Pacific": (-140.0, -70.0, -55.0, 0.0),
        "Pacific Basin": (110.0, -70.0, -50.0, 60.0),
        "Tropical Pacific": (130.0, -75.0, -20.0, 25.0),
        "North Atlantic": (-85.0, -5.0, 15.0, 65.0),
        "Tropical Atlantic": (-65.0, 15.0, -15.0, 25.0),
        "Western Atlantic": (-85.0, -40.0, 10.0, 45.0),
        "Caribbean": (-90.0, -55.0, 10.0, 28.0),
    },
    "Globe Views": {
        "Pacific Globe": (130.0, -70.0, -60.0, 60.0),
        "Atlantic Globe": (-80.0, 20.0, -60.0, 60.0),
        "Arctic Globe": (-180.0, 180.0, 55.0, 90.0),
        "Antarctic Globe": (-180.0, 180.0, -90.0, -55.0),
    },
}

# Flattened list maintaining strict India-first order for simple lookups
ALL_REGIONS: dict[str, tuple[float, float, float, float]] = {}
for _cat, _regions in REGION_CATEGORIES.items():
    for _rname, _coords in _regions.items():
        if _rname not in ALL_REGIONS:
            ALL_REGIONS[_rname] = _coords
        else:
            ALL_REGIONS[f"{_rname} ({_cat})"] = _coords

# =============================================================================
# Natural Earth Feature Layers Registry & Scales
# =============================================================================
FEATURE_REGISTRY: list[dict[str, str]] = [
    {"id": "coastline", "name": "Coastlines", "category": "physical", "layer": "coastline"},
    {"id": "countries", "name": "Country Borders", "category": "cultural", "layer": "admin_0_countries"},
    {"id": "states", "name": "State / Provinces", "category": "cultural", "layer": "admin_1_states_provinces_lines"},
    {"id": "rivers", "name": "Rivers & Canals", "category": "physical", "layer": "rivers_lake_centerlines"},
    {"id": "lakes", "name": "Lakes & Reservoirs", "category": "physical", "layer": "lakes"},
]

RESOLUTIONS: list[str] = ["110m", "50m", "10m"]
DEFAULT_RESOLUTION: str = "50m"

# =============================================================================
# Plotting & Map Default Color Assumptions (Light Theme Strict)
# =============================================================================
DEFAULT_PLOT_BG_COLOR: str = "#ffffff"
DEFAULT_PLOT_FG_COLOR: str = "#0f172a"
DEFAULT_COAST_COLOR: str = "#1e293b"
DEFAULT_BORDER_COLOR: str = "#334155"
DEFAULT_STATE_COLOR: str = "#64748b"
DEFAULT_RIVER_COLOR: str = "#0284c7"
DEFAULT_LAKE_COLOR: str = "#0284c7"
DEFAULT_GRID_COLOR: str = "#94a3b8"
DEFAULT_SHP_COLOR: str = "#e11d48"

# Default Path Assumptions
DEFAULT_CARTOPY_CACHE_DIR: Path = Path.home() / ".local/share/cartopy"
