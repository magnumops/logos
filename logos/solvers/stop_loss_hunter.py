import z3
import math

class StopLossHunter:
    """
    Модуль 'Снайпер'.
    Использует Z3 для поиска оптимальной точки краха (Crash Target).
    Цель: Найти минимальное падение цены, которое активирует каскад стоп-лоссов.
    """
    
    def find_minimal_crash(self, current_price: float, volatility: float = 0.02) -> float:
        """
        Вычисляет Target Price для атаки.
        Гипотеза: Большинство ботов ставят стопы на круглых уровнях или % от входа.
        Мы ищем ближайший 'Магнитный уровень' (Likely Stop Loss) внизу.
        """
        
        # Эвристика: Уровни ликвидации часто находятся на -1%, -2%, -5% или на круглых числах.
        # Для MVP упростим задачу Z3:
        # Найти dX (падение), такое что (Price - dX) является "Круглым числом" или "Критическим уровнем".
        
        solver = z3.Optimize() # Используем Optimize для минимизации dX
        
        # Переменные
        dX = z3.Real('dX')
        target_price = z3.Real('target_price')
        
        # Константы
        curr = float(current_price)
        
        # Ограничения (Constraints)
        solver.add(target_price == curr - dX)
        solver.add(dX > 0) # Цена должна падать
        
        # Ограничение "Разумного краха": Не падать больше чем на 10% (иначе это не реалистично для одной свечи)
        solver.add(dX <= curr * 0.10) 
        
        # Ограничение "Охоты": Цель должна быть "вкусной".
        # Пусть "Вкусный уровень" - это число, кратное 100 (для BTC) или 10 (для ETH).
        # Z3 работает с Integers/Reals. Чтобы проверить кратность, используем % (mod).
        # target_price % 100 == 0
        solver.add(z3.ToInt(target_price) % 100 == 0)
        
        # Целевая функция: Найти МИНИМАЛЬНОЕ падение, которое достигает цели.
        # Мы хотим сбить стопы "малой кровью".
        solver.minimize(dX)
        
        if solver.check() == z3.sat:
            model = solver.model()
            # Конвертируем дробь (Rational) в float
            crash_size = float(model[dX].numerator_as_long()) / float(model[dX].denominator_as_long())
            target = curr - crash_size
            return target
        else:
            # Если Z3 не нашел решения (странно), просто падаем на 5%
            return curr * 0.95
