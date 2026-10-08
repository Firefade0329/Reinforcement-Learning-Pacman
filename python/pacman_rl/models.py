"""Q-networks of increasing depth.

* ``mlp``   - 2 x 128 on the 29-d engineered features (no spatial input).
* ``cnn2``  - 2 conv layers on the (C, 24, 32) grid; receptive field 5.  C = 7 with the BFS
              distance fields (default) or 5 for the raw planes (``obs="grid"``).
* ``resN``  - stem conv + N residual blocks (2N + 1 conv layers); receptive field 4N + 3
              (res2: 11, res4: 19, res8: 35 >= map width 32, i.e. whole-map view).

The conv nets are fully convolutional and read the Q-values out at Pacman's cell (dueling
optional); the MLP ends in a dueling head.  The conv trunks carry
no normalisation layer; instead the second conv of each residual block starts at zero so every
block is an identity at initialisation (Fixup-style), which keeps the 17-layer net trainable.
"""
from __future__ import annotations

import torch
import torch.nn as nn

from .env import NUM_ACTIONS
from .features import FEATURE_DIM
from .maps import H, W

ARCHS = ("mlp", "cnn2", "res2", "res4", "res8")


class Head(nn.Module):
    def __init__(self, in_dim: int, hidden: int, dueling: bool):
        super().__init__()
        self.dueling = dueling
        self.fc = nn.Sequential(nn.Linear(in_dim, hidden), nn.ReLU())
        self.adv = nn.Linear(hidden, NUM_ACTIONS)
        self.val = nn.Linear(hidden, 1) if dueling else None

    def forward(self, x):
        h = self.fc(x)
        a = self.adv(h)
        if not self.dueling:
            return a
        return self.val(h) + a - a.mean(dim=1, keepdim=True)


class ResBlock(nn.Module):
    def __init__(self, w: int):
        super().__init__()
        self.c1 = nn.Conv2d(w, w, 3, padding=1)
        self.c2 = nn.Conv2d(w, w, 3, padding=1)
        nn.init.zeros_(self.c2.weight)
        nn.init.zeros_(self.c2.bias)

    def forward(self, x):
        return torch.relu(x + self.c2(torch.relu(self.c1(x))))


class MLPQ(nn.Module):
    kind = "feat"

    def __init__(self, dueling: bool = True, hidden: int = 128):
        super().__init__()
        self.body = nn.Sequential(nn.Linear(FEATURE_DIM, hidden), nn.ReLU(), nn.Linear(hidden, hidden), nn.ReLU())
        self.head = Head(hidden, hidden, dueling)

    def forward(self, x):
        return self.head(self.body(x))


class ConvQ(nn.Module):
    """Fully convolutional Q-network.  The trunk maps (C, H, W) -> (6, H, W) (1 state value +
    5 advantages per cell, or 5 plain Q-values) and the output is read at Pacman's cell.  Filters
    are shared across positions, so every visited cell trains the same weights, and the
    receptive field of the read-out (see ``receptive_field``) is exactly the depth of the trunk."""

    kind = "grid"
    AGENT_CHANNEL = 2

    def __init__(self, blocks: int, width: int = 16, dueling: bool = True, in_ch: int = 7):
        super().__init__()
        self.dueling = dueling
        layers = [nn.Conv2d(in_ch, width, 3, padding=1), nn.ReLU()]
        if blocks == 0:  # cnn2
            layers += [nn.Conv2d(width, width, 3, padding=1), nn.ReLU()]
        else:
            layers += [ResBlock(width) for _ in range(blocks)]
        self.trunk = nn.Sequential(*layers)
        self.out = nn.Conv2d(width, NUM_ACTIONS + (1 if dueling else 0), 1)

    def forward(self, x):
        b = x.shape[0]
        idx = x[:, self.AGENT_CHANNEL].reshape(b, -1).argmax(dim=1)  # Pacman's flattened cell index
        y = self.out(self.trunk(x.contiguous(memory_format=torch.channels_last)))
        y = y.reshape(b, y.shape[1], -1)[torch.arange(b), :, idx]  # (b, 5 or 6)
        if not self.dueling:
            return y
        v, a = y[:, :1], y[:, 1:]
        return v + a - a.mean(dim=1, keepdim=True)


def build_model(arch: str, width: int = 16, dueling: bool = True, in_ch: int = 7) -> nn.Module:
    if arch == "mlp":
        return MLPQ(dueling)
    if arch == "cnn2":
        m = ConvQ(0, width, dueling, in_ch)
    elif arch.startswith("res"):
        m = ConvQ(int(arch[3:]), width, dueling, in_ch)
    else:
        raise ValueError(arch)
    return m.to(memory_format=torch.channels_last)


def receptive_field(arch: str) -> int:
    """Side length (cells) of the input region that influences the Q-values (read-out at Pacman)."""
    if arch == "mlp":
        return 0
    layers = 2 if arch == "cnn2" else 2 * int(arch[3:]) + 1
    return 2 * layers + 1
