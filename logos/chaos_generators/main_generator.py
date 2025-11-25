import random
from logos.solvers.stop_loss_hunter import StopLossHunter

class ChaosGenerator:
    """
    Фабрика хаоса.
    Принимает здоровые данные и возвращает отравленные.
    """
    
    def __init__(self):
        self.sniper = StopLossHunter()

    def inject_flash_crash(self, klines: list):
        """
        Модифицирует ПОСЛЕДНЮЮ свечу в массиве, превращая её в свечу краха.
        Формат Kline Binance:
        [Open time, Open, High, Low, Close, Volume, ...]
        """
        if not klines:
            return klines
            
        # Берем последнюю свечу
        last_kline = klines[-1]
        
        # Текущая цена (Close предыдущей или Open текущей)
        current_price = float(last_kline[4]) # Close
        
        # Вычисляем цель атаки через Z3
        target_price = self.sniper.find_minimal_crash(current_price)
        
        # Модифицируем свечу:
        # Open остается, но High не может быть ниже Open, Low падает до Target, Close закрывается на дне.
        # Индексы: 1=Open, 2=High, 3=Low, 4=Close
        
        open_price = float(last_kline[1])
        new_low = target_price
        new_close = target_price + (target_price * 0.001) # Небольшой отскок "дохлой кошки"
        
        # Обновляем свечу (все строки!)
        last_kline[2] = str(max(open_price, new_close) + 10) # High чуть выше
        last_kline[3] = str(new_low)   # Low (CRASH POINT)
        last_kline[4] = str(new_close) # Close
        
        print(f"[Chaos] INJECTED CRASH: {current_price} -> {new_low} (Delta: {current_price - new_low:.2f})")
        
        klines[-1] = last_kline
        return klines
