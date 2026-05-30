import os
import requests
import json
import websocket
import threading
import pandas as pd
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
from http.server import BaseHTTPRequestHandler, HTTPServer

TG_TOKEN = "8887188073:AAFUeOxDpQK4yZo0Y2MHSrqVFDhQbnETtuI"
TG_CHAT = "8541515922"
price_history = {}
MAX_TICKS = 100
latest_status = "বট সচল আছে, ডাটা স্ক্যান করা হচ্ছে..."

# HTML এবং ট্রেডিংভিউ চার্ট ডিজাইন ইন্টারফেস
HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QUOTEX OTC PRO PANEL</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0b0e11; color: #ffffff; margin: 0; padding: 15px; text-align: center; }
        h2 { color: #00e676; margin-bottom: 10px; font-size: 22px; }
        .container { max-width: 800px; margin: auto; }
        .status-box { background: #151a22; padding: 12px; border-radius: 8px; border: 1px solid #00e676; font-size: 14px; margin-bottom: 15px; color: #00e676; font-weight: bold; }
        .chart-container { position: relative; height: 450px; width: 100%; border-radius: 8px; overflow: hidden; border: 1px solid #2b3139; }
        footer { margin-top: 15px; font-size: 11px; color: #475467; }
    </style>
</head>
<body>
    <div class="container">
        <h2>📊 QUOTEX OTC LIVE SIGNAL PANEL</h2>
        <div class="status-box">🟢 SYSTEM STATUS: Bot Active & Scanning Deriv OTC Markets</div>
        
        <div class="chart-container">
            <div id="tradingview_otc" style="height: 100%; width: 100%;"></div>
            <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
            <script type="text/javascript">
            new TradingView.widget({
                "autosize": true,
                "symbol": "FX_IDC:EURUSD",
                "interval": "1",
                "timezone": "Asia/Dhaka",
                "theme": "dark",
                "style": "1",
                "locale": "en",
                "toolbar_bg": "#f1f3f6",
                "enable_publishing": false,
                "hide_side_toolbar": false,
                "allow_symbol_change": true,
                "container_id": "tradingview_otc"
            });
            </script>
        </div>
        <footer>Powered by Ashikul Islam • Auto Signal Bot v2.0</footer>
    </div>
</body>
</html>
"""

def send_telegram_signal(pair, action, current_price, rsi_val):
    message = (
        f"🎯 QUOTEX OTC PRO SIGNAL\n"
        f"----------------------------\n"
        f"PAIR: {pair}\n"
        f"ACTION: {action}\n"
        f"ENTRY PRICE: {current_price}\n"
        f"⏳ EXPIRY: STRICTLY 1 MINUTE\n"
        f"📊 RSI VALUE: {rsi_val:.2f}\n"
        f"⚠️ EXECUTION: Next Candle Entry!"
    )
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TG_CHAT, "text": message}, timeout=5)
    except:
        pass

def process_market_data(pair, live_price, time_left):
    if pair not in price_history:
        price_history[pair] = []
    price_history[pair].append(live_price)
    if len(price_history[pair]) > MAX_TICKS:
        price_history[pair].pop(0)

    if time_left <= 1 and len(price_history[pair]) >= 30:
        df = pd.DataFrame(price_history[pair], columns=['close'])
        rsi = RSIIndicator(close=df['close'], window=14).rsi().iloc[-1]
        bb = BollingerBands(close=df['close'], window=20, window_dev=2)
        bb_high = bb.bollinger_hband().iloc[-1]
        bb_low = bb.bollinger_lband().iloc[-1]

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
        on_error=lambda ws, err: None,
        on_close=lambda ws, status, msg: None
    )
    def on_open(ws):
        for asset in ["frxEURUSD", "frxGBPUSD", "frxUSDJPY"]:
            ws.send(json.dumps({"ticks": asset}))
    ws.on_open = on_open
    ws.run_forever()

class WebServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML_DASHBOARD.encode("utf-8"))

if __name__ == "__main__":
    threading.Thread(target=start_socket_stream, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(("0.0.0.0", port), WebServer).serve_forever()
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
