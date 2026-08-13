import asyncio
import websockets
import json
import random
import math
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
from src.signal_processing.radar_sim import generate_wifi_burst

# Define the swarm (3 authorized, 2 rogue)
drones = [
    {"id": 0, "name": "AUTH-ALPHA", "is_rogue": False, "x": 100, "y": 100, "vx": 2.5, "vy": 1.2},
    {"id": 1, "name": "AUTH-BRAVO", "is_rogue": False, "x": 800, "y": 200, "vx": -1.8, "vy": 2.1},
    {"id": 2, "name": "AUTH-CHARLIE", "is_rogue": False, "x": 500, "y": 800, "vx": 0.5, "vy": -3.0},
    {"id": 3, "name": "UNKNOWN-X", "is_rogue": True, "x": 900, "y": 900, "vx": -3.5, "vy": -2.0},
    {"id": 4, "name": "UNKNOWN-Y", "is_rogue": True, "x": 100, "y": 900, "vx": 2.0, "vy": -4.0},
]

async def drone_movement_loop():
    """
    Simulates the movement of the drone swarm and broadcasts 
    their physical location to the C2 server over WebSockets.
    """
    uri = "ws://127.0.0.1:8000/ws/sim"
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                print("Connected to C2 Radar Server.")
                while True:
                    updates = []
                    for d in drones:
                        # Update positions
                        d["x"] += d["vx"]
                        d["y"] += d["vy"]
                        
                        # Bounce off walls (1000x1000 grid)
                        if d["x"] < 0 or d["x"] > 1000: d["vx"] *= -1
                        if d["y"] < 0 or d["y"] > 1000: d["vy"] *= -1
                        
                        # Periodically 'transmit' a Wi-Fi burst
                        if random.random() < 0.15: # 15% chance per tick to broadcast
                            payload = f"MAC:{d['name']}-OK"
                            iq, cfo = generate_wifi_burst(d["id"], d["is_rogue"], payload)
                            updates.append({
                                "id": d["id"],
                                "x": round(d["x"]),
                                "y": round(d["y"]),
                                "iq_real": iq[0].tolist()[0:150], # Snippet for UI drawing
                                "carrier_freq": cfo,
                                "raw_iq": iq.tolist() # The C2 server will run FPFE-1D on this
                            })
                        else:
                            updates.append({
                                "id": d["id"],
                                "x": round(d["x"]),
                                "y": round(d["y"])
                            })
                            
                    print(f"Sending radar sweep with {len(updates)} drone updates...", flush=True)
                    await websocket.send(json.dumps({"type": "RADAR_SWEEP", "data": updates}))
                    await asyncio.sleep(0.5) # Radar updates every 500ms
        except Exception as e:
            print(f"Waiting for C2 Server... ({e})")
            await asyncio.sleep(2)

if __name__ == "__main__":
    print("Spawning Drone Swarm (3 Authorized, 2 Rogue)...")
    asyncio.run(drone_movement_loop())
