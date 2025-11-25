import json
import time
import os
from datetime import datetime

class BlackBox:
    """
    Бортовой самописец.
    Сохраняет телеметрию сессии для последующего разбора полетов.
    """
    def __init__(self, log_dir="/data/logs"):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Создаем файл сессии
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.filename = os.path.join(self.log_dir, f"session_{session_id}.jsonl")
        print(f"[BlackBox] Recording flight data to {self.filename}")

    def log_event(self, event_type: str, payload: dict):
        """
        Записывает событие.
        event_type: 'MARKET_DATA', 'INJECTED_ATTACK', 'BOT_REQUEST'
        """
        entry = {
            "timestamp": time.time(),
            "type": event_type,
            "data": payload
        }
        with open(self.filename, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def log_kline(self, symbol, kline, is_poisoned=False):
        """Спец-метод для логирования свечи"""
        payload = {
            "symbol": symbol,
            "open": kline[1],
            "high": kline[2],
            "low": kline[3],
            "close": kline[4],
            "volume": kline[5],
            "is_poisoned": is_poisoned
        }
        self.log_event("KLINE_UPDATE", payload)
