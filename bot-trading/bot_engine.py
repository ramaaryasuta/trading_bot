"""
Mesin utama bot (orchestrator).

Rencana isi:
- Loop utama: ambil data dari exchange -> hitung sinyal via strategy ->
  eksekusi order via exchange -> simpan hasil via database.
- Manajemen risiko: ukuran posisi, stop loss, take profit, batas kerugian.
- Menjaga state posisi yang sedang terbuka.
- Logging aktivitas & penanganan error agar loop tidak mati.
"""

# TODO: implementasi bot engine
