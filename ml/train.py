"""
Wendy — CNN clap classifier training.

Usage
-----
    python3 ml/train.py
    python3 ml/train.py --epochs 60 --lr 0.0005

Expects
-------
    ml/data/clap/sample_*.npy   (positive examples)
    ml/data/noise/sample_*.npy  (negative examples)

Output
------
    ml/models/clap_cnn_<timestamp>.pt

Minimum recommended: 30 clap + 30 noise samples.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DATA_DIR   = ROOT / "ml" / "data"
MODELS_DIR = ROOT / "ml" / "models"


def load_dataset(
    n_mels:    int = 64,
    n_frames:  int = 32,
) -> tuple[np.ndarray, np.ndarray]:
    """Load .npy audio files → mel spectrograms (X) and labels (y)."""
    from ml.mel import compute_mel

    X_list, y_list = [], []

    for label, cls in (("clap", 1.0), ("noise", 0.0)):
        paths = sorted((DATA_DIR / label).glob("sample_*.npy"))
        if not paths:
            print(f"  ⚠  No samples for class «{label}» in {DATA_DIR / label}")
            continue
        for p in paths:
            audio = np.load(p).astype(np.float32)
            mel   = compute_mel(audio, n_frames=n_frames)  # (n_mels, n_frames)
            X_list.append(mel[None])   # add channel dim → (1, n_mels, n_frames)
            y_list.append(cls)
        print(f"  ✓ Loaded {len(paths):3d} «{label}» samples")

    if not X_list:
        raise SystemExit("No training data found. Run ml/collect.py first.")

    return np.stack(X_list).astype(np.float32), np.array(y_list, dtype=np.float32)


def train(epochs: int = 50, lr: float = 1e-3, batch_size: int = 32) -> Path:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset, random_split
    from ml.clap_cnn import _build_model

    print("\n  Wendy — training clap CNN\n")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    X, y = load_dataset()
    n_pos = int(y.sum())
    n_neg = len(y) - n_pos
    print(f"\n  Dataset: {len(y)} samples  ({n_pos} clap / {n_neg} noise)")

    if n_pos < 10 or n_neg < 10:
        print("  ⚠  Very few samples — collect at least 30 per class for good accuracy.")

    dataset = TensorDataset(
        torch.from_numpy(X[:, None] if X.ndim == 3 else X),  # ensure (N,1,H,W)
        torch.from_numpy(y),
    )

    val_size   = max(1, int(0.15 * len(dataset)))
    train_size = len(dataset) - val_size
    train_ds, val_ds = random_split(dataset, [train_size, val_size],
                                    generator=torch.Generator().manual_seed(42))

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader   = DataLoader(val_ds,   batch_size=batch_size)

    model     = _build_model()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    criterion = nn.BCEWithLogitsLoss()
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    best_val_loss = float("inf")
    best_state    = None

    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0.0
        for xb, yb in train_loader:
            optimizer.zero_grad()
            logits = model(xb).squeeze(-1)
            loss   = criterion(logits, yb)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * len(xb)
        train_loss /= train_size

        model.eval()
        val_loss, correct = 0.0, 0
        with torch.no_grad():
            for xb, yb in val_loader:
                logits = model(xb).squeeze(-1)
                val_loss += criterion(logits, yb).item() * len(xb)
                preds  = (torch.sigmoid(logits) >= 0.5).float()
                correct += (preds == yb).sum().item()
        val_loss /= val_size
        val_acc   = correct / val_size

        if epoch % 10 == 0 or epoch == 1:
            print(f"  [{epoch:3d}/{epochs}]  train={train_loss:.4f}  "
                  f"val={val_loss:.4f}  acc={val_acc:.1%}")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state    = {k: v.clone() for k, v in model.state_dict().items()}
        scheduler.step()

    # Save best model
    model.load_state_dict(best_state)
    ts       = time.strftime("%Y%m%d_%H%M%S")
    out_path = MODELS_DIR / f"clap_cnn_{ts}.pt"
    torch.save(model.state_dict(), out_path)
    print(f"\n  ✓ Saved → {out_path.relative_to(ROOT)}")
    print(f"  Best val loss: {best_val_loss:.4f}\n")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Wendy clap CNN")
    parser.add_argument("--epochs",     type=int,   default=50)
    parser.add_argument("--lr",         type=float, default=1e-3)
    parser.add_argument("--batch-size", type=int,   default=32)
    args = parser.parse_args()
    train(epochs=args.epochs, lr=args.lr, batch_size=args.batch_size)


if __name__ == "__main__":
    main()
