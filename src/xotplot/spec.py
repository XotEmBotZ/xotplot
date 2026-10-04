"""Plot specification and validation schemas for xotplot.

Single source of truth for serializable configurations adhering to FAIL-FAST,
SIMPLE-ONLY, and LEAST-CODE principles.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Dict, List, Literal, Optional, Tuple
import uuid
from pydantic import BaseModel, Field

from xotplot.constants import (
    DEFAULT_BORDER_COLOR,
    DEFAULT_COAST_COLOR,
    DEFAULT_GLOBAL_TITLE,
    DEFAULT_GRID_COLOR,
    DEFAULT_LAKE_COLOR,
    DEFAULT_PLOT_BG_COLOR,
    DEFAULT_PLOT_FG_COLOR,
    DEFAULT_RESOLUTION,
    DEFAULT_RIVER_COLOR,
    DEFAULT_SHP_COLOR,
    DEFAULT_STATE_COLOR,
    DEFAULT_SUBTITLE_POST,
    DEFAULT_SUBTITLE_PRE,
    DEFAULT_SUBTITLE_TEMPLATE,
    DEFAULT_VAR_TEMPLATE,
    DEFAULT_WIND_BARBS_COLOR,
    DEFAULT_WIND_BARBS_ENABLED,
    DEFAULT_WIND_BARBS_LENGTH,
    DEFAULT_WIND_BARBS_PIVOT,
    DEFAULT_WIND_BARBS_STEP,
)

CrsId = Literal[
    "LambertConformal",
    "PlateCarree",
    "Mercator",
    "NorthPolarStereo",
    "Orthographic",
    "Robinson",
]

FeatureScale = Literal["110m", "50m", "10m"]
LineStyle = Literal["-", "--", ":", "-."]


class ExtentSpec(BaseModel):
    """Geographic bounding box specification (West, East, South, North)."""

    west: Annotated[float, Field(ge=-180.0, le=180.0, description="West boundary longitude in degrees")]
    east: Annotated[float, Field(ge=-180.0, le=180.0, description="East boundary longitude in degrees")]
    south: Annotated[float, Field(ge=-90.0, le=90.0, description="South boundary latitude in degrees")]
    north: Annotated[float, Field(ge=-90.0, le=90.0, description="North boundary latitude in degrees")]

    def as_tuple(self) -> Tuple[float, float, float, float]:
        """Return (west, east, south, north) tuple."""
        return (self.west, self.east, self.south, self.north)


class ProjectionSpec(BaseModel):
    """Cartopy projection and coordinate reference system specification."""

    crs_id: CrsId = "LambertConformal"
    central_longitude: Annotated[float, Field(ge=-180.0, le=180.0)] = 82.5
    central_latitude: Annotated[float, Field(ge=-90.0, le=90.0)] = 22.0
    standard_parallels: Tuple[
        Annotated[float, Field(ge=-90.0, le=90.0)],
        Annotated[float, Field(ge=-90.0, le=90.0)],
    ] = (12.0, 28.0)


class FeatureLayerSpec(BaseModel):
    """Configuration for an individual Cartopy or shapefile feature layer."""

    enabled: bool = True
    color: str
    linewidth: Annotated[float, Field(gt=0.0)] = 1.0
    linestyle: LineStyle = "-"
    custom_shapefile: Optional[Path] = None


class FeaturesSpec(BaseModel):
    """Granular Cartopy natural earth and shapefile feature layers specification."""

    scale: FeatureScale = DEFAULT_RESOLUTION
    coastlines: FeatureLayerSpec = Field(
        default_factory=lambda: FeatureLayerSpec(
            enabled=True,
            color=DEFAULT_COAST_COLOR,
            linewidth=1.0,
            linestyle="-",
        )
    )
    borders: FeatureLayerSpec = Field(
        default_factory=lambda: FeatureLayerSpec(
            enabled=True,
            color=DEFAULT_BORDER_COLOR,
            linewidth=0.8,
            linestyle="--",
        )
    )
    states: FeatureLayerSpec = Field(
        default_factory=lambda: FeatureLayerSpec(
            enabled=False,
            color=DEFAULT_STATE_COLOR,
            linewidth=0.5,
            linestyle=":",
        )
    )
    rivers: FeatureLayerSpec = Field(
        default_factory=lambda: FeatureLayerSpec(
            enabled=False,
            color=DEFAULT_RIVER_COLOR,
            linewidth=0.6,
            linestyle="-",
        )
    )
    lakes: FeatureLayerSpec = Field(
        default_factory=lambda: FeatureLayerSpec(
            enabled=False,
            color=DEFAULT_LAKE_COLOR,
            linewidth=0.6,
            linestyle="-",
        )
    )


class CustomShapefileSpec(BaseModel):
    """Standalone custom shapefile overlay specification."""

    path: Path
    name: str = ""
    enabled: bool = True
    color: str = DEFAULT_SHP_COLOR
    linewidth: Annotated[float, Field(gt=0.0)] = 1.2


class GraticuleSpec(BaseModel):
    """Coordinate graticules, gridlines and label annotations specification."""

    enabled: bool = True
    draw_labels: bool = True
    linestyle: LineStyle = "--"
    lon_step: Annotated[float, Field(gt=0.0, le=60.0)] = 5.0
    lat_step: Annotated[float, Field(gt=0.0, le=60.0)] = 5.0
    color: str = DEFAULT_GRID_COLOR
    alpha: Annotated[float, Field(ge=0.0, le=1.0)] = 0.6


class RegionViewSpec(BaseModel):
    """Complete serializable specification for the Projection & Region view."""

    category: str = "India & Subcontinent"
    preset_name: str = "India (National Subcontinent)"
    extent: ExtentSpec = Field(
        default_factory=lambda: ExtentSpec(west=68.0, east=97.5, south=6.5, north=37.5)
    )
    projection: ProjectionSpec = Field(default_factory=ProjectionSpec)
    features: FeaturesSpec = Field(default_factory=FeaturesSpec)
    custom_shapefiles: List[CustomShapefileSpec] = Field(default_factory=list)
    graticules: GraticuleSpec = Field(default_factory=GraticuleSpec)
    canvas_bg_color: str = DEFAULT_PLOT_BG_COLOR
    canvas_fg_color: str = DEFAULT_PLOT_FG_COLOR


class PlotSpec(BaseModel):
    """Root plot specification schema for saving, loading and validating xotplot configs."""

    version: str = "0.1.0"
    region_view: RegionViewSpec = Field(default_factory=RegionViewSpec)

    def to_json_file(self, path: Path | str) -> None:
        """Serialize configuration to a JSON file."""
        p = Path(path)
        p.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def from_json_file(cls, path: Path | str) -> "PlotSpec":
        """Load and validate configuration from a JSON file."""
        p = Path(path)
        content = p.read_text(encoding="utf-8")
        return cls.model_validate_json(content)


# =============================================================================
# Unified Dataset & IO Ingestion Schemas
# =============================================================================
SupportedFormat = Literal["auto", "grib2", "netcdf4", "zarr"]


class OpenDatasetRequest(BaseModel):
    """Request sent across IPC to open and ingest a dataset inside the Engine."""

    file_path: str
    format_override: SupportedFormat = "auto"
    dataset_id: Optional[str] = None


class VariableInfo(BaseModel):
    """Metadata descriptor for a single data variable."""

    name: str
    dimensions: List[str]
    shape: List[int]
    dtype: str
    units: Optional[str] = None
    long_name: Optional[str] = None
    standard_name: Optional[str] = None
    level_type: Optional[str] = None


class CoordinateInfo(BaseModel):
    """Metadata descriptor for a canonical coordinate axis."""

    name: str  # 'lat', 'lon', 'time', 'level'
    dimensions: List[str]
    size: int
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    units: Optional[str] = None
    discrete_values: Optional[List[float]] = None


class DatasetMetadata(BaseModel):
    """Complete serialized metadata returned by Engine to GUI/TUI/CLI."""

    dataset_id: str
    file_path: str
    detected_format: str
    variables: Dict[str, VariableInfo]
    coordinates: Dict[str, CoordinateInfo]
    global_attrs: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Meteorological Field Slicing & Plotting Schemas
# =============================================================================
PlotFieldType = Literal["contourf", "pcolormesh", "contour"]


class WindBarbsSpec(BaseModel):
    """Specification for overlaying wind barbs on meteorological maps."""

    enabled: bool = DEFAULT_WIND_BARBS_ENABLED
    u_var: Optional[str] = None
    v_var: Optional[str] = None
    step: Annotated[int, Field(ge=1, le=50)] = DEFAULT_WIND_BARBS_STEP
    length: Annotated[float, Field(gt=0.0)] = DEFAULT_WIND_BARBS_LENGTH
    color: str = DEFAULT_WIND_BARBS_COLOR
    pivot: Literal["tip", "middle"] = "middle"
    linewidth: Annotated[float, Field(gt=0.0)] = 0.8


class DataSliceSpec(BaseModel):
    """Specification for slicing a 2D horizontal field from an in-memory dataset."""

    variable: str
    level_type: Optional[str] = None
    level_value: Optional[float] = None
    time_index: int = 0


# =============================================================================
# Variable & Global Title Formatting Schemas
# =============================================================================
class VariableTitleSpec(BaseModel):
    """Specification for configuring variable-specific text using a single template slot."""

    template: str = DEFAULT_VAR_TEMPLATE

    def format_var_text(
        self,
        var_name: str,
        long_name: Optional[str] = None,
        level: Optional[float] = None,
        units: Optional[str] = None,
    ) -> str:
        """Format variable text using placeholders ({name}, {long_name}, {level}, {units})."""
        text = self.template
        lname = long_name if long_name else var_name

        text = text.replace("{name}", var_name)
        text = text.replace("{var}", var_name)
        text = text.replace("{var_name}", var_name)
        text = text.replace("{long_name}", lname)

        if level is None:
            text = text.replace("@ {level}", "").replace("@{level}", "").replace("{level}", "")
        else:
            text = text.replace("{level}", f"{level:.0f} hPa")

        if not units:
            text = text.replace("[{units}]", "").replace("{units}", "")
        else:
            text = text.replace("{units}", units)

        text = text.replace("[]", "").replace("()", "")
        return " ".join(text.split()).strip()


class GlobalTitleSpec(BaseModel):
    """Global common title and subtitle specification following (pre - var title - post) format."""

    # Common Global Title (not in variable)
    title: str = DEFAULT_GLOBAL_TITLE

    # Subtitle with slot for variable text
    subtitle_enabled: bool = True
    subtitle_pre: str = DEFAULT_SUBTITLE_PRE
    subtitle_post: str = DEFAULT_SUBTITLE_POST
    subtitle_template: str = DEFAULT_SUBTITLE_TEMPLATE

    def format_title(self, var_title: str = "") -> str:
        """Return the common global title."""
        return self.title.strip()

    def format_subtitle(self, var_text: str) -> str:
        """Generate formatted subtitle incorporating the variable text."""
        if not self.subtitle_enabled:
            return ""

        pre = self.subtitle_pre.strip()
        post = self.subtitle_post.strip()

        if "{var_text}" in self.subtitle_template or "{var_title}" in self.subtitle_template:
            res = self.subtitle_template
            res = res.replace("{pre}", pre)
            res = res.replace("{post}", post)
            res = res.replace("{var_text}", var_text)
            res = res.replace("{var_title}", var_text)
            parts = [p.strip() for p in res.split("-") if p.strip()]
            return " - ".join(parts)

        # Default (pre - var title - post) format
        parts: List[str] = []
        if pre:
            parts.append(pre)
        if var_text.strip():
            parts.append(var_text.strip())
        if post:
            parts.append(post)
        return " - ".join(parts)


class DataPlotSpec(BaseModel):
    """Complete specification for rendering a 2D meteorological field onto a map."""

    dataset_id: Optional[str] = None
    slice_spec: DataSliceSpec
    plot_type: PlotFieldType = "contourf"
    colormap: str = "coolwarm"
    vmin: Optional[float] = None
    vmax: Optional[float] = None
    num_levels: Annotated[int, Field(ge=5, le=100)] = 15
    show_colorbar: bool = True
    colorbar_label: Optional[str] = None
    region_view: RegionViewSpec = Field(default_factory=RegionViewSpec)
    wind_barbs: Optional[WindBarbsSpec] = None
    custom_title: Optional[str] = None
    custom_subtitle: Optional[str] = None
    global_title_spec: Optional[GlobalTitleSpec] = None


class PlotConfig(BaseModel):
    """Configuration for an individual plot layer/variable pushed to centralized plotconfig."""

    id: str = Field(default_factory=lambda: f"cfg_{uuid.uuid4().hex[:6]}")
    variable: str
    level: Optional[float] = None
    level_type: Optional[str] = "surface"
    plot_type: PlotFieldType = "contourf"
    colormap: str = "coolwarm"
    vmin: Optional[float] = None
    vmax: Optional[float] = None
    num_levels: int = 15
    is_wind: bool = False
    barbs_step: int = 5
    barbs_length: float = 6.0
    barbs_pivot: str = "middle"
    barbs_color: str = "#0f172a"
    var_text_template: str = DEFAULT_VAR_TEMPLATE
    computed_var_text: str = ""
    enabled: bool = True
    z_index: int = 0

    def to_data_plot_spec(
        self,
        dataset_id: Optional[str] = None,
        region_view: Optional[RegionViewSpec] = None,
        global_title_spec: Optional[GlobalTitleSpec] = None,
    ) -> DataPlotSpec:
        """Convert this plot configuration into a renderable DataPlotSpec."""
        wind_spec = None
        if self.is_wind:
            wind_spec = WindBarbsSpec(
                enabled=True,
                step=self.barbs_step,
                length=self.barbs_length,
                color=self.barbs_color,
                pivot=self.barbs_pivot,  # type: ignore[arg-type]
            )

        title = global_title_spec.format_title() if global_title_spec else None
        subtitle = global_title_spec.format_subtitle(self.computed_var_text) if global_title_spec else None

        return DataPlotSpec(
            dataset_id=dataset_id,
            slice_spec=DataSliceSpec(
                variable=self.variable,
                level_type=self.level_type,
                level_value=self.level,
            ),
            plot_type=self.plot_type,
            colormap=self.colormap,
            vmin=self.vmin,
            vmax=self.vmax,
            num_levels=self.num_levels,
            region_view=region_view or RegionViewSpec(),
            wind_barbs=wind_spec,
            custom_title=title,
            custom_subtitle=subtitle,
            global_title_spec=global_title_spec,
        )





