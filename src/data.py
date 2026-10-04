from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pandas as pd

from .config import DATA_PROCESSED


@lru_cache(maxsize=1)
def load_imk(path: Path | None = None) -> pd.DataFrame:
    target = path or (DATA_PROCESSED / "imk_analysis.csv")
    return pd.read_csv(target)


@lru_cache(maxsize=1)
def load_pdrb_map(path: Path | None = None) -> pd.DataFrame:
    target = path or (DATA_PROCESSED / "pdrb_map.csv")
    return pd.read_csv(target)


@lru_cache(maxsize=1)
def load_boundary(path: Path | None = None) -> dict:
    target = path or (DATA_PROCESSED / "boundary_513.geojson")
    with target.open("r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_quality(path: Path | None = None) -> dict:
    target = path or (DATA_PROCESSED / "data_quality.json")
    with target.open("r", encoding="utf-8") as f:
        return json.load(f)


def selected_provinces_from_plotly_event(event) -> list[str]:
    """Extract province names from Streamlit Plotly selection state.

    Plotly Express stores province as customdata[0]. This is intentionally defensive
    because Streamlit may return either a dict-like object or PlotlyState.
    """
    if event is None:
        return []
    try:
        selection = event.selection
    except Exception:
        selection = event.get("selection", {}) if isinstance(event, dict) else {}
    try:
        points = selection.points
    except Exception:
        points = selection.get("points", []) if isinstance(selection, dict) else []

    provinces: list[str] = []
    for point in points or []:
        custom = point.get("customdata") if isinstance(point, dict) else getattr(point, "customdata", None)
        if custom and len(custom) >= 1:
            provinces.append(str(custom[0]))
    return list(dict.fromkeys(provinces))
