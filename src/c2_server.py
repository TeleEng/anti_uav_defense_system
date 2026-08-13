from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.signal_processing.radar_sim import generate_wifi_burst
from src.signal_processing.sentinel_model import classify_drone_signal
from src.control.mavlink_node import MavlinkNode

app = FastAPI(title="SENTINEL C-UAS Command & Control")

# Enable CORS for our Eye-Catching Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the MAVLink node for UDP Wi-Fi communication
mav_node = MavlinkNode()

class SignalRequest(BaseModel):
    drone_type: str  # 'friendly' or 'unknown' (Used to simulate the scenario)

@app.post("/api/radar/scan")
async def perform_radar_scan(req: SignalRequest):
    """
    1. Simulates detecting a Wi-Fi burst from an incoming drone.
    2. Runs the FPFE-1D RF Fingerprinting model to classify it.
    3. Issues MAVLink commands if it is Friendly. Ignores if Unknown.
    """
    print(f"\n--- RADAR CONTACT DETECTED ---")
    
    # 1. Simulating the RF Burst (2x4096 I/Q Data)
    iq_data = generate_wifi_burst(signal_type=req.drone_type)
    
    # 2. RF Fingerprinting Classification (SENTINEL FPFE-1D)
    classification = classify_drone_signal(iq_data)
    print(f"SENTINEL Model Classification: {classification}")
    
    response = {
        "classification": classification,
        "action_taken": "NONE",
        "protocol": "MAVLink over Wi-Fi (UDP)"
    }
    
    # 3. Decision Logic (Safe landing only, no firing)
    if classification == "UNKNOWN_ROGUE":
        print("WARNING: Unknown RF Signature. Ignoring (No coordinates sent).")
        response["action_taken"] = "IGNORED (Safety Protocol: No landing coordinates sent to Unverified Target)"
    
    elif classification == "KNOWN_FRIENDLY":
        print("AUTHORIZED DRONE DETECTED. Issuing safe landing sequence...")
        mav_node.send_land_command()
        response["action_taken"] = "MAV_CMD_NAV_LAND TRANSMITTED"
        
    return response
