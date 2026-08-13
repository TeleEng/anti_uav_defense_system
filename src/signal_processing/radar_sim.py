import numpy as np

def generate_wifi_burst(signal_type: str = "friendly", num_samples=4096):
    """
    Simulates a Wi-Fi physical layer I/Q burst from a drone.
    signal_type: 'friendly' or 'unknown'
    Returns a numpy array of shape (2, num_samples) representing I and Q channels.
    """
    # Create base carrier wave (complex)
    t = np.linspace(0, 1, num_samples)
    
    if signal_type == "friendly":
        # Simulate a specific known hardware signature (Authorized drone fleet)
        # Low hardware phase noise
        freq = 10.5
        phase_noise = np.random.normal(0, 0.05, num_samples)
    else:
        # Simulate unknown hardware (Rogue drone)
        # High, erratic hardware phase noise typical of cheap transmitters
        freq = 11.2
        phase_noise = np.random.normal(0, 0.25, num_samples)
        
    # Generate the baseband signal
    complex_signal = np.exp(1j * (2 * np.pi * freq * t + phase_noise))
    
    # Add AWGN (Additive White Gaussian Noise) simulating air channel
    noise = (np.random.randn(num_samples) + 1j * np.random.randn(num_samples)) * 0.1
    received_signal = complex_signal + noise
    
    # Separate into I (In-phase) and Q (Quadrature) channels for the 1D-FPFE neural network
    iq_data = np.stack((np.real(received_signal), np.imag(received_signal)), axis=0)
    
    # Final Shape is (2, 4096)
    return iq_data
