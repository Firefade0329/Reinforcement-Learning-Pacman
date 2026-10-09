"""Action selection among tied Q values is whatever the frozen ``torch.argmax`` does (v0.3.2: ties are NOT assumed away).
These cases pin that behaviour on the real action-selection paths -- training (greedy_actions), evaluation (make_policy) and
the Double-DQN end action (td_target) -- for the torch version in use; they must be re-run on the formal machine (CUDA too)."""
import inspect

import numpy as np
import pytest
import torch

import pacman_rl.dqn as dqn
from nstep_harness import TableQ

CASES = [([0, 2, 2, 1, 0], 1), ([3, 3, 3, 3, 3], 0), ([5, 1, 5, 5, 2], 0), ([2, 2, 0, 0, 0], 0), ([0, 0, 0, 0, 1], 4), ([1, 0, 0, 0, 1], 0),
         ([-1, -1, -1, -1, -1], 0), ([0.0, -0.0, 0.0, 0.0, 0.0], 0)]
DEVICES = ["cpu"] + (["cuda"] if torch.cuda.is_available() else [])


class _Net(TableQ):
    """TableQ plus a dummy parameter, because make_policy locates the device through model.parameters()."""

    def __init__(self, table):
        super().__init__(table)
        self.dummy = torch.nn.Parameter(torch.zeros(1))


def model_for(rows, device="cpu"):
    """A network whose Q table row i is `rows[i]` for the one-hot observation i (5 states, 5 actions)."""
    table = np.zeros((5, 5), np.float32)
    table[: len(rows)] = rows
    return _Net(table).to(device)


def one_hot(n, k=5):
    return [np.eye(k, dtype=np.float32)[i] for i in range(n)]


@pytest.mark.parametrize("device", DEVICES)
def test_greedy_actions_on_the_training_path(device):
    rows = [q for q, _ in CASES[:5]]
    got = dqn.greedy_actions(model_for(rows, device), one_hot(len(rows)), torch.device(device))
    assert got.tolist() == [i for _, i in CASES[:5]]
    rows = [q for q, _ in CASES[5:]]
    got = dqn.greedy_actions(model_for(rows, device), one_hot(len(rows)), torch.device(device))
    assert got.tolist() == [i for _, i in CASES[5:]]


@pytest.mark.parametrize("device", DEVICES)
def test_make_policy_on_the_evaluation_path(device):
    rows = [q for q, _ in CASES[:5]]
    policy = dqn.make_policy(model_for(rows, device))
    assert policy(np.stack(one_hot(len(rows)))).tolist() == [i for _, i in CASES[:5]]


@pytest.mark.parametrize("device", DEVICES)
def test_double_dqn_end_action_uses_the_same_rule(device):
    """online Q [0,2,2,1,0] is tied between actions 1 and 2: the end action is index 1, so the TARGET value of index 1 (7)
    is used, not that of index 2 (100); an all-equal online row selects index 0."""
    online = model_for([[0, 2, 2, 1, 0], [3, 3, 3, 3, 3]], device)
    target = model_for([[5, 7, 100, 0, 0], [9, 50, 60, 70, 80]], device)
    o2 = torch.tensor(np.stack(one_hot(2)), device=device)
    y = dqn.td_target(online, target, torch.zeros(2, device=device), torch.ones(2, device=device), o2, True)
    assert y.cpu().tolist() == [7.0, 9.0]


def test_ties_are_resolved_to_the_first_maximal_index_on_random_cpu_batches():
    """Wider scan for the shipped torch version (CPU): argmax of tied rows == first index attaining the maximum."""
    g = torch.Generator().manual_seed(0)
    for _ in range(200):
        v = torch.randint(0, 3, (64, 5), generator=g).float()
        first = (v == v.max(dim=1, keepdim=True).values).float().argmax(dim=1)  # independent: argmax of the boolean mask is also "first"
        want = torch.tensor([int((row == row.max()).nonzero()[0, 0]) for row in v])
        assert torch.equal(v.argmax(dim=1), want) and torch.equal(first, want)


def test_training_loop_selects_greedy_actions_through_the_tested_helper():
    assert "greedy_actions(online, obs, device)" in inspect.getsource(dqn.train)


def test_the_behaviour_is_the_installed_torch_not_an_assumption():
    """If a future torch changed the tie rule this is where it would show: the cases above are the contract."""
    assert int(torch.tensor([[0.0, 2.0, 2.0, 1.0, 0.0]]).argmax(dim=1)) == 1
    assert int(torch.tensor([[7.0] * 5]).argmax(dim=1)) == 0
    print("torch", torch.__version__)
