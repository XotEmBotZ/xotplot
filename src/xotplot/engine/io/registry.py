"""In-memory dataset registry for isolated Engine workers."""

from typing import Dict, List, Optional
import xarray as xr

from xotplot.spec import CoordinateInfo, DatasetMetadata, VariableInfo


class DatasetRegistry:
    """Manages loaded xarray.Dataset instances within an Engine process."""

    def __init__(self) -> None:
        self._datasets: Dict[str, xr.Dataset] = {}
        self._metadata: Dict[str, DatasetMetadata] = {}
        self._active_id: Optional[str] = None

    def register(self, dataset_id: str, ds: xr.Dataset, metadata: DatasetMetadata) -> None:
        """Register a dataset and set as active."""
        self._datasets[dataset_id] = ds
        self._metadata[dataset_id] = metadata
        self._active_id = dataset_id

    def get(self, dataset_id: Optional[str] = None) -> xr.Dataset:
        """Get dataset by ID, defaulting to active dataset.

        Raises:
            KeyError: If no dataset is registered or ID is invalid.
        """
        target_id = dataset_id or self._active_id
        if not target_id or target_id not in self._datasets:
            raise KeyError(f"No active dataset found (requested id: {target_id})")
        return self._datasets[target_id]

    def get_metadata(self, dataset_id: Optional[str] = None) -> DatasetMetadata:
        """Get metadata by ID, defaulting to active dataset."""
        target_id = dataset_id or self._active_id
        if not target_id or target_id not in self._metadata:
            raise KeyError(f"No metadata found for dataset: {target_id}")
        return self._metadata[target_id]

    def set_active(self, dataset_id: str) -> None:
        """Set active dataset pointer."""
        if dataset_id not in self._datasets:
            raise KeyError(f"Dataset ID not found in registry: {dataset_id}")
        self._active_id = dataset_id

    @property
    def active_id(self) -> Optional[str]:
        return self._active_id

    def close(self, dataset_id: str) -> None:
        """Close dataset file handles and evict from registry."""
        ds = self._datasets.pop(dataset_id, None)
        self._metadata.pop(dataset_id, None)
        if ds is not None:
            ds.close()
        if self._active_id == dataset_id:
            self._active_id = next(iter(self._datasets.keys()), None)

    def close_all(self) -> None:
        """Close all datasets."""
        for ds in self._datasets.values():
            ds.close()
        self._datasets.clear()
        self._metadata.clear()
        self._active_id = None


def extract_metadata(
    dataset_id: str,
    file_path: str,
    detected_format: str,
    ds: xr.Dataset,
) -> DatasetMetadata:
    """Build serializable Pydantic DatasetMetadata from an xarray.Dataset."""
    variables: Dict[str, VariableInfo] = {}
    coordinates: Dict[str, CoordinateInfo] = {}

    for var_name, da in ds.data_vars.items():
        v_name = str(var_name)
        variables[v_name] = VariableInfo(
            name=v_name,
            dimensions=[str(d) for d in da.dims],
            shape=list(da.shape),
            dtype=str(da.dtype),
            units=da.attrs.get("units"),
            long_name=da.attrs.get("long_name"),
            standard_name=da.attrs.get("standard_name"),
            level_type=da.attrs.get("GRIB_typeOfLevel") or da.attrs.get("level_type"),
        )

    for coord_name, da in ds.coords.items():
        c_name = str(coord_name)
        min_v = float(da.min().values) if da.size > 0 and da.dtype.kind in "iufc" else None
        max_v = float(da.max().values) if da.size > 0 and da.dtype.kind in "iufc" else None
        discrete_v = None
        if da.size <= 64 and da.dtype.kind in "iufc":
            discrete_v = [float(x) for x in da.values.flatten()]

        coordinates[c_name] = CoordinateInfo(
            name=c_name,
            dimensions=[str(d) for d in da.dims],
            size=int(da.size),
            min_value=min_v,
            max_value=max_v,
            units=da.attrs.get("units"),
            discrete_values=discrete_v,
        )

    clean_attrs = {
        str(k): str(v) if not isinstance(v, (int, float, bool, str)) else v
        for k, v in ds.attrs.items()
    }

    return DatasetMetadata(
        dataset_id=dataset_id,
        file_path=file_path,
        detected_format=detected_format,
        variables=variables,
        coordinates=coordinates,
        global_attrs=clean_attrs,
    )
