# Methodology Notes

## Prinsip desain

Aplikasi diposisikan sebagai **web story**, bukan dashboard operasional. Urutan naratif tetap—multivariat, hierarki, geospasial—tetapi pengguna dapat melakukan seleksi, drill-down, filter, dan zoom di setiap bab. Tidak ada custom component berbasis iframe; halaman menggunakan satu scroll surface milik browser.

## Multivariat

- Unit analisis: 38 provinsi.
- 9 indikator numerik IMK: jumlah perusahaan, tenaga kerja, nilai input, nilai output, nilai tambah, pengeluaran tenaga kerja, persentase pemanfaatan internet, persentase pemanfaatan pinjaman, dan persentase kemitraan.
- Magnitude/right-skewed: `log1p` sebelum standardisasi.
- Semua indikator: `StandardScaler`.
- PCA: reduksi dimensi untuk scatter dua komponen pertama.
- K-Means: tiga kelompok eksploratif. Standardized values di-clip ±2,5 **hanya pada clustering** agar pencilan tunggal tidak mendominasi centroid. PCA, heatmap, parallel coordinates, dan outlier score memakai standardized matrix asli.
- Outlier score: jarak Euclidean dari origin di ruang standardized 9 indikator. Ini ukuran deskriptif, bukan uji statistik formal.
- Brushing & linking: lasso/box selection pada PCA mengubah highlight parallel coordinates dan subset heatmap.
- Heatmap: hierarchical clustering Ward untuk ordering baris/kolom.
- Radar: percentile rank antar-38 provinsi agar sumbu dengan satuan berbeda dapat dibandingkan secara visual.

## Hierarki

Empat level: `Indonesia → kelompok pulau → provinsi → skala mikro/kecil`.

- Treemap: area = jumlah perusahaan; warna = nilai tambah per pekerja.
- Sunburst: sudut/luas sektor = jumlah tenaga kerja; warna = output per usaha.
- Pada tampilan nasional, struktur penuh adalah `Indonesia → pulau → provinsi → skala`; ketika satu pulau difilter, root Indonesia dihilangkan sehingga menjadi `pulau → provinsi → skala`.
- Treemap memakai pathbar/breadcrumb; sunburst mempertahankan relasi induk-anak secara radial.

Interpretasi area dilakukan untuk dominasi besar, bukan perbandingan selisih kecil.

## Geospasial

- PDRB: 514 kabupaten/kota.
- Boundary: 513 geometry valid, unique, exact-match; Sumbawa tanpa geometry.
- Choropleth: `sektor C / PDRB total × 100` sehingga warna mengkode rasio, bukan nilai absolut.
- Proportional symbol: nilai sektor C absolut (miliar rupiah); marker menggunakan `sizemode='area'` sehingga area simbol proporsional terhadap nilai.
- Quantile: default, berguna ketika distribusi sangat skewed dan tujuan utamanya membaca peringkat/pola regional.
- Equal interval: alternatif untuk mempertahankan interval numerik sama.
- Palet sequential lembut digunakan untuk nilai numerik pada hierarki dan peta; Okabe–Ito dipakai untuk kategori/highlight.
- Seluruh layout memakai satu scroll surface dan chart Plotly responsif terhadap lebar container.

## Keterbatasan

1. Boundary bukan data utama BPS dan saat ini tidak memuat geometry Kabupaten Sumbawa.
2. Join deployment memakai nama kabupaten/kota yang sudah direkonsiliasi. Untuk pipeline institusional jangka panjang, kode wilayah BPS lebih kuat sebagai primary key.
3. Tabel PDRB hanya membandingkan dua triwulan pada 2026; pertumbuhan jangka sangat pendek dapat dipengaruhi efek basis/seasonality.
4. Cluster dan outlier bersifat eksploratif, tidak boleh diberi interpretasi kausal atau normatif.
5. Rasio internet/kemitraan dari tabel publikasi memiliki perbedaan denominator ±1 unit terhadap total usaha pada sebagian provinsi; nilai asli dipertahankan dan denominator masing-masing indikator digunakan dalam perhitungan persentase.
