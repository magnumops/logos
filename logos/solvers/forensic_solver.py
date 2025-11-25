import z3
import pandas as pd

class ForensicSolver:
    """
    Судья на базе Microsoft Z3.
    Доказывает математическую невозможность честного исполнения сделки.
    """

    def verify(self, trade: dict, historical_trades: pd.DataFrame, orderbook: dict):
        print("[Solver] Building Z3 Model for Fair Execution...")
        
        solver = z3.Solver()
        
        # 1. Переменные (Символы)
        # Цена исполнения сделки (Real number)
        exec_price = z3.Real('exec_price')
        
        # Лучшая цена в стакане (Best Bid/Ask) на момент сделки
        market_price = z3.Real('market_price')
        
        # Спред и Проскальзывание
        spread = z3.Real('spread')
        slippage = z3.Real('slippage')
        
        # 2. Загрузка фактов (Константы из данных)
        actual_exec_price = float(trade['price'])
        
        # Определяем рыночную цену из стакана
        if trade['side'] == 'BUY':
            # Для покупки рыночная цена - это лучший продавец (min Ask)
            best_market_price = float(orderbook['asks']['price'].min())
        else:
            # Для продажи - лучший покупатель (max Bid)
            best_market_price = float(orderbook['bids']['price'].max())
            
        # Спред (разница между лучшим бидом и аском)
        best_ask = float(orderbook['asks']['price'].min())
        best_bid = float(orderbook['bids']['price'].max())
        actual_spread = best_ask - best_bid
        
        # 3. Формируем Z3 утверждения (Constraints)
        
        # Утверждение А: Параметры модели равны фактам
        solver.add(exec_price == actual_exec_price)
        solver.add(market_price == best_market_price)
        solver.add(spread == actual_spread)
        
        # Утверждение Б: Модель "Честного Рынка" (Fair Market Invariant)
        # Цена исполнения не должна отклоняться от рыночной больше чем на спред + 1% (допуск на проскальзывание)
        # Формула: Abs(Exec - Market) <= Spread + (Market * 0.01)
        
        # Z3 не имеет встроенного Abs, пишем через If
        diff = z3.If(exec_price > market_price, exec_price - market_price, market_price - exec_price)
        allowed_slippage = spread + (market_price * 0.01)
        
        # ГЛАВНОЕ: Мы просим Z3 проверить, является ли сделка "Честной"
        solver.add(diff <= allowed_slippage)
        
        # 4. Суд (Check Satisfiability)
        result = solver.check()
        
        if result == z3.sat:
            return {
                "verdict": "CLEAN",
                "details": "Execution is mathematically consistent with market liquidity."
            }
        else:
            return {
                "verdict": "LIQUIDITY_VOID_DETECTED",
                "details": f"UNSAT: Execution price {actual_exec_price} is impossible given Best Market Price {best_market_price} and Spread {actual_spread:.2f}."
            }
