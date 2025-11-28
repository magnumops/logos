import requests
import pandas as pd
import time
from datetime import datetime, timezone

class TimeMachine:
    BASE_URL = "https://api.binance.com"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Logos-Pathologist/0.5"
        })

    def _get(self, endpoint, params=None):
        url = f"{self.BASE_URL}{endpoint}"
        try:
            # DEBUG: Print URL being requested
            print(f"[DEBUG] Requesting: {url} with params: {params}")
            response = self.session.get(url, params=params, timeout=10)
            
            # DEBUG: Print status code
            if response.status_code != 200:
                print(f"[DEBUG] API Error {response.status_code}: {response.text[:200]}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[TimeMachine] CRITICAL NETWORK ERROR: {e}")
            return None

    def get_orderbook_snapshot(self, symbol: str, limit: int = 1000):
        endpoint = "/api/v3/depth"
        params = {"symbol": symbol.upper(), "limit": limit}
        print(f"[TimeMachine] Downloading Order Book for {symbol}...")
        data = self._get(endpoint, params)
        if not data: return None
        
        bids = pd.DataFrame(data['bids'], columns=['price', 'qty'], dtype=float)
        asks = pd.DataFrame(data['asks'], columns=['price', 'qty'], dtype=float)
        bids['side'] = 'bid'
        asks['side'] = 'ask'
        return {"lastUpdateId": data['lastUpdateId'], "bids": bids, "asks": asks}

    def get_historical_agg_trades(self, symbol: str, start_time_ms: int, end_time_ms: int):
        endpoint = "/api/v3/aggTrades"
        params = {
            "symbol": symbol.upper(),
            "startTime": start_time_ms,
            "endTime": end_time_ms,
            "limit": 1000
        }
        print(f"[TimeMachine] Fetching trades for {symbol}...")
        data = self._get(endpoint, params)
        
        if not data: 
            print("[DEBUG] Received empty data or None from _get")
            return pd.DataFrame()

        df = pd.DataFrame(data)
        if df.empty:
            print("[DEBUG] DataFrame is empty after parsing JSON")
            return df
            
        df = df.rename(columns={'a': 'trade_id', 'p': 'price', 'q': 'qty', 'T': 'timestamp', 'm': 'is_buyer_maker'})
        df['price'] = df['price'].astype(float)
        df['qty'] = df['qty'].astype(float)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
