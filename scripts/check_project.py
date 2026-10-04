from __future__ import annotations

import compileall
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analytics import build_hierarchy_long, compute_pca_and_clusters  # noqa: E402
from src.config import IMK_FEATURES  # noqa: E402
from src.data import load_boundary, load_imk, load_pdrb_map, load_quality  # noqa: E402
from src.figures import geospatial_map, heatmap_figure, hierarchy_sunburst, hierarchy_treemap, parallel_coordinates, pca_scatter, radar_profile  # noqa: E402


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"[PASS] {message}")


def main() -> None:
    print("== Syntax check ==")
    check(compileall.compile_dir(str(ROOT), quiet=1), "Semua file Python dapat dikompilasi")

    print("\n== Data contract ==")
    imk = load_imk(ROOT / "data" / "processed" / "imk_analysis.csv")
    map_df = load_pdrb_map(ROOT / "data" / "processed" / "pdrb_map.csv")
    geo = load_boundary(ROOT / "data" / "processed" / "boundary_513.geojson")
    quality = load_quality(ROOT / "data" / "processed" / "data_quality.json")
    check(len(imk) == 38 and imk["provinsi"].nunique() == 38, "38 provinsi IMK unik")
    check(int(imk["jumlah_perusahaan_total"].sum()) == 4_461_888, "Total usaha dibaca dari data: 4.461.888")
    check(int(imk["jumlah_tk_total"].sum()) == 9_484_645, "Total tenaga kerja dibaca dari data: 9.484.645")
    check(len(map_df) == 513 and map_df["kab_kota"].nunique() == 513, "513 unit peta unik")
    check(len(geo["features"]) == 513, "GeoJSON memuat 513 feature")
    check(quality["geospatial"]["pdrb_without_geometry"] == ["Sumbawa"], "Hanya Sumbawa yang tidak memiliki geometri")

    print("\n== Multivariate contract ==")
    check(len(IMK_FEATURES) == 9, "PCA memakai tepat 9 indikator IMK")
    check("share_kecil" not in IMK_FEATURES, "Indikator 'porsi usaha kecil' tidak masuk PCA")
    pca = compute_pca_and_clusters(imk)
    check(pca.explained_ratio[:2].sum() > 0.5, "PC1+PC2 menjelaskan >50% variasi")
    check(pca.scores["cluster"].nunique() == 3, "K-Means menghasilkan 3 cluster eksploratif")

    parallel = parallel_coordinates(pca.standardized)
    check(len(parallel.data[0].dimensions) == 9, "Parallel coordinates memiliki 9 sumbu")
    heatmap = heatmap_figure(pca.standardized, ["ACEH", "RIAU", "JAMBI"])
    check(len(heatmap.data[0].x) == 9 and len(heatmap.data[0].y) == 3, "Heatmap dinamis mengikuti subset 3 provinsi × 9 indikator")
    radar = radar_profile(imk, "ACEH")
    check(len(radar.data[1].theta) == 10, "Radar memakai 9 indikator + titik penutup")

    print("\n== Hierarchy contract ==")
    hierarchy = build_hierarchy_long(imk)
    check(len(hierarchy) == 76, "Hierarki memiliki 38 provinsi × 2 skala")
    check(int(hierarchy["jumlah_perusahaan"].sum()) == int(imk["jumlah_perusahaan_total"].sum()), "Agregat hierarki konsisten dengan total IMK")
    check(set(hierarchy["skala"]) == {"Mikro", "Kecil"}, "Level skala mikro/kecil tersedia")

    print("\n== Figure serialization ==")
    treemap = hierarchy_treemap(hierarchy)
    sunburst = hierarchy_sunburst(hierarchy)
    choropleth = geospatial_map(map_df, geo, quarter="Triwulan II", classification="Quantile", layer_mode="Choropleth")[0]
    check(treemap.data[0].maxdepth == -1, "Treemap menampilkan seluruh level hierarki")
    check(sunburst.data[0].maxdepth == -1, "Sunburst menampilkan seluruh level hierarki")
    check(len(treemap.data[0].ids) == 121 and len(sunburst.data[0].ids) == 121, "Visual nasional memuat node Indonesia → pulau → provinsi → skala")
    check(set(map(int, choropleth.data[0].z)).issubset(set(range(5))), "Choropleth memakai kode kelas ordinal untuk legenda diskret")

    figs = [
        pca_scatter(pca.scores, pca.explained_ratio),
        parallel,
        heatmap,
        radar,
        treemap,
        sunburst,
        choropleth,
    ]
    for i, fig in enumerate(figs, start=1):
        check(len(fig.to_json()) > 1000, f"Figure {i} berhasil diserialisasi")

    print("\n== UI architecture ==")
    app_source = (ROOT / "app.py").read_text(encoding="utf-8")
    css_source = (ROOT / "assets" / "style.css").read_text(encoding="utf-8")
    config_source = (ROOT / "src" / "config.py").read_text(encoding="utf-8")
    check("components.html" not in app_source and "streamlit.components" not in app_source, "Tidak menggunakan iframe custom component")
    check('scrollZoom": False' in config_source, "Scroll-wheel zoom dinonaktifkan")
    check("site-nav" in css_source and "position: sticky" in css_source, "Navigasi editorial dibuat sticky")
    check('[data-testid="stHeader"]' in css_source and "display: none !important" in css_source, "Header/toolbar native Streamlit disembunyikan")
    check("13 indikator" not in app_source.lower(), "Tidak ada klaim lama '13 indikator' pada aplikasi")
    check("metric_grid(" not in app_source, "Blok metric-card pembuka yang bocor sebagai HTML sudah dihapus")

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
