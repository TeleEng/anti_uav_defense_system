import torch
import torch.nn as nn
import numpy as np
from scipy.spatial.distance import cosine

class Conv1DBlock(nn.Module):
    def __init__(self, in_ch, out_ch, k, p):
        super().__init__()
        self.conv = nn.Conv1d(in_ch, out_ch, k, padding=p)
        self.bn = nn.BatchNorm1d(out_ch)
        self.act = nn.ReLU(inplace=True)
    def forward(self, x):
        return self.act(self.bn(self.conv(x)))

class FPFE1D(nn.Module):
    """
    1D Fingerprint Pyramid Feature Extractor.
    Directly derived from the Contrastive Learning / SCSC Architecture.
    """
    def __init__(self, num_classes=3):
        super().__init__()
        self.block1 = nn.Sequential(Conv1DBlock(2, 16, 15, 7), Conv1DBlock(16, 16, 15, 7), nn.MaxPool1d(2))
        self.block2 = nn.Sequential(Conv1DBlock(16, 32, 17, 8), Conv1DBlock(32, 32, 17, 8), nn.MaxPool1d(2))
        self.block3 = nn.Sequential(Conv1DBlock(32, 64, 19, 9), Conv1DBlock(64, 64, 19, 9), nn.MaxPool1d(2))
        self.block4 = nn.Sequential(Conv1DBlock(64, 128, 21, 10), Conv1DBlock(128, 128, 21, 10), nn.MaxPool1d(2))
        self.block5 = nn.Sequential(Conv1DBlock(128, 256, 23, 11), Conv1DBlock(256, 256, 23, 11), nn.MaxPool1d(2))
        
        self.pool = nn.Sequential(nn.AdaptiveAvgPool1d(1), nn.Flatten())
        
        # Latent space embedding (256-D) used for Open Set Recognition distance calculation
        self.embedding_layer = nn.Sequential(
            nn.Linear(256, 256),
            nn.ReLU()
        )
        
        # Classifier for known classes
        self.classifier = nn.Linear(256, num_classes)
        
    def get_embedding(self, x):
        x = self.block1(x)
        x = self.block2(x)
        x = self.block3(x)
        x = self.block4(x)
        x = self.block5(x)
        x = self.pool(x)
        return self.embedding_layer(x)
        
    def forward(self, x):
        emb = self.get_embedding(x)
        return self.classifier(emb)

class SentinelOSR:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = FPFE1D(num_classes=3).to(self.device)
        self.centroids = None
        self.is_loaded = False
        
    def load(self):
        import os
        weights_path = os.path.join(os.path.dirname(__file__), '..', '..', 'sentinel_weights.pth')
        centroids_path = os.path.join(os.path.dirname(__file__), '..', '..', 'osr_centroids.npy')
        
        try:
            self.model.load_state_dict(torch.load(weights_path, map_location=self.device))
            self.model.eval()
            self.centroids = np.load(centroids_path)
            self.is_loaded = True
            print("SENTINEL FPFE-1D Model and OSR Centroids Loaded Successfully.")
        except Exception as e:
            print(f"Warning: Model not loaded: {e}. Please run 'python src/signal_processing/train_sentinel.py' first.")
            
    def analyze_signal(self, iq_data: np.ndarray):
        """
        Performs Open Set Recognition. 
        Returns (Classification_String, Latent_Distance).
        """
        if not self.is_loaded:
            return "UNINITIALIZED", 999.0
            
        tensor_data = torch.tensor(iq_data, dtype=torch.float32).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            emb = self.model.get_embedding(tensor_data).squeeze().cpu().numpy()
            
        # OSR Logic: Calculate Cosine distance to all known authorized drone centroids
        distances = [cosine(emb, c) for c in self.centroids]
        min_dist = min(distances)
        closest_id = np.argmin(distances)
        
        # OSR Decision Boundary: If the signal feature is far from known clusters, it's a Rogue Drone.
        OSR_THRESHOLD = 0.15
        
        if min_dist > OSR_THRESHOLD:
            return "UNKNOWN_ROGUE", round(min_dist, 4)
        else:
            return f"AUTHORIZED_DRONE_{closest_id}", round(min_dist, 4)

# Global instance
sentinel_ai = SentinelOSR()
