from pymavlink import mavutil
import time

def start_simulated_drone():
    # Bind to the UDP port that the C2 server will send commands to
    connection_string = "udpin:127.0.0.1:14550"
    print(f"=====================================")
    print(f"[DRONE SIMULATOR] Powered On.")
    print(f"[DRONE SIMULATOR] Listening on {connection_string} via Wi-Fi UDP...")
    print(f"=====================================")
    
    drone = mavutil.mavlink_connection(connection_string)
    
    while True:
        # Wait for a command over the Wi-Fi link
        msg = drone.recv_match(blocking=True)
        
        if not msg:
            continue
            
        if msg.get_type() == "COMMAND_LONG":
            if msg.command == mavutil.mavlink.MAV_CMD_NAV_LAND:
                print("\n>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                print("[DRONE] OVERRIDE RECEIVED: MAV_CMD_NAV_LAND")
                print("[DRONE] Initiating safe descent sequence...")
                time.sleep(1.5)
                print("[DRONE] Touchdown confirmed. Motors disarmed.")
                print("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<\n")
                
if __name__ == "__main__":
    start_simulated_drone()
