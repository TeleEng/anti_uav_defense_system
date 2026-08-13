class _Mav:
    def command_long_send(self, *args, **kwargs):
        pass

class _Master:
    def __init__(self):
        self.mav = _Mav()
        self.target_system = 1
        self.target_component = 1

def mavlink_connection(device):
    return _Master()
