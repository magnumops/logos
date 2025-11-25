from fastapi import FastAPI, Request, HTTPException, Query
import httpx
import logging
from logos.chaos_generators.main_generator import ChaosGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BinanceProxy")

app = FastAPI(title="Logos Fake Exchange")
chaos = ChaosGenerator()
CLIENT = httpx.AsyncClient()
REAL_BINANCE_URL = "https://api.binance.com"

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
    Параметр crash_mode=True активирует атаку.
    В реальном боевом режиме мы бы включали это через админку,
    но для теста передаем флагом.
    """
    logger.info(f"Request: {symbol} {interval} (Crash: {crash_mode})")
    
    url = f"{REAL_BINANCE_URL}/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    
    try:
        resp = await CLIENT.get(url, params=params)
        data = resp.json()
        
        if crash_mode:
            # Впрыскиваем яд в последнюю свечу
            data = chaos.inject_flash_crash(data)
            
        return data
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=502, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
