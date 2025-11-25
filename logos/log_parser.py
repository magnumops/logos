import pandas as pd
import os

class LogParser:
    """
    Нормализатор торговых логов.
    Приводит разношерстные CSV к единому формату Logos Evidence.
    """
    
    REQUIRED_COLUMNS = ['timestamp', 'symbol', 'side', 'price', 'qty']

    def normalize(self, filepath: str) -> pd.DataFrame:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Evidence file not found: {filepath}")

        # Читаем CSV (пытаемся угадать разделитель)
        try:
            df = pd.read_csv(filepath, sep=None, engine='python')
        except Exception as e:
            raise ValueError(f"Failed to read CSV: {e}")

        # Нормализация имен колонок (приводим к нижнему регистру и стрипаем)
        df.columns = [c.lower().strip() for c in df.columns]

        # Эвристика для маппинга колонок
        column_map = {}
        
        # 1. Timestamp
        if 'time' in df.columns: column_map['time'] = 'timestamp'
        elif 'date' in df.columns: column_map['date'] = 'timestamp'
        elif 'timestamp' in df.columns: column_map['timestamp'] = 'timestamp'
        
        # 2. Symbol
        if 'symbol' in df.columns: column_map['symbol'] = 'symbol'
        elif 'pair' in df.columns: column_map['pair'] = 'symbol'
        
        # 3. Price
        if 'price' in df.columns: column_map['price'] = 'price'
        elif 'avg_price' in df.columns: column_map['avg_price'] = 'price'
        elif 'exec_price' in df.columns: column_map['exec_price'] = 'price'

        # 4. Quantity
        if 'qty' in df.columns: column_map['qty'] = 'qty'
        elif 'amount' in df.columns: column_map['amount'] = 'qty'
        elif 'size' in df.columns: column_map['size'] = 'qty'

        # 5. Side
        if 'side' in df.columns: column_map['side'] = 'side'
        elif 'type' in df.columns: column_map['type'] = 'side' # BUY/SELL

        # Применяем маппинг
        df = df.rename(columns=column_map)

        # Проверка обязательных полей
        missing = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            raise ValueError(f"CSV format invalid. Missing columns: {missing}. Found: {list(df.columns)}")

        # Форматирование данных
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        # Конвертируем в ms timestamp
        df['timestamp_ms'] = df['timestamp'].astype('int64') // 10**6
        df['price'] = df['price'].astype(float)
        df['qty'] = df['qty'].astype(float)
        df['side'] = df['side'].astype(str).str.upper()

        return df[self.REQUIRED_COLUMNS + ['timestamp_ms']]

    def get_death_trade(self, df: pd.DataFrame) -> dict:
        """
        Находит 'Точку Смерти' — последнюю сделку в логе.
        """
        if df.empty:
            return None
        return df.iloc[-1].to_dict()
