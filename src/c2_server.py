from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import numpy as np
import asyncio

from src.signal_processing.sentinel_model import sentinel_ai
from src.signal_processing.demodulator import demodulate_bpsk
from src.control.mavlink_node import MavlinkNode

app = FastAPI(title="SENTINEL C-UAS Command & Control")

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

mav_node = MavlinkNode()

# Serve the main index.html at the root
@app.get("/")
async def serve_frontend():
    return FileResponse(os.path.join(os.path.dirname(__file__), "../frontend/index.html"))

@app.get("/style.css")
async def serve_css():
    return FileResponse(os.path.join(os.path.dirname(__file__), "../frontend/style.css"))

@app.get("/app.js")
async def serve_js():
    return FileResponse(os.path.join(os.path.dirname(__file__), "../frontend/app.js"))

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
            print("Received data from simulator!")
            payload = json.loads(data)
            
            if payload["type"] == "RADAR_SWEEP":
                processed_drones = []
                for drone in payload["data"]:
                    processed = {"id": drone["id"], "x": drone["x"], "y": drone["y"]}
                    
                    if "raw_iq" in drone:
                        print(f"[{drone['id']}] Intercepted raw_iq burst!")
                        try:
                            # 1. We intercepted a Wi-Fi burst from this drone
                            iq_array = np.array(drone["raw_iq"])
                            cfo = drone["carrier_freq"]
                            
                            # Auto-retry loading if it failed on startup
                            if not sentinel_ai.is_loaded:
                                print("AI not loaded, attempting to load...")
                                sentinel_ai.load()
                                
                            if sentinel_ai.is_loaded:
                                label, dist = sentinel_ai.analyze_signal(iq_array)
                            else:
                                label, dist = "UNINITIALIZED", 999.0
                                
                            print(f"[{drone['id']}] AI Classification Result: {label} (Distance: {dist})")
                                
                            processed["classification"] = label
                            processed["osr_dist"] = dist
                            
                            # 3. Demodulation (Read physical payload)
                            demod_text = demodulate_bpsk(iq_array, cfo)
                            processed["payload"] = demod_text
                            
                            # 4. C2 Action Logic (Fail-Safe)
                            if "AUTHORIZED_DRONE" in label:
                                processed["action"] = "MAV_CMD_NAV_LAND TRANSMITTED"
                                try:
                                    mav_node.send_land_command()
                                except Exception:
                                    pass  # MAVLink send is best-effort
                            else:
                                processed["action"] = "IGNORED (UNAUTHORIZED/UNINITIALIZED TARGET)"
                                
                            # Send snippet for UI graph
                            processed["iq_snippet"] = drone["iq_real"]
                        except Exception as e:
                            print(f"Processing error for drone {drone.get('id')}: {e}")
                            processed["classification"] = "ERROR"
                            processed["action"] = f"PROCESSING ERROR: {e}"
                        
                    processed_drones.append(processed)
                    
                # Broadcast the fully processed radar sweep to all connected Frontends
                await manager.broadcast_to_frontends({"type": "RADAR_UPDATE", "data": processed_drones})
                
    except WebSocketDisconnect:
        print("Simulator Disconnected.")

