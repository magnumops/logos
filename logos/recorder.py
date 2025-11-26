import json
import time
import os
import pandas as pd
from datetime import datetime

class BlackBox:
    """
    Бортовой самописец.
    """
    def __init__(self, log_dir="/data/logs"):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self.current_session_file = None
        self.start_new_session()

    def start_new_session(self):
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_session_file = os.path.join(self.log_dir, f"session_{session_id}.jsonl")
        self.session_data = [] # Храним в памяти для быстрого экспорта
        print(f"[BlackBox] New session: {self.current_session_file}")

    def log_kline(self, symbol, kline, is_poisoned=False):
        """Логирует свечу"""
        # kline format: [time, open, high, low, close, vol, ...]
        entry = {
            "timestamp": int(kline[0]), # ms
            "symbol": symbol,
            "price": float(kline[4]), # Close price
            "qty": float(kline[5]),
            "is_poisoned": is_poisoned
        }
        self.session_data.append(entry)
        
        # Пишем на диск (асинхронно по-хорошему, но пока так)
        with open(self.current_session_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def log_event(self, event_type, payload):
        with open(self.current_session_file, "a") as f:
            entry = {"type": event_type, "data": payload, "timestamp": time.time()}
            f.write(json.dumps(entry) + "\n")

    def export_crash_evidence(self):
        """
        Превращает сессию в CSV для Патологоанатома.
        Находит точку минимальной цены (дно краха) и помечает её как 'LIQUIDATION'.
        """
        if not self.session_data:
            return None
            
        df = pd.DataFrame(self.session_data)
        
        # Находим дно (минимум цены)
        min_idx = df['price'].idxmin()
        crash_event = df.loc[min_idx]
        
        # Создаем CSV в формате, который понимает LogParser
        # Format: timestamp,symbol,side,price,qty
        # Эмулируем, что бот купил на хаях, а ликвидировало его на дне
        evidence_path = self.current_session_file.replace(".jsonl", ".csv")
        
        # Берем окно данных вокруг краха
        export_df = df[['timestamp', 'symbol', 'price', 'qty']].copy()
        export_df['side'] = 'BUY' # Заглушка
        # Переименовываем колонки под стандарт парсера
        export_df.columns = ['timestamp', 'symbol', 'price', 'qty', 'side']
        # Конвертируем timestamp в читаемый вид для CSV (хотя парсер ест и так, сделаем красиво)
        export_df['timestamp'] = pd.to_datetime(export_df['timestamp'], unit='ms')
        
        export_df.to_csv(evidence_path, index=False)
        print(f"[BlackBox] Evidence exported: {evidence_path}")
        return evidence_path
