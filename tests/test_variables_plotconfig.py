"""Tests for VariableTitleSpec, GlobalTitleSpec, PlotConfig and VariablesInspectorView."""

import unittest
from xotplot.spec import (
    GlobalTitleSpec,
    PlotConfig,
    VariableTitleSpec,
)


class TestPlotConfigAndTitles(unittest.TestCase):
    """Verify title formatting schemas and PlotConfig models."""

    def test_variable_title_formatting_with_template(self) -> None:
        spec = VariableTitleSpec(template="{long_name} ({name}) @ {level} [{units}]")
        var_text = spec.format_var_text(
            var_name="t2m",
            long_name="2-metre Temperature",
            level=None,
            units="K",
        )
        self.assertEqual(var_text, "2-metre Temperature (t2m) [K]")

        # Test with isobaric level
        var_text_lvl = spec.format_var_text(
            var_name="gh",
            long_name="Geopotential Height",
            level=500.0,
            units="gpm",
        )
        self.assertEqual(var_text_lvl, "Geopotential Height (gh) @ 500 hPa [gpm]")

        # Test simpler custom template slot
        spec_simple = VariableTitleSpec(template="{name} [{units}]")
        self.assertEqual(spec_simple.format_var_text("u10", units="m/s"), "u10 [m/s]")

    def test_global_title_formatting(self) -> None:
        gt = GlobalTitleSpec(
            title="GFS 0.25° Synoptic Weather Map",
            subtitle_enabled=True,
            subtitle_pre="Analysis 00Z",
            subtitle_post="Step 24h",
        )
        self.assertEqual(gt.format_title(), "GFS 0.25° Synoptic Weather Map")

        formatted_subtitle = gt.format_subtitle("Temperature @ 850 hPa [K]")
        self.assertEqual(
            formatted_subtitle,
            "Analysis 00Z - Temperature @ 850 hPa [K] - Step 24h",
        )

    def test_plot_config_instantiation_and_conversion(self) -> None:
        cfg = PlotConfig(
            variable="t2m",
            plot_type="contourf",
            colormap="coolwarm",
            vmin=250.0,
            vmax=310.0,
            num_levels=20,
            computed_var_text="2m Temperature [K]",
        )
        self.assertEqual(cfg.variable, "t2m")
        self.assertEqual(cfg.plot_type, "contourf")
        self.assertEqual(cfg.vmin, 250.0)

        global_spec = GlobalTitleSpec(
            title="Common Global Title",
            subtitle_pre="Analysis",
            subtitle_post="Forecast",
        )
        data_spec = cfg.to_data_plot_spec(global_title_spec=global_spec)
        self.assertEqual(data_spec.slice_spec.variable, "t2m")
        self.assertEqual(data_spec.custom_title, "Common Global Title")
        self.assertEqual(data_spec.custom_subtitle, "Analysis - 2m Temperature [K] - Forecast")


class TestVariablesInspectorViewUI(unittest.TestCase):
    """Verify VariablesInspectorView GUI controls and PlotConfig bottom sidebar operations."""

    @classmethod
    def setUpClass(cls) -> None:
        from PyQt6.QtWidgets import QApplication
        import sys
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_view_plotconfig_crud_workflow(self) -> None:
        from xotplot.gui.views.spatial_viewport_view import SpatialViewportView
        from xotplot.gui.views.variables_inspector_view import VariablesInspectorView

        viewport = SpatialViewportView()
        view = VariablesInspectorView()
        view.set_global_title_provider(viewport.get_global_title_spec)
        viewport.global_title_changed.connect(lambda _: view._on_title_setting_changed())

        # 1. Verify initial state: map only is default, button text is Add Config
        self.assertEqual(len(view.get_plot_configs()), 0)
        self.assertEqual(view.btn_add_config.text(), "Add Config")
        self.assertTrue(view.btn_toggle_histogram.isChecked(), "Map Only should be checked by default")

        # 2. Configure common title in viewport and variable template in inspector
        viewport.edit_global_title.setText("ECMWF HRES Global Model")
        viewport.edit_subtitle_pre.setText("Init 00Z")
        viewport.edit_subtitle_post.setText("T+48h")
        view.edit_var_template.setText("{long_name} [{units}]")

        # 3. Trigger Add Config
        view.btn_add_config.click()
        configs = view.get_plot_configs()
        self.assertEqual(len(configs), 1)
        cfg0 = configs[0]
        self.assertEqual(cfg0.variable, "t2m")
        self.assertEqual(cfg0.var_text_template, "{long_name} [{units}]")
        self.assertIn("t2m", cfg0.computed_var_text)

        # 4. Add a second configuration
        view.combo_style.setCurrentText("contour")
        view.btn_add_config.click()
        self.assertEqual(len(view.get_plot_configs()), 2)
        self.assertEqual(view.config_table.rowCount(), 2)

        # 5. Select first row, modify control, and update config
        view.config_table.selectRow(0)
        view.combo_style.setCurrentText("pcolormesh")
        view.btn_update_config.click()
        configs = view.get_plot_configs()
        self.assertEqual(configs[0].plot_type, "pcolormesh")

        # 6. Delete selected configuration
        view.config_table.selectRow(0)
        view.btn_delete_config.click()
        self.assertEqual(len(view.get_plot_configs()), 1)
        self.assertEqual(view.config_table.rowCount(), 1)

        # 7. Clear all configurations
        view.btn_clear_configs.click()
        self.assertEqual(len(view.get_plot_configs()), 0)
        self.assertEqual(view.config_table.rowCount(), 0)

    def test_rapid_typing_debounces_render(self) -> None:
        from xotplot.gui.views.spatial_viewport_view import SpatialViewportView
        from xotplot.gui.views.variables_inspector_view import VariablesInspectorView

        viewport = SpatialViewportView()
        view = VariablesInspectorView()
        view.set_global_title_provider(viewport.get_global_title_spec)
        viewport.global_title_changed.connect(lambda _: view._on_title_setting_changed())

        # Rapid typing simulation on variable template
        accum = ""
        for char in "{name} @ {level}":
            accum += char
            view.edit_var_template.setText(accum)
            # Debounce timer should be active and running
            self.assertTrue(view._render_debounce_timer.isActive())
            # Title preview updates immediately
            self.assertIn("Title (Common):", view.lbl_title_preview.text())
        self.assertIn("t2m", view.lbl_title_preview.text())


if __name__ == "__main__":
    unittest.main()
