import random
import numpy as np
from logos.solvers.stop_loss_hunter import StopLossHunter

class ChaosGenerator:
    """
    Генератор Хаоса v0.3 (Aggressive).
    Гарантирует визуальный обвал цены при активации.
    """
    
    def __init__(self):
        self.sniper = StopLossHunter()

    def inject_flash_crash(self, klines: list):
        """
        Модифицирует ПОСЛЕДНЮЮ свечу в массиве.
        Формат Kline Binance: [time, open, high, low, close, vol, ...]
        """
        if not klines:
            return klines
            
        # Берем последнюю свечу (которая сейчас рисуется)
        # Важно: мы создаем копию данных, чтобы не ломать логику ссылок,
        # но вставляем обратно в список.
        last_kline = klines[-1]
        
        # Парсим текущие данные
        open_price = float(last_kline[1])
        current_close = float(last_kline[4])
        
        # --- ЛОГИКА АТАКИ ---
        
        # 1. Вычисляем цель (Z3 или Hard Drop)
        # Чтобы гарантировать видимость, мы берем минимум 5% падения
        target_price = self.sniper.find_minimal_crash(open_price)
        
        # Hard cap: Если Z3 предложил слишком мягкое падение, форсируем -8%
        if target_price > open_price * 0.95:
            target_price = open_price * 0.92
            
        # 2. Формируем "Свечу Смерти"
        # High: Небольшой вынос вверх (Stop Hunt лонгов/шортов) перед падением
        new_high = open_price * 1.002
        
        # Low: То самое дно
        new_low = target_price
        
        # Close: Отскок "дохлой кошки" (немного выше дна)
        new_close = target_price * 1.005
        
        # Volume: Панический объем (x50 от обычного)
        current_vol = float(last_kline[5])
        new_vol = current_vol * 50.0
        
        # 3. Применяем изменения (строки, как требует API Binance)
        # Индексы: 0=Time, 1=Open, 2=High, 3=Low, 4=Close, 5=Vol
        
        # ВАЖНО: Мы меняем только Low, Close и Vol. Open оставляем как есть, чтобы график был непрерывным.
        last_kline[2] = str(new_high)
        last_kline[3] = str(new_low)   # CRASH
        last_kline[4] = str(new_close) # CLOSE AT BOTTOM
        last_kline[5] = str(new_vol)
        
        # DEBUG LOG (Чтобы видеть в консоли)
        print(f"\n[CHAOS] INJECTION: {open_price:.2f} -> {new_close:.2f} (DROP: {open_price - new_close:.2f})")
        
        # Возвращаем модифицированный список
        klines[-1] = last_kline
        return klines
