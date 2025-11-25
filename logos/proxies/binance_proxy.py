from fastapi import FastAPI, Request, HTTPException
import httpx
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BinanceProxy")

app = FastAPI(title="Logos Fake Exchange")

# Реальный Binance API URL
REAL_BINANCE_URL = "https://api.binance.com"
CLIENT = httpx.AsyncClient()

@app.on_event("shutdown")
async def shutdown_event():
    await CLIENT.aclose()

@app.get("/api/v3/ping")
async def ping():
    """Проверка связи. Бот думает, что пингует Binance."""
    return {}

@app.get("/api/v3/time")
async def time():
    """Синхронизация времени."""
    resp = await CLIENT.get(f"{REAL_BINANCE_URL}/api/v3/time")
    return resp.json()

@app.get("/api/v3/klines")
async def get_klines(symbol: str, interval: str, limit: int = 500):
    """
    Эндпоинт свечей. 
    ЗДЕСЬ будет жить Chaos Generator.
    Пока работаем в режиме 'Transparent Proxy' (Прозрачный Прокси).
    """
    logger.info(f"Bot requesting klines for {symbol} {interval}")
    
    # 1. Получаем реальные данные
    url = f"{REAL_BINANCE_URL}/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    
    try:
        resp = await CLIENT.get(url, params=params)
        data = resp.json()
        
        # TODO: Внедрить logos.chaos_generators.inject_poison(data)
        
        return data
    except Exception as e:
        logger.error(f"Upstream error: {e}")
        raise HTTPException(status_code=502, detail="Binance Upstream Error")

if __name__ == "__main__":
    import uvicorn
    # Запускаем на порту 8080, чтобы бот мог подключиться к localhost:8080
    uvicorn.run(app, host="0.0.0.0", port=8080)
