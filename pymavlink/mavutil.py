class _Mav:
    def command_long_send(self, *args, **kwargs):
        pass

class _MavlinkConstants:
    """Mock MAVLink protocol constants."""
    MAV_CMD_NAV_LAND = 21

class _Master:
    def __init__(self):
        self.mav = _Mav()
        self.target_system = 1
        self.target_component = 1

# Expose as mavutil.mavlink so mavutil.mavlink.MAV_CMD_NAV_LAND works
mavlink = _MavlinkConstants()

def mavlink_connection(device):
    return _Master()
