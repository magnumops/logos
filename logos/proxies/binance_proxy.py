from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
import httpx
import logging
import json
import os
from typing import List
from glob import glob

from logos.chaos_generators.main_generator import ChaosGenerator
from logos.recorder import BlackBox
from logos.forensic_delegator import ForensicDelegator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MagnumCockpit")

app = FastAPI(title="Magnum Control Center")
chaos = ChaosGenerator()
recorder = BlackBox()
forensics = ForensicDelegator()

CLIENT = httpx.AsyncClient()
REAL_BINANCE_URL = "https://api.binance.com"
REPORTS_DIR = "/data/reports"

CHAOS_STATE = {"active": False, "intensity": 1.0, "mode": "MERTON"}

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

@app.on_event("shutdown")
async def shutdown_event():
    await CLIENT.aclose()

@app.get("/api/reports")
async def list_reports():
    files = glob(os.path.join(REPORTS_DIR, "*.pdf"))
    files.sort(key=os.path.getmtime, reverse=True)
    return [os.path.basename(f) for f in files]

@app.get("/api/reports/{filename}")
async def download_report(filename: str):
    file_path = os.path.join(REPORTS_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type='application/pdf', filename=filename)
    raise HTTPException(status_code=404, detail="Report not found")

@app.get("/api/v3/ping")
async def ping(): return {}

@app.get("/api/v3/time")
async def time():
    resp = await CLIENT.get(f"{REAL_BINANCE_URL}/api/v3/time")
    return resp.json()

@app.get("/api/v3/klines")
async def get_klines(symbol: str, interval: str, limit: int = 500, crash_mode: bool = False):
    is_chaos_active = crash_mode or CHAOS_STATE["active"]
    url = f"{REAL_BINANCE_URL}/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        resp = await CLIENT.get(url, params=params)
        data = resp.json()
        if is_chaos_active:
            data = chaos.inject_flash_crash(data)
        
        last_candle = data[-1]
        recorder.log_kline(symbol, last_candle, is_poisoned=is_chaos_active)
        
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

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/control/chaos")
async def set_chaos_params(params: dict):
    global CHAOS_STATE
    prev_active = CHAOS_STATE["active"]
    new_active = params.get("active", prev_active)
    
    CHAOS_STATE.update(params)
    recorder.log_event("SYSTEM_CONFIG_CHANGE", CHAOS_STATE)
    
    response = {"status": "ok", "state": CHAOS_STATE}
    
    # ЛОГИКА FREEMIUM: Анализ при остановке
    if prev_active and not new_active:
        logger.info("Crash deactivated. Initiating Post-Mortem...")
        evidence_csv = recorder.export_crash_evidence()
        
        if evidence_csv:
            try:
                verdict_data = forensics.run_investigation(evidence_csv)
                verdict_status = verdict_data.get("verdict", "UNKNOWN")
                
                response["verdict"] = verdict_status
                
                # УСЛОВИЕ 1: CRASH / LIQUIDITY VOID (Красный) -> Бесплатно
                if verdict_status != "CLEAN":
                    pdf_path = verdict_data.get("report_path")
                    if pdf_path:
                        pdf_filename = os.path.basename(pdf_path)
                        response["report_ready"] = True
                        response["report_url"] = f"/api/reports/{pdf_filename}"
                        response["paywall"] = False
                
                # УСЛОВИЕ 2: CLEAN / SUCCESS (Зеленый) -> Paywall
                else:
                    response["report_ready"] = False # Скрываем прямую ссылку
                    response["paywall"] = True
                    
            except Exception as e:
                logger.error(f"Forensics Failed: {e}")
                response["error"] = str(e)
                
        recorder.start_new_session()
        
    return response

app.mount("/static", StaticFiles(directory="/app/vendor/logos/logos/ui/static"), name="static")

@app.get("/dashboard", response_class=HTMLResponse)
async def read_root():
    with open("/app/vendor/logos/logos/ui/index.html", "r") as f:
        return f.read()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
