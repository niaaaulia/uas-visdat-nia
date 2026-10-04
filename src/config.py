from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
ASSETS = ROOT / "assets"

APP_TITLE = "Jejak Industri Mikro & Kecil Indonesia"
APP_SUBTITLE = (
    "Membandingkan profil IMK antarprovinsi dan jejak industri pengolahan di kabupaten/kota"
)
ACCESS_DATE = "4 Oktober 2026"

# Color system: color-blind friendly accents + softer editorial sequential scales.
OKABE_ITO = {
    "blue": "#0072B2",
    "orange": "#E69F00",
    "sky": "#56B4E9",
    "green": "#009E73",
    "yellow": "#F0E442",
    "vermillion": "#D55E00",
    "purple": "#CC79A7",
    "black": "#111827",
    "gray": "#9CA3AF",
}
CLUSTER_COLORS = [
    OKABE_ITO["blue"],
    OKABE_ITO["orange"],
    OKABE_ITO["green"],
    OKABE_ITO["purple"],
]

SOFT_BLUE_SCALE = ["#EEF3F8", "#C9D8E8", "#91AFCE", "#587FAE", "#2F5A8A"]
SOFT_TEAL_SCALE = ["#F1F7FA", "#D4DFEE", "#A7B7D5", "#7588B6", "#425B91"]
SOFT_AMBER_SCALE = ["#FFF4D6", "#F6D37A", "#E4AA42", "#C47A1C", "#8B4E08"]
SOFT_VIOLET_SCALE = ["#F3F4FA", "#D8DDEE", "#ADB7D8", "#7788B9", "#3F568E"]
BLUE_PURPLE_SCALE = ["#F3F4FA", "#D8DDEE", "#ADB7D8", "#7788B9", "#3F568E", "#273A6B"]
CIVIDIS_5 = ["#00204C", "#414D6B", "#7C7B78", "#BFAF6A", "#F6D547"]

NEUTRAL = {
    "ink": "#101828",
    "muted": "#667085",
    "line": "#E4E7EC",
    "paper": "#FAFBFC",
    "white": "#FFFFFF",
    "surface": "#F4F6F8",
}

IMK_FEATURES = {
    "jumlah_perusahaan_total": "Jumlah perusahaan",
    "jumlah_tk_total": "Tenaga kerja",
    "nilai_input_total": "Nilai input",
    "nilai_output_total": "Nilai output",
    "nilai_tambah_total": "Nilai tambah",
    "pengeluaran_tk_total": "Pengeluaran tenaga kerja",
    "internet_pct": "Pemanfaatan internet (%)",
    "pinjaman_pct": "Pemanfaatan pinjaman (%)",
    "kemitraan_pct": "Menjalin kemitraan (%)",
}

LOG_FEATURES = {
    "jumlah_perusahaan_total",
    "jumlah_tk_total",
    "nilai_input_total",
    "nilai_output_total",
    "nilai_tambah_total",
    "pengeluaran_tk_total",
}

SOURCES = {
    "imk_stat_tables": [
        (
            "Jumlah Perusahaan Industri Skala Mikro dan Kecil Menurut Provinsi (Unit), 2025",
            "https://www.bps.go.id/id/statistics-table/2/NDQwIzI=/jumlah-perusahaan-industri-skala-mikro-dan-kecil-menurut-provinsi--unit-.html",
        ),
        (
            "Jumlah Tenaga Kerja Industri Skala Mikro dan Kecil Menurut Provinsi (Orang), 2025",
            "https://www.bps.go.id/id/statistics-table/2/NDQxIzI=/jumlah-tenaga-kerja-industri-skala-mikro-dan-kecil-menurut-provinsi--orang-.html",
        ),
        (
            "Nilai Input Industri Skala Mikro dan Kecil Menurut Provinsi (Juta Rupiah), 2025",
            "https://www.bps.go.id/id/statistics-table/2/NDQyIzI=/nilai-input-industri-skala-mikro-dan-kecil-menurut-provinsi--juta-rupiah-.html",
        ),
        (
            "Nilai Output Industri Skala Mikro dan Kecil Menurut Provinsi (Juta Rupiah), 2025",
            "https://www.bps.go.id/id/statistics-table/2/NDQzIzI=/nilai-output-industri-skala-mikro-dan-kecil-menurut-provinsi--juta-rupiah-.html",
        ),
        (
            "Nilai Tambah (Harga Pasar) Industri Skala Mikro dan Kecil Menurut Provinsi (Juta Rupiah), 2025",
            "https://www.bps.go.id/id/statistics-table/2/NDQ0IzI=/nilai-tambah--harga-pasar--industri-skala-mikro-dan-kecil-menurut-provinsi--juta-rupiah-.html",
        ),
        (
            "Pengeluaran untuk Tenaga Kerja Industri Skala Mikro dan Kecil Menurut Provinsi (Juta Rupiah), 2025",
            "https://www.bps.go.id/id/statistics-table/2/NDQ2IzI=/pengeluaran-untuk-tenaga-kerja-industri-skala-mikro-dan-kecil-menurut-provinsi--juta-rupiah-.html",
        ),
    ],
    "imk_publication": (
        "Profil Industri Mikro dan Kecil 2025 — Tabel 30, 38, dan 48",
        "https://web-api.bps.go.id/download.php?f=XA23BDECIJTYc/3DhsJtyGgxU1JmaGI5UVFXWHZpOVFjLzMzdGFGaXpUSlZRQnR2a3BLWm11Q1RRTjBXSWNKZGt6RnFVYU0wRXNLaHE0bFVlZlkwdnhTd09DenVzRnNYamZzUkpNclZKNVREc09oR2NCQndTelV3RHRONmZaT2xMZFdSQWRzZW1TdjA0TXNybHh4ck5zZTVXZTlKMmhCNFBSUjQ3NHFzaERRY1J6dHFaeWJXZWRqQnUyaml2dC9zc0JGdktrYzFSZnB3eFhTTzF4UnNsdGMrN0dyTTcxREVYcDRKZFc2bjluTEpEQjgxVC8yTjVBMnZuR0xKTXdLcHNqLzU0c0pCT0Z0OTlqQ0c=",
    ),
    "pdrb": (
        "PDRB Triwulanan ADHB Menurut 17 Kategori Lapangan Usaha di Kabupaten/Kota, 2026",
        "https://www.bps.go.id/id/statistics-table/2/Mjc3NiMy/pdrb-triwulanan-atas-dasar-harga-berlaku-menurut-17-kategori-lapangan-usaha-di-kabupaten-kota--milyar-rupiah-.html",
    ),
    "boundary": (
        "Batas Kabupaten/Kota Indonesia — LapakGIS (diolah dan disederhanakan)",
        "https://www.lapakgis.com/2022/01/shp-batas-kabupaten-kota-indonesia.html",
    ),
}

PLOTLY_CONFIG = {
    "displaylogo": False,
    "responsive": True,
    "scrollZoom": False,
}
