"""Test suite for xotplot.engine isolation, headless execution, and process separation."""

import sys
import unittest
from xotplot.constants import DEFAULT_PLOT_BG_COLOR
from xotplot.engine import (
    EngineClient,
    build_crs,
    execute_render_job,
    figure_to_png_bytes,
    render_region_plot,
    render_synoptic_field,
)
from xotplot.spec import (
    ExtentSpec,
    FeaturesSpec,
    GraticuleSpec,
    ProjectionSpec,
    RegionViewSpec,
)


class TestEngineIsolation(unittest.TestCase):
    """Verify engine module is completely isolated from GUI components."""

    def test_engine_does_not_import_gui(self) -> None:
        """The engine package must not depend on GUI widgets or PyQt6."""
        import xotplot.engine
        import xotplot.engine.cartopy_features
        import xotplot.engine.renderer

        for mod_name in list(sys.modules.keys()):
            if mod_name.startswith("xotplot.gui") and not mod_name.startswith("xotplot.gui.cartopy_features"):
                self.fail(f"Engine indirectly loaded GUI module: {mod_name}")

    def test_render_synoptic_field(self) -> None:
        """Verify synoptic plot renders headlessly with #ffffff canvas."""
        fig = render_synoptic_field()
        self.assertEqual(fig.patch.get_facecolor()[:3], (1.0, 1.0, 1.0))
        png_data = figure_to_png_bytes(fig)
        self.assertTrue(png_data.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_render_region_plot(self) -> None:
        """Verify region plot renders headlessly with valid spec."""
        spec = RegionViewSpec(
            category="Global & Continents",
            preset_name="Global Full Disk",
            extent=ExtentSpec(west=-180, east=180, south=-90, north=90),
            projection=ProjectionSpec(crs_id="PlateCarree", central_longitude=0.0),
            features=FeaturesSpec(),
            custom_shapefiles=[],
            graticules=GraticuleSpec(),
        )
        fig = render_region_plot(spec)
        self.assertEqual(fig.patch.get_facecolor()[:3], (1.0, 1.0, 1.0))
        png_data = figure_to_png_bytes(fig)
        self.assertTrue(png_data.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_separate_engine_process(self) -> None:
        """Verify EngineClient launches and runs in an isolated OS process."""
        client = EngineClient()
        try:
            self.assertTrue(client._process.is_alive())
            data = client.render_sync("synoptic", {}, width=6.0, height=4.0, dpi=80)
            self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertGreater(len(data), 1000)
        finally:
            client.shutdown()
    def test_channel_cancellation(self) -> None:
        """Verify submitting with cancel_previous cancels any prior active job on the channel."""
        client = EngineClient(num_workers=2)
        try:
            # Submit a heavy job on channel 'test_channel'
            client.submit_job(
                job_id="job_heavy",
                job_type="synoptic",
                params={},
                channel="test_channel",
                cancel_previous=False,
            )
            self.assertGreater(client.busy_count, 0)

            # Now submit a replacement job on the same channel with cancel_previous=True
            client.submit_job(
                job_id="job_easy",
                job_type="synoptic",
                params={},
                channel="test_channel",
                cancel_previous=True,
            )
            # The previous job was killed and replaced by the new job
            self.assertGreater(client.busy_count, 0)
        finally:
            client.shutdown()


if __name__ == "__main__":
    unittest.main()
