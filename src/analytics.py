from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import leaves_list, linkage
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from .config import IMK_FEATURES, LOG_FEATURES


@dataclass(frozen=True)
class PCAResult:
    scores: pd.DataFrame
    loadings: pd.DataFrame
    standardized: pd.DataFrame
    explained_ratio: np.ndarray
    cluster_profiles: pd.DataFrame


def _analysis_matrix(df: pd.DataFrame) -> pd.DataFrame:
    x = df[list(IMK_FEATURES)].copy().astype(float)
    for col in LOG_FEATURES:
        x[col] = np.log1p(x[col])
    return x


def compute_pca_and_clusters(df: pd.DataFrame, n_clusters: int = 3) -> PCAResult:
    if len(df) < 34:
        raise ValueError("Analisis multivariat memerlukan sekurangnya 34 observasi.")
    if len(IMK_FEATURES) < 8:
        raise ValueError("Analisis multivariat memerlukan sekurangnya 8 variabel numerik.")

    x = _analysis_matrix(df)
    scaler = StandardScaler()
    z = scaler.fit_transform(x)

    pca = PCA(n_components=min(len(IMK_FEATURES), len(df)), random_state=42)
    pcs = pca.fit_transform(z)

    # Robust exploratory grouping: clip extreme standardized values only for K-Means so
    # a single extreme province does not define an entire cluster. PCA and outlier scores
    # still use the un-clipped standardized matrix.
    z_cluster = np.clip(z, -2.5, 2.5)
    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=50)
    labels = km.fit_predict(z_cluster)

    score_cols = [f"PC{i + 1}" for i in range(pcs.shape[1])]
    scores = pd.DataFrame(pcs, columns=score_cols, index=df.index)
    scores.insert(0, "provinsi", df["provinsi"].values)
    scores.insert(1, "pulau", df["pulau"].values)
    scores["cluster_id"] = labels + 1
    scores["cluster"] = scores["cluster_id"].map(lambda x: f"Cluster {x}")
    scores["jumlah_perusahaan_total"] = df["jumlah_perusahaan_total"].values

    # Distance from the multivariate center in standardized space; descriptive outlier score.
    scores["outlier_score"] = np.sqrt(np.square(z).sum(axis=1))
    scores["outlier_rank"] = scores["outlier_score"].rank(method="min", ascending=False).astype(int)

    standardized = pd.DataFrame(z, columns=list(IMK_FEATURES), index=df.index)
    standardized.insert(0, "provinsi", df["provinsi"].values)
    standardized.insert(1, "cluster", scores["cluster"].values)

    loadings = pd.DataFrame(
        pca.components_.T,
        index=list(IMK_FEATURES),
        columns=score_cols,
    )
    loadings["label"] = [IMK_FEATURES[idx] for idx in loadings.index]

    profile = pd.DataFrame(z, columns=list(IMK_FEATURES))
    profile["cluster_id"] = labels + 1
    cluster_profiles = profile.groupby("cluster_id").mean(numeric_only=True)
    cluster_profiles.index = [f"Cluster {i}" for i in cluster_profiles.index]

    return PCAResult(
        scores=scores,
        loadings=loadings,
        standardized=standardized,
        explained_ratio=pca.explained_variance_ratio_,
        cluster_profiles=cluster_profiles,
    )


def cluster_signature(cluster_profiles: pd.DataFrame, cluster_name: str, top_n: int = 3) -> str:
    row = cluster_profiles.loc[cluster_name]
    top = row.abs().sort_values(ascending=False).head(top_n).index.tolist()
    parts = []
    for col in top:
        direction = "tinggi" if row[col] >= 0 else "rendah"
        parts.append(f"{IMK_FEATURES[col].lower()} {direction}")
    return ", ".join(parts)


def clustered_heatmap_matrix(
    standardized: pd.DataFrame,
    provinces: list[str] | None = None,
) -> tuple[pd.DataFrame, list[str], list[str]]:
    z = standardized.copy()
    if provinces:
        z = z[z["provinsi"].isin(provinces)].copy()
    matrix = z.set_index("provinsi").drop(columns=["cluster"])

    if len(matrix) >= 2:
        row_order = leaves_list(linkage(matrix.values, method="ward", metric="euclidean"))
        matrix = matrix.iloc[row_order]
    if matrix.shape[1] >= 2:
        col_order = leaves_list(linkage(matrix.values.T, method="ward", metric="euclidean"))
        matrix = matrix.iloc[:, col_order]

    row_labels = matrix.index.tolist()
    col_labels = [IMK_FEATURES[c] for c in matrix.columns]
    return matrix, row_labels, col_labels


def build_hierarchy_long(df: pd.DataFrame) -> pd.DataFrame:
    records: list[dict] = []
    for _, r in df.iterrows():
        for scale, suffix in [("Mikro", "mikro"), ("Kecil", "kecil")]:
            companies = float(r[f"jumlah_perusahaan_{suffix}"])
            workers = float(r[f"jumlah_tk_{suffix}"])
            output = float(r[f"nilai_output_{suffix}"])
            value_added = float(r[f"nilai_tambah_{suffix}"])
            records.append(
                {
                    "root": "Indonesia",
                    "pulau": r["pulau"].title(),
                    "provinsi": r["provinsi"].title(),
                    "skala": scale,
                    "jumlah_perusahaan": companies,
                    "jumlah_tk": workers,
                    "nilai_output": output,
                    "nilai_tambah": value_added,
                    "nilai_tambah_per_pekerja": value_added / workers if workers else np.nan,
                    "output_per_usaha": output / companies if companies else np.nan,
                }
            )
    out = pd.DataFrame(records)
    if out[["jumlah_perusahaan", "jumlah_tk", "nilai_output", "nilai_tambah"]].isna().any().any():
        raise ValueError("Hierarchy menghasilkan nilai kosong tak terduga.")
    return out


def classify_values(series: pd.Series, method: str, k: int = 5) -> tuple[pd.Series, list[str]]:
    values = pd.to_numeric(series, errors="raise").astype(float)
    if method == "Quantile":
        codes, bins = pd.qcut(values, q=k, labels=False, retbins=True, duplicates="drop")
    elif method == "Equal interval":
        lo, hi = float(values.min()), float(values.max())
        if np.isclose(lo, hi):
            codes = pd.Series(np.zeros(len(values), dtype=int), index=values.index)
            bins = np.array([lo, hi])
        else:
            bins = np.linspace(lo, hi, k + 1)
            codes = pd.cut(values, bins=bins, labels=False, include_lowest=True)
    else:
        raise ValueError(f"Metode klasifikasi tidak dikenal: {method}")

    codes = pd.Series(codes, index=values.index).fillna(0).astype(int)
    labels: list[str] = []
    for a, b in zip(bins[:-1], bins[1:]):
        labels.append(f"{a:.1f}–{b:.1f}%".replace(".", ","))
    return codes, labels


def summarize_story(imk: pd.DataFrame, map_df: pd.DataFrame) -> dict:
    def top_row(col: str) -> pd.Series:
        return imk.loc[imk[col].idxmax()]

    t2_share_top = map_df.loc[map_df["share_c_t2"].idxmax()]
    growth_top = map_df.loc[map_df["growth_c_pct"].idxmax()]
    return {
        "internet_top": top_row("internet_pct")["provinsi"].title(),
        "internet_top_value": float(top_row("internet_pct")["internet_pct"]),
        "value_added_per_worker_top": top_row("nilai_tambah_per_usaha")["provinsi"].title(),
        "small_share_top": top_row("share_kecil")["provinsi"].title(),
        "map_share_top": str(t2_share_top["kab_kota"]),
        "map_share_top_value": float(t2_share_top["share_c_t2"]),
        "map_growth_top": str(growth_top["kab_kota"]),
        "map_growth_top_value": float(growth_top["growth_c_pct"]),
    }
