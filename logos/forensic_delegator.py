from logos.log_parser import LogParser
from logos.time_machine import TimeMachine
import os

class ForensicDelegator:
    """
    Координатор расследования.
    Связывает улики (CSV), машину времени (API) и судью (Solver).
    """
    
    def __init__(self):
        self.parser = LogParser()
        self.tm = TimeMachine()
        # Solver будет подключен позже

    def run_investigation(self, csv_path: str):
        print(f"[Delegator] Starting investigation on case file: {csv_path}")
        
        # 1. Анализ улик (Парсинг)
        try:
            evidence_df = self.parser.normalize(csv_path)
            death_trade = self.parser.get_death_trade(evidence_df)
            print(f"[Delegator] Identified Death Trade: {death_trade['side']} {death_trade['symbol']} @ {death_trade['price']}")
        except Exception as e:
            return f"CRITICAL ERROR: Failed to parse evidence. {e}"

        # 2. Путешествие во времени (Сбор данных)
        symbol = death_trade['symbol']
        timestamp = death_trade['timestamp_ms']
        
        # Берем окно +/- 1 секунда вокруг сделки
        start_time = timestamp - 1000
        end_time = timestamp + 1000
        
        print("[Delegator] Engaging Time Machine...")
        historical_trades = self.tm.get_historical_agg_trades(symbol, start_time, end_time)
        orderbook = self.tm.get_orderbook_snapshot(symbol, limit=100)
        
        if historical_trades.empty or orderbook is None:
            return "ERROR: Time Machine failed to retrieve historical context."
            
        print(f"[Delegator] Recovered {len(historical_trades)} historical trades and orderbook state.")

        # 3. Вызов Судьи (ForensicSolver) - Placeholder
        return {
            "status": "READY_FOR_TRIAL",
            "suspect_trade": death_trade,
            "context_trades_count": len(historical_trades),
            "orderbook_depth": len(orderbook['bids'])
        }

# Self-test
if __name__ == "__main__":
    # Создаем фиктивный файл улик для теста
    with open("test_crash.csv", "w") as f:
        f.write("time,symbol,side,price,qty\n")
        f.write("2025-11-25 09:30:00,BTCUSDT,BUY,95000.00,0.5\n")
    
    delegator = ForensicDelegator()
    result = delegator.run_investigation("test_crash.csv")
    print("\n[RESULT]", result)
    
    # Чистим за собой
    if os.path.exists("test_crash.csv"):
        os.remove("test_crash.csv")
