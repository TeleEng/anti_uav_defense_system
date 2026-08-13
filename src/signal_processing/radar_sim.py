import numpy as np

def text_to_bits(text: str):
    bits = []
    for char in text:
        binval = bin(ord(char))[2:].zfill(8)
        bits.extend([int(b) for b in binval])
    return np.array(bits)

def generate_wifi_burst(drone_id: int, is_rogue: bool, payload_text: str, num_samples=4096):
    """
    Generates a BPSK modulated signal with specific hardware impairments.
    Includes the payload text.
    """
    t = np.linspace(0, 1, num_samples)
    
    # Convert text to bits and pad to match required length
    required_symbols = num_samples // 16
    bits = text_to_bits(payload_text)
    
    if len(bits) < required_symbols:
        # Pad with alternating bits
        padding = np.random.randint(0, 2, required_symbols - len(bits))
        bits = np.concatenate((bits, padding))
    else:
        bits = bits[:required_symbols]
        
    symbols = np.repeat(bits * 2 - 1, 16) # BPSK: -1 and 1
    
    # Inject Hardware Impairments
    if not is_rogue:
        # Authorized Drones (0, 1, 2)
        cfos = [10.1, 10.5, 9.8]
        phase_vars = [0.02, 0.03, 0.01]
        cfo = cfos[drone_id % 3]
        phase_var = phase_vars[drone_id % 3]
    else:
        # Rogue Drones
        cfo = 11.2 + np.random.uniform(-0.5, 0.5)
        phase_var = 0.25 # Huge phase noise variance
        
    phase_noise = np.random.normal(0, phase_var, num_samples)
    carrier = np.exp(1j * (2 * np.pi * cfo * t + phase_noise))
    
    signal = symbols * carrier
    
    # Add Channel Noise
    noise = (np.random.randn(num_samples) + 1j * np.random.randn(num_samples)) * 0.5
    rx = signal + noise
    
    return np.stack((np.real(rx), np.imag(rx)), axis=0), cfo
