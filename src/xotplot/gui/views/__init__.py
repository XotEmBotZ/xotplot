"""Views package initialization."""

from xotplot.gui.views.cli_batch_engine_view import CliBatchEngineView
from xotplot.gui.views.colormap_transfer_view import ColormapTransferView
from xotplot.gui.views.compute_dask_view import ComputeDaskView
from xotplot.gui.views.derived_diagnostics_view import DerivedDiagnosticsView
from xotplot.gui.views.layer_stack_view import LayerStackView
from xotplot.gui.views.projection_region_view import ProjectionCartopyView, ProjectionRegionView
from xotplot.gui.views.spatial_viewport_view import SpatialViewportView
from xotplot.gui.views.variables_inspector_view import VariablesInspectorView

__all__ = [
    "CliBatchEngineView",
    "ColormapTransferView",
    "ComputeDaskView",
    "DerivedDiagnosticsView",
    "LayerStackView",
    "ProjectionCartopyView",
    "ProjectionRegionView",
    "SpatialViewportView",
    "VariablesInspectorView",
]


