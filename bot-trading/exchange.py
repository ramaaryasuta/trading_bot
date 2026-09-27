"""
Lapisan koneksi ke exchange Indodax (via ccxt).

Tahap saat ini: HANYA data publik (tanpa API key).
- get_ticker(pair)                  -> harga terkini
- get_ohlcv(pair, timeframe, limit) -> candlestick historis (DataFrame)

Semua error dari ccxt/jaringan diubah menjadi ExchangeDataError dengan
pesan yang mudah dipahami.

Rencana berikutnya:
- Ambil saldo akun, kirim / batalkan order, cek status order
  (butuh API key dari config).
- Dukungan mode DRY_RUN (simulasi order tanpa mengirim ke exchange).
"""

import time

import ccxt
import pandas as pd

# ccxt belum memetakan timeframe 5m untuk Indodax, padahal endpoint
# tradingview Indodax menerimanya (tf=5).
EXTRA_TIMEFRAMES = {"5m": "5"}

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2

_exchange = None


class ExchangeDataError(Exception):
    """Error saat mengambil data dari Indodax, dengan pesan yang mudah dipahami."""


def _get_exchange():
    """Buat client ccxt Indodax sekali saja, lalu pakai ulang."""
    global _exchange
    if _exchange is None:
        exchange = ccxt.indodax({"enableRateLimit": True, "timeout": 15000})
        exchange.timeframes = {**exchange.timeframes, **EXTRA_TIMEFRAMES}
        _exchange = exchange
    return _exchange


def _call(func, *args, **kwargs):
    """
    Jalankan pemanggilan ccxt dengan retry untuk gangguan sementara
    (timeout, rate limit, server down), dan terjemahkan exception
    menjadi ExchangeDataError.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return func(*args, **kwargs)
        except ccxt.BadSymbol as e:
            raise ExchangeDataError(f"Pair tidak ditemukan di Indodax. ({e})") from e
        except ccxt.NetworkError as e:
            # Mencakup RateLimitExceeded, OnMaintenance, ExchangeNotAvailable,
            # RequestTimeout, dan koneksi internet gagal.
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS * attempt)
                continue
            raise ExchangeDataError(_network_error_message(e)) from e
        except ccxt.ExchangeError as e:
            raise ExchangeDataError(f"Indodax menolak permintaan: {e}") from e


def _network_error_message(e):
    if isinstance(e, ccxt.RateLimitExceeded):
        reason = "Terlalu banyak permintaan (rate limit). Tunggu sebentar lalu coba lagi."
    elif isinstance(e, ccxt.DDoSProtection):
        reason = "Permintaan diblokir sementara oleh proteksi Indodax. Tunggu beberapa menit."
    elif isinstance(e, ccxt.OnMaintenance):
        reason = "Indodax sedang maintenance."
    elif isinstance(e, ccxt.ExchangeNotAvailable):
        reason = "Server Indodax sedang down atau tidak merespons dengan benar."
    elif isinstance(e, ccxt.RequestTimeout):
        reason = "Koneksi ke Indodax timeout. Cek koneksi internet atau coba lagi."
    else:
        reason = "Gagal terhubung ke Indodax. Cek koneksi internet Anda."
    return f"{reason} (gagal setelah {MAX_RETRIES}x percobaan)"


def _resolve_symbol(pair):
    """
    Ubah pair gaya Indodax ("btc_idr", "btcidr") atau gaya ccxt ("BTC/IDR")
    menjadi simbol ccxt yang valid.
    """
    exchange = _get_exchange()
    _call(exchange.load_markets)

    market_id = pair.strip().lower().replace("_", "").replace("/", "")
    markets = exchange.markets_by_id.get(market_id)
    if not markets:
        raise ExchangeDataError(
            f"Pair '{pair}' tidak ditemukan di Indodax. "
            f"Contoh format yang benar: 'btc_idr', 'eth_idr'."
        )
    return markets[0]["symbol"]


def get_ticker(pair):
    """
    Ambil harga terkini untuk sebuah pair.

    Args:
        pair: contoh "btc_idr" (juga menerima "BTC/IDR").

    Returns:
        dict berisi pair, symbol, last, bid, ask, high, low,
        volume_24h (koin), volume_24h_quote (IDR), timestamp (UTC).

    Raises:
        ExchangeDataError: pair tidak ada, koneksi gagal, atau API bermasalah.
    """
    symbol = _resolve_symbol(pair)
    ticker = _call(_get_exchange().fetch_ticker, symbol)
    return {
        "pair": pair,
        "symbol": symbol,
        "last": ticker["last"],
        "bid": ticker["bid"],
        "ask": ticker["ask"],
        "high": ticker["high"],
        "low": ticker["low"],
        "volume_24h": ticker["baseVolume"],
        "volume_24h_quote": ticker["quoteVolume"],
        "timestamp": pd.to_datetime(ticker["timestamp"], unit="ms", utc=True),
    }


def get_ohlcv(pair, timeframe="5m", limit=100):
    """
    Ambil data candlestick historis.

    Args:
        pair: contoh "btc_idr".
        timeframe: "1m", "5m", "15m", "30m", "1h", "4h", "1d", "3d", "1w".
        limit: jumlah candle terakhir yang diambil.

    Returns:
        pandas DataFrame dengan kolom timestamp (UTC), open, high, low,
        close, volume, urut dari lama ke baru. Candle terakhir biasanya
        masih berjalan (belum close).

    Raises:
        ExchangeDataError: pair/timeframe tidak valid, koneksi gagal,
        atau API bermasalah.
    """
    exchange = _get_exchange()
    if timeframe not in exchange.timeframes:
        raise ExchangeDataError(
            f"Timeframe '{timeframe}' tidak didukung Indodax. "
            f"Pilihan: {', '.join(exchange.timeframes)}."
        )
    if limit < 1:
        raise ExchangeDataError("limit harus minimal 1.")

    symbol = _resolve_symbol(pair)
    candles = _call(exchange.fetch_ohlcv, symbol, timeframe, limit=limit)

    df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    return df.tail(limit).reset_index(drop=True)


if __name__ == "__main__":
    def rupiah(value):
        return "Rp " + f"{value:,.0f}".replace(",", ".")

    def to_wib(ts):
        return ts.tz_convert("Asia/Jakarta").strftime("%Y-%m-%d %H:%M:%S WIB")

    print("=== get_ticker('btc_idr') ===")
    try:
        t = get_ticker("btc_idr")
        print(f"Pair          : {t['symbol']}")
        print(f"Waktu         : {to_wib(t['timestamp'])}")
        print(f"Harga terakhir: {rupiah(t['last'])}")
        print(f"Bid (beli)    : {rupiah(t['bid'])}")
        print(f"Ask (jual)    : {rupiah(t['ask'])}")
        print(f"Spread        : {rupiah(t['ask'] - t['bid'])}")
        print(f"High / Low 24j: {rupiah(t['high'])} / {rupiah(t['low'])}")
        print(f"Volume 24j    : {t['volume_24h']:.4f} BTC ({rupiah(t['volume_24h_quote'])})")
    except ExchangeDataError as e:
        print(f"ERROR: {e}")

    print("\n=== get_ohlcv('btc_idr', '5m', 10) ===")
    try:
        df = get_ohlcv("btc_idr", "5m", 10)
        table = df.copy()
        table["timestamp"] = table["timestamp"].dt.tz_convert("Asia/Jakarta").dt.strftime("%Y-%m-%d %H:%M")
        for col in ["open", "high", "low", "close"]:
            table[col] = table[col].map(lambda v: f"{v:,.0f}".replace(",", "."))
        table["volume"] = table["volume"].map(lambda v: f"{v:.6f}")
        table = table.rename(columns={"timestamp": "waktu (WIB)", "volume": "volume (BTC)"})
        print(table.to_string(index=False))
    except ExchangeDataError as e:
        print(f"ERROR: {e}")

    print("\n=== Uji penanganan error ===")
    for label, func in [
        ("Pair tidak ada ('xyz_idr')", lambda: get_ticker("xyz_idr")),
        ("Timeframe tidak valid ('2m')", lambda: get_ohlcv("btc_idr", "2m")),
    ]:
        try:
            func()
            print(f"{label}: (tidak ada error?)")
        except ExchangeDataError as e:
            print(f"{label}: {e}")
