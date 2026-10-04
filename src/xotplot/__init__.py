def main() -> None:
    """Entry point for xotplot CLI and GUI launcher."""
    import sys
    from xotplot.gui.app import run_app

    sys.exit(run_app())

