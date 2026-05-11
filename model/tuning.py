import optuna
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from sklearn.model_selection import train_test_split

# --- 1. Synthetic Data Generation ---
# Simulating CLIP embeddings (512 dims) behaving like "Delay" predictors
def generate_data(num_samples=1000):
    np.random.seed(42)
    # Feature 1-10 correlated with delay labels
    X = np.random.randn(num_samples, 512).astype(np.float32)
    
    # Label generation logic (simple linear separator + noise)
    weights = np.random.randn(512)
    # Make some features highly predictive
    weights[0:10] *= 5.0 
    
    logits = np.dot(X, weights)
    probs = 1 / (1 + np.exp(-logits))
    y = (probs > 0.5).astype(np.int64)
    
    return train_test_split(X, y, test_size=0.2, random_state=42)

X_train, X_val, y_train, y_val = generate_data()
X_train_tensor = torch.tensor(X_train)
y_train_tensor = torch.tensor(y_train)
X_val_tensor = torch.tensor(X_val)
y_val_tensor = torch.tensor(y_val)

# --- 2. Model Definition ---
class SimpleClassifier(nn.Module):
    def __init__(self, input_dim, hidden_dim, dropout_rate):
        super(SimpleClassifier, self).__init__()
        self.layer1 = nn.Linear(input_dim, hidden_dim)
        self.dropout = nn.Dropout(dropout_rate)
        self.relu = nn.ReLU()
        self.layer2 = nn.Linear(hidden_dim, 2) # Binary output
        
    def forward(self, x):
        x = self.layer1(x)
        x = self.relu(x)
        x = self.dropout(x)
        x = self.layer2(x)
        return x

# --- 3. Objective Function ---
def objective(trial):
    # Hyperparameters to tune
    lr = trial.suggest_float("lr", 1e-5, 1e-1, log=True)
    hidden_dim = trial.suggest_int("hidden_dim", 32, 128)
    dropout = trial.suggest_float("dropout", 0.1, 0.5)
    batch_size = trial.suggest_categorical("batch_size", [16, 32, 64])
    
    model = SimpleClassifier(512, hidden_dim, dropout)
    optimizer = optim.Adam(model.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss()
    
    # Training Loop (Short for demo)
    epochs = 5
    for epoch in range(epochs):
        model.train()
        indices = torch.randperm(len(X_train_tensor))
        for i in range(0, len(X_train_tensor), batch_size):
            batch_idx = indices[i:i+batch_size]
            batch_X = X_train_tensor[batch_idx]
            batch_y = y_train_tensor[batch_idx]
            
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            
    # Validation
    model.eval()
    with torch.no_grad():
        outputs = model(X_val_tensor)
        _, predicted = torch.max(outputs.data, 1)
        correct = (predicted == y_val_tensor).sum().item()
        accuracy = correct / len(y_val_tensor)
        
    return accuracy

# --- 4. Main Execution ---
if __name__ == "__main__":
    print("Starting Bayesian Optimization with Optuna...")
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=15)
    
    print("\noptimization Complete!")
    print(f"Best Accuracy: {study.best_value:.4f}")
    print("Best Hyperparameters:")
    for key, value in study.best_params.items():
        print(f"  {key}: {value}")
