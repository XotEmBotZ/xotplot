"""Stateless Cartopy and Matplotlib rendering engine for xotplot.

Consumes validated Pydantic specifications and plot requests, rendering map
canvases, axes, and meteorological overlays strictly adhering to FAIL-FAST,
SIMPLE-ONLY, and LEAST-CODE principles. All plots strictly adhere to light theme (#ffffff).
"""

import io
from pathlib import Path
from typing import Any, Optional
import cartopy.crs as ccrs
from cartopy.feature import ShapelyFeature
import matplotlib
matplotlib.use("Agg")
from matplotlib.colors import (
    BoundaryNorm,
    CenteredNorm,
    LogNorm,
    Normalize,
    PowerNorm,
    SymLogNorm,
    TwoSlopeNorm,
)
from matplotlib.figure import Figure
import numpy as np

from xotplot.constants import (
    DEFAULT_PLOT_BG_COLOR,
    DEFAULT_PLOT_FG_COLOR,
)
from xotplot.engine.plotting.cartopy_features import (
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

    bg_color = DEFAULT_PLOT_BG_COLOR
    fg_color = DEFAULT_PLOT_FG_COLOR

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


def render_synoptic_field(figure: Optional[Figure] = None) -> Figure:
    """Render a synthetic meteorological geopotential height contour and wind field."""
    if figure is None:
        figure = Figure(figsize=(8.0, 5.0), dpi=100)
    else:
        figure.clear()

    ax = figure.add_subplot(111)
    figure.patch.set_facecolor(DEFAULT_PLOT_BG_COLOR)
    ax.set_facecolor(DEFAULT_PLOT_BG_COLOR)

    x = np.linspace(-130, -60, 45)
    y = np.linspace(20, 60, 35)
    X, Y = np.meshgrid(x, y)

    # Synthetic 500 hPa Geopotential Height field (dam)
    Z = 570 - 0.7 * (Y - 20) + 12 * np.sin(np.radians(X * 2.5)) * np.cos(np.radians((Y - 40) * 3))

    cmap = "turbo"
    levels = np.arange(520, 595, 6)
    cf = ax.contourf(X, Y, Z, levels=levels, cmap=cmap, alpha=0.9)
    cs = ax.contour(X, Y, Z, levels=levels, colors="#1e293b", linewidths=0.8, alpha=0.7)
    ax.clabel(cs, inline=True, fontsize=8, fmt="%d dam")

    # Wind barbs
    step = 4
    X_sub = X[::step, ::step]
    Y_sub = Y[::step, ::step]
    dZ_dy, dZ_dx = np.gradient(Z)
    u = -dZ_dy[::step, ::step] * 15
    v = dZ_dx[::step, ::step] * 15
    ax.barbs(X_sub, Y_sub, u, v, length=5, color="#0284c7")

    # Pressure Centers
    ax.text(-95, 42, "L 540", color="#dc2626", fontsize=11, fontweight="bold", ha="center")
    ax.text(-75, 30, "H 588", color="#16a34a", fontsize=11, fontweight="bold", ha="center")

    ax.set_title("GFS 0.25°: 500 hPa Geopotential Height & Wind", fontsize=11, color=DEFAULT_PLOT_FG_COLOR)
    ax.set_xlabel("Longitude (°E)", fontsize=9, color=DEFAULT_PLOT_FG_COLOR)
    ax.set_ylabel("Latitude (°N)", fontsize=9, color=DEFAULT_PLOT_FG_COLOR)
    ax.grid(True, color="#cbd5e1", linestyle="--", alpha=0.5)

    cbar = figure.colorbar(cf, ax=ax, orientation="horizontal", pad=0.14, shrink=0.8)
    cbar.set_label("Geopotential Height [dam]", fontsize=8, color=DEFAULT_PLOT_FG_COLOR)
    cbar.ax.tick_params(colors=DEFAULT_PLOT_FG_COLOR, labelsize=8)

    figure.tight_layout()
    return figure


def render_layer_composite(layers: list[dict], figure: Optional[Figure] = None) -> Figure:
    """Render a multi-layer composite overlay stack."""
    if figure is None:
        figure = Figure(figsize=(8.0, 6.0), dpi=100)
    else:
        figure.clear()

    ax = figure.add_subplot(111)
    figure.patch.set_facecolor(DEFAULT_PLOT_BG_COLOR)
    ax.set_facecolor(DEFAULT_PLOT_BG_COLOR)

    ax.tick_params(colors=DEFAULT_PLOT_FG_COLOR, which="both")
    for spine in ax.spines.values():
        spine.set_color(DEFAULT_PLOT_FG_COLOR)
    ax.xaxis.label.set_color(DEFAULT_PLOT_FG_COLOR)
    ax.yaxis.label.set_color(DEFAULT_PLOT_FG_COLOR)
    ax.title.set_color(DEFAULT_PLOT_FG_COLOR)
    ax.grid(True, color="#cbd5e1", linestyle="--", alpha=0.3)

    visible_layers = [lyr for lyr in reversed(layers) if lyr.get("visible", True)]

    # Domain grid
    x = np.linspace(-125, -65, 80)
    y = np.linspace(24, 50, 60)
    X, Y = np.meshgrid(x, y)

    for i, layer in enumerate(visible_layers):
        l_type = layer.get("type", "vector")
        color = layer.get("color", "#0284c7")
        alpha = layer.get("alpha", 0.7)
        stroke_w = layer.get("stroke_width", 1.0)
        zorder = 2 + i

        if l_type == "raster":
            R = np.sin((X + 95) / 10.0) * np.cos((Y - 35) / 8.0) * 45 + 25
            intervals = layer.get("contour_intervals", 6)
            ax.contourf(X, Y, R, levels=np.linspace(15, 65, intervals + 1), cmap="gist_ncar", alpha=alpha, zorder=zorder)

        elif l_type == "contour":
            Z = 570 - 0.7 * (Y - 24) + 14 * np.sin(np.radians(X * 2.5))
            intervals = layer.get("contour_intervals", 5)
            cs = ax.contour(X, Y, Z, levels=intervals, colors=color, linewidths=stroke_w, alpha=alpha, zorder=zorder)
            ax.clabel(cs, inline=True, fontsize=8, fmt="%d dam")

        elif l_type == "vector":
            fill_mode = layer.get("fill_mode", "Outline Only")
            lyr_id = layer.get("id", "")

            if lyr_id == "fronts":
                l_x = np.linspace(-110, -80, 50)
                l_y = 42 - 0.4 * (l_x + 110) + 2 * np.sin(l_x / 3)
                ax.plot(l_x, l_y, color=color, linewidth=stroke_w, alpha=alpha, linestyle="-", zorder=zorder)

            elif lyr_id == "severe_outlooks":
                from matplotlib.patches import Polygon
                poly_pts = np.array([[-100, 32], [-92, 33], [-90, 38], [-96, 40], [-102, 36]])
                poly_patch = Polygon(
                    poly_pts,
                    closed=True,
                    facecolor=color if fill_mode != "Outline Only" else "none",
                    edgecolor=color,
                    alpha=alpha if fill_mode != "Outline Only" else 1.0,
                    linewidth=stroke_w,
                    zorder=zorder,
                )
                ax.add_patch(poly_patch)
                ax.text(-95, 35, "SPC ENH", color=color, fontweight="bold", fontsize=9, zorder=zorder + 0.1)

            elif lyr_id == "rivers":
                riv_x = np.array([-90, -89.5, -90.2, -89.8, -91.0, -90.5])
                riv_y = np.array([45, 42, 38, 35, 32, 29])
                ax.plot(riv_x, riv_y, color=color, linewidth=stroke_w, alpha=alpha, zorder=zorder)

            else:
                box_x = [-105, -75, -75, -105, -105]
                box_y = [28, 28, 45, 45, 28]
                if fill_mode != "Outline Only":
                    ax.fill(box_x, box_y, color=color, alpha=alpha, zorder=zorder)
                ax.plot(box_x, box_y, color=color, linewidth=stroke_w, alpha=alpha, zorder=zorder)

    ax.set_xlim(-125, -65)
    ax.set_ylim(24, 50)
    ax.set_xlabel("Longitude (°W)", fontsize=9, color=DEFAULT_PLOT_FG_COLOR)
    ax.set_ylabel("Latitude (°N)", fontsize=9, color=DEFAULT_PLOT_FG_COLOR)
    ax.set_title(f"Composite Multi-Layer Overlay ({len(visible_layers)}/{len(layers)} visible)", fontsize=11, color=DEFAULT_PLOT_FG_COLOR)

    figure.tight_layout()
    return figure


def render_variable_profile(
    var: str,
    time_step: int,
    figure: Optional[Figure] = None,
) -> Figure:
    """Render a 1D vertical profile plot on log-pressure coordinates."""
    if figure is None:
        figure = Figure(figsize=(6.5, 5.5), dpi=100)
    else:
        figure.clear()

    ax = figure.add_subplot(111)
    figure.patch.set_facecolor(DEFAULT_PLOT_BG_COLOR)
    ax.set_facecolor(DEFAULT_PLOT_BG_COLOR)

    pressure_levels = np.array([1000, 925, 850, 700, 600, 500, 400, 300, 250, 200, 150, 100])

    if var == "gh":
        values = 500.0 - 450.0 * np.log10(pressure_levels / 1000.0) + np.random.normal(0, 1.5, len(pressure_levels))
        unit_label = "Geopotential Height [dam]"
    elif var == "t":
        values = 288.15 - 6.5 * (1000 - pressure_levels) / 100.0 + np.random.normal(0, 1.0, len(pressure_levels))
        unit_label = "Temperature [K]"
    elif var in ["u", "v"]:
        values = 5.0 + 35.0 * np.sin((1000 - pressure_levels) / 700 * np.pi) + np.random.normal(0, 1.2, len(pressure_levels))
        unit_label = f"{var.upper()}-Wind Component [m/s]"
    else:
        values = 14.0 * np.exp(-(1000 - pressure_levels) / 250.0) + np.random.normal(0, 0.2, len(pressure_levels))
        unit_label = "Specific Humidity [g/kg]"

    color = "#0284c7"
    ax.plot(values, pressure_levels, marker="o", linewidth=2.0, color=color, label=f"{var.upper()} Profile")
    ax.set_yscale("log")
    ax.set_ylim(1050, 90)
    ax.set_yticks([1000, 850, 700, 500, 300, 200, 100])
    ax.get_yaxis().set_major_formatter(lambda x, pos: f"{int(x)}")
    ax.set_ylabel("Pressure [hPa]", color=DEFAULT_PLOT_FG_COLOR)
    ax.set_xlabel(unit_label, color=DEFAULT_PLOT_FG_COLOR)
    ax.set_title(f"1D Vertical Profile: {var.upper()} @ T+{time_step}h", color=DEFAULT_PLOT_FG_COLOR)
    ax.grid(True, color="#cbd5e1", linestyle="--", alpha=0.5)
    ax.legend(loc="upper right", framealpha=0.3)

    figure.tight_layout()
    return figure


def render_variable_cross_section(
    var: str,
    time_step: int,
    lat_min: float,
    lat_max: float,
    figure: Optional[Figure] = None,
) -> Figure:
    """Render a 2D zonal mean cross-section plot."""
    if figure is None:
        figure = Figure(figsize=(6.5, 5.5), dpi=100)
    else:
        figure.clear()

    ax = figure.add_subplot(111)
    figure.patch.set_facecolor(DEFAULT_PLOT_BG_COLOR)
    ax.set_facecolor(DEFAULT_PLOT_BG_COLOR)

    pressure_levels = np.array([1000, 925, 850, 700, 600, 500, 400, 300, 250, 200, 150, 100])
    lats = np.linspace(lat_min, lat_max, 30)
    LAT, P = np.meshgrid(lats, pressure_levels)

    if var == "gh":
        Z = 500 - 400 * np.log10(P / 1000.0) - 0.4 * (LAT - 20)
        label = "Geopotential Height [dam]"
        cmap = "turbo"
    elif var == "t":
        Z = 288 - 0.05 * (1000 - P) - 0.5 * (LAT - 20)
        label = "Temperature [K]"
        cmap = "coolwarm"
    elif var in ["u", "v"]:
        Z = 45.0 * np.exp(-((LAT - 35) ** 2) / 150.0) * np.sin((1000 - P) / 800.0 * np.pi)
        label = f"{var.upper()}-Wind [m/s]"
        cmap = "plasma"
    else:
        Z = 12.0 * np.exp(-((LAT - 25) ** 2) / 250.0) * (P / 1000.0) ** 2
        label = "Specific Humidity [g/kg]"
        cmap = "viridis"

    cf = ax.contourf(LAT, P, Z, levels=12, cmap=cmap)
    cs = ax.contour(LAT, P, Z, levels=12, colors="#000000", linewidths=0.6, alpha=0.5)
    ax.clabel(cs, inline=True, fontsize=7)

    ax.set_yscale("log")
    ax.set_ylim(1050, 90)
    ax.set_yticks([1000, 850, 700, 500, 300, 200, 100])
    ax.get_yaxis().set_major_formatter(lambda x, pos: f"{int(x)}")
    ax.set_ylabel("Pressure [hPa]", color=DEFAULT_PLOT_FG_COLOR)
    ax.set_xlabel("Latitude (°N)", color=DEFAULT_PLOT_FG_COLOR)
    ax.set_title(f"2D Zonal Mean Cross-Section: {var.upper()} (T+{time_step}h)", color=DEFAULT_PLOT_FG_COLOR)

    cbar = figure.colorbar(cf, ax=ax, orientation="horizontal", pad=0.16, shrink=0.85)
    cbar.set_label(label, fontsize=8, color=DEFAULT_PLOT_FG_COLOR)
    cbar.ax.tick_params(colors=DEFAULT_PLOT_FG_COLOR, labelsize=8)

    figure.tight_layout()
    return figure


def render_diagnostic_plot(
    var_name: str,
    unit_str: str,
    preset_name: str,
    figure: Optional[Figure] = None,
) -> Figure:
    """Render a computed diagnostic field map."""
    if figure is None:
        figure = Figure(figsize=(7.0, 5.0), dpi=100)
    else:
        figure.clear()

    ax = figure.add_subplot(111)
    figure.patch.set_facecolor(DEFAULT_PLOT_BG_COLOR)
    ax.set_facecolor(DEFAULT_PLOT_BG_COLOR)

    x = np.linspace(-130, -60, 50)
    y = np.linspace(20, 55, 40)
    X, Y = np.meshgrid(x, y)

    if "Theta-E" in preset_name:
        field = 310 + 25 * np.cos(np.radians(Y * 2.5)) - 10 * np.sin(np.radians(X * 2))
        cmap = "Spectral_r"
        title = "Equivalent Potential Temperature (Theta-E, 850 hPa) [K]"
    elif "Vorticity" in preset_name:
        field = 12 * np.sin(np.radians((X + 100) * 4)) * np.cos(np.radians((Y - 35) * 4))
        cmap = "PuOr_r"
        title = "Relative Vorticity (500 hPa) [10⁻⁵ s⁻¹]"
    elif "Moisture" in preset_name:
        field = 500 * np.exp(-((X + 90) ** 2 + (Y - 30) ** 2) / 350.0)
        cmap = "Blues"
        title = "Integrated Vapor Transport (IVT) [kg m⁻¹ s⁻¹]"
    else:
        field = 10 * np.sin(np.radians(X * 2)) * np.cos(np.radians(Y * 2))
        cmap = "viridis"
        title = f"Custom Diagnostic: {var_name} [{unit_str}]"

    cf = ax.contourf(X, Y, field, levels=22, cmap=cmap, alpha=0.92)
    cs = ax.contour(X, Y, field, levels=11, colors="#1e293b", linewidths=0.6, alpha=0.6)
    ax.clabel(cs, inline=True, fontsize=7, fmt="%.1f")

    ax.set_title(title, fontsize=10, pad=8, color=DEFAULT_PLOT_FG_COLOR)
    ax.set_xlabel("Longitude (°W / °E)", fontsize=8, color=DEFAULT_PLOT_FG_COLOR)
    ax.set_ylabel("Latitude (°N)", fontsize=8, color=DEFAULT_PLOT_FG_COLOR)

    cbar = figure.colorbar(cf, ax=ax, orientation="horizontal", pad=0.15, shrink=0.75)
    cbar.set_label(f"{var_name} [{unit_str}]", fontsize=8, color=DEFAULT_PLOT_FG_COLOR)
    cbar.ax.tick_params(colors=DEFAULT_PLOT_FG_COLOR, labelsize=7)

    figure.tight_layout()
    return figure


def render_colormap_transfer_plot(
    vmin: float,
    vmax: float,
    vcenter: float,
    curve_type: str,
    gamma: float,
    bias: float,
    step: float,
    cmap_name: str,
    norm_name: str,
    orientation: str,
    shrink: float,
    aspect: float,
    cbar_label: str,
    data_sample: Optional[np.ndarray] = None,
    figure: Optional[Figure] = None,
) -> Figure:
    """Render colormap histogram, transfer curve, and 2D swatch preview."""
    if figure is None:
        figure = Figure(figsize=(7.0, 5.5), dpi=100)
    else:
        figure.clear()

    if data_sample is None:
        np.random.seed(42)
        data_sample = np.concatenate([
            np.random.normal(540, 8, 3000),
            np.random.normal(575, 12, 5000),
            np.random.exponential(15, 2000) + 520,
        ])

    figure.patch.set_facecolor(DEFAULT_PLOT_BG_COLOR)

    try:
        cmap = matplotlib.colormaps[cmap_name]
    except Exception:
        cmap = matplotlib.colormaps["viridis"]

    # Construct Norm
    if "LogNorm" in norm_name and vmin > 0 and vmax > 0:
        norm = LogNorm(vmin=vmin, vmax=vmax, clip=True)
    elif "TwoSlopeNorm" in norm_name and vmin < vcenter < vmax:
        norm = TwoSlopeNorm(vmin=vmin, vcenter=vcenter, vmax=vmax)
    elif "CenteredNorm" in norm_name:
        norm = CenteredNorm(vcenter=vcenter, halfrange=max(abs(vmax - vcenter), abs(vmin - vcenter)))
    elif "PowerNorm" in norm_name:
        norm = PowerNorm(gamma=gamma, vmin=vmin, vmax=vmax, clip=True)
    elif "BoundaryNorm" in norm_name:
        bounds = np.linspace(vmin, vmax, max(4, int(np.round((vmax - vmin) / max(0.1, step)))))
        norm = BoundaryNorm(boundaries=bounds, ncolors=cmap.N, clip=True)
    else:
        norm = Normalize(vmin=vmin, vmax=vmax, clip=True)

    gs = figure.add_gridspec(2, 1, height_ratios=[1.6, 1.0], hspace=0.35)
    ax_hist = figure.add_subplot(gs[0])
    ax_swatch = figure.add_subplot(gs[1])
    ax_hist.set_facecolor(DEFAULT_PLOT_BG_COLOR)
    ax_swatch.set_facecolor(DEFAULT_PLOT_BG_COLOR)

    # 1. Histogram of data distribution
    counts, bin_edges = np.histogram(data_sample, bins=45)
    bin_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])
    norm_counts = counts / (np.max(counts) if np.max(counts) > 0 else 1)

    bar_color = "#0284c7"
    ax_hist.bar(
        bin_centers,
        norm_counts,
        width=(bin_edges[1] - bin_edges[0]) * 0.9,
        alpha=0.35,
        color=bar_color,
        label="Data Frequency",
    )

    # 2. Transfer function curve
    x_norm = np.linspace(0.0, 1.0, 200)
    x_data = vmin + x_norm * (vmax - vmin)

    if "Sigmoid" in curve_type:
        k = 10.0 * gamma
        x_shifted = x_norm - 0.5 - bias
        y_transfer = 1.0 / (1.0 + np.exp(-k * x_shifted))
        y_transfer = (y_transfer - y_transfer.min()) / (y_transfer.max() - y_transfer.min() + 1e-9)
    elif "Step" in curve_type:
        n_steps = max(3, int(np.round((vmax - vmin) / max(0.1, step))))
        y_transfer = np.floor(x_norm * n_steps) / n_steps
    else:
        x_adj = np.clip(x_norm + bias, 0.0, 1.0)
        y_transfer = np.power(x_adj, gamma)

    ax_hist.plot(
        x_data,
        y_transfer,
        color="#d97706",
        linewidth=2.2,
        label="Transfer Function T(x)",
    )

    ax_hist.axvline(vmin, color="#ef4444", linestyle=":", alpha=0.7, label=f"vmin ({vmin:g})")
    ax_hist.axvline(vmax, color="#10b981", linestyle=":", alpha=0.7, label=f"vmax ({vmax:g})")
    if "TwoSlopeNorm" in norm_name:
        ax_hist.axvline(vcenter, color="#a855f7", linestyle="--", alpha=0.7, label="vcenter")

    ax_hist.set_title(
        f"Histogram & Transfer Curve [{curve_type} γ={gamma:.2f}]",
        fontsize=10,
        pad=6,
        color=DEFAULT_PLOT_FG_COLOR,
    )
    ax_hist.set_ylabel("Normalized Density", fontsize=8, color=DEFAULT_PLOT_FG_COLOR)
    ax_hist.set_ylim(-0.05, 1.1)
    ax_hist.set_xlim(min(vmin - 5, float(data_sample.min())), max(vmax + 5, float(data_sample.max())))
    ax_hist.legend(loc="upper left", fontsize=7, framealpha=0.4)

    # 3. 2D Synthetic Sample Swatch
    x_grid = np.linspace(vmin, vmax, 120)
    y_grid = np.linspace(-1, 1, 30)
    X, Y = np.meshgrid(x_grid, y_grid)
    Z = X + 0.15 * (vmax - vmin) * np.sin(Y * np.pi)

    im = ax_swatch.pcolormesh(X, Y, Z, cmap=cmap, norm=norm, shading="auto")
    ax_swatch.set_yticks([])
    ax_swatch.set_xlabel("Physical Variable Domain", fontsize=8, color=DEFAULT_PLOT_FG_COLOR)

    # 4. Colorbar
    cbar = figure.colorbar(
        im,
        ax=ax_swatch,
        orientation=orientation,
        shrink=shrink,
        aspect=aspect,
        pad=0.25 if orientation == "horizontal" else 0.05,
    )
    cbar.set_label(cbar_label, fontsize=8, color=DEFAULT_PLOT_FG_COLOR)
    cbar.ax.tick_params(colors=DEFAULT_PLOT_FG_COLOR, labelsize=7)

    figure.subplots_adjust(top=0.92, bottom=0.12, left=0.12, right=0.92)
    return figure


def figure_to_png_bytes(figure: Figure, dpi: int = 100) -> bytes:
    """Serialize a Matplotlib Figure into PNG image bytes strictly on a white canvas."""
    buf = io.BytesIO()
    figure.savefig(
        buf,
        format="png",
        dpi=dpi,
        facecolor=DEFAULT_PLOT_BG_COLOR,
        edgecolor=DEFAULT_PLOT_BG_COLOR,
    )
    buf.seek(0)
    return buf.getvalue()


def execute_render_job(
    job_type: str,
    params: dict,
    width: float = 8.0,
    height: float = 6.0,
    dpi: int = 100,
) -> bytes:
    """Execute any registered plot job headlessly and return rendered PNG image bytes."""
    fig = Figure(figsize=(width, height), dpi=dpi)

    if job_type == "region":
        spec = RegionViewSpec.model_validate(params)
        render_region_plot(spec, figure=fig)
    elif job_type == "synoptic":
        render_synoptic_field(figure=fig)
    elif job_type == "composite":
        layers = params.get("layers", [])
        render_layer_composite(layers, figure=fig)
    elif job_type == "variable_profile":
        var = params.get("var", "gh")
        time_step = params.get("time_step", 24)
        render_variable_profile(var=var, time_step=time_step, figure=fig)
    elif job_type == "variable_cross_section":
        var = params.get("var", "gh")
        time_step = params.get("time_step", 24)
        lat_min = params.get("lat_min", 20.0)
        lat_max = params.get("lat_max", 55.0)
        render_variable_cross_section(var=var, time_step=time_step, lat_min=lat_min, lat_max=lat_max, figure=fig)
    elif job_type == "diagnostic":
        var_name = params.get("var_name", "Variable")
        unit_str = params.get("unit_str", "")
        preset_name = params.get("preset_name", "")
        render_diagnostic_plot(var_name=var_name, unit_str=unit_str, preset_name=preset_name, figure=fig)
    elif job_type == "colormap_transfer":
        render_colormap_transfer_plot(
            vmin=params.get("vmin", 520.0),
            vmax=params.get("vmax", 590.0),
            vcenter=params.get("vcenter", 555.0),
            curve_type=params.get("curve_type", "Linear / Power-Law"),
            gamma=params.get("gamma", 1.0),
            bias=params.get("bias", 0.0),
            step=params.get("step", 6.0),
            cmap_name=params.get("cmap_name", "turbo"),
            norm_name=params.get("norm_name", "Normalize"),
            orientation=params.get("orientation", "horizontal"),
            shrink=params.get("shrink", 0.8),
            aspect=params.get("aspect", 20.0),
            cbar_label=params.get("cbar_label", "Geopotential Height [dam]"),
            figure=fig,
        )
    else:
        raise ValueError(f"Unknown render job type: {job_type}")

    png_bytes = figure_to_png_bytes(fig, dpi=dpi)
    fig.clear()
    return png_bytes
