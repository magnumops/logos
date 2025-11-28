import pandas as pd
import os

class LogParser:
    REQUIRED_COLUMNS = ['timestamp', 'symbol', 'side', 'price', 'qty']

    def normalize(self, filepath: str) -> pd.DataFrame:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Evidence file not found: {filepath}")

        try:
            df = pd.read_csv(filepath, sep=None, engine='python')
        except Exception as e:
            raise ValueError(f"Failed to read CSV: {e}")

        # Нормализация имен колонок
        df.columns = [c.lower().strip() for c in df.columns]
        
        # Маппинг колонок (стандартный)
        column_map = {}
        if 'time' in df.columns: column_map['time'] = 'timestamp'
        elif 'date' in df.columns: column_map['date'] = 'timestamp'
        
        if 'pair' in df.columns: column_map['pair'] = 'symbol'
        if 'type' in df.columns: column_map['type'] = 'side'
        if 'amount' in df.columns: column_map['amount'] = 'qty'
        if 'size' in df.columns: column_map['size'] = 'qty'
        if 'quantity' in df.columns: column_map['quantity'] = 'qty' # ДОБАВИЛИ quantity
        
        if 'avg_price' in df.columns: column_map['avg_price'] = 'price'
        if 'exec_price' in df.columns: column_map['exec_price'] = 'price'

        df = df.rename(columns=column_map)

        # Проверка
        missing = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing}. Found: {list(df.columns)}")

        # --- FIX ВРЕМЕНИ ---
        # Если число большое (13 цифр) - это уже миллисекунды. Не трогаем.
        # Если строка - парсим.
        
        def parse_time(val):
            try:
                # Если это число и оно больше 2000 года в секундах (946684800), но меньше 3000 года
                val_float = float(val)
                if val_float > 10**12: # Уже миллисекунды (13 знаков)
                    return int(val_float)
                if val_float > 10**9: # Секунды (10 знаков) -> переводим в мс
                    return int(val_float * 1000)
            except:
                pass
            # Иначе пробуем как строку даты
            return int(pd.to_datetime(val).timestamp() * 1000)

        df['timestamp_ms'] = df['timestamp'].apply(parse_time)
        
        df['price'] = df['price'].astype(float)
        df['qty'] = df['qty'].astype(float)
        df['side'] = df['side'].astype(str).str.upper()

        return df
    
    def get_death_trade(self, df: pd.DataFrame) -> dict:
        if df.empty: return None
        return df.iloc[-1].to_dict()
