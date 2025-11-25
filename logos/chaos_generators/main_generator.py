import random
import numpy as np
from logos.solvers.stop_loss_hunter import StopLossHunter

class ChaosGenerator:
    """
    Генератор Хаоса v0.2 (Merton Enhanced).
    Сочетает Z3 (поиск цели) и Merton Jump-Diffusion (симуляция процесса).
    """
    
    def __init__(self):
        self.sniper = StopLossHunter()

    def merton_jump_diffusion(self, S0, T, mu, sigma, lambda_j, mu_j, sigma_j):
        """
        Симуляция одного шага модели Мертона.
        S0: Текущая цена
        T: Временной шаг (1 минута normalized)
        mu: Дрифт (тренд)
        sigma: Волатильность (диффузия)
        lambda_j: Интенсивность прыжков (сколько прыжков в год)
        mu_j: Средний размер прыжка
        sigma_j: Волатильность прыжка
        """
        # Диффузия (Обычный рынок)
        dt = T
        dW = np.random.normal(0, np.sqrt(dt))
        diffusion = (mu - 0.5 * sigma**2) * dt + sigma * dW
        
        # Прыжок (Крах)
        # Poisson процесс: произошло ли событие?
        N = np.random.poisson(lambda_j * dt)
        jump = 0
        if N > 0:
            # Если прыжок случился, вычисляем его размер
            # Для краш-теста мы форсируем прыжок, если он не выпал случайно
            jump = np.random.normal(mu_j, sigma_j) * N
            
        return S0 * np.exp(diffusion + jump)

    def inject_flash_crash(self, klines: list):
        """
        Превращает последнюю свечу в 'Свечу Мертона'.
        """
        if not klines:
            return klines
            
        last_kline = klines[-1]
        
        # Данные текущей свечи
        open_price = float(last_kline[1])
        current_close = float(last_kline[4])
        
        # 1. Z3 Снайпер находит идеальное дно
        # Мы ищем дно относительно цены открытия
        target_low = self.sniper.find_minimal_crash(open_price)
        
        # 2. Моделируем "Тень" свечи через Мертона
        # Мы хотим показать, что цена "гуляла" перед тем как упасть
        # Симулируем волатильность внутри свечи
        
        # Параметры для "Панической свечи"
        sigma = 0.5 # Высокая волатильность
        lambda_j = 100 # Высокая вероятность прыжка (мы же в crash_mode)
        
        # Генерируем "Close" цену используя Мертона, но ограничиваем её
        # Close должен быть ниже Open (красная свеча), но выше Low (Target)
        # Для простоты: Close - это "отскок дохлой кошки" от Target
        rebound = (open_price - target_low) * random.uniform(0.05, 0.15)
        new_close = target_low + rebound
        
        # Формируем свечу
        # High: Цена могла дернуться вверх на панике перед обвалом
        fake_pump = open_price * (1 + random.uniform(0.001, 0.005)) 
        new_high = max(open_price, fake_pump)
        
        # Обновляем структуру свечи
        last_kline[1] = str(open_price)
        last_kline[2] = str(new_high)      # High
        last_kline[3] = str(target_low)    # Low (Z3 Target)
        last_kline[4] = str(new_close)     # Close (Merton Rebound)
        
        # Также увеличиваем объем (Panic Selling)
        original_vol = float(last_kline[5])
        last_kline[5] = str(original_vol * random.uniform(5.0, 10.0))
        
        print(f"[Merton] INJECTED: Open={open_price} -> Low={target_low} (Target) -> Close={new_close}")
        
        klines[-1] = last_kline
        return klines
