import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import os
import sys

# Setup GPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")

# Ensure we can import from src
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))
from src.signal_processing.sentinel_model import FPFE1D

def generate_bpsk_burst(drone_id: int, num_samples=4096):
    """
    Generates a BPSK modulated signal with specific hardware impairments (RF Fingerprints)
    for 3 distinct 'Authorized' drones.
    """
    t = np.linspace(0, 1, num_samples)
    
    # Base BPSK payload
    bits = np.random.randint(0, 2, num_samples // 16)
    symbols = np.repeat(bits * 2 - 1, 16) # -1 and 1
    
    # Inject Drone-Specific Hardware Impairments (CFO & Phase Noise)
    if drone_id == 0:
        cfo = 10.1; phase_var = 0.02
    elif drone_id == 1:
        cfo = 10.5; phase_var = 0.03
    elif drone_id == 2:
        cfo = 9.8; phase_var = 0.01
        
    phase_noise = np.random.normal(0, phase_var, num_samples)
    carrier = np.exp(1j * (2 * np.pi * cfo * t + phase_noise))
    
    signal = symbols * carrier
    
    # Add Channel Noise (AWGN)
    noise = (np.random.randn(num_samples) + 1j * np.random.randn(num_samples)) * 0.5
    rx = signal + noise
    
    return np.stack((np.real(rx), np.imag(rx)), axis=0)

def generate_dataset(samples_per_class=200):
    X, y = [], []
    for d_id in range(3): # 3 Authorized Drones
        for _ in range(samples_per_class):
            X.append(generate_bpsk_burst(d_id))
            y.append(d_id)
    
    return torch.tensor(np.array(X), dtype=torch.float32), torch.tensor(np.array(y), dtype=torch.long)

def train():
    print(f"1. Generating Synthetic RF Fingerprint Dataset for 3 Authorized Drones...")
    X_train, y_train = generate_dataset(500)
    
    dataset = torch.utils.data.TensorDataset(X_train, y_train)
    dataloader = torch.utils.data.DataLoader(dataset, batch_size=32, shuffle=True)
    
    model = FPFE1D(num_classes=3).to(device)
    model.train()
    
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    print("2. Training SENTINEL FPFE-1D Model...")
    for epoch in range(10):
        total_loss = 0
        for data, labels in dataloader:
            data, labels = data.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(data)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        print(f"   Epoch {epoch+1}/10 - Loss: {total_loss/len(dataloader):.4f}")
        
    print("3. Training Complete. Saving Weights...")
    weights_path = os.path.join(os.path.dirname(__file__), '..', '..', 'sentinel_weights.pth')
    torch.save(model.state_dict(), weights_path)
    
    print("4. Extracting OSR Centroids for Contrastive Distance Matching...")
    model.eval()
    centroids = []
    with torch.no_grad():
        for d_id in range(3):
            class_data = X_train[y_train == d_id].to(device)
            embeddings = model.get_embedding(class_data)
            centroid = embeddings.mean(dim=0).cpu().numpy()
            centroids.append(centroid)
            
    centroids_path = os.path.join(os.path.dirname(__file__), '..', '..', 'osr_centroids.npy')
    np.save(centroids_path, np.array(centroids))
    print("System is ready. You can now launch the C-UAS Server.")

if __name__ == "__main__":
    train()
