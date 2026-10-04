"""GRIB2 dataset loader with hypercube inspection and systematic level merging."""

from pathlib import Path
from typing import Dict, List
import cfgrib
import xarray as xr

from xotplot.constants import (
    CANONICAL_LAT_NAME,
    CANONICAL_LEVEL_NAME,
    CANONICAL_LON_NAME,
)
from xotplot.io.canonical import canonicalize_coordinates


def load_grib2_dataset(file_path: str | Path) -> xr.Dataset:
    """Open a GRIB2 file, merge multiple hypercubes into a single canonical xarray.Dataset.

    - Splits the GRIB2 file using cfgrib.open_datasets to prevent DatasetBuildError.
    - Systematic Level-Type Suffixing:
      - 3D isobaric variables (isobaricInhPa) are normalized to variable names e.g. 't_isobaric'
        with canonical dimension 'level'.
      - Other level types get suffixed by their level type if multi-level or named cleanly.
      - 2D surface variables retain clean shortNames or standard names (e.g. 't2m', 'msl', 'sp').
    - Standardizes coordinates to canonical lowercase ('lat', 'lon', 'time', 'level') and
      strictly ascending ordering with longitude in [-180, 180).
    """
    path = str(Path(file_path).expanduser().resolve())
    cubes: List[xr.Dataset] = cfgrib.open_datasets(path)
    if not cubes:
        raise ValueError(f"No valid GRIB2 hypercubes found in {path}")

    # Process each cube and disambiguate variable names
    all_vars: Dict[str, xr.DataArray] = {}
    shared_coords: Dict[str, xr.DataArray] = {}

    for cube in cubes:
        # Determine the primary vertical dimension of this hypercube if any
        level_dim = None
        level_type = None

        for dim in cube.dims:
            if "isobaric" in str(dim).lower() or dim == "isobaricInhPa":
                level_dim = dim
                level_type = "isobaric"
                break
            elif dim in ("heightAboveGround", "depthBelowLandLayer", "soilLayer", "hybrid"):
                level_dim = dim
                level_type = str(dim)
                break

        # Process each data variable in this cube
        for var_name, da in cube.data_vars.items():
            clean_name = str(var_name)

            if level_type == "isobaric" and level_dim:
                # Rename isobaric dimension to canonical CANONICAL_LEVEL_NAME
                da = da.rename({level_dim: CANONICAL_LEVEL_NAME})
                # Suffix isobaric variables to distinguish from surface (e.g. t -> t_isobaric)
                out_name = f"{clean_name}_isobaric"
                da.attrs["level_type"] = "isobaric"
            elif level_type and level_type not in ("isobaric",):
                out_name = f"{clean_name}_{level_type}"
                da.attrs["level_type"] = level_type
            else:
                out_name = clean_name
                if "surface" in cube.coords or "entireAtmosphere" in cube.coords:
                    da.attrs["level_type"] = "surface"

            # Avoid collision by appending index if still colliding
            if out_name in all_vars:
                collision_idx = 1
                while f"{out_name}_{collision_idx}" in all_vars:
                    collision_idx += 1
                out_name = f"{out_name}_{collision_idx}"

            # Strip scalar coordinates that conflict across hypercubes (e.g. heightAboveGround=10 vs 2 vs 100)
            scalar_coords = [c for c in da.coords if c not in da.dims and c not in ("latitude", "longitude", "valid_time", "time")]
            if scalar_coords:
                da = da.drop_vars(scalar_coords)

            all_vars[out_name] = da

    # Merge all variables into a single Dataset
    unified = xr.Dataset(all_vars)

    # Standardize to canonical coordinates and ascending ranges
    unified = canonicalize_coordinates(unified)

    return unified
