"""Stateless Cartopy and Matplotlib rendering engine for xotplot.

Consumes validated Pydantic specifications (e.g. RegionViewSpec, PlotSpec) and
renders map canvases, axes, and features adhering to FAIL-FAST, SIMPLE-ONLY, and
LEAST-CODE principles.
"""

from pathlib import Path
from typing import Any, Optional
import cartopy.crs as ccrs
from cartopy.feature import ShapelyFeature
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import numpy as np

from xotplot.gui.cartopy_features import (
    get_cached_feature,
    load_shapefile_geometries,
)
from xotplot.spec import FeatureLayerSpec, ProjectionSpec, RegionViewSpec


def build_crs(proj_spec: ProjectionSpec) -> Any:
    """Build a Cartopy CRS instance from a ProjectionSpec."""
    c_lon = proj_spec.central_longitude
    c_lat = proj_spec.central_latitude
    sp1, sp2 = proj_spec.standard_parallels

    if proj_spec.crs_id == "LambertConformal":
        return ccrs.LambertConformal(
            central_longitude=c_lon,
            central_latitude=c_lat,
            standard_parallels=(sp1, sp2),
        )
    elif proj_spec.crs_id == "PlateCarree":
        return ccrs.PlateCarree(central_longitude=c_lon)
    elif proj_spec.crs_id == "Mercator":
        return ccrs.Mercator(central_longitude=c_lon, latitude_true_scale=c_lat)
    elif proj_spec.crs_id == "NorthPolarStereo":
        return ccrs.NorthPolarStereo(
            central_longitude=c_lon,
            true_scale_latitude=c_lat if c_lat != 0 else 70.0,
        )
    elif proj_spec.crs_id == "Orthographic":
        return ccrs.Orthographic(central_longitude=c_lon, central_latitude=c_lat)
    elif proj_spec.crs_id == "Robinson":
        return ccrs.Robinson(central_longitude=c_lon)
    return ccrs.PlateCarree()


def _render_feature_layer(
    ax: Any,
    category: str,
    layer_name: str,
    scale: str,
    layer_spec: FeatureLayerSpec,
    zorder: int,
) -> None:
    """Render a single feature layer via custom shapefile override or cached Natural Earth."""
    if not layer_spec.enabled:
        return

    if layer_spec.custom_shapefile and Path(layer_spec.custom_shapefile).exists():
        geoms = load_shapefile_geometries(layer_spec.custom_shapefile)
        if geoms:
            feat = ShapelyFeature(
                geoms,
                crs=ccrs.PlateCarree(),
                edgecolor=layer_spec.color,
                facecolor="none",
                linewidth=layer_spec.linewidth,
                linestyle=layer_spec.linestyle,
                zorder=zorder,
            )
            ax.add_feature(feat)
    else:
        cached_feat = get_cached_feature(
            category=category,
            layer=layer_name,
            resolution=scale,
            edgecolor=layer_spec.color,
            linewidth=layer_spec.linewidth,
            linestyle=layer_spec.linestyle,
            zorder=zorder,
        )
        if cached_feat is not None:
            ax.add_feature(cached_feat)


def render_region_plot(
    spec: RegionViewSpec,
    figure: Optional[Figure] = None,
) -> Figure:
    """Render a Cartopy projection and region plot based on a RegionViewSpec."""
    if figure is None:
        figure = Figure(figsize=(8.0, 6.0), dpi=100)
    else:
        figure.clear()

    crs_proj = build_crs(spec.projection)
    ax = figure.add_subplot(111, projection=crs_proj)

    bg_color = spec.canvas_bg_color
    fg_color = spec.canvas_fg_color

    figure.patch.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)

    # Set geographic extent
    w, e, s, n = spec.extent.as_tuple()
    if spec.projection.crs_id not in ("Orthographic",):
        try:
            ax.set_extent([w, e, s, n], crs=ccrs.PlateCarree())
        except Exception:
            pass

    # Render granular Cartopy features
    scale = spec.features.scale
    _render_feature_layer(ax, "physical", "coastline", scale, spec.features.coastlines, zorder=3)
    _render_feature_layer(ax, "cultural", "admin_0_countries", scale, spec.features.borders, zorder=3)
    _render_feature_layer(ax, "cultural", "admin_1_states_provinces_lines", scale, spec.features.states, zorder=2)
    _render_feature_layer(ax, "physical", "rivers_lake_centerlines", scale, spec.features.rivers, zorder=2)
    _render_feature_layer(ax, "physical", "lakes", scale, spec.features.lakes, zorder=2)

    # Render additional custom shapefile overlay stack
    for shp in spec.custom_shapefiles:
        if shp.enabled and shp.path.exists():
            geoms = load_shapefile_geometries(shp.path)
            if geoms:
                custom_feat = ShapelyFeature(
                    geoms,
                    crs=ccrs.PlateCarree(),
                    edgecolor=shp.color,
                    facecolor="none",
                    linewidth=shp.linewidth,
                    zorder=4,
                )
                ax.add_feature(custom_feat)

    # Render Graticules
    if spec.graticules.enabled:
        try:
            gl = ax.gridlines(
                crs=ccrs.PlateCarree(),
                draw_labels=spec.graticules.draw_labels,
                linewidth=0.75,
                color=spec.graticules.color,
                alpha=spec.graticules.alpha,
                linestyle=spec.graticules.linestyle,
                xlocs=np.arange(-180, 181, spec.graticules.lon_step),
                ylocs=np.arange(-90, 91, spec.graticules.lat_step),
            )
            if spec.graticules.draw_labels:
                gl.top_labels = False
                gl.right_labels = False
                gl.xlabel_style = {"size": 8, "color": fg_color}
                gl.ylabel_style = {"size": 8, "color": fg_color}
        except Exception:
            pass

    title = f"{spec.projection.crs_id} Projection [{spec.preset_name}]"
    ax.set_title(title, fontsize=10, color=fg_color, pad=10)
    figure.tight_layout()

    return figure
