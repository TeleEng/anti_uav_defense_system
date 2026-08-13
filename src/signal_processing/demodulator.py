import numpy as np

def text_to_bits(text: str):
    bits = []
    for char in text:
        binval = bin(ord(char))[2:].zfill(8)
        bits.extend([int(b) for b in binval])
    return np.array(bits)

def bits_to_text(bits: np.ndarray):
    chars = []
    for i in range(0, len(bits), 8):
        byte = bits[i:i+8]
        if len(byte) < 8: break
        val = int("".join([str(b) for b in byte]), 2)
        if 32 <= val <= 126: # Printable ASCII
            chars.append(chr(val))
    return "".join(chars)

def demodulate_bpsk(iq_data: np.ndarray, carrier_freq: float) -> str:
    """
    Extracts the binary payload from the I/Q signal by stripping the carrier
    and thresholding the phase.
    """
    num_samples = iq_data.shape[1]
    t = np.linspace(0, 1, num_samples)
    
    # Reconstruct complex signal
    rx = iq_data[0] + 1j * iq_data[1]
    
    # Remove carrier (Downconversion)
    baseband = rx * np.exp(-1j * 2 * np.pi * carrier_freq * t)
    
    # Smooth over symbol length (16 samples per symbol)
    samples_per_symbol = 16
    smoothed = np.convolve(np.real(baseband), np.ones(samples_per_symbol)/samples_per_symbol, mode='valid')
    
    # Sample at the center of the symbol
    sampled = smoothed[::samples_per_symbol]
    
    # BPSK Decision threshold (greater than 0 is bit 1, else bit 0)
    bits = (sampled > 0).astype(int)
    
    # Convert to text
    text = bits_to_text(bits)
    return text if text else "<GARBLED DATA>"
