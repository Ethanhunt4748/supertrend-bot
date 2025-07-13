import time
import requests
import pandas as pd
from datetime import datetime
from binance.client import Client
from ta.trend import supertrend

# ====== Telegram Settings ======
TELEGRAM_BOT_TOKEN = '8062081758:AAGKMMc1WMfoCW6TMfxdCaoJ_7TMMoZ7kOg'
TELEGRAM_CHAT_ID = '7939328432'

# ====== Supertrend Parameters ======
SUPER_ATR_PERIOD = 14
SUPER_MULTIPLIER = 5.0
INTERVAL = '1m'

# ====== Coins to Track ======
SYMBOLS = [
    'SHIBUSDT', 'ICXUSDT', 'SXPUSDT', 'KAVAUSDT', 'LINKUSDT', 'LRCUSDT', 'ADAUSDT', 'XLMUSDT',
    'LAYERUSDT', 'CRVUSDT', 'TRXUSDT', 'ANKRUSDT', 'NEARUSDT', 'AVAXUSDT', 'IOTXUSDT', 'BTCUSDT',
    'STORJUSDT', 'ICPUSDT', 'MASKUSDT', 'ACHUSDT', 'ATOMUSDT', 'EGLDUSDT', 'FILUSDT', 'ENJUSDT',
    'VETUSDT', 'XTZUSDT'
]

client = Client()

last_trend = {}

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print("Telegram error:", e)

def fetch_heikin_ashi(symbol):
    try:
        klines = client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_1MINUTE, limit=50)
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close',
            'volume', 'close_time', 'qav', 'num_trades',
            'tbbav', 'tbqav', 'ignore'
        ])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df[['open', 'high', 'low', 'close']] = df[['open', 'high', 'low', 'close']].astype(float)

        ha_df = pd.DataFrame()
        ha_df['close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
        ha_open = [(df['open'][0] + df['close'][0]) / 2]
        for i in range(1, len(df)):
            ha_open.append((ha_open[i-1] + ha_df['close'][i-1]) / 2)
        ha_df['open'] = ha_open
        ha_df['high'] = df[['high', 'open', 'close']].max(axis=1)
        ha_df['low'] = df[['low', 'open', 'close']].min(axis=1)
        ha_df['timestamp'] = df['timestamp']
        return ha_df
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None

def apply_supertrend(df):
    st = supertrend(df, atr_period=SUPER_ATR_PERIOD, atr_multiplier=SUPER_MULTIPLIER)
    df['supertrend'] = st[f'SUPERT_{SUPER_ATR_PERIOD}']
    df['trend'] = st[f'SUPERT_{SUPER_ATR_PERIOD}_direction']
    return df

print("🟢 Supertrend Heikin Ashi Bot Running...")

while True:
    for symbol in SYMBOLS:
        df = fetch_heikin_ashi(symbol)
        if df is None or df.empty:
            continue

        try:
            df = apply_supertrend(df)
            latest = df['trend'].iloc[-1]
            previous = df['trend'].iloc[-2]

            prev_state = last_trend.get(symbol, None)

            if prev_state is not None and latest != previous:
                direction = "🟢 BUY" if latest else "🔴 SELL"
                message = f"{direction} signal on {symbol}\nTime: {datetime.now().strftime('%H:%M:%S')}"
                send_telegram_alert(message)
                print(message)
                last_trend[symbol] = latest
            elif prev_state is None:
                last_trend[symbol] = latest

        except Exception as e:
            print(f"Error processing {symbol}: {e}")

    time.sleep(15)
