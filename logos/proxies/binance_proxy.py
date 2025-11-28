from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
import httpx
import logging
import json
import os
import shutil
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
EVIDENCE_DIR = "/data/evidence"
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(EVIDENCE_DIR, exist_ok=True)

CHAOS_STATE = {"active": False, "intensity": 1.0, "mode": "MERTON"}

class ConnectionManager:
    def __init__(self):
        self.active_connections = []
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try: await connection.send_json(message)
            except: pass
manager = ConnectionManager()

@app.on_event("shutdown")
async def shutdown_event(): await CLIENT.aclose()

@app.post("/api/v1/forensics/upload")
async def upload_evidence(file: UploadFile = File(...)):
    try:
        file_location = os.path.join(EVIDENCE_DIR, file.filename)
        with open(file_location, "wb") as buffer: shutil.copyfileobj(file.file, buffer)
        
        # Запускаем анализ
        result = forensics.run_investigation(file_location)
        
        if "error" in result:
            return {"status": "error", "message": result["error"]}
            
        pdf_filename = os.path.basename(result["report_path"])
        
        # Возвращаем ПОЛНЫЙ пакет данных для визуализации
        return {
            "status": "success",
            "verdict": result["verdict"],
            "z3_details": result["z3_details"],
            "report_url": f"/api/reports/{pdf_filename}",
            "chart_data": result["chart_data"],
            "death_point": result["death_point"]
        }
    except Exception as e:
        logger.error(f"Upload Failed: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/reports/{filename}")
async def download_report(filename: str):
    file_path = os.path.join(REPORTS_DIR, filename)
    if os.path.exists(file_path): return FileResponse(file_path, media_type='application/pdf', filename=filename)
    raise HTTPException(status_code=404, detail="Not found")

@app.get("/api/reports")
async def list_reports():
    files = glob(os.path.join(REPORTS_DIR, "*.pdf"))
    files.sort(key=os.path.getmtime, reverse=True)
    return [os.path.basename(f) for f in files]

@app.get("/api/v3/ping")
async def ping(): return {}
@app.get("/api/v3/time")
async def time():
    r = await CLIENT.get(f"{REAL_BINANCE_URL}/api/v3/time")
    return r.json()

@app.get("/api/v3/klines")
async def get_klines(symbol: str, interval: str, limit: int = 500, crash_mode: bool = False):
    active = crash_mode or CHAOS_STATE["active"]
    try:
        r = await CLIENT.get(f"{REAL_BINANCE_URL}/api/v3/klines", params={"symbol":symbol,"interval":interval,"limit":limit})
        data = r.json()
        if active: data = chaos.inject_flash_crash(data)
        lc = data[-1]
        recorder.log_kline(symbol, lc, is_poisoned=active)
        await manager.broadcast({"type":"CANDLE_UPDATE","data":{"time":lc[0],"open":float(lc[1]),"high":float(lc[2]),"low":float(lc[3]),"close":float(lc[4]),"is_poisoned":active}})
        return data
    except Exception as e: raise HTTPException(status_code=502, detail=str(e))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True: await websocket.receive_text()
    except: manager.disconnect(websocket)

@app.post("/control/chaos")
async def set_chaos_params(params: dict):
    global CHAOS_STATE
    prev = CHAOS_STATE["active"]
    new = params.get("active", prev)
    CHAOS_STATE.update(params)
    recorder.log_event("SYSTEM_CONFIG_CHANGE", CHAOS_STATE)
    
    # Auto-Analysis logic (simplified for clarity, mostly handled by frontend upload now)
    if prev and not new:
        recorder.start_new_session()
        
    return {"status": "ok", "state": CHAOS_STATE}

app.mount("/static", StaticFiles(directory="/app/vendor/logos/logos/ui/static"), name="static")
@app.get("/dashboard", response_class=HTMLResponse)
async def read_root():
    with open("/app/vendor/logos/logos/ui/index.html", "r") as f: return f.read()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
