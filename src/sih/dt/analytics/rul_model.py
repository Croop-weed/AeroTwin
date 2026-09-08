import torch
import torch.nn as nn

class AeroTwinRULModel(nn.Module):
    """
    Dual Encoder LSTM for Remaining Useful Life (RUL) Estimation.
    Allows pretraining on a 14-sensor dataset (C-MAPSS) and fine-tuning
    on a 6-sensor dataset (Simulator Residuals) by sharing the core LSTM physics engine.
    """
    def __init__(self, cmapss_dim=14, sim_dim=6, latent_dim=32, hidden_size=64):
        super().__init__()
        
        # Door A: C-MAPSS Encoder (MLP for non-linear mapping)
        self.cmapss_encoder = nn.Sequential(
            nn.Linear(cmapss_dim, 64),
            nn.ReLU(),
            nn.Linear(64, latent_dim)
        )
        
        # Door B: Simulator Encoder (MLP for non-linear mapping)
        self.sim_encoder = nn.Sequential(
            nn.Linear(sim_dim, 64),
            nn.ReLU(),
            nn.Linear(64, latent_dim)
        )
        
        # The Shared Brain
        self.lstm = nn.LSTM(input_size=latent_dim, hidden_size=hidden_size, batch_first=True)
        
        # Final output scalar
        self.rul_predictor = nn.Linear(hidden_size, 1)
        
    def forward_cmapss(self, x):
        """Passes C-MAPSS sequences (Batch, Seq_Len, 14) -> RUL"""
        encoded = self.cmapss_encoder(x)
        lstm_out, _ = self.lstm(encoded)
        # Take the output of the last timestep
        last_out = lstm_out[:, -1, :] 
        rul = self.rul_predictor(last_out)
        return rul

    def forward_sim(self, x):
        """Passes Simulator sequences (Batch, Seq_Len, 6) -> RUL"""
        encoded = self.sim_encoder(x)
        lstm_out, _ = self.lstm(encoded)
        # Take the output of the last timestep
        last_out = lstm_out[:, -1, :] 
        rul = self.rul_predictor(last_out)
        return rul

    def freeze_shared_core(self):
        """Freezes the LSTM and predictor to preserve pretrained physics."""
        for param in self.lstm.parameters():
            param.requires_grad = False
        for param in self.rul_predictor.parameters():
            param.requires_grad = False
            
    def unfreeze_shared_core(self):
        """Unfreezes the LSTM and predictor."""
        for param in self.lstm.parameters():
            param.requires_grad = True
        for param in self.rul_predictor.parameters():
            param.requires_grad = True
