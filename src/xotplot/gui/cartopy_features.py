"""Backward-compatible re-export of Cartopy features from xotplot.engine.cartopy_features."""

from xotplot.engine.plotting.cartopy_features import (
    clear_cartopy_cache,
    download_feature,
    get_cached_feature,
    get_cartopy_data_dir,
    is_feature_cached,
    load_shapefile_geometries,
    set_cartopy_data_dir,
)

__all__ = [
    "clear_cartopy_cache",
    "download_feature",
    "get_cached_feature",
    "get_cartopy_data_dir",
    "is_feature_cached",
    "load_shapefile_geometries",
    "set_cartopy_data_dir",
]
