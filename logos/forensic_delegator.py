from logos.log_parser import LogParser
from logos.time_machine import TimeMachine
from logos.solvers.forensic_solver import ForensicSolver
from logos.reporter import Reporter
import sys
import os
import time
import pandas as pd

class ForensicDelegator:
    def __init__(self):
        self.parser = LogParser()
        self.tm = TimeMachine()
        self.solver = ForensicSolver()
        self.reporter = Reporter(output_dir="/data/reports")

    def run_investigation(self, csv_path: str):
        if not os.path.exists(csv_path):
             return {"error": f"File not found: {csv_path}"}

        print(f"[Delegator] Starting investigation on case file: {csv_path}")
        
        try:
            evidence_df = self.parser.normalize(csv_path)
            death_trade = self.parser.get_death_trade(evidence_df)
        except Exception as e:
            return {"error": f"Failed to parse evidence. {e}"}

        symbol = death_trade['symbol']
        timestamp = death_trade['timestamp_ms']
        start_time = timestamp - 5000 
        end_time = timestamp + 1000
        
        historical_trades = self.tm.get_historical_agg_trades(symbol, start_time, end_time)
        orderbook = self.tm.get_orderbook_snapshot(symbol, limit=100)
        
        if historical_trades.empty or orderbook is None:
            return {"error": "Time Machine failed to retrieve historical context."}

        z3_result = self.solver.verify(death_trade, historical_trades, orderbook)
        
        case_id = f"CASE-{int(time.time())}"
        pdf_path = self.reporter.create_verdict(case_id, death_trade, z3_result, historical_trades)
        
        # Подготовка данных для Фронтенда (JSON)
        # Конвертируем DataFrame в список словарей
        history_json = historical_trades[['timestamp', 'price']].copy()
        # Приводим timestamp к секундам (unix) для JS
        history_json['time'] = history_json['timestamp'].astype(int) / 10**9 
        history_list = history_json[['time', 'price']].to_dict(orient='records')
        
        return {
            "status": "success",
            "verdict": z3_result['verdict'],
            "z3_details": z3_result.get('details', ''),
            "report_path": pdf_path,
            "chart_data": history_list,
            "death_point": {
                "time": timestamp / 1000, # seconds
                "price": death_trade['price']
            }
        }
