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

# ---------- Contrastive Center Loss ----------
class CenterLoss(nn.Module):
    """
    Minimizes intra-class embedding distance (pulls same-class embeddings toward
    their centroid) so that the OSR threshold boundary is tight and compact.
    """
    def __init__(self, num_classes, feat_dim, device):
        super().__init__()
        self.centers = nn.Parameter(torch.randn(num_classes, feat_dim).to(device))
        self.num_classes = num_classes

    def forward(self, embeddings, labels):
        batch_centers = self.centers[labels]
        diff = embeddings - batch_centers
        loss = 0.5 * (diff * diff).sum() / embeddings.size(0)
        return loss

def train():
    print(f"1. Generating Synthetic RF Fingerprint Dataset for 3 Authorized Drones...")
    X_train, y_train = generate_dataset(500)
    
    dataset = torch.utils.data.TensorDataset(X_train, y_train)
    dataloader = torch.utils.data.DataLoader(dataset, batch_size=32, shuffle=True)
    
    model = FPFE1D(num_classes=3).to(device)
    model.train()
    
    criterion_ce = nn.CrossEntropyLoss()
    criterion_center = CenterLoss(num_classes=3, feat_dim=256, device=device)
    
    # Separate optimizers: one for the model, one for the center loss centers
    optimizer_model = optim.Adam(model.parameters(), lr=0.001)
    optimizer_centers = optim.Adam(criterion_center.parameters(), lr=0.01)
    
    LAMBDA_CENTER = 0.1  # Weight for center loss
    
    print("2. Training SENTINEL FPFE-1D with CrossEntropy + Center Loss...")
    for epoch in range(15):
        total_loss = 0
        for data, labels in dataloader:
            data, labels = data.to(device), labels.to(device)
            
            optimizer_model.zero_grad()
            optimizer_centers.zero_grad()
            
            # Forward
            embeddings = model.get_embedding(data)
            outputs = model.classifier(embeddings)
            
            # Combined loss
            loss_ce = criterion_ce(outputs, labels)
            loss_center = criterion_center(embeddings, labels)
            loss = loss_ce + LAMBDA_CENTER * loss_center
            
            loss.backward()
            optimizer_model.step()
            optimizer_centers.step()
            
            total_loss += loss.item()
        print(f"   Epoch {epoch+1}/15 - Loss: {total_loss/len(dataloader):.4f}")
        
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
            print(f"   Centroid {d_id}: norm={np.linalg.norm(centroid):.4f}")
            
    centroids_path = os.path.join(os.path.dirname(__file__), '..', '..', 'osr_centroids.npy')
    np.save(centroids_path, np.array(centroids))
    
    # 5. Validate: test authorized vs rogue separation
    print("\n5. Validating OSR Discrimination...")
    from scipy.spatial.distance import cosine
    
    auth_dists = []
    for d_id in range(3):
        for _ in range(20):
            sig = generate_bpsk_burst(d_id)
            t = torch.tensor(sig, dtype=torch.float32).unsqueeze(0).to(device)
            with torch.no_grad():
                emb = model.get_embedding(t).squeeze().cpu().numpy()
            dists = [cosine(emb, c) for c in centroids]
            auth_dists.append(min(dists))
    
    rogue_dists = []
    for _ in range(40):
        # Generate rogue signal (different CFO & high phase noise, matching radar_sim.py)
        t_vec = np.linspace(0, 1, 4096)
        bits = np.random.randint(0, 2, 256)
        symbols = np.repeat(bits * 2 - 1, 16)
        cfo = 11.2 + np.random.uniform(-0.5, 0.5)
        phase_noise = np.random.normal(0, 0.25, 4096)
        carrier = np.exp(1j * (2 * np.pi * cfo * t_vec + phase_noise))
        signal = symbols * carrier
        noise = (np.random.randn(4096) + 1j * np.random.randn(4096)) * 0.5
        rx = signal + noise
        sig = np.stack((np.real(rx), np.imag(rx)), axis=0)
        
        t_tensor = torch.tensor(sig, dtype=torch.float32).unsqueeze(0).to(device)
        with torch.no_grad():
            emb = model.get_embedding(t_tensor).squeeze().cpu().numpy()
        dists = [cosine(emb, c) for c in centroids]
        rogue_dists.append(min(dists))
    
    auth_mean = np.mean(auth_dists)
    auth_max = np.max(auth_dists)
    rogue_mean = np.mean(rogue_dists)
    rogue_min = np.min(rogue_dists)
    
    print(f"   Authorized drones - mean dist: {auth_mean:.6f}, max: {auth_max:.6f}")
    print(f"   Rogue drones      - mean dist: {rogue_mean:.6f}, min: {rogue_min:.6f}")
    print(f"   Separation gap: {rogue_min - auth_max:.6f}")
    
    # Suggest threshold
    suggested_threshold = (auth_max + rogue_min) / 2
    print(f"   Suggested OSR threshold: {suggested_threshold:.4f}")
    
    print("\nSystem is ready. You can now launch the C-UAS Server.")

if __name__ == "__main__":
    train()
