"""File format detection and sniffing for meteorological datasets."""

from pathlib import Path
from typing import Literal

SupportedFormat = Literal["grib2", "netcdf4", "zarr"]


def detect_file_format(
    path: str | Path,
    override: str = "auto",
) -> SupportedFormat:
    """Detect dataset format via magic bytes, structure, or file extensions.

    Raises:
        FileNotFoundError: If the specified path does not exist.
        ValueError: If the format is unsupported or cannot be recognized.
    """
    if override != "auto":
        if override in ("grib2", "netcdf4", "zarr"):
            return override  # type: ignore[return-value]
        raise ValueError(f"Unsupported format override: {override}")

    target = Path(path).expanduser().resolve()
    if not target.exists():
        raise FileNotFoundError(f"Dataset path does not exist: {target}")

    # Zarr check (directory with .zgroup, .zmetadata or zarr.json)
    if target.is_dir():
        if (
            (target / ".zgroup").exists()
            or (target / ".zmetadata").exists()
            or (target / "zarr.json").exists()
            or target.suffix.lower() == ".zarr"
        ):
            return "zarr"
        raise ValueError(f"Directory is not a valid Zarr store: {target}")

    # Magic byte inspection for regular files
    with open(target, "rb") as f:
        header = f.read(16)

    # GRIB detection (starts with b"GRIB")
    if header.startswith(b"GRIB"):
        return "grib2"

    # NetCDF / HDF5 detection
    # NetCDF classic starts with b"CDF", HDF5 (NetCDF4) starts with \x89HDF\r\n\x1a\n
    if header.startswith(b"CDF") or header.startswith(b"\x89HDF\r\n\x1a\n"):
        return "netcdf4"

    # Fallback to extension matching
    ext = target.suffix.lower()
    if ext in (".grib", ".grib2", ".grb", ".grb2"):
        return "grib2"
    if ext in (".nc", ".nc4", ".netcdf", ".hdf5", ".h5"):
        return "netcdf4"
    if ext == ".zarr":
        return "zarr"

    raise ValueError(
        f"Unable to determine format for file: {target}. Specify format_override explicitly."
    )
