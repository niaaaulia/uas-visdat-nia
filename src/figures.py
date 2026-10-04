from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .analytics import classify_values, clustered_heatmap_matrix
from .config import (
    CLUSTER_COLORS,
    IMK_FEATURES,
    NEUTRAL,
    OKABE_ITO,
    SOFT_AMBER_SCALE,
    SOFT_BLUE_SCALE,
    SOFT_TEAL_SCALE,
    BLUE_PURPLE_SCALE,
    CIVIDIS_5,
)

FONT_FAMILY = "Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"


def _base_layout(fig: go.Figure, height: int = 560, margin: dict | None = None) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=margin or dict(l=20, r=20, t=54, b=28),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT_FAMILY, color=NEUTRAL["ink"], size=13),
        hoverlabel=dict(font=dict(family=FONT_FAMILY, size=13), bgcolor="#FFFFFF"),
        separators=",.",
        legend=dict(
            title=None,
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="left",
            x=0,
        ),
    )
    return fig


def pca_scatter(scores: pd.DataFrame, explained_ratio: np.ndarray) -> go.Figure:
    order = [f"Cluster {i}" for i in sorted(scores["cluster_id"].unique())]
    color_map = {name: CLUSTER_COLORS[i] for i, name in enumerate(order)}
    fig = px.scatter(
        scores,
        x="PC1",
        y="PC2",
        color="cluster",
        category_orders={"cluster": order},
        color_discrete_map=color_map,
        hover_name="provinsi",
        custom_data=["provinsi", "pulau", "cluster", "jumlah_perusahaan_total", "outlier_rank"],
        render_mode="svg",
    )
    fig.update_traces(
        marker=dict(size=12, opacity=0.88, line=dict(width=1.1, color="#FFFFFF")),
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Kelompok pulau: %{customdata[1]}<br>"
            "%{customdata[2]}<br>"
            "Jumlah usaha: %{customdata[3]:,.0f}<br>"
            "Peringkat jarak multivariat: %{customdata[4]}<extra></extra>"
        ),
    )

    top_outliers = scores.nsmallest(3, "outlier_rank")
    for _, row in top_outliers.iterrows():
        fig.add_annotation(
            x=float(row["PC1"]),
            y=float(row["PC2"]),
            text=str(row["provinsi"]).title(),
            showarrow=True,
            arrowhead=0,
            arrowwidth=1,
            arrowcolor="#98A2B3",
            ax=34 if float(row["PC1"]) <= 0 else -34,
            ay=-24 if float(row["PC2"]) <= 0 else 24,
            bgcolor="rgba(255,255,255,.88)",
            bordercolor="rgba(152,162,179,.45)",
            borderpad=3,
            font=dict(size=10, color=NEUTRAL["ink"]),
        )

    fig.add_hline(y=0, line_width=1, line_dash="dot", line_color="#CBD5E1")
    fig.add_vline(x=0, line_width=1, line_dash="dot", line_color="#CBD5E1")

    x_min, x_max = float(scores["PC1"].min()), float(scores["PC1"].max())
    y_min, y_max = float(scores["PC2"].min()), float(scores["PC2"].max())
    x_pad = max((x_max - x_min) * 0.12, 0.5)
    y_pad = max((y_max - y_min) * 0.14, 0.5)
    fig.update_xaxes(
        title=f"PC1 · {explained_ratio[0] * 100:.1f}% variasi".replace(".", ","),
        range=[x_min - x_pad, x_max + x_pad],
        showgrid=True,
        gridcolor="#EEF0F2",
        zeroline=False,
    )
    fig.update_yaxes(
        title=f"PC2 · {explained_ratio[1] * 100:.1f}% variasi".replace(".", ","),
        range=[y_min - y_pad, y_max + y_pad],
        showgrid=True,
        gridcolor="#EEF0F2",
        zeroline=False,
    )
    fig.update_layout(dragmode="lasso")
    return _base_layout(fig, height=530, margin=dict(l=62, r=34, t=42, b=60))


def _cluster_colorscale(n_clusters: int = 3) -> list[list]:
    colors = CLUSTER_COLORS[:n_clusters]
    scale: list[list] = []
    for i, color in enumerate(colors):
        left = i / n_clusters
        right = (i + 1) / n_clusters
        scale.extend([[left, color], [right, color]])
    return scale


def parallel_coordinates(standardized: pd.DataFrame, selected_provinces: list[str] | None = None) -> go.Figure:
    label_short = {
        "jumlah_perusahaan_total": "Usaha",
        "jumlah_tk_total": "Tenaga kerja",
        "nilai_input_total": "Input",
        "nilai_output_total": "Output",
        "nilai_tambah_total": "Nilai tambah",
        "pengeluaran_tk_total": "Pengeluaran TK",
        "internet_pct": "Internet (%)",
        "pinjaman_pct": "Pinjaman (%)",
        "kemitraan_pct": "Kemitraan (%)",
    }
    dims = []
    for col in IMK_FEATURES:
        values = standardized[col].astype(float)
        lo, hi = float(values.min()), float(values.max())
        pad = max((hi - lo) * 0.05, 0.15)
        dims.append(dict(label=label_short[col], values=values, range=[lo - pad, hi + pad]))

    if selected_provinces:
        selected = standardized["provinsi"].isin(selected_provinces).astype(int)
        line = dict(
            color=selected,
            colorscale=[[0.0, "#D9DEE5"], [0.499, "#D9DEE5"], [0.5, OKABE_ITO["blue"]], [1.0, OKABE_ITO["blue"]]],
            cmin=0,
            cmax=1,
            showscale=False,
        )
    else:
        cluster_ids = standardized["cluster"].str.extract(r"(\d+)")[0].astype(int)
        n_clusters = int(cluster_ids.max())
        line = dict(color=cluster_ids, colorscale=_cluster_colorscale(n_clusters), cmin=1, cmax=n_clusters + 0.999, showscale=False)

    fig = go.Figure(
        data=go.Parcoords(
            line=line,
            dimensions=dims,
            labelfont=dict(size=11, family=FONT_FAMILY, color=NEUTRAL["ink"]),
            tickfont=dict(size=9, family=FONT_FAMILY, color=NEUTRAL["muted"]),
            rangefont=dict(size=9, family=FONT_FAMILY, color=NEUTRAL["muted"]),
        )
    )
    return _base_layout(fig, height=480, margin=dict(l=44, r=44, t=70, b=34))


def heatmap_figure(standardized: pd.DataFrame, selected_provinces: list[str] | None = None) -> go.Figure:
    matrix, row_labels, _ = clustered_heatmap_matrix(standardized, selected_provinces)
    label_short = {
        "jumlah_perusahaan_total": "Usaha",
        "jumlah_tk_total": "Tenaga kerja",
        "nilai_input_total": "Input",
        "nilai_output_total": "Output",
        "nilai_tambah_total": "Nilai tambah",
        "pengeluaran_tk_total": "Pengeluaran TK",
        "internet_pct": "Internet",
        "pinjaman_pct": "Pinjaman",
        "kemitraan_pct": "Kemitraan",
    }
    x_labels = [label_short[c] for c in matrix.columns]
    fig = go.Figure(
        data=go.Heatmap(
            z=matrix.values,
            x=x_labels,
            y=[x.title() for x in row_labels],
            zmid=0,
            zmin=-3,
            zmax=3,
            colorscale=[[0.0, OKABE_ITO["blue"]], [0.5, "#F7F7F5"], [1.0, OKABE_ITO["vermillion"]]],
            colorbar=dict(title="z-score", thickness=12, len=0.60, x=1.02),
            hovertemplate="<b>%{y}</b><br>%{x}<br>z = %{z:.2f}<extra></extra>",
        )
    )
    fig.update_xaxes(tickangle=-28, side="bottom", tickfont=dict(size=10))
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=10), automargin=True)
    n_rows = len(matrix)
    height = max(400, min(900, 185 + n_rows * 20))
    return _base_layout(fig, height=height, margin=dict(l=150, r=70, t=28, b=100))


def radar_profile(imk: pd.DataFrame, province: str) -> go.Figure:
    cols = list(IMK_FEATURES.keys())
    labels = ["Usaha", "Tenaga kerja", "Input", "Output", "Nilai tambah", "Pengeluaran TK", "Internet", "Pinjaman", "Kemitraan"]
    percentile = imk[cols].rank(pct=True, method="average") * 100
    idx = imk.index[imk["provinsi"] == province][0]
    vals = percentile.loc[idx, cols].tolist()
    vals += vals[:1]
    theta = labels + labels[:1]
    median = [50.0] * len(theta)

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=median, theta=theta, mode="lines", line=dict(color="#B6BBC4", dash="dot", width=2), name="Median nasional", hovertemplate="Median nasional<extra></extra>"))
    fig.add_trace(
        go.Scatterpolar(
            r=vals,
            theta=theta,
            fill="toself",
            fillcolor="rgba(0,114,178,0.16)",
            line=dict(color=OKABE_ITO["blue"], width=2.5),
            marker=dict(size=5),
            name=province.title(),
            hovertemplate="%{theta}: persentil %{r:.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        polar=dict(
            radialaxis=dict(range=[0, 100], tickvals=[25, 50, 75, 100], gridcolor="#E5E7EB", tickfont=dict(size=9, color=NEUTRAL["muted"])),
            angularaxis=dict(gridcolor="#EEF0F2", tickfont=dict(size=10)),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=True,
    )
    return _base_layout(fig, height=540, margin=dict(l=70, r=70, t=40, b=54))


def _hierarchy_nodes(hierarchy: pd.DataFrame, island: str = "Semua") -> pd.DataFrame:
    """Build explicit hierarchy nodes so every level has complete hover metrics."""
    data = hierarchy.copy()
    if island != "Semua":
        data = data[data["pulau"] == island].copy()

    rows: list[dict] = []

    def add_node(node_id: str, label: str, parent: str, level: str, frame: pd.DataFrame) -> None:
        companies = float(frame["jumlah_perusahaan"].sum())
        workers = float(frame["jumlah_tk"].sum())
        output = float(frame["nilai_output"].sum())
        value_added = float(frame["nilai_tambah"].sum())
        rows.append(
            {
                "id": node_id,
                "label": label,
                "parent": parent,
                "level": level,
                "jumlah_perusahaan": companies,
                "jumlah_tk": workers,
                "nilai_output": output,
                "nilai_tambah": value_added,
                "nilai_tambah_per_pekerja": value_added / workers if workers else 0.0,
                "output_per_usaha": output / companies if companies else 0.0,
            }
        )

    if island == "Semua":
        root_id = "root::Indonesia"
        add_node(root_id, "Indonesia", "", "Indonesia", data)
        for pulau, pulau_df in data.groupby("pulau", sort=False):
            island_id = f"pulau::{pulau}"
            add_node(island_id, pulau, root_id, "Kelompok pulau", pulau_df)
            for provinsi, prov_df in pulau_df.groupby("provinsi", sort=False):
                province_id = f"provinsi::{pulau}::{provinsi}"
                add_node(province_id, provinsi, island_id, "Provinsi", prov_df)
                for _, leaf in prov_df.iterrows():
                    leaf_id = f"skala::{pulau}::{provinsi}::{leaf['skala']}"
                    add_node(leaf_id, str(leaf["skala"]), province_id, "Skala usaha", prov_df[prov_df["skala"] == leaf["skala"]])
    else:
        root_id = f"root::{island}"
        add_node(root_id, island, "", "Kelompok pulau", data)
        for provinsi, prov_df in data.groupby("provinsi", sort=False):
            province_id = f"provinsi::{island}::{provinsi}"
            add_node(province_id, provinsi, root_id, "Provinsi", prov_df)
            for _, leaf in prov_df.iterrows():
                leaf_id = f"skala::{island}::{provinsi}::{leaf['skala']}"
                add_node(leaf_id, str(leaf["skala"]), province_id, "Skala usaha", prov_df[prov_df["skala"] == leaf["skala"]])

    return pd.DataFrame(rows)


def hierarchy_treemap(hierarchy: pd.DataFrame, island: str = "Semua") -> go.Figure:
    nodes = _hierarchy_nodes(hierarchy, island)
    maxdepth = -1
    custom = np.column_stack(
        [
            nodes["level"],
            nodes["jumlah_perusahaan"],
            nodes["jumlah_tk"],
            nodes["nilai_output"],
            nodes["nilai_tambah"],
            nodes["nilai_tambah_per_pekerja"],
        ]
    )
    fig = go.Figure(
        go.Treemap(
            ids=nodes["id"],
            labels=nodes["label"],
            parents=nodes["parent"],
            values=nodes["jumlah_perusahaan"],
            branchvalues="total",
            maxdepth=maxdepth,
            customdata=custom,
            marker=dict(
                colors=nodes["nilai_tambah_per_pekerja"],
                colorscale=BLUE_PURPLE_SCALE,
                line=dict(color="#FFFFFF", width=1.2),
                colorbar=dict(
                    title=dict(text="Nilai tambah per pekerja<br>(juta rupiah/orang)", side="top"),
                    orientation="h",
                    x=0.5,
                    xanchor="center",
                    y=0.02,
                    yanchor="bottom",
                    len=0.48,
                    thickness=10,
                    tickformat=",.1f",
                    tickfont=dict(size=9),
                ),
            ),
            domain=dict(x=[0, 1], y=[0.17, 1]),
            root=dict(color="#F7F8FB"),
            textinfo="label",
            textfont=dict(size=13),
            hovertemplate=(
                "<b>%{label}</b><br>"
                "Tingkat: %{customdata[0]}<br>"
                "Jumlah usaha: %{customdata[1]:,.0f} unit<br>"
                "Tenaga kerja: %{customdata[2]:,.0f} orang<br>"
                "Nilai output: Rp %{customdata[3]:,.0f} juta<br>"
                "Nilai tambah: Rp %{customdata[4]:,.0f} juta<br>"
                "Nilai tambah per pekerja: Rp %{customdata[5]:,.2f} juta/orang"
                "<extra></extra>"
            ),
            pathbar=dict(visible=True, thickness=24, textfont=dict(size=11)),
            tiling=dict(packing="squarify", pad=2),
        )
    )
    fig.update_layout(uniformtext=dict(minsize=10, mode="hide"))
    return _base_layout(fig, height=545, margin=dict(l=10, r=10, t=12, b=12))


def hierarchy_sunburst(hierarchy: pd.DataFrame, island: str = "Semua") -> go.Figure:
    nodes = _hierarchy_nodes(hierarchy, island)
    maxdepth = -1
    custom = np.column_stack(
        [
            nodes["level"],
            nodes["jumlah_perusahaan"],
            nodes["jumlah_tk"],
            nodes["nilai_output"],
            nodes["output_per_usaha"],
        ]
    )
    fig = go.Figure(
        go.Sunburst(
            ids=nodes["id"],
            labels=nodes["label"],
            parents=nodes["parent"],
            values=nodes["jumlah_tk"],
            branchvalues="total",
            maxdepth=maxdepth,
            customdata=custom,
            marker=dict(
                colors=nodes["output_per_usaha"],
                colorscale=SOFT_AMBER_SCALE,
                line=dict(color="#FFFFFF", width=1.1),
                colorbar=dict(
                    title=dict(text="Output per usaha<br>(juta rupiah/unit)", side="top"),
                    orientation="h",
                    x=0.5,
                    xanchor="center",
                    y=0.02,
                    yanchor="bottom",
                    len=0.48,
                    thickness=10,
                    tickformat=",.1f",
                    tickfont=dict(size=9),
                ),
            ),
            domain=dict(x=[0.08, 0.92], y=[0.17, 1]),
            insidetextorientation="radial",
            textinfo="label",
            hovertemplate=(
                "<b>%{label}</b><br>"
                "Tingkat: %{customdata[0]}<br>"
                "Jumlah usaha: %{customdata[1]:,.0f} unit<br>"
                "Tenaga kerja: %{customdata[2]:,.0f} orang<br>"
                "Nilai output: Rp %{customdata[3]:,.0f} juta<br>"
                "Output per usaha: Rp %{customdata[4]:,.2f} juta/unit"
                "<extra></extra>"
            ),
        )
    )
    fig.update_layout(uniformtext=dict(minsize=10, mode="hide"))
    return _base_layout(fig, height=520, margin=dict(l=10, r=10, t=12, b=12))


def _discrete_colorscale(colors: list[str]) -> list[list]:
    if len(colors) == 1:
        return [[0.0, colors[0]], [1.0, colors[0]]]
    scale: list[list] = []
    n = len(colors)
    for i, color in enumerate(colors):
        left = i / n
        right = (i + 1) / n
        scale.extend([[left, color], [right, color]])
    return scale




def _classification_bins(values: pd.Series, method: str, k: int = 5) -> tuple[pd.Series, np.ndarray, list[str]]:
    """Return class codes, numeric bin edges, and Indonesian-formatted labels.

    Numeric bin edges are kept so the choropleth colorbar can use the actual
    percentage scale instead of equally spaced categorical positions.
    """
    vals = pd.to_numeric(values, errors="raise").astype(float)
    if method == "Quantile":
        codes, bins = pd.qcut(vals, q=k, labels=False, retbins=True, duplicates="drop")
    elif method == "Equal interval":
        lo, hi = float(vals.min()), float(vals.max())
        if np.isclose(lo, hi):
            bins = np.array([lo, hi])
            codes = pd.Series(np.zeros(len(vals), dtype=int), index=vals.index)
        else:
            bins = np.linspace(lo, hi, k + 1)
            codes = pd.cut(vals, bins=bins, labels=False, include_lowest=True)
    else:
        raise ValueError(f"Metode klasifikasi tidak dikenal: {method}")

    codes = pd.Series(codes, index=vals.index).fillna(0).astype(int)
    labels = [f"{a:.1f}–{b:.1f}%".replace(".", ",") for a, b in zip(bins[:-1], bins[1:])]
    return codes, np.asarray(bins, dtype=float), labels


def _stepped_colorscale_from_bins(bins: np.ndarray, colors: list[str]) -> list[list]:
    """Build a hard-stepped Plotly colorscale whose segment widths follow bin widths."""
    if len(colors) == 1 or len(bins) <= 2:
        color = colors[0]
        return [[0.0, color], [1.0, color]]
    lo, hi = float(bins[0]), float(bins[-1])
    if np.isclose(lo, hi):
        return [[0.0, colors[0]], [1.0, colors[0]]]
    positions = (bins - lo) / (hi - lo)
    scale: list[list] = []
    for i, color in enumerate(colors[: len(bins) - 1]):
        left = float(positions[i])
        right = float(positions[i + 1])
        scale.append([left, color])
        scale.append([right, color])
    return scale

def geospatial_map(
    map_df: pd.DataFrame,
    geojson: dict,
    quarter: str = "Triwulan II",
    classification: str = "Quantile",
    layer_mode: str = "Choropleth",
) -> tuple[go.Figure, list[str]]:
    data = map_df.copy()
    if quarter == "Triwulan I":
        share_col = "share_c_t1"
        sector_col = "sektorC_t1"
        pdrb_col = "pdrb_t1"
    else:
        share_col = "share_c_t2"
        sector_col = "sektorC_t2"
        pdrb_col = "pdrb_t2"

    class_code, bins, labels = _classification_bins(data[share_col], classification, k=5)
    data["class_code"] = class_code
    data["class_label"] = data["class_code"].map({i: label for i, label in enumerate(labels)})
    n_classes = len(labels)

    fig = go.Figure()
    if layer_mode == "Choropleth":
        # Classification is encoded as ordinal classes, not as a continuous percentage ramp.
        # This keeps each legend swatch equally legible. With Equal interval (the default),
        # every class also represents the same numerical percentage range, so high-contribution
        # districts stand out cleanly in the top classes.
        fig.add_trace(
            go.Choroplethmap(
                geojson=geojson,
                featureidkey="properties.kab_kota",
                locations=data["kab_kota"],
                z=data["class_code"],
                zmin=-0.5,
                zmax=max(0.5, n_classes - 0.5),
                colorscale=_discrete_colorscale(CIVIDIS_5[: max(1, n_classes)]),
                marker=dict(opacity=0.94, line=dict(width=0.42, color="#FFFFFF")),
                colorbar=dict(
                    title=dict(text="Kontribusi sektor C terhadap PDRB (%)", side="top"),
                    orientation="h",
                    tickmode="array",
                    tickvals=list(range(n_classes)),
                    ticktext=labels,
                    thickness=12,
                    len=0.64,
                    x=0.5,
                    xanchor="center",
                    y=1.01,
                    yanchor="bottom",
                    tickfont=dict(size=9),
                ),
                customdata=np.stack(
                    [data["provinsi"], data[share_col], data[sector_col], data[pdrb_col], data["class_label"]],
                    axis=-1,
                ),
                hovertemplate=(
                    "<b>%{location}</b><br>"
                    "Provinsi: %{customdata[0]}<br>"
                    "Kontribusi sektor C: %{customdata[1]:,.2f}%<br>"
                    "PDRB sektor C: Rp %{customdata[2]:,.2f} miliar<br>"
                    "PDRB total: Rp %{customdata[3]:,.2f} miliar<br>"
                    "Kelas: %{customdata[4]}"
                    "<extra></extra>"
                ),
                name="Kontribusi sektor C",
                showscale=True,
            )
        )
        labels_out = labels
    else:
        values = data[sector_col].astype(float)
        max_size = 34
        sizeref = 2.0 * values.max() / (max_size**2)
        fig.add_trace(
            go.Scattermap(
                lat=data["repr_lat"],
                lon=data["repr_lon"],
                mode="markers",
                marker=dict(
                    size=values,
                    sizemode="area",
                    sizeref=sizeref,
                    sizemin=3,
                    color=OKABE_ITO["vermillion"],
                    opacity=0.70,
                ),
                customdata=np.stack([data["kab_kota"], data["provinsi"], values, data[share_col]], axis=-1),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Provinsi: %{customdata[1]}<br>"
                    "PDRB sektor C: Rp %{customdata[2]:,.2f} miliar<br>"
                    "Kontribusi sektor C: %{customdata[3]:,.2f}%"
                    "<extra></extra>"
                ),
                name="Besaran PDRB sektor C",
                showlegend=False,
            )
        )
        labels_out = []

    fig.update_layout(
        map=dict(
            style="carto-positron",
            center=dict(lat=-2.3, lon=118.0),
            zoom=3.35,
            domain=dict(x=[0, 1], y=[0, 0.90] if layer_mode == "Choropleth" else [0, 1]),
        ),
        showlegend=False,
    )
    return _base_layout(fig, height=555, margin=dict(l=0, r=0, t=12, b=8)), labels_out


def top_contribution_bar(map_df: pd.DataFrame, quarter: str = "Triwulan II", n: int = 10) -> go.Figure:
    share_col = "share_c_t1" if quarter == "Triwulan I" else "share_c_t2"
    top = map_df.nlargest(n, share_col).sort_values(share_col)
    fig = go.Figure(
        go.Bar(
            x=top[share_col],
            y=top["kab_kota"],
            orientation="h",
            marker=dict(color=OKABE_ITO["blue"], line=dict(color="#FFFFFF", width=0.4)),
            customdata=top[["provinsi"]],
            text=top[share_col],
            texttemplate="%{text:,.1f}%",
            textposition="outside",
            cliponaxis=False,
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Provinsi: %{customdata[0]}<br>"
                "Kontribusi sektor C: %{x:,.2f}%"
                "<extra></extra>"
            ),
        )
    )
    upper = float(top[share_col].max()) * 1.10
    fig.update_xaxes(
        title=dict(text="Kontribusi sektor C terhadap PDRB (%)", standoff=10),
        range=[0, upper],
        gridcolor="#E9EDF2",
        zeroline=False,
        tickformat=",.0f",
    )
    fig.update_yaxes(title=None, automargin=True, tickfont=dict(size=12))
    return _base_layout(fig, height=440, margin=dict(l=145, r=42, t=18, b=58))
