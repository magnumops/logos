from logos.log_parser import LogParser
from logos.time_machine import TimeMachine
from logos.solvers.forensic_solver import ForensicSolver
import os

class ForensicDelegator:
    def __init__(self):
        self.parser = LogParser()
        self.tm = TimeMachine()
        self.solver = ForensicSolver()

    def run_investigation(self, csv_path: str):
        print(f"[Delegator] Starting investigation on case file: {csv_path}")
        
        # 1. Анализ улик
        try:
            evidence_df = self.parser.normalize(csv_path)
            death_trade = self.parser.get_death_trade(evidence_df)
            print(f"[Delegator] Identified Death Trade: {death_trade['side']} {death_trade['symbol']} @ {death_trade['price']}")
        except Exception as e:
            return f"CRITICAL ERROR: Failed to parse evidence. {e}"

        # 2. Путешествие во времени
        symbol = death_trade['symbol']
        timestamp = death_trade['timestamp_ms']
        start_time = timestamp - 1000
        end_time = timestamp + 1000
        
        print("[Delegator] Engaging Time Machine...")
        historical_trades = self.tm.get_historical_agg_trades(symbol, start_time, end_time)
        orderbook = self.tm.get_orderbook_snapshot(symbol, limit=100)
        
        if historical_trades.empty or orderbook is None:
            return "ERROR: Time Machine failed to retrieve historical context."

        # 3. Вызов Судьи (Z3)
        print("[Delegator] Data secured. Summoning The Solver...")
        verdict = self.solver.verify(death_trade, historical_trades, orderbook)
        return verdict

if __name__ == "__main__":
    # Тест на "нормальной" сделке (должен вернуть CLEAN, если цена близка к рынку)
    # ПРИМЕЧАНИЕ: Поскольку TimeMachine качает РЕАЛЬНЫЙ стакан СЕЙЧАС, а дата сделки в будущем/прошлом,
    # мы можем получить UNSAT просто из-за разницы времени. Это нормально для теста.
    with open("test_crash.csv", "w") as f:
        f.write("time,symbol,side,price,qty\n")
        # Ставим заведомо нереальную цену (1M за биток), чтобы получить UNSAT
        f.write("2025-11-25 09:30:00,BTCUSDT,BUY,1000000.00,0.5\n")
    
    delegator = ForensicDelegator()
    result = delegator.run_investigation("test_crash.csv")
    print("\n[FINAL VERDICT]", result)
    
    if os.path.exists("test_crash.csv"):
        os.remove("test_crash.csv")
