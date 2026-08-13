import pytest
import numpy as np
import sys
import os

# Add root project dir to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.signal_processing.demodulator import demodulate_bpsk, text_to_bits
from src.signal_processing.radar_sim import generate_wifi_burst

def test_text_to_bits():
    bits = text_to_bits("A")
    # 'A' is 65 in ASCII -> 01000001 in binary
    assert list(bits) == [0, 1, 0, 0, 0, 0, 0, 1]

def test_demodulator():
    payload = "MAVLINK-TEST-PAYLOAD"
    # Generate BPSK burst with ID 0 (Friendly), Not rogue
    iq_data, cfo = generate_wifi_burst(drone_id=0, is_rogue=False, payload_text=payload)
    
    # Demodulate physical layer back to text
    decoded_text = demodulate_bpsk(iq_data, cfo)
    
    # We check if the payload is found inside the extracted string (since it pads randomly)
    assert payload in decoded_text
