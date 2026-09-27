# Bot Trading Indodax

Bot trading crypto untuk exchange [Indodax](https://indodax.com), ditulis dalam Python.
Menggunakan `ccxt` untuk koneksi exchange, `pandas`/`numpy`/`ta` untuk analisis teknikal,
dan `streamlit` untuk dashboard monitoring.

> Status: tahap awal — baru kerangka project, belum ada logika bot.

## Struktur

| File | Fungsi |
|---|---|
| `config.py` | Memuat konfigurasi dari `.env` |
| `exchange.py` | Koneksi ke Indodax via ccxt |
| `strategy.py` | Indikator & sinyal trading |
| `bot_engine.py` | Loop utama bot & manajemen risiko |
| `database.py` | Penyimpanan riwayat trade & sinyal |
| `app.py` | Dashboard Streamlit |

## Setup

1. Buat virtual environment:

   ```bash
   python -m venv venv
   ```

2. Aktifkan venv:

   - Windows (PowerShell): `venv\Scripts\Activate.ps1`
   - Windows (cmd): `venv\Scripts\activate.bat`
   - Linux/macOS: `source venv/bin/activate`

3. Install dependency:

   ```bash
   pip install -r requirements.txt
   ```

4. Salin `.env.example` menjadi `.env`, lalu isi API key Indodax.
   **Jangan pernah commit file `.env`.**
