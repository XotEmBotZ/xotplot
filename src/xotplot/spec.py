"""Plot specification and validation schemas for xotplot.

Single source of truth for serializable configurations adhering to FAIL-FAST,
SIMPLE-ONLY, and LEAST-CODE principles.
"""

from pathlib import Path
from typing import Annotated, Any, Dict, List, Literal, Optional, Tuple
from pydantic import BaseModel, Field

from xotplot.constants import (
    DEFAULT_BORDER_COLOR,
    DEFAULT_COAST_COLOR,
    DEFAULT_GRID_COLOR,
    DEFAULT_LAKE_COLOR,
    DEFAULT_PLOT_BG_COLOR,
    DEFAULT_PLOT_FG_COLOR,
    DEFAULT_RESOLUTION,
    DEFAULT_RIVER_COLOR,
    DEFAULT_SHP_COLOR,
    DEFAULT_STATE_COLOR,
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


class DataSliceSpec(BaseModel):
    """Specification for slicing a 2D horizontal field from an in-memory dataset."""

    variable: str
    level_type: Optional[str] = None
    level_value: Optional[float] = None
    time_index: int = 0


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


