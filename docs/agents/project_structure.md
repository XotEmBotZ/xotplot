# Project Structure Reference

This document records the foundational package layout for `xotplot`.

## Layout

```
xotplot/
├── docs/
│   └── agents/               # Agent logs, architecture notes, and session state
├── src/
│   └── xotplot/
│       ├── __init__.py       # Package entry point
│       ├── spec.py           # Pydantic PlotSpec (serializable single source of truth)
│       ├── io/               # Data ingestion (GRIB2/NetCDF) & coordinate normalizer
│       │   └── __init__.py
│       ├── engine/           # Stateless Matplotlib + Cartopy rendering engine
│       │   └── __init__.py
│       ├── cli/              # Headless CLI batch execution
│       │   └── __init__.py
│       ├── tui/              # Textual TUI inspector
│       │   └── __init__.py
│       └── gui/              # PyQt6 dual-stage GUI viewport
│           └── __init__.py
├── tests/
│   └── __init__.py
├── pyproject.toml
└── README.md
```
