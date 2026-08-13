from pymavlink import mavutil
import time

class MavlinkNode:
    def __init__(self, target_ip="127.0.0.1", port=14550):
        # We use UDP for robust Wi-Fi communication. 
        # UDP is connectionless, meaning it is inherently tolerant to packet loss
        # which is vital for high-speed drone telemetry.
        connection_string = f"udpout:{target_ip}:{port}"
        print(f"Initializing MAVLink C2 Link on {connection_string}...")
        self.master = mavutil.mavlink_connection(connection_string)
        
    def send_land_command(self):
        """
        Issues a MAV_CMD_NAV_LAND command to safely land an authorized drone.
        """
        print("TRANSMITTING UDP: MAV_CMD_NAV_LAND...")
        # Send a COMMAND_LONG message to the flight controller
        self.master.mav.command_long_send(
            1, # Target system ID (Default 1)
            1, # Target component ID (Default 1)
            mavutil.mavlink.MAV_CMD_NAV_LAND, # The command ID
            0, # Confirmation
            0, 0, 0, 0, 0, 0, 0 # Empty parameters (force landing at current location)
        )
        print("Landing coordinates transmitted via Wi-Fi.")
