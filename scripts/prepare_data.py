from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.geometry import shape

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)


def parse_id_number(series: pd.Series) -> pd.Series:
    """Parse Indonesian decimal strings like '1.234,56' or '1234,56'."""
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="raise")
    cleaned = (
        series.astype(str)
        .str.strip()
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    return pd.to_numeric(cleaned, errors="raise")


def safe_ratio(num: pd.Series, den: pd.Series, scale: float = 1.0) -> pd.Series:
    den = den.replace(0, np.nan)
    out = num / den * scale
    if out.isna().any():
        raise ValueError("Ratio menghasilkan NA/inf; periksa denominator bernilai nol.")
    return out


def prepare_imk() -> tuple[pd.DataFrame, dict]:
    path = RAW / "data_imk_fix.csv"
    df = pd.read_csv(path, sep=";")
    df.columns = [c.strip() for c in df.columns]
    df["pulau"] = df["pulau"].astype(str).str.strip().str.upper()
    df["provinsi"] = df["provinsi"].astype(str).str.strip().str.upper()

    if len(df) != 38:
        raise AssertionError(f"IMK diharapkan 38 provinsi, ditemukan {len(df)}")
    if df["provinsi"].duplicated().any():
        raise AssertionError("Nama provinsi duplikat pada data IMK.")

    numeric_cols = [c for c in df.columns if c not in {"pulau", "provinsi"}]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="raise")
    if (df[numeric_cols] < 0).any().any():
        raise AssertionError("Terdapat nilai negatif tak terduga pada data IMK.")

    additive_checks = [
        ("jumlah_perusahaan_total", "jumlah_perusahaan_mikro", "jumlah_perusahaan_kecil"),
        ("jumlah_tk_total", "jumlah_tk_mikro", "jumlah_tk_kecil"),
        ("nilai_input_total", "nilai_input_mikro", "nilai_input_kecil"),
        ("nilai_output_total", "nilai_output_mikro", "nilai_output_kecil"),
        ("nilai_tambah_total", "nilai_tambah_mikro", "nilai_tambah_kecil"),
        ("pengeluaran_tk_total", "pengeluaran_tk_mikro", "pengeluaran_tk_kecil"),
    ]
    additive_ok = {}
    for total, mikro, kecil in additive_checks:
        ok = bool((df[total] == df[mikro] + df[kecil]).all())
        additive_ok[total] = ok
        if not ok:
            raise AssertionError(f"{total} tidak konsisten dengan {mikro} + {kecil}.")

    # Normalized rates used in the 9-indicator PCA plus supporting metrics used elsewhere in the story.
    df["usaha_total"] = df["jumlah_perusahaan_total"]
    df["tk_total"] = df["jumlah_tk_total"]
    df["output_total"] = df["nilai_output_total"]
    df["nilai_tambah_total_ind"] = df["nilai_tambah_total"]
    df["pekerja_per_usaha"] = safe_ratio(df["jumlah_tk_total"], df["jumlah_perusahaan_total"])
    df["output_per_pekerja"] = safe_ratio(df["nilai_output_total"], df["jumlah_tk_total"])
    df["nilai_tambah_per_usaha"] = safe_ratio(df["nilai_tambah_total"], df["jumlah_perusahaan_total"])
    df["rasio_output_input"] = safe_ratio(df["nilai_output_total"], df["nilai_input_total"])
    df["share_kecil"] = safe_ratio(df["jumlah_perusahaan_kecil"], df["jumlah_perusahaan_total"], 100)
    df["internet_pct"] = safe_ratio(df["internet_ya"], df["internet_ya"] + df["internet_tidak"], 100)
    df["pinjaman_pct"] = safe_ratio(df["banyak_umk_pinjaman"], df["jumlah_perusahaan_total"], 100)
    df["kemitraan_pct"] = safe_ratio(
        df["umk_kemitraan_ya"], df["umk_kemitraan_ya"] + df["umk_kemitraan_tidak"], 100
    )
    df["upah_per_pekerja"] = safe_ratio(df["pengeluaran_tk_total"], df["jumlah_tk_total"])

    # Small ±1 differences in publication-derived internet/partnership totals are retained and documented.
    internet_diff = (df["internet_ya"] + df["internet_tidak"] - df["jumlah_perusahaan_total"]).astype(int)
    partnership_diff = (
        df["umk_kemitraan_ya"] + df["umk_kemitraan_tidak"] - df["jumlah_perusahaan_total"]
    ).astype(int)

    out_path = OUT / "imk_analysis.csv"
    df.to_csv(out_path, index=False)

    audit = {
        "rows": int(len(df)),
        "unique_provinces": int(df["provinsi"].nunique()),
        "missing_values": int(df.isna().sum().sum()),
        "additive_checks": additive_ok,
        "internet_denominator_difference_min": int(internet_diff.min()),
        "internet_denominator_difference_max": int(internet_diff.max()),
        "partnership_denominator_difference_min": int(partnership_diff.min()),
        "partnership_denominator_difference_max": int(partnership_diff.max()),
    }
    return df, audit


def prepare_pdrb_and_boundary() -> tuple[pd.DataFrame, dict]:
    pdrb_path = RAW / "data_pdrb_kabkota.csv"
    boundary_path = RAW / "batas_kabkota_indonesia_simplify.geojson"

    pdrb = pd.read_csv(pdrb_path, sep=";")
    pdrb.columns = [c.strip() for c in pdrb.columns]
    pdrb["kab_kota"] = pdrb["kab_kota"].astype(str).str.strip()
    for c in ["sektorC_t1", "sektorC_t2", "pdrb_t1", "pdrb_t2"]:
        pdrb[c] = parse_id_number(pdrb[c])

    if len(pdrb) != 514 or pdrb["kab_kota"].nunique() != 514:
        raise AssertionError("Data PDRB harus berisi 514 kabupaten/kota unik.")
    if (pdrb[["sektorC_t1", "sektorC_t2", "pdrb_t1", "pdrb_t2"]] <= 0).any().any():
        raise AssertionError("PDRB/sektor C mengandung nilai nol atau negatif tak terduga.")

    pdrb["share_c_t1"] = safe_ratio(pdrb["sektorC_t1"], pdrb["pdrb_t1"], 100)
    pdrb["share_c_t2"] = safe_ratio(pdrb["sektorC_t2"], pdrb["pdrb_t2"], 100)
    pdrb["growth_c_pct"] = (pdrb["sektorC_t2"] / pdrb["sektorC_t1"] - 1) * 100
    pdrb["growth_pdrb_pct"] = (pdrb["pdrb_t2"] / pdrb["pdrb_t1"] - 1) * 100

    with boundary_path.open("r", encoding="utf-8") as f:
        geo = json.load(f)

    features = geo.get("features", [])
    if len(features) != 513:
        raise AssertionError(f"Boundary diharapkan 513 feature, ditemukan {len(features)}")

    boundary_rows: list[dict] = []
    clean_features: list[dict] = []
    invalid_geometry: list[str] = []
    empty_geometry: list[str] = []

    for ft in features:
        props = ft.get("properties") or {}
        kab = str(props.get("WADMKK") or "").strip()
        prov = str(props.get("WADMPR") or "").strip()
        if not kab:
            raise AssertionError("Masih ada feature boundary tanpa WADMKK.")
        geom = shape(ft["geometry"])
        if geom.is_empty:
            empty_geometry.append(kab)
        if not geom.is_valid:
            invalid_geometry.append(kab)
        rp = geom.representative_point()
        boundary_rows.append(
            {
                "kab_kota": kab,
                "provinsi": prov,
                "repr_lon": float(rp.x),
                "repr_lat": float(rp.y),
            }
        )
        clean_features.append(
            {
                "type": "Feature",
                "properties": {"kab_kota": kab, "provinsi": prov},
                "geometry": ft["geometry"],
            }
        )

    boundary_df = pd.DataFrame(boundary_rows)
    if boundary_df["kab_kota"].duplicated().any():
        dup = boundary_df.loc[boundary_df["kab_kota"].duplicated(), "kab_kota"].tolist()
        raise AssertionError(f"WADMKK duplikat setelah preprocessing: {dup}")
    if invalid_geometry or empty_geometry:
        raise AssertionError(
            f"Geometry invalid={invalid_geometry[:5]}, geometry empty={empty_geometry[:5]}"
        )

    boundary_names = set(boundary_df["kab_kota"])
    pdrb_names = set(pdrb["kab_kota"])
    missing_geometry = sorted(pdrb_names - boundary_names)
    boundary_without_pdrb = sorted(boundary_names - pdrb_names)

    # This project intentionally keeps the 513 valid geometries and documents the single missing unit.
    expected_missing = ["Sumbawa"]
    if missing_geometry != expected_missing:
        raise AssertionError(
            "Mismatch boundary/PDRB berubah. "
            f"PDRB tanpa geometry={missing_geometry}; boundary tanpa PDRB={boundary_without_pdrb}"
        )
    if boundary_without_pdrb:
        raise AssertionError(f"Boundary tanpa pasangan PDRB: {boundary_without_pdrb}")

    map_df = boundary_df.merge(pdrb, on="kab_kota", how="left", validate="one_to_one")
    if map_df[["sektorC_t1", "sektorC_t2", "pdrb_t1", "pdrb_t2"]].isna().any().any():
        raise AssertionError("Ada boundary yang gagal mendapat data PDRB.")

    map_df.to_csv(OUT / "pdrb_map.csv", index=False)
    pdrb.loc[pdrb["kab_kota"].isin(missing_geometry)].to_csv(
        OUT / "pdrb_without_geometry.csv", index=False
    )

    clean_geo = {"type": "FeatureCollection", "features": clean_features}
    with (OUT / "boundary_513.geojson").open("w", encoding="utf-8") as f:
        json.dump(clean_geo, f, ensure_ascii=False, separators=(",", ":"))

    audit = {
        "pdrb_rows": int(len(pdrb)),
        "pdrb_unique_kabkota": int(pdrb["kab_kota"].nunique()),
        "boundary_features": int(len(boundary_df)),
        "boundary_unique_kabkota": int(boundary_df["kab_kota"].nunique()),
        "matched_map_units": int(len(map_df)),
        "pdrb_without_geometry": missing_geometry,
        "boundary_without_pdrb": boundary_without_pdrb,
        "invalid_geometry_count": len(invalid_geometry),
        "empty_geometry_count": len(empty_geometry),
    }
    return map_df, audit


def main() -> None:
    _, imk_audit = prepare_imk()
    _, geo_audit = prepare_pdrb_and_boundary()
    quality = {
        "status": "PASS",
        "imk": imk_audit,
        "geospatial": geo_audit,
        "notes": [
            "Boundary final berisi 513 geometri valid dan unik.",
            "Data PDRB BPS berisi 514 kabupaten/kota; Kabupaten Sumbawa dipertahankan di data tabular tetapi tidak ditampilkan pada peta karena geometri tidak tersedia pada boundary yang digunakan.",
            "Join peta dilakukan secara exact match pada nama kabupaten/kota yang sudah direkonsiliasi saat preprocessing. Untuk pengembangan lanjutan, kode wilayah BPS tetap lebih disarankan sebagai key permanen.",
        ],
    }
    with (OUT / "data_quality.json").open("w", encoding="utf-8") as f:
        json.dump(quality, f, ensure_ascii=False, indent=2)
    print(json.dumps(quality, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
