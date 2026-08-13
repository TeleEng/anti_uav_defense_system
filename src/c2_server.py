from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import numpy as np
import asyncio

from src.signal_processing.sentinel_model import sentinel_ai
from src.signal_processing.demodulator import demodulate_bpsk
from src.control.mavlink_node import MavlinkNode

app = FastAPI(title="SENTINEL C-UAS Command & Control")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

mav_node = MavlinkNode()

@app.on_event("startup")
async def startup_event():
    # Load the trained FPFE-1D weights and the OSR Centroids
    sentinel_ai.load()

class ConnectionManager:
    def __init__(self):
        self.frontend_clients = []
        
    async def connect_frontend(self, websocket: WebSocket):
        await websocket.accept()
        self.frontend_clients.append(websocket)
        
    def disconnect_frontend(self, websocket: WebSocket):
        self.frontend_clients.remove(websocket)

    async def broadcast_to_frontends(self, message: dict):
        for connection in self.frontend_clients:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

@app.websocket("/ws/frontend")
async def websocket_frontend(websocket: WebSocket):
    await manager.connect_frontend(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_frontend(websocket)

@app.websocket("/ws/sim")
async def websocket_sim(websocket: WebSocket):
    """Receives data from the drone simulator and orchestrates the AI pipeline."""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            if payload["type"] == "RADAR_SWEEP":
                processed_drones = []
                for drone in payload["data"]:
                    processed = {"id": drone["id"], "x": drone["x"], "y": drone["y"]}
                    
                    if "raw_iq" in drone:
                        # 1. We intercepted a Wi-Fi burst from this drone
                        iq_array = np.array(drone["raw_iq"])
                        cfo = drone["carrier_freq"]
                        
                        # Auto-retry loading if it failed on startup
                        if not sentinel_ai.is_loaded:
                            sentinel_ai.load()
                            
                        if sentinel_ai.is_loaded:
                            label, dist = sentinel_ai.analyze_signal(iq_array)
                        else:
                            label, dist = "UNINITIALIZED", 999.0
                            
                        processed["classification"] = label
                        processed["osr_dist"] = dist
                        
                        # 3. Demodulation (Read physical payload)
                        demod_text = demodulate_bpsk(iq_array, cfo)
                        processed["payload"] = demod_text
                        
                        # 4. C2 Action Logic (Fail-Safe)
                        if "AUTHORIZED_DRONE" in label:
                            processed["action"] = "MAV_CMD_NAV_LAND TRANSMITTED"
                            mav_node.send_land_command()
                        else:
                            processed["action"] = "IGNORED (UNAUTHORIZED/UNINITIALIZED TARGET)"
                            
                        # Send snippet for UI graph
                        processed["iq_snippet"] = drone["iq_real"]
                        
                    processed_drones.append(processed)
                    
                # Broadcast the fully processed radar sweep to all connected Frontends
                await manager.broadcast_to_frontends({"type": "RADAR_UPDATE", "data": processed_drones})
                
    except WebSocketDisconnect:
        print("Simulator Disconnected.")
