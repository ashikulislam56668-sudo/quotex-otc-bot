import os
import time
import requests
import json
import websocket
import threading
import pandas as pd
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands

TG_TOKEN = "8887188073:AAFUeOxDpQK4yZo0Y2MHSrqVFDhQbnETtuI"
TG_CHAT = "8541515922"
price_history = {}
MAX_TICKS = 100

def send_telegram_signal(pair, action, current_price, rsi_val):
    message = (
        f"🎯 QUOTEX OTC PRO SIGNAL\n"
        f"----------------------------\n"
        f"PAIR: {pair}\n"
        f"ACTION: {action}\n"
        f"ENTRY PRICE: {current_price}\n"
        f"⏳ EXPIRY: STRICTLY 1 MINUTE\n"
        f"📊 RSI VALUE: {rsi_val:.2f}\n"
        f"⚠️ EXECUTION: Place trade instantly at the open of the next candle!"
    )
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TG_CHAT, "text": message}, timeout=5)
        print(f"⚡ [SIGNAL FIRED] {pair} -> {action}")
    except Exception as e:
        print(f"❌ Telegram Error: {e}")

def process_market_data(pair, live_price, time_left):
    if pair not in price_history:
        price_history[pair] = []
    price_history[pair].append(live_price)
    if len(price_history[pair]) > MAX_TICKS:
        price_history[pair].pop(0)

    if time_left <= 1:
        if len(price_history[pair]) >= 30:
            df = pd.DataFrame(price_history[pair], columns=['close'])
            rsi = RSIIndicator(close=df['close'], window=14).rsi().iloc[-1]
            bb = BollingerBands(close=df['close'], window=20, window_dev=2)
            bb_high = bb.bollinger_hband().iloc[-1]
            bb_low = bb.bollinger_lband().iloc[-1]

            print(f"📊 [ANALYSIS] {pair} | Price: {live_price} | RSI: {rsi:.2f}")

            if rsi < 25 and live_price <= bb_low:
                send_telegram_signal(pair, "BUY (CALL)", live_price, rsi)
            elif rsi > 75 and live_price >= bb_high:
                send_telegram_signal(pair, "SELL (PUT)", live_price, rsi)

def on_message(ws, message):
    try:
        data = json.loads(message)
        if "price" in data and "asset" in data:
            process_market_data(data["asset"], float(data["price"]), int(data.get("time_left", 30)))
    except:
        pass

def start_socket_stream():
    ws_url = "wss://ws.derivws.com/websockets/v3?app_id=1089" 
    ws = websocket.WebSocketApp(
        ws_url,
        on_message=on_message,
        on_error=lambda ws, err: print(f"⚠️ Connection loss: {err}"),
        on_close=lambda ws, status, msg: print("🔄 Reconnecting...")
    )
    def on_open(ws):
        print("🛰️ Connected to Live Stream Engine...")
        for asset in ["frxEURUSD", "frxGBPUSD", "frxUSDJPY"]:
            ws.send(json.dumps({"ticks": asset}))
    ws.on_open = on_open
    ws.run_forever()

if __name__ == "__main__":
    threading.Thread(target=start_socket_stream, daemon=True).start()
    from http.server import BaseHTTPRequestHandler, HTTPServer
    class HealthServer(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot Active")
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(("0.0.0.0", port), HealthServer).serve_forever()
