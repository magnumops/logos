from fpdf import FPDF
import matplotlib.pyplot as plt
import os
from datetime import datetime

class VerdictReport(FPDF):
    def header(self):
        self.set_font('Courier', 'B', 15)
        self.cell(0, 10, 'LOGOS FORENSIC LAB // AUTOPSY REPORT', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Courier', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

class Reporter:
    def __init__(self, output_dir="/data/reports"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_chart(self, trades_df, death_trade, filename):
        """Рисует график 'Момент смерти'"""
        plt.figure(figsize=(10, 4))
        
        # Рисуем цену
        plt.plot(trades_df['timestamp'], trades_df['price'], color='black', linewidth=1, label='Market Price')
        
        # Рисуем точку смерти
        death_time = death_trade['timestamp']
        death_price = death_trade['price']
        plt.scatter([death_time], [death_price], color='red', s=100, zorder=5, label='LIQUIDATION')
        
        plt.title(f"Case Evidence: {death_trade['symbol']}")
        plt.xlabel("Time")
        plt.ylabel("Price")
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.legend()
        
        chart_path = os.path.join(self.output_dir, filename)
        plt.savefig(chart_path)
        plt.close()
        return chart_path

    def create_verdict(self, case_id, trade_data, z3_result, historical_df):
        pdf = VerdictReport()
        pdf.add_page()
        pdf.set_font("Courier", size=12)
        
        # 1. Информация о Деле
        pdf.cell(0, 10, f"CASE ID: {case_id}", 0, 1)
        pdf.cell(0, 10, f"DATE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1)
        pdf.cell(0, 10, f"SUBJECT: {trade_data['symbol']} {trade_data['side']}", 0, 1)
        pdf.ln(10)
        
        # 2. Вердикт
        verdict = z3_result.get('verdict', 'UNKNOWN')
        color = (255, 0, 0) if verdict != 'CLEAN' else (0, 128, 0)
        
        pdf.set_font("Courier", 'B', 16)
        pdf.set_text_color(*color)
        pdf.cell(0, 10, f"VERDICT: {verdict}", 0, 1, 'C')
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Courier", size=12)
        pdf.ln(10)
        
        # 3. Доказательства (График)
        if not historical_df.empty:
            chart_file = f"chart_{case_id}.png"
            chart_path = self.generate_chart(historical_df, trade_data, chart_file)
            pdf.image(chart_path, x=10, w=190)
            pdf.ln(5)
        
        # 4. Детали Z3
        pdf.set_font("Courier", 'B', 12)
        pdf.cell(0, 10, "MATHEMATICAL PROOF (Z3 SOLVER):", 0, 1)
        pdf.set_font("Courier", size=10)
        pdf.multi_cell(0, 10, z3_result.get('details', 'No details provided.'))
        
        # Сохранение
        filename = f"VERDICT_{case_id}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        pdf.output(filepath)
        print(f"[Reporter] PDF Verdict generated: {filepath}")
        return filepath
