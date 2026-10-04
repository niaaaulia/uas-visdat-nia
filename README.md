# Jejak Industri Mikro & Kecil Indonesia (Streamlit Scrollytelling)

Web story interaktif untuk proyek UAS Visualisasi Data dan Informasi. Aplikasi menggabungkan **tiga topik** yaitu: **data berdimensi tinggi (multivariat), data berhierarki, dan data geospasial**.

## Kenapa arsitekturnya seperti ini?

Proyek menggunakan **Streamlit + Plotly** dengan satu halaman panjang, navigasi editorial yang selalu terlihat, dan satu permukaan scroll browser. Semua chart adalah native `st.plotly_chart`; **tidak ada `components.html()` / iframe custom**, sehingga tidak tercipta scrollbar kedua. Bab multivariat memakai visual full-width agar seleksi dan label terbaca lega, sedangkan bab hierarki/geospasial tetap dapat memakai sticky visual pada desktop. Setiap bab interaktif dibungkus `st.fragment`, sehingga interaksi tidak merender ulang seluruh halaman.

### Fitur utama

- PCA 9 indikator IMK / 38 provinsi.
- K-Means eksploratif tiga cluster + outlier score.
- **Brushing & linking**: lasso/box selection pada PCA → parallel coordinates + clustered heatmap.
- Radar persentil untuk profil provinsi; daftar provinsinya mengikuti seleksi PCA.
- Hierarki level: pulau → provinsi → skala usaha.
- Treemap + sunburst dengan **size dan color untuk dua variabel berbeda**.
- Choropleth kontribusi sektor C (%) + proportional symbols nilai sektor C (miliar rupiah).
- Quantile / equal interval classification.
- Tooltip, legend, pan/zoom, layer control, quarter filter.
- Palet **Okabe–Ito + Cividis**.
- Source disclosure di setiap visualisasi.
- Data-quality audit dan automated checks.

---

## Struktur proyek

```text
vdi_imk_streamlit_story/
├── app.py
├── requirements.txt
├── requirements-dev.txt
├── README.md
├── PROJECT_STRUCTURE.txt
├── .gitignore
├── .streamlit/
│   └── config.toml
├── assets/
│   └── style.css
├── data/
│   ├── raw/
│   │   ├── data_imk_fix.csv
│   │   ├── data_pdrb_kabkota.csv
│   │   └── batas_kabkota_indonesia_simplify.geojson
│   └── processed/
│       ├── imk_analysis.csv
│       ├── pdrb_map.csv
│       ├── pdrb_without_geometry.csv
│       ├── boundary_513.geojson
│       └── data_quality.json
├── docs/
│   ├── data_dictionary.md
│   └── methodology.md
├── scripts/
│   ├── prepare_data.py
│   └── check_project.py
├── src/
│   ├── __init__.py
│   ├── analytics.py
│   ├── config.py
│   ├── data.py
│   ├── figures.py
│   └── ui.py
└── tests/
    ├── conftest.py
    └── test_data_contract.py
```

---

## Menjalankan aplikasi

Disarankan Python 3.11 atau 3.12.

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
python scripts/prepare_data.py
python scripts/check_project.py
streamlit run app.py
```

Aplikasi akan tersedia pada alamat lokal yang ditampilkan Streamlit, biasanya `http://localhost:8501`.

> `scripts/prepare_data.py` bersifat deterministic: data raw → data processed → audit JSON. Commit `data/processed/` ke repositori agar deployment tidak perlu memproses GeoJSON setiap startup.

---

## Deployment ke Streamlit Community Cloud

1. Buat repository GitHub publik dan commit seluruh folder proyek.
2. Pastikan `requirements.txt`, `.streamlit/config.toml`, `app.py`, dan `data/processed/` ikut di-commit.
3. Pada Streamlit Community Cloud, pilih repository/branch.
4. Main file: `app.py`.
5. Deploy.
6. Uji pada desktop dan mobile serta pastikan semua source link dan tooltip berfungsi.

Tidak ada API key atau secret untuk aplikasi ini.

---

## Data audit yang sudah dilakukan

Output `data/processed/data_quality.json` saat ini:

- IMK: **38 provinsi unik**, tanpa missing value.
- Seluruh total mikro+kecil untuk jumlah perusahaan, tenaga kerja, input, output, nilai tambah, dan pengeluaran tenaga kerja **konsisten secara aritmetis**.
- PDRB: **514 kabupaten/kota unik**.
- Boundary: **513 feature unik**, invalid geometry = **0**, empty geometry = **0**.
- Semua 513 boundary exact-match ke PDRB.
- PDRB tanpa geometry: **Kabupaten Sumbawa**.

Jangan menghapus Kabupaten Sumbawa dari data PDRB. Aplikasi secara eksplisit menyatakan cakupan peta 513/514.

---

## Pemenuhan ketentuan topik

### 1) Data berdimensi tinggi

| Ketentuan | Implementasi |
|---|---|
| ≥8 variabel numerik, ≥34 observasi | 9 indikator IMK, 38 provinsi |
| Reduksi dimensi | PCA |
| ≥2 teknik lain | parallel coordinates, clustered heatmap, radar |
| Brushing & linking | seleksi PCA menautkan parallel coordinates + heatmap + pilihan radar |
| Kelompok/pencilan | K-Means 3 cluster + outlier score |

### 2) Struktur hierarki IMK

| Ketentuan | Implementasi |
|---|---|
| ≥3 level | 4 level: Indonesia → pulau → provinsi → skala |
| ≥2 representasi | treemap + sunburst |
| size/color berbeda | treemap: perusahaan vs nilai tambah/pekerja; sunburst: tenaga kerja vs output/usaha |
| drill-down/breadcrumb | native Plotly zoom + treemap pathbar |

### 3) Jejak spasial industri pengolahan

| Ketentuan | Implementasi |
|---|---|
| tingkat kab/kota ±500 | 514 geometry |
| ≥2 peta | choropleth + proportional symbols |
| choropleth rasio | kontribusi sektor C / PDRB total (%) |
| klasifikasi | quantile (default) + equal interval |
| interaksi | tooltip, legend, pan/zoom, tipe peta, periode, dan klasifikasi |

---

## Mengapa choropleth memakai kontribusi, bukan sektor C absolut?

Nilai absolut akan sangat dipengaruhi ukuran ekonomi kabupaten/kota. Karena itu warna mengkodekan:

```text
kontribusi sektor C (%) = PDRB sektor C / PDRB total × 100

Periode geospasial yang digunakan adalah **Triwulan I dan Triwulan II tahun 2026**.
```

Nilai absolut sektor C tetap ditampilkan melalui **peta simbol proporsional**, sehingga pembaca bisa membedakan:

- wilayah yang **besar secara nominal**, dan
- wilayah yang **sangat terspesialisasi pada industri pengolahan**.

---

## Catatan metodologi PCA

PCA memakai **9 indikator IMK**. Enam indikator magnitude—jumlah perusahaan, tenaga kerja, nilai input, nilai output, nilai tambah, dan pengeluaran tenaga kerja—ditransformasi `log1p`. Tiga indikator adopsi—internet, pinjaman, dan kemitraan—dipakai sebagai persentase. Setelah itu seluruh indikator distandardisasi dengan z-score.

K-Means hanya dipakai sebagai bantuan membaca pola. Standardized values di-clip ±2,5 **hanya pada tahap K-Means** agar pencilan ekstrem tidak membentuk cluster tunggal. PCA, heatmap, parallel coordinates, dan outlier score tetap menggunakan nilai standardized asli.

Lihat `docs/methodology.md` untuk uraian lengkap.

---

## Sumber

Data utama bersumber dari **Badan Pusat Statistik (BPS)**:

- enam tabel statistik IMK 2025: jumlah perusahaan, tenaga kerja, input, output, nilai tambah, pengeluaran tenaga kerja;
- *Profil Industri Mikro dan Kecil 2025*, khususnya Tabel 30 (pinjaman), Tabel 38 (kemitraan), Tabel 48 (internet);
- PDRB Triwulanan ADHB menurut 17 kategori lapangan usaha kabupaten/kota 2026, kategori C dan PDRB total untuk Triwulan I dan II.

Boundary kabupaten/kota merupakan data pendukung non-BPS dari LapakGIS yang telah direkonsiliasi dan disederhanakan penulis. URL lengkap sumber disimpan di `src/config.py` dan ditampilkan pada setiap visualisasi. Tanggal akses default aplikasi: 4 Oktober 2026.

---

## Pengujian sebelum submit

```bash
python scripts/prepare_data.py
python scripts/check_project.py
```

Jika memasang development dependencies:

```bash
pip install -r requirements-dev.txt
pytest -q
```

Target akhir:

```text
38 provinsi IMK unik                  PASS
513 unit peta unik                    PASS
GeoJSON 513 feature                   PASS
Hanya Sumbawa tanpa geometri          PASS
PC1+PC2 > 50% variasi                 PASS
3 cluster eksploratif                 PASS
Agregat hierarki konsisten            PASS
Core Plotly figures serializable      PASS
No iframe custom component            PASS
```

---

## Penulisan makalah

Dalam makalah, hindari menyebut cluster sebagai kategori resmi atau menyimpulkan hubungan kausal. Gunakan bahasa seperti **"secara deskriptif", "pada data ini", "menunjukkan pola", "berasosiasi secara visual"**.

Keterbatasan yang sebaiknya disebutkan:

1. satu kabupaten (Sumbawa) tidak memiliki geometry pada boundary final;
2. join deployment masih memakai nama kabupaten/kota yang telah direkonsiliasi, bukan kode BPS permanen;
3. PDRB hanya dua triwulan sehingga pertumbuhan dapat dipengaruhi seasonality dan base effect;
4. cluster/outlier bersifat eksploratif;
5. boundary merupakan data pendukung non-BPS.

Penggunaan AI untuk membantu kode/desain harus dideklarasikan dalam Metodologi sesuai ketentuan tugas. Penulis tetap bertanggung jawab untuk memahami dan mendemonstrasikan setiap transformasi serta visualisasi.

## Responsif

Layout menggunakan breakpoint CSS untuk desktop, tablet, dan ponsel. Navigasi tetap dapat digulir horizontal pada layar sangat sempit; kolom cerita, kontrol, dan insight ditumpuk menjadi satu kolom pada ponsel; seluruh Plotly chart menggunakan `use_container_width=True` dan konfigurasi responsive.
