from __future__ import annotations

import base64
from pathlib import Path

import pandas as pd
import streamlit as st

from src.analytics import build_hierarchy_long, cluster_signature, compute_pca_and_clusters, summarize_story
from src.config import ACCESS_DATE, APP_SUBTITLE, APP_TITLE, ASSETS, IMK_FEATURES, PLOTLY_CONFIG
from src.data import load_boundary, load_imk, load_pdrb_map, load_quality, selected_provinces_from_plotly_event
from src.figures import (
    geospatial_map,
    heatmap_figure,
    hierarchy_sunburst,
    hierarchy_treemap,
    parallel_coordinates,
    pca_scatter,
    radar_profile,
    top_contribution_bar,
)
from src.ui import anchor, callout, chapter_nav, insight_card, section_header, source_note, source_note_geospatial, story_card, subsection_header

st.set_page_config(page_title=APP_TITLE, page_icon="◼", layout="wide", initial_sidebar_state="collapsed")


def inject_css() -> None:
    css_path = ASSETS / "style.css"
    st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def fmt_num_id(value: float, digits: int = 0) -> str:
    text = f"{value:,.{digits}f}"
    return text.replace(",", "§").replace(".", ",").replace("§", ".")


def fmt_int_id(value: float) -> str:
    return fmt_num_id(value, 0)


def fmt_pct(value: float, digits: int = 1) -> str:
    return f"{fmt_num_id(value, digits)}%"


def fmt_money_id(value: float, unit: str = "juta", digits: int = 2) -> str:
    return f"Rp {fmt_num_id(value, digits)} {unit}"


def feature_label(col: str) -> str:
    return IMK_FEATURES.get(col, col)


def parallel_interpretation(standardized: pd.DataFrame, selected: list[str]) -> str:
    feature_cols = list(IMK_FEATURES)
    if selected:
        subset = standardized[standardized["provinsi"].isin(selected)]
        means = subset[feature_cols].mean().sort_values()
        low = means.index[0]
        high = means.index[-1]
        return (
            f"Rata-rata <strong>{len(subset)} provinsi terpilih</strong> paling menonjol pada "
            f"<strong>{feature_label(high)}</strong> (z = {fmt_num_id(means[high], 2)}) dan paling rendah pada "
            f"<strong>{feature_label(low)}</strong> (z = {fmt_num_id(means[low], 2)}) dibanding rata-rata nasional."
        )
    ranges = standardized[feature_cols].max() - standardized[feature_cols].min()
    feature = ranges.idxmax()
    hi_idx = standardized[feature].idxmax()
    lo_idx = standardized[feature].idxmin()
    return (
        f"Pada seluruh provinsi, rentang relatif paling lebar terlihat pada <strong>{feature_label(feature)}</strong>. "
        f"Nilai z-score tertinggi terdapat di <strong>{standardized.loc[hi_idx, 'provinsi'].title()}</strong> "
        f"({fmt_num_id(standardized.loc[hi_idx, feature], 2)}), sedangkan yang terendah di "
        f"<strong>{standardized.loc[lo_idx, 'provinsi'].title()}</strong> ({fmt_num_id(standardized.loc[lo_idx, feature], 2)})."
    )


def heatmap_interpretation(standardized: pd.DataFrame, selected: list[str]) -> str:
    feature_cols = list(IMK_FEATURES)
    subset = standardized[standardized["provinsi"].isin(selected)].copy() if selected else standardized.copy()
    matrix = subset.set_index("provinsi")[feature_cols]
    abs_matrix = matrix.abs()
    row_pos, col_pos = divmod(abs_matrix.to_numpy().argmax(), abs_matrix.shape[1])
    province = matrix.index[row_pos]
    feature = matrix.columns[col_pos]
    z = float(matrix.iloc[row_pos, col_pos])
    direction = "di atas" if z >= 0 else "di bawah"
    scope = f"subset {len(subset)} provinsi" if selected else "seluruh 38 provinsi"
    return (
        f"Pada {scope}, sel paling ekstrem terdapat pada <strong>{province.title()}</strong> untuk indikator "
        f"<strong>{feature_label(feature)}</strong>, dengan z-score {fmt_num_id(z, 2)} ({direction} rata-rata nasional)."
    )


def radar_interpretation(imk_df: pd.DataFrame, province: str) -> str:
    cols = list(IMK_FEATURES)
    percentiles = imk_df[cols].rank(pct=True, method="average") * 100
    idx = imk_df.index[imk_df["provinsi"] == province][0]
    row = percentiles.loc[idx].sort_values()
    low = row.index[0]
    high = row.index[-1]
    return (
        f"Untuk <strong>{province.title()}</strong>, posisi relatif tertinggi terdapat pada <strong>{feature_label(high)}</strong> "
        f"(persentil {fmt_num_id(row[high], 0)}), sedangkan posisi terendah terdapat pada <strong>{feature_label(low)}</strong> "
        f"(persentil {fmt_num_id(row[low], 0)})."
    )


def interpret_hierarchy(df: pd.DataFrame, island: str) -> dict:
    subset = df if island == "Semua" else df[df["pulau"] == island]
    province = (
        subset.groupby(["pulau", "provinsi"], as_index=False)
        .agg(
            jumlah_perusahaan=("jumlah_perusahaan", "sum"),
            jumlah_tk=("jumlah_tk", "sum"),
            nilai_output=("nilai_output", "sum"),
            nilai_tambah=("nilai_tambah", "sum"),
        )
    )
    province["nilai_tambah_per_pekerja"] = province["nilai_tambah"] / province["jumlah_tk"]
    province["output_per_usaha"] = province["nilai_output"] / province["jumlah_perusahaan"]
    total_usaha = float(subset["jumlah_perusahaan"].sum())
    national_share = total_usaha / float(df["jumlah_perusahaan"].sum()) * 100
    return {
        "total_usaha": total_usaha,
        "national_share": national_share,
        "top_usaha": province.nlargest(1, "jumlah_perusahaan").iloc[0],
        "top_nt_worker": province.nlargest(1, "nilai_tambah_per_pekerja").iloc[0],
        "top_tk": province.nlargest(1, "jumlah_tk").iloc[0],
        "top_output_per_usaha": province.nlargest(1, "output_per_usaha").iloc[0],
    }

def interpret_map(map_df: pd.DataFrame, quarter: str, mode: str) -> dict:
    share_col = "share_c_t1" if quarter == "Triwulan I" else "share_c_t2"
    sector_col = "sektorC_t1" if quarter == "Triwulan I" else "sektorC_t2"
    top_share = map_df.nlargest(1, share_col).iloc[0]
    top_sector = map_df.nlargest(1, sector_col).iloc[0]
    above20 = int((map_df[share_col] >= 20).sum())
    median_share = float(map_df[share_col].median())
    return {
        "share_col": share_col,
        "sector_col": sector_col,
        "top_share": top_share,
        "top_sector": top_sector,
        "above20": above20,
        "median_share": median_share,
        "mode": mode,
    }


def interpret_top10(map_df: pd.DataFrame, quarter: str) -> str:
    share_col = "share_c_t1" if quarter == "Triwulan I" else "share_c_t2"
    top10 = map_df.nlargest(10, share_col)
    leader = top10.iloc[0]
    prov_counts = top10["provinsi"].value_counts()
    dom_prov, dom_count = prov_counts.index[0], int(prov_counts.iloc[0])
    avg_top10 = float(top10[share_col].mean())
    return (
        f"Peringkat teratas dipimpin <strong>{leader['kab_kota']}</strong> ({leader['provinsi']}) dengan kontribusi {fmt_pct(float(leader[share_col]))}. "
        f"Di dalam 10 besar, provinsi yang paling sering muncul adalah <strong>{dom_prov}</strong> ({dom_count} daerah), "
        f"dan rata-rata kontribusi kelompok 10 besar mencapai <strong>{fmt_pct(avg_top10)}</strong>."
    )

def get_base64_image(image_path: Path) -> str:
    image_bytes = image_path.read_bytes()
    return base64.b64encode(image_bytes).decode()


inject_css()

hero_image = get_base64_image(ASSETS / "hero-imk.jpg")

st.markdown(
    f"""
    <style>
    .hero {{
        background:
            linear-gradient(
                90deg,
                rgba(8, 24, 43, 0.92) 0%,
                rgba(8, 24, 43, 0.78) 42%,
                rgba(8, 24, 43, 0.46) 70%,
                rgba(8, 24, 43, 0.25) 100%
            ),
            url("data:image/jpeg;base64,{hero_image}") center center / cover no-repeat !important;
    }}

    @media (max-width: 640px) {{
        .hero {{
            background:
                linear-gradient(
                    rgba(8, 24, 43, 0.78),
                    rgba(8, 24, 43, 0.78)
                ),
                url("data:image/jpeg;base64,{hero_image}") 56% center / cover no-repeat !important;
        }}
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ───────────────────────────────── Data & analysis ─────────────────────────────────
imk = load_imk()
map_df = load_pdrb_map()
boundary = load_boundary()
quality = load_quality()
pca = compute_pca_and_clusters(imk)
hierarchy_df = build_hierarchy_long(imk)
story = summarize_story(imk, map_df)

total_usaha = int(imk["jumlah_perusahaan_total"].sum())
total_tk = int(imk["jumlah_tk_total"].sum())

# ───────────────────────────────── Navigation ─────────────────────────────────
chapter_nav()

# ───────────────────────────────── Hero ─────────────────────────────────
anchor("pembuka")
st.markdown(
    f"""
    <section class="hero">
      <div class="hero__kicker">Data story · Industri Mikro dan Kecil 2025</div>
      <h1>Jejak Industri Mikro &amp; Kecil Indonesia</h1>
      <p class="hero__dek">{APP_SUBTITLE}.</p>
    </section>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="chapter-break chapter-break--compact"></div>', unsafe_allow_html=True)

# ───────────────────────────────── Chapter 1: Multivariate ─────────────────────────────────
anchor("multivariat")
section_header(
    "01 · Profil Provinsi",
    "Provinsi yang sama-sama besar belum tentu memiliki profil IMK yang sama.",
    "Sembilan indikator IMK 2025 dibandingkan pada 38 provinsi: jumlah perusahaan, tenaga kerja, nilai input, nilai output, nilai tambah, pengeluaran tenaga kerja, pemanfaatan internet, pemanfaatan pinjaman, dan usaha yang menjalin kemitraan.",
)


@st.fragment
def render_multivariate_interaction() -> None:
    subsection_header(
        "Peta kemiripan provinsi",
        "PCA merangkum sembilan indikator ke dua sumbu. Titik yang berdekatan memiliki kombinasi indikator yang lebih mirip, serta warna menunjukkan tiga cluster K-Means eksploratif.",
        meta=f"PC1 + PC2 menjelaskan {fmt_pct((pca.explained_ratio[0] + pca.explained_ratio[1]) * 100)} variasi",
    )

    if "pca_selection_epoch" not in st.session_state:
        st.session_state["pca_selection_epoch"] = 0

    pca_event = st.plotly_chart(
        pca_scatter(pca.scores, pca.explained_ratio),
        use_container_width=True,
        theme=None,
        key=f"pca-selection-{st.session_state['pca_selection_epoch']}",
        on_select="rerun",
        selection_mode=("points", "box", "lasso"),
        config=PLOTLY_CONFIG,
    )
    source_note(
        ["imk_stat_tables", "imk_publication"],
        extra=(
            "PCA memakai 9 indikator pada 38 provinsi. Enam indikator magnitude ditransformasi log1p; "
            "tiga indikator adopsi (internet, pinjaman, kemitraan) dipakai sebagai persentase. Seluruh indikator kemudian distandardisasi."
        ),
    )

    selected_provinces = selected_provinces_from_plotly_event(pca_event)

    guide_left, guide_right = st.columns([0.82, 0.18], vertical_alignment="center")
    with guide_left:
        if selected_provinces:
            names = ", ".join(x.title() for x in selected_provinces[:10])
            if len(selected_provinces) > 10:
                names += "…"
            callout("Pilihan aktif", f"{len(selected_provinces)} provinsi: {names}. Pilihan ini dipakai kembali pada parallel coordinates, heatmap, dan daftar provinsi radar.", "good")
        else:
            callout("Coba pilih beberapa provinsi", "Gunakan lasso atau box-select pada grafik. Tiga tampilan di bawah akan mengikuti pilihan yang sama.")
    with guide_right:
        if st.button("Reset pilihan", use_container_width=True, disabled=not bool(selected_provinces)):
            st.session_state["pca_selection_epoch"] += 1
            st.rerun(scope="fragment")

    st.markdown('<div class="cluster-heading">Ringkasan cluster</div>', unsafe_allow_html=True)
    cluster_cols = st.columns(len(pca.cluster_profiles.index), gap="medium")
    for col, cluster_name in zip(cluster_cols, pca.cluster_profiles.index):
        members = int((pca.scores["cluster"] == cluster_name).sum())
        signature = cluster_signature(pca.cluster_profiles, cluster_name)
        with col:
            insight_card(cluster_name, f"{members} provinsi. Ciri relatif yang paling menonjol: {signature}.")

    outlier_names = pca.scores.nsmallest(3, "outlier_rank")["provinsi"].str.title().tolist()
    st.caption(
        "Profil yang paling jauh dari pusat data pada kombinasi sembilan indikator: "
        + ", ".join(outlier_names)
        + ". Jarak ini bersifat deskriptif, bukan penilaian baik/buruk."
    )

    with st.expander("Detail transformasi PCA dan clustering", expanded=False):
        st.markdown(
            f"""
            - Enam variabel magnitude (`jumlah perusahaan`, `tenaga kerja`, `input`, `output`, `nilai tambah`, `pengeluaran tenaga kerja`) ditransformasi `log1p` lalu seluruh 9 indikator distandardisasi sebagai z-score.
            - Dua komponen pertama PCA menjelaskan **{fmt_pct((pca.explained_ratio[0] + pca.explained_ratio[1]) * 100)}** variasi.
            - K-Means memakai 3 cluster untuk eksplorasi. Hanya pada tahap K-Means, z-score di-clip pada ±2,5 agar satu nilai ekstrem tidak mendominasi centroid; PCA tetap memakai matriks standar asli.
            """
        )

    st.markdown('<div class="viz-spacer"></div>', unsafe_allow_html=True)
    subset_text = f"{len(selected_provinces)} provinsi terpilih" if selected_provinces else "seluruh 38 provinsi"
    subsection_header(
        "Lintasan sembilan indikator",
        "Setiap garis adalah satu provinsi. Saat ada seleksi PCA, garis biru menunjukkan provinsi terpilih dan garis abu-abu menjadi konteks pembanding.",
        meta=subset_text,
    )
    st.plotly_chart(parallel_coordinates(pca.standardized, selected_provinces), use_container_width=True, theme=None, key="parallel-linked", config=PLOTLY_CONFIG)
    callout("Interpretasi", parallel_interpretation(pca.standardized, selected_provinces))
    source_note(["imk_stat_tables", "imk_publication"], extra="Semua sumbu menggunakan z-score dari transformasi yang sama dengan PCA dan sembilan indikator yang sama.")

    st.markdown('<div class="viz-spacer"></div>', unsafe_allow_html=True)
    subsection_header(
        "Heatmap pola indikator",
        "Baris adalah provinsi dan kolom adalah sembilan indikator. Urutan baris serta kolom dihitung ulang pada subset yang dipilih agar pola internal kelompok lebih mudah terlihat.",
        meta=subset_text,
    )
    st.plotly_chart(heatmap_figure(pca.standardized, selected_provinces), use_container_width=True, theme=None, key="heatmap-linked", config=PLOTLY_CONFIG)
    callout("Interpretasi", heatmap_interpretation(pca.standardized, selected_provinces))
    source_note(["imk_stat_tables", "imk_publication"], extra="Urutan heatmap memakai hierarchical clustering metode Ward pada matriks z-score yang sedang ditampilkan.")

    st.markdown('<div class="viz-spacer"></div>', unsafe_allow_html=True)
    radar_options = selected_provinces if selected_provinces else imk["provinsi"].sort_values().tolist()
    radar_default = selected_provinces[0] if selected_provinces else ("DKI JAKARTA" if "DKI JAKARTA" in radar_options else radar_options[0])
    if st.session_state.get("radar_province") not in radar_options:
        st.session_state["radar_province"] = radar_default

    subsection_header(
        "Profil satu provinsi",
        "Radar memakai persentil nasional (0–100), sehingga indikator dengan satuan berbeda dapat dibaca dalam satu profil. Jika PCA sedang diseleksi, pilihan provinsi di bawah hanya berisi subset tersebut.",
        meta=f"{len(radar_options)} opsi provinsi",
    )
    st.selectbox("Provinsi", radar_options, key="radar_province", format_func=lambda x: x.title())
    st.plotly_chart(radar_profile(imk, st.session_state["radar_province"]), use_container_width=True, theme=None, key="radar-profile", config=PLOTLY_CONFIG)
    callout("Interpretasi", radar_interpretation(imk, st.session_state["radar_province"]))
    source_note(["imk_stat_tables", "imk_publication"], extra="Radar menampilkan persentil nasional untuk sembilan indikator yang sama dengan PCA, bukan nilai absolut.")


render_multivariate_interaction()

st.markdown('<div class="chapter-break"></div>', unsafe_allow_html=True)

# ───────────────────────────────── Chapter 2: Hierarchy ─────────────────────────────────
anchor("hierarki")
section_header(
    "02 · Membaca susunan IMK",
    "Dari pulau hingga skala usaha, susunan IMK terlihat berbeda.",
    "Pilih satu kelompok pulau untuk mempersempit pembacaan, struktur mikro/kecil tetap dipertahankan sebagai level paling bawah.",
)


@st.fragment
def render_hierarchy_interaction() -> None:
    with st.container(key="hierarchy-story"):
        story_cols = st.columns(3, gap="medium")
        with story_cols[0]:
            story_card(
                "02A",
                "Besaran usaha",
                "Pada treemap, luas kotak mengikuti <strong>jumlah perusahaan</strong>. Cabang yang lebih besar berarti menampung lebih banyak unit IMK.",
                "blue",
            )
        with story_cols[1]:
            story_card(
                "02B",
                "Produktivitas tenaga kerja",
                "Warna treemap menunjukkan <strong>nilai tambah per pekerja</strong> dalam juta rupiah per orang. Jadi besaran usaha dan intensitas nilai tambah dibaca terpisah.",
                "purple",
            )
        with story_cols[2]:
            story_card(
                "02C",
                "Sudut pandang tenaga kerja",
                "Sunburst memakai struktur wilayah dan skala yang sama, tetapi luas sektor mengikuti <strong>jumlah tenaga kerja</strong> dan warna menunjukkan <strong>output per usaha</strong>.",
                "orange",
            )

    with st.container(key="hierarchy-controls"):
        control_col1, control_col2 = st.columns([0.38, 0.62], vertical_alignment="bottom")
        with control_col1:
            island_options = ["Semua"] + sorted(hierarchy_df["pulau"].unique().tolist())
            island_filter = st.selectbox("Fokus wilayah", island_options, index=0, key="hierarchy_island")
        with control_col2:
            if island_filter == "Semua":
                callout("Tampilan nasional", "Klik area pada visual untuk masuk lebih dalam.")
            else:
                callout("Fokus wilayah", f"Tampilan difokuskan pada <strong>{island_filter}</strong>. Level yang terlihat menjadi kelompok pulau → provinsi → skala mikro/kecil.", "good")

    summary = interpret_hierarchy(hierarchy_df, island_filter)
    scope_meta = "Seluruh Indonesia" if island_filter == "Semua" else island_filter

    subsection_header(
        "Di mana jumlah usaha terkonsentrasi?",
        "Treemap mempertahankan jalur Indonesia → kelompok pulau → provinsi → skala. Pada tampilan nasional, level skala baru terlihat saat provinsi dibuka; ketika satu pulau dipilih, level mikro/kecil dapat dibaca lebih langsung.",
        meta=scope_meta,
    )
    st.plotly_chart(
        hierarchy_treemap(hierarchy_df, island_filter),
        use_container_width=True,
        theme=None,
        key="treemap-hierarchy",
        config=PLOTLY_CONFIG,
    )

    with st.container(key="hierarchy-insights"):
        info_cols = st.columns(3, gap="medium")
        with info_cols[0]:
            insight_card(
                "Usaha dalam cakupan",
                f"Terdapat <strong>{fmt_int_id(summary['total_usaha'])} unit</strong> IMK, setara {fmt_pct(summary['national_share'])} dari total nasional.",
            )
        with info_cols[1]:
            top_usaha = summary["top_usaha"]
            insight_card(
                "Jumlah usaha terbesar",
                f"<strong>{top_usaha['provinsi']}</strong> memiliki {fmt_int_id(top_usaha['jumlah_perusahaan'])} unit usaha pada cakupan yang sedang dilihat.",
            )
        with info_cols[2]:
            top_nt_worker = summary["top_nt_worker"]
            insight_card(
                "Nilai tambah per pekerja tertinggi",
                f"<strong>{top_nt_worker['provinsi']}</strong> mencatat {fmt_money_id(top_nt_worker['nilai_tambah_per_pekerja'], 'juta/orang')} pada cakupan ini.",
            )
    source_note(
        ["imk_stat_tables"],
        extra="Ukuran treemap = jumlah perusahaan (unit); warna = nilai tambah per pekerja (juta rupiah/orang).",
    )

    st.markdown('<div class="viz-spacer"></div>', unsafe_allow_html=True)
    subsection_header(
        "Bagaimana tenaga kerja tersebar di struktur yang sama?",
        "Sunburst memakai hierarki yang sama. Luas sektor mengikuti jumlah tenaga kerja, sedangkan warna menunjukkan output per usaha. Klik sektor untuk memperbesar cabang dan klik bagian tengah untuk kembali.",
        meta=scope_meta,
    )
    st.plotly_chart(
        hierarchy_sunburst(hierarchy_df, island_filter),
        use_container_width=True,
        theme=None,
        key="sunburst-hierarchy",
        config=PLOTLY_CONFIG,
    )
    top_tk = summary["top_tk"]
    top_output_per = summary["top_output_per_usaha"]
    callout(
        "Interpretasi",
        f"Pada cakupan <strong>{scope_meta}</strong>, tenaga kerja IMK terbanyak berada di <strong>{top_tk['provinsi']}</strong> "
        f"dengan <strong>{fmt_int_id(top_tk['jumlah_tk'])} orang</strong>. Sementara itu, output per usaha tertinggi terdapat di "
        f"<strong>{top_output_per['provinsi']}</strong> sebesar <strong>{fmt_money_id(top_output_per['output_per_usaha'], 'juta/unit')}</strong>.",
    )
    source_note(
        ["imk_stat_tables"],
        extra="Ukuran sunburst = jumlah tenaga kerja (orang); warna = nilai output dibagi jumlah perusahaan (juta rupiah/unit).",
    )


render_hierarchy_interaction()

st.markdown('<div class="chapter-break"></div>', unsafe_allow_html=True)

# ───────────────────────────────── Chapter 3: Geospatial ─────────────────────────────────
anchor("geospasial")
section_header(
    "03 · Industri pengolahan dalam ruang",
    "Industri yang besar belum tentu paling dominan bagi ekonomi daerah.",
    "Data PDRB kabupaten/kota yang digunakan adalah PDRB atas dasar harga berlaku Triwulan I dan Triwulan II tahun 2026. Choropleth menunjukkan seberapa besar peran sektor C dalam PDRB daerah, sedangkan simbol proporsional menunjukkan besaran nilai sektor C secara nominal.",
)


@st.fragment
def render_geospatial_interaction() -> None:
    with st.container(key="geospatial-story"):
        story_cols = st.columns(2, gap="medium")
        with story_cols[0]:
            story_card(
                "03A",
                "Seberapa dominan industrinya?",
                "Choropleth memakai <strong>kontribusi sektor C terhadap PDRB total (%)</strong>. Warna menjawab seberapa penting industri pengolahan bagi ekonomi kabupaten/kota tersebut.",
                "blue",
            )
        with story_cols[1]:
            story_card(
                "03B",
                "Seberapa besar nilai industrinya?",
                "Simbol proporsional memakai <strong>PDRB sektor C (miliar rupiah)</strong>. Luas lingkaran bertambah seiring besarnya nilai industri pengolahan secara nominal.",
                "orange",
            )

    with st.container(key="geospatial-controls"):
        c1, c2, c3 = st.columns(3, gap="medium", vertical_alignment="top")
        with c1:
            quarter = st.radio(
                "Periode PDRB 2026",
                ["Triwulan I", "Triwulan II"],
                index=1,
                horizontal=True,
                key="geo_quarter",
            )
        with c2:
            layer_mode = st.radio(
                "Tipe peta",
                ["Choropleth", "Simbol proporsional"],
                index=0,
                horizontal=True,
                key="geo_layer_mode",
            )
        with c3:
            classification = st.radio(
                "Klasifikasi choropleth",
                ["Equal interval", "Quantile"],
                index=0,
                horizontal=True,
                key="geo_classification",
                disabled=layer_mode != "Choropleth",
                help=(
                    "Equal interval (default) membagi rentang persentase ke kelas dengan jangkauan numerik yang sama, "
                    "sehingga wilayah dengan kontribusi sektor C sangat tinggi lebih mudah menonjol. "
                    "Quantile membagi wilayah agar jumlah observasi per kelas relatif seimbang; akibatnya jangkauan persentase antar kelas memang dapat berbeda. "
                    "Pilihan ini hanya memengaruhi mode choropleth."
                ),
            )

    map_fig, class_labels = geospatial_map(
        map_df,
        boundary,
        quarter=quarter,
        classification=classification,
        layer_mode=layer_mode,
    )
    map_meta = interpret_map(map_df, quarter, layer_mode)

    if layer_mode == "Choropleth":
        map_title = f"Kontribusi industri pengolahan terhadap PDRB · {quarter} 2026"
        map_dek = "Warna menunjukkan persentase PDRB sektor C terhadap PDRB total kabupaten/kota. Semakin tinggi kelasnya, semakin besar peran industri pengolahan dalam ekonomi lokal."
    else:
        map_title = f"Besaran PDRB industri pengolahan · {quarter} 2026"
        map_dek = "Luas lingkaran proporsional terhadap nilai PDRB sektor C dalam miliar rupiah. Peta ini menjawab besaran nominal, bukan tingkat ketergantungan ekonomi daerah terhadap industri."

    subsection_header(map_title, map_dek, meta="PDRB ADHB kabupaten/kota")
    st.plotly_chart(map_fig, use_container_width=True, theme=None, key="map-main", config=PLOTLY_CONFIG)

    if layer_mode == "Choropleth":
        callout(
            "Interpretasi",
            f"Pada <strong>{quarter} 2026</strong>, kontribusi sektor C tertinggi terdapat di <strong>{map_meta['top_share']['kab_kota']}</strong> "
            f"({map_meta['top_share']['provinsi']}) sebesar <strong>{fmt_pct(float(map_meta['top_share'][map_meta['share_col']]))}</strong>. "
            f"Median seluruh kabupaten/kota adalah <strong>{fmt_pct(map_meta['median_share'])}</strong>, dan <strong>{map_meta['above20']} daerah</strong> memiliki kontribusi sedikitnya 20%.",
        )
    else:
        callout(
            "Interpretasi",
            f"Pada <strong>{quarter} 2026</strong>, nilai PDRB sektor C terbesar terdapat di <strong>{map_meta['top_sector']['kab_kota']}</strong> "
            f"({map_meta['top_sector']['provinsi']}) sebesar <strong>{fmt_money_id(float(map_meta['top_sector'][map_meta['sector_col']]), 'miliar')}</strong>. "
            "Besaran nominal ini tidak selalu sejalan dengan tingginya kontribusi sektor C terhadap PDRB daerah.",
        )

    src_extra = f"PDRB ADHB {quarter} 2026; mode tampilan: {layer_mode}."
    if layer_mode == "Choropleth":
        src_extra += f" Klasifikasi: {classification}; kelas: {', '.join(class_labels)}."
    source_note_geospatial(extra=src_extra)

    st.markdown('<div class="viz-spacer"></div>', unsafe_allow_html=True)
    subsection_header(
        f"Peringkat kontribusi sektor C tertinggi · {quarter} 2026",
        "Diagram batang mengurutkan sepuluh kabupaten/kota dengan proporsi sektor industri pengolahan terbesar terhadap PDRB daerah pada periode yang dipilih.",
        meta="10 kabupaten/kota teratas",
    )
    st.plotly_chart(
        top_contribution_bar(map_df, quarter=quarter),
        use_container_width=True,
        theme=None,
        key="top-contribution",
        config=PLOTLY_CONFIG,
    )
    callout("Interpretasi", interpret_top10(map_df, quarter), "good")
    source_note_geospatial(extra=f"Peringkat menggunakan kontribusi sektor C terhadap PDRB pada {quarter} 2026.")


render_geospatial_interaction()

# ───────────────────────────────── Closing insights ─────────────────────────────────
st.markdown('<div class="chapter-break chapter-break--epilog"></div>', unsafe_allow_html=True)
anchor("epilog")
with st.container(key="epilog-section"):
    section_header(
        "Epilog · tiga lensa, satu cerita",
        "Skala, susunan usaha, dan ruang memberi jawaban yang berbeda dan hal ini membuatnya berguna ketika dibaca bersama.",
        "Profil provinsi memperlihatkan kemiripan dan perbedaan, hierarki menunjukkan bagaimana usaha tersusun dari wilayah ke skala, sementara peta geospasial menempatkan industri pengolahan dalam konteks ekonomi kabupaten/kota.",
    )
    closing_cols = st.columns(3, gap="medium")
    with closing_cols[0]:
        insight_card(
            "Digitalisasi tertinggi",
            f"<strong>{story['internet_top']}</strong> memiliki proporsi pemanfaatan internet tertinggi pada indikator IMK 2025 yang digunakan.",
            value=fmt_pct(story["internet_top_value"]),
        )
    with closing_cols[1]:
        insight_card(
            "Kontribusi sektor C tertinggi",
            f"Pada PDRB Triwulan II 2026, <strong>{story['map_share_top']}</strong> memiliki kontribusi sektor C terbesar terhadap PDRB daerahnya.",
            value=fmt_pct(story["map_share_top_value"]),
        )
    with closing_cols[2]:
        insight_card(
            "Kenaikan nilai sektor C terbesar",
            f"Dari Triwulan I ke Triwulan II 2026, <strong>{story['map_growth_top']}</strong> mencatat kenaikan persentase nilai sektor C terbesar.",
            value=fmt_pct(story["map_growth_top_value"]),
        )
    callout(
        "Ingat", "Provinsi yang mirip pada profil multivariat belum tentu mempunyai susunan skala usaha yang sama. Demikian pula, kabupaten/kota dengan nilai industri terbesar belum tentu merupakan daerah yang ekonominya paling bergantung pada industri pengolahan. Membaca ketiga lensa secara bersama mencegah kesimpulan yang terlalu sederhana.",
    )

# ───────────────────────────────── Methodology / audit ─────────────────────────────────
anchor("metode")
st.markdown('<div class="chapter-break"></div>', unsafe_allow_html=True)
section_header(
    "Metode",
    "Transformasi data dan aturan baca.",
    "Bagian ini merangkum cara pengolahan data, pilihan encoding, dan pemeriksaan kualitas yang paling relevan untuk memahami visual di atas.",
)

with st.expander("Metodologi multivariat", expanded=False):
    st.markdown(
        f"""
        - **Observasi:** 38 provinsi; **variabel:** {len(IMK_FEATURES)} indikator numerik.
        - Variabel magnitude yang sangat skewed memakai `log1p`; semua indikator kemudian distandardisasi (`z-score`).
        - **PCA** digunakan untuk reduksi dimensi; dua komponen pertama menjelaskan **{fmt_pct((pca.explained_ratio[0] + pca.explained_ratio[1]) * 100)}** variasi.
        - K-Means tiga cluster digunakan sebagai pengelompokan eksploratif. Untuk clustering saja, z-score di-clip pada ±2,5 agar satu pencilan ekstrem tidak mendominasi centroid.
        - Heatmap diurutkan menggunakan hierarchical clustering metode Ward; pemilihan titik pada PCA dipakai sebagai **brushing & linking** untuk parallel coordinates, heatmap, dan radar.
        """
    )

with st.expander("Metodologi hierarki", expanded=False):
    st.markdown(
        """
        - Struktur hierarki penuh adalah **Indonesia → kelompok pulau → provinsi → skala mikro/kecil**.
        - Ketika satu kelompok pulau dipilih, root Indonesia dihilangkan sehingga tampilan menjadi **pulau → provinsi → skala** tanpa mengubah data leaf mikro/kecil.
        - **Treemap:** ukuran = jumlah perusahaan; warna = nilai tambah per pekerja.
        - **Sunburst:** ukuran = jumlah tenaga kerja; warna = output per usaha.
        - Kedua representasi mendukung drill-down, treemap memakai pathbar/breadcrumb, sedangkan sunburst mempertahankan konteks induk melalui cincin radial.
        """
    )

with st.expander("Metodologi geospasial & kualitas data", expanded=False):
    geo = quality["geospatial"]
    st.markdown(
        f"""
        - PDRB BPS memuat **{geo['pdrb_rows']}** kabupaten/kota unik; boundary hasil rekonsiliasi memuat 514 feature.
        - Choropleth memakai rasio `sektor C / PDRB total × 100`, sedangkan simbol proporsional memakai nilai sektor C absolut (miliar rupiah).
        - Klasifikasi choropleth dapat diganti antara **quantile** dan **equal interval** sesuai kebutuhan pembacaan.
        - Data utama tetap berasal dari BPS; batas wilayah dipakai sebagai data spasial pendukung.
        """
    )

st.markdown(
    f"""
    <div class="footer-story">
      <div class="footer-story__title">Jejak Industri Mikro &amp; Kecil Indonesia</div>
      <div class="footer-story__meta">Data utama: BPS · Data spasial pendukung: boundary kabupaten/kota yang telah direkonsiliasi · Akses data: {ACCESS_DATE}</div>
    </div>
    """,
    unsafe_allow_html=True,
)
