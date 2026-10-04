"""Offline-safe Cartopy feature manager and download preferences controller."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import cartopy
import cartopy.feature as cfeature
import cartopy.io.shapereader as shpreader

from xotplot.constants import DEFAULT_CARTOPY_CACHE_DIR, FEATURE_REGISTRY, RESOLUTIONS


def get_cartopy_data_dir() -> Path:
    """Return the cartopy user data directory path."""
    return Path(cartopy.config.get("data_dir", DEFAULT_CARTOPY_CACHE_DIR))



def set_cartopy_data_dir(new_dir: str | Path) -> None:
    """Update Cartopy's cache directory dynamically."""
    p = Path(new_dir).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    cartopy.config["data_dir"] = str(p)



def is_feature_cached(category: str, layer: str, resolution: str) -> bool:
    """Check if the given Natural Earth feature shapefile exists locally on disk without downloading."""
    dl = cartopy.config.get("downloaders", {}).get(("shapefiles", "natural_earth"))
    if not dl:
        return False

    fmt = {
        "config": cartopy.config,
        "category": category,
        "name": layer,
        "resolution": resolution,
    }

    # 1. Check user cache directory
    target_path = Path(dl.target_path(fmt))
    if target_path.exists():
        return True

    # 2. Check repo data directory
    repo_data = cartopy.config.get("repo_data_dir")
    if repo_data:
        pre_path = Path(repo_data) / dl.pre_downloaded_path(fmt)
        if pre_path.exists():
            return True

    return False


def get_cached_feature(
    category: str,
    layer: str,
    resolution: str,
    edgecolor: str = "#1e293b",
    facecolor: str = "none",
    linewidth: float = 1.0,
    linestyle: str = "-",
    zorder: int = 2,
) -> Optional[cfeature.NaturalEarthFeature]:
    """Return a NaturalEarthFeature ONLY if already cached locally, otherwise return None (skip)."""
    if not is_feature_cached(category, layer, resolution):
        return None

    return cfeature.NaturalEarthFeature(
        category=category,
        name=layer,
        scale=resolution,
        edgecolor=edgecolor,
        facecolor=facecolor,
        linewidth=linewidth,
        linestyle=linestyle,
        zorder=zorder,
    )


def download_feature(category: str, layer: str, resolution: str) -> Path:
    """Explicitly download and extract a specific Natural Earth feature to cartopy data dir."""
    dl = cartopy.config.get("downloaders", {}).get(("shapefiles", "natural_earth"))
    if not dl:
        raise RuntimeError("Cartopy natural_earth downloader not configured")

    fmt = {
        "config": cartopy.config,
        "category": category,
        "name": layer,
        "resolution": resolution,
    }
    target = Path(dl.target_path(fmt))
    return dl.acquire_resource(target, fmt)


def clear_cartopy_cache() -> int:
    """Delete all downloaded cartopy shapefiles and caches. Returns count of files removed."""
    data_dir = get_cartopy_data_dir()
    count = 0
    if data_dir.exists():
        for item in list(data_dir.rglob("*")):
            if item.is_file():
                item.unlink(missing_ok=True)
                count += 1
    return count


def load_shapefile_geometries(shp_path: str | Path, simplify_tolerance: float = 0.005) -> list[Any]:
    """Robustly load geometries from a shapefile (.shp).

    Handles standalone .shp/.shx pairs missing .dbf files, and simplifies high-vertex
    geometries to keep interactive Matplotlib transforms responsive.
    """
    path = Path(shp_path)
    if not path.exists():
        return []

    geoms: list[Any] = []
    # 1. Try standard cartopy reader
    try:
        reader = shpreader.Reader(str(path))
        geoms = list(reader.geometries())
    except Exception:
        # 2. Fallback to pyshp Reader without DBF requirement
        try:
            import shapefile
            from shapely.geometry import shape

            shx_path = path.with_suffix(".shx")
            kwargs: dict[str, Any] = {"shp": str(path)}
            if shx_path.exists():
                kwargs["shx"] = str(shx_path)
            sf = shapefile.Reader(**kwargs)
            for s in sf.shapes():
                try:
                    geoms.append(shape(s.__geo_interface__))
                except Exception:
                    pass
        except Exception:
            return []

    if not geoms:
        return []

    # Check total vertex count to auto-simplify if dense
    try:
        import shapely
        total_coords = sum(shapely.get_num_coordinates(g) for g in geoms)
        if total_coords > 10000:
            return [g.simplify(simplify_tolerance, preserve_topology=True) for g in geoms]
    except Exception:
        pass

    return geoms


