"""Coordinate canonicalization and spatial normalization for xarray datasets."""

import numpy as np
import xarray as xr

from xotplot.constants import (
    CANONICAL_LAT_NAME,
    CANONICAL_LEVEL_NAME,
    CANONICAL_LON_NAME,
    CANONICAL_TIME_NAME,
    KNOWN_LAT_NAMES,
    KNOWN_LEVEL_NAMES,
    KNOWN_LON_NAMES,
    KNOWN_TIME_NAMES,
)


def canonicalize_coordinates(ds: xr.Dataset) -> xr.Dataset:
    """Standardize dataset coordinates, dimensions, and spatial ordering.

    Enforces:
    - Lowercase canonical dimension/coordinate names: 'lat', 'lon', 'time', 'level'
    - Strictly ascending latitude: -90 to 90
    - Strictly ascending longitude: normalized to [-180, 180)
    """
    rename_map: dict[str, str] = {}

    # Match latitude
    for name in KNOWN_LAT_NAMES:
        if name in ds.coords or name in ds.dims:
            if name != CANONICAL_LAT_NAME:
                rename_map[name] = CANONICAL_LAT_NAME
            break

    # Match longitude
    for name in KNOWN_LON_NAMES:
        if name in ds.coords or name in ds.dims:
            if name != CANONICAL_LON_NAME:
                rename_map[name] = CANONICAL_LON_NAME
            break

    # Match time
    for name in KNOWN_TIME_NAMES:
        if name in ds.coords or name in ds.dims:
            if name != CANONICAL_TIME_NAME and CANONICAL_TIME_NAME not in ds.coords:
                rename_map[name] = CANONICAL_TIME_NAME
            break

    # Match level
    for name in KNOWN_LEVEL_NAMES:
        if name in ds.coords or name in ds.dims:
            if name != CANONICAL_LEVEL_NAME and CANONICAL_LEVEL_NAME not in ds.coords:
                rename_map[name] = CANONICAL_LEVEL_NAME
            break

    if rename_map:
        ds = ds.rename(rename_map)

    # Normalize longitude bounds to [-180, 180) and sort ascending
    if CANONICAL_LON_NAME in ds.coords and ds[CANONICAL_LON_NAME].ndim == 1:
        lon_vals = ds[CANONICAL_LON_NAME].values
        if np.any(lon_vals > 180.0):
            # Convert [0, 360) -> [-180, 180)
            norm_lon = ((ds[CANONICAL_LON_NAME] + 180.0) % 360.0) - 180.0
            ds = ds.assign_coords({CANONICAL_LON_NAME: norm_lon})
            ds = ds.sortby(CANONICAL_LON_NAME)
        else:
            # Check if sorted ascending
            if len(lon_vals) > 1 and lon_vals[0] > lon_vals[-1]:
                ds = ds.sortby(CANONICAL_LON_NAME)

    # Normalize latitude to strictly ascending [-90, 90]
    if CANONICAL_LAT_NAME in ds.coords and ds[CANONICAL_LAT_NAME].ndim == 1:
        lat_vals = ds[CANONICAL_LAT_NAME].values
        if len(lat_vals) > 1 and lat_vals[0] > lat_vals[-1]:
            ds = ds.sortby(CANONICAL_LAT_NAME)

    return ds
