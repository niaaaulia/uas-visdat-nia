from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.analytics import build_hierarchy_long, compute_pca_and_clusters
from src.data import load_boundary, load_imk, load_pdrb_map, load_quality
from src.config import IMK_FEATURES
from src.figures import _hierarchy_nodes, geospatial_map, heatmap_figure, hierarchy_sunburst, hierarchy_treemap, parallel_coordinates, pca_scatter, radar_profile


ROOT = Path(__file__).resolve().parents[1]


def test_imk_contract() -> None:
    df = load_imk(ROOT / "data" / "processed" / "imk_analysis.csv")
    assert len(df) == 38
    assert df["provinsi"].nunique() == 38
    assert df.isna().sum().sum() == 0
    assert (df["jumlah_perusahaan_total"] == df["jumlah_perusahaan_mikro"] + df["jumlah_perusahaan_kecil"]).all()
    assert (df["jumlah_tk_total"] == df["jumlah_tk_mikro"] + df["jumlah_tk_kecil"]).all()


def test_geospatial_contract() -> None:
    m = load_pdrb_map(ROOT / "data" / "processed" / "pdrb_map.csv")
    geo = load_boundary(ROOT / "data" / "processed" / "boundary_513.geojson")
    quality = load_quality(ROOT / "data" / "processed" / "data_quality.json")
    assert len(m) == 513
    assert m["kab_kota"].nunique() == 513
    assert len(geo["features"]) == 513
    assert quality["geospatial"]["pdrb_without_geometry"] == ["Sumbawa"]
    feature_names = {f["properties"]["kab_kota"] for f in geo["features"]}
    assert feature_names == set(m["kab_kota"])


def test_multivariate_and_hierarchy_build() -> None:
    df = load_imk(ROOT / "data" / "processed" / "imk_analysis.csv")
    result = compute_pca_and_clusters(df)
    assert len(IMK_FEATURES) == 9
    assert "share_kecil" not in IMK_FEATURES
    assert result.scores.shape[0] == 38
    assert result.standardized.shape == (38, 11)  # provinsi + cluster + 9 indikator
    assert result.explained_ratio[:2].sum() > 0.5
    assert result.scores["cluster"].nunique() == 3
    assert len(parallel_coordinates(result.standardized).data[0].dimensions) == 9
    assert len(heatmap_figure(result.standardized, ["ACEH", "RIAU"]).data[0].x) == 9
    assert len(radar_profile(df, "ACEH").data[1].theta) == 10

    h = build_hierarchy_long(df)
    assert len(h) == 76  # 38 provinsi × mikro/kecil
    assert h["jumlah_perusahaan"].sum() == df["jumlah_perusahaan_total"].sum()
    nodes = _hierarchy_nodes(h, "Jawa")
    assert not nodes.isna().any().any()  # semua level punya nilai hover; tidak ada NaN


def test_core_figures_serialize() -> None:
    df = load_imk(ROOT / "data" / "processed" / "imk_analysis.csv")
    m = load_pdrb_map(ROOT / "data" / "processed" / "pdrb_map.csv")
    geo = load_boundary(ROOT / "data" / "processed" / "boundary_513.geojson")
    result = compute_pca_and_clusters(df)
    hierarchy = build_hierarchy_long(df)

    figures = [
        pca_scatter(result.scores, result.explained_ratio),
        hierarchy_treemap(hierarchy),
        hierarchy_sunburst(hierarchy),
        geospatial_map(m, geo)[0],
    ]
    for fig in figures:
        payload = fig.to_json()
        assert len(payload) > 1000


def test_no_iframe_component_pattern() -> None:
    app_source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "streamlit.components" not in app_source
    assert "components.html" not in app_source
