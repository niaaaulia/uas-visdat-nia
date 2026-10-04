# Data Dictionary

## 1. `data/raw/data_imk_fix.csv`

Satu baris = satu provinsi (38 observasi). Delimiter `;`.

| Kelompok | Variabel utama | Satuan / makna |
|---|---|---|
| Identitas | `pulau`, `provinsi` | kelompok pulau dan provinsi |
| Usaha | `jumlah_perusahaan_mikro`, `jumlah_perusahaan_kecil`, `jumlah_perusahaan_total` | unit |
| Tenaga kerja | `jumlah_tk_mikro`, `jumlah_tk_kecil`, `jumlah_tk_total` | orang |
| Input | `nilai_input_*` | juta rupiah |
| Output | `nilai_output_*` | juta rupiah |
| Nilai tambah | `nilai_tambah_*` | juta rupiah |
| Pengeluaran TK | `pengeluaran_tk_*` | juta rupiah |
| Internet | `internet_tidak`, `internet_ya` | banyak usaha |
| Pinjaman | `banyak_umk_pinjaman` | banyak usaha |
| Kemitraan | `umk_kemitraan_tidak`, `umk_kemitraan_ya` | banyak usaha |

### 9 indikator multivariat IMK

| Variabel analisis | Sumber/rumus | Perlakuan PCA |
|---|---|---|
| `jumlah_perusahaan_total` | jumlah perusahaan IMK | `log1p` + z-score |
| `jumlah_tk_total` | jumlah tenaga kerja IMK | `log1p` + z-score |
| `nilai_input_total` | nilai input IMK | `log1p` + z-score |
| `nilai_output_total` | nilai output IMK | `log1p` + z-score |
| `nilai_tambah_total` | nilai tambah IMK | `log1p` + z-score |
| `pengeluaran_tk_total` | pengeluaran tenaga kerja IMK | `log1p` + z-score |
| `internet_pct` | `internet_ya / (internet_ya + internet_tidak) × 100` | z-score |
| `pinjaman_pct` | `banyak_umk_pinjaman / jumlah_perusahaan_total × 100` | z-score |
| `kemitraan_pct` | `umk_kemitraan_ya / (ya + tidak) × 100` | z-score |

PDRB tidak dimasukkan ke PCA karena data PDRB tersedia pada unit kabupaten/kota, sedangkan observasi multivariat adalah provinsi.
