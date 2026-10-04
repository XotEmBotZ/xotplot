"""Plotting subsystem of the headless execution engine."""

from xotplot.engine.plotting.cartopy_features import (
    clear_cartopy_cache,
    download_feature,
    get_cached_feature,
    get_cartopy_data_dir,
    is_feature_cached,
    load_shapefile_geometries,
    set_cartopy_data_dir,
)
from xotplot.engine.plotting.renderer import (
    build_crs,
    execute_render_job,
    figure_to_png_bytes,
    render_colormap_transfer_plot,
    render_diagnostic_plot,
    render_layer_composite,
    render_region_plot,
    render_synoptic_field,
    render_variable_cross_section,
    render_variable_profile,
)

__all__ = [
    "clear_cartopy_cache",
    "download_feature",
    "get_cached_feature",
    "get_cartopy_data_dir",
    "is_feature_cached",
    "load_shapefile_geometries",
    "set_cartopy_data_dir",
    "build_crs",
    "execute_render_job",
    "figure_to_png_bytes",
    "render_region_plot",
    "render_synoptic_field",
    "render_layer_composite",
    "render_variable_profile",
    "render_variable_cross_section",
    "render_diagnostic_plot",
    "render_colormap_transfer_plot",
]
