"""Engine IO subsystem exports and unified ingestion interface."""

from pathlib import Path
from typing import Optional
import uuid
import xarray as xr

from xotplot.engine.io.grib import load_grib2_dataset
from xotplot.engine.io.registry import (
    DatasetRegistry,
    extract_metadata,
)
from xotplot.io.detector import detect_file_format
from xotplot.spec import DatasetMetadata, OpenDatasetRequest


def open_dataset(
    request: OpenDatasetRequest,
    registry: Optional[DatasetRegistry] = None,
) -> tuple[xr.Dataset, DatasetMetadata]:
    """Ingest a dataset via format auto-detection, canonicalize coordinates and register it.

    Supports GRIB2, NetCDF4, and Zarr.
    """
    file_path = str(Path(request.file_path).expanduser().resolve())
    detected_format = detect_file_format(file_path, override=request.format_override)
    dataset_id = request.dataset_id or str(uuid.uuid4())

    if detected_format == "grib2":
        ds = load_grib2_dataset(file_path)
    elif detected_format == "netcdf4":
        raise NotImplementedError("NetCDF4 loader will be implemented in subsequent step")
    elif detected_format == "zarr":
        raise NotImplementedError("Zarr loader will be implemented in subsequent step")
    else:
        raise ValueError(f"Unsupported format: {detected_format}")

    metadata = extract_metadata(
        dataset_id=dataset_id,
        file_path=file_path,
        detected_format=detected_format,
        ds=ds,
    )

    if registry is not None:
        registry.register(dataset_id=dataset_id, ds=ds, metadata=metadata)

    return ds, metadata


__all__ = [
    "DatasetRegistry",
    "extract_metadata",
    "load_grib2_dataset",
    "open_dataset",
]
