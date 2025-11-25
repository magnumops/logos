from logos.log_parser import LogParser
from logos.time_machine import TimeMachine
from logos.solvers.forensic_solver import ForensicSolver
import sys
import os

class ForensicDelegator:
    def __init__(self):
        self.parser = LogParser()
        self.tm = TimeMachine()
        self.solver = ForensicSolver()

    def run_investigation(self, csv_path: str):
        if not os.path.exists(csv_path):
             return f"ERROR: File not found: {csv_path}"

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
        # Берем данные чуть шире для контекста
        start_time = timestamp - 5000 
        end_time = timestamp + 1000
        
        print("[Delegator] Engaging Time Machine...")
        historical_trades = self.tm.get_historical_agg_trades(symbol, start_time, end_time)
        orderbook = self.tm.get_orderbook_snapshot(symbol, limit=100)
        
        if historical_trades.empty or orderbook is None:
            return "ERROR: Time Machine failed to retrieve historical context (Network issue?)"

        # 3. Вызов Судьи (Z3)
        print(f"[Delegator] Data secured ({len(historical_trades)} trades). Summoning The Solver...")
        verdict = self.solver.verify(death_trade, historical_trades, orderbook)
        return verdict

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m logos.forensic_delegator <path_to_csv>")
        sys.exit(1)
        
    csv_path = sys.argv[1]
    delegator = ForensicDelegator()
    result = delegator.run_investigation(csv_path)
    print("\n[FINAL VERDICT]", result)
