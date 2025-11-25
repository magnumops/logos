from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import httpx
import logging
import json
import asyncio
from typing import List

from logos.chaos_generators.main_generator import ChaosGenerator
from logos.recorder import BlackBox

# Настройка
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MagnumCockpit")

app = FastAPI(title="Magnum Control Center")
chaos = ChaosGenerator()
recorder = BlackBox()

# HTTP Клиент для Binance
CLIENT = httpx.AsyncClient()
REAL_BINANCE_URL = "https://api.binance.com"

# Глобальное состояние Хаоса (управляется через UI)
CHAOS_STATE = {
    "active": False,        # Включен ли режим атаки
    "intensity": 1.0,       # Множитель волатильности (для ползунка)
    "mode": "MERTON"        # Тип атаки
}

# Менеджер WebSockets (для рассылки данных на фронтенд)
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

# --- API Эндпоинты для Бота ---

@app.on_event("shutdown")
async def shutdown_event():
    await CLIENT.aclose()

@app.get("/api/v3/ping")
async def ping():
    return {}

@app.get("/api/v3/time")
async def time():
    resp = await CLIENT.get(f"{REAL_BINANCE_URL}/api/v3/time")
    return resp.json()

@app.get("/api/v3/klines")
async def get_klines(symbol: str, interval: str, limit: int = 500, crash_mode: bool = False):
    """
    Основной цикл данных.
    1. Получает данные с Binance.
    2. Если включен ХАОС (через UI или флаг) -> Впрыскивает яд.
    3. Логирует в BlackBox.
    4. Отправляет данные на UI (WebSocket) для отрисовки.
    """
    # Синхронизация флага из запроса и глобального состояния UI
    is_chaos_active = crash_mode or CHAOS_STATE["active"]
    
    url = f"{REAL_BINANCE_URL}/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    
    try:
        resp = await CLIENT.get(url, params=params)
        data = resp.json()
        
        if is_chaos_active:
            # Применяем Merton Model
            # В будущем передадим CHAOS_STATE['intensity'] в генератор
            data = chaos.inject_flash_crash(data)
        
        # Берем последнюю свечу для телеметрии
        last_candle = data[-1]
        
        # 1. Пишем в Черный Ящик
        recorder.log_kline(symbol, last_candle, is_poisoned=is_chaos_active)
        
        # 2. Отправляем на Фронтенд (Cockpit)
        await manager.broadcast({
            "type": "CANDLE_UPDATE",
            "data": {
                "time": last_candle[0],
                "open": float(last_candle[1]),
                "high": float(last_candle[2]),
                "low": float(last_candle[3]),
                "close": float(last_candle[4]),
                "is_poisoned": is_chaos_active
            }
        })
            
        return data
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=502, detail=str(e))

# --- API Эндпоинты для UI (Control Center) ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Слушаем команды от UI (если будут)
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/control/chaos")
async def set_chaos_params(params: dict):
    """Управление параметрами хаоса с фронтенда"""
    global CHAOS_STATE
    CHAOS_STATE.update(params)
    
    # Логируем изменение режима
    recorder.log_event("SYSTEM_CONFIG_CHANGE", CHAOS_STATE)
    
    logger.info(f"Chaos Config Updated: {CHAOS_STATE}")
    return {"status": "ok", "state": CHAOS_STATE}

# --- Раздача Статики (UI) ---

# Монтируем папку static для JS/CSS
app.mount("/static", StaticFiles(directory="/app/vendor/logos/logos/ui/static"), name="static")

@app.get("/dashboard", response_class=HTMLResponse)
async def read_root():
    # Отдаем index.html
    with open("/app/vendor/logos/logos/ui/index.html", "r") as f:
        return f.read()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
