"""T2: the death penalty of the environment (-10) and the recorder's death component Z, as an independent contract.

Part 1 drives the REAL PacmanEnv and states what the environment pays, with hand literals: death -10 on top of the step cost -0.01 and the pellet +1 when the
death step eats one, so the total is -10.01 or -9.01 -- the total reward is never -10, so a recorder that looked for r == -10 (or r < 0, or `terminated`)
would be wrong.  Part 2 feeds REAL environment trajectories to the recorder and checks D and Z against numbers written here (Z = -10 * 0.99^j_D), not derived
from the recorder.  Changing the recorder's death constant (or the way D is decided) turns these red.  Same-AI implementer and test author."""
import numpy as np
import pytest

from pacman_rl import window_diag as W
from pacman_rl.env import STANDARD, EnvConfig, PacmanEnv

GAMMA = 0.99


def episode(seed, policy_seed):
    env = PacmanEnv(STANDARD)
    env.reset(seed)
    rng = np.random.default_rng(policy_seed)
    out = []
    while True:
        _, r, term, trunc, info = env.step(int(rng.integers(0, 5)))
        out.append((r, term, trunc, bool(info["died"]), bool(info["won"])))
        if term or trunc:
            return out


@pytest.fixture(scope="module")
def trajectories():
    """Real random-policy episodes that end in a death: one where the death step eats a pellet, one where it does not (and a few more)."""
    with_pellet, without_pellet = [], []
    for seed in range(40000, 40400):  # smoke partition seeds only
        ep = episode(seed, seed)
        r, term, trunc, died, won = ep[-1]
        if died and len(ep) >= 4:
            (with_pellet if abs(r - (-9.01)) < 1e-9 else without_pellet if abs(r - (-10.01)) < 1e-9 else []).append(ep)
        if len(with_pellet) >= 2 and len(without_pellet) >= 2:
            break
    assert with_pellet and without_pellet, "the scan did not find both kinds of death in 400 episodes"
    return with_pellet, without_pellet


def test_environment_constants_are_the_ones_the_contract_assumes():
    assert (EnvConfig().r_death, EnvConfig().r_step, EnvConfig().r_gold, EnvConfig().r_win) == (-10.0, -0.01, 1.0, 10.0)
    assert W.DEATH_REWARD == -10.0  # the recorder's constant is the environment's penalty


def test_the_real_environment_pays_minus_10_01_or_minus_9_01_on_a_death_step_and_marks_it_in_info(trajectories):
    with_pellet, without_pellet = trajectories
    for ep in with_pellet:
        r, term, trunc, died, won = ep[-1]
        assert abs(r - (-0.01 + 1.0 - 10.0)) < 1e-9 and term and not trunc and died and not won  # step cost + pellet + death penalty
    for ep in without_pellet:
        r, term, trunc, died, won = ep[-1]
        assert abs(r - (-0.01 - 10.0)) < 1e-9 and term and died
    assert all(not any(s[3] for s in ep[:-1]) for ep in with_pellet + without_pellet)  # a death ends the episode: at most once, at the last step


def feed(ep, n=3):
    rec = W.WindowRecorder(1, n, GAMMA, 100_000)
    for t, (r, term, trunc, died, won) in enumerate(ep):
        rec.begin_batch(t, 0.5, np.array([False]))  # every executed action equals the greedy one: G chain
        rec.step(0, 0, r, term, trunc, died, won)
    return rec


@pytest.mark.parametrize("which", [0, 1], ids=["death with a pellet (-9.01)", "death without a pellet (-10.01)"])
def test_recorder_takes_D_from_info_and_Z_from_the_penalty_alone(trajectories, which):
    ep = trajectories[which][0]
    rec = feed(ep)
    d = rec.to_dict()
    # hand expectation: the death is the last step; windows starting 0, 1, 2 steps before it have h = 1, 2, 3 and Z = -10 * 0.99^(h-1)
    z = {1: -10.0, 2: -9.9, 3: -9.801}
    for h, want in z.items():
        cell = next(c for c in d["cells"] if c["h"] == h and c["n"] and c["C_g_l_d"][1][0][1])  # greedy start, no later deviation, death
        assert abs(cell["death_component_sum_g_l_d"][1][0][1] - want * cell["C_g_l_d"][1][0][1]) < 1e-9
    assert d["totals"]["death_events"] == 1 and d["rates"]["run"]["all"]["counts"]["N_D"] == 3  # the single death sits in exactly 3 emitted windows (h = 1, 2, 3)
    # the component never contains the pellet: -9.01 and -10.01 give identical Z
    assert abs(d["rates"]["run"]["all"]["death_component_sum_greedy_start_death"] - (-10.0 - 9.9 - 9.801)) < 1e-9


def winning_step():
    """A real environment arranged so that the next step eats the last pellet: terminated, won, not died, reward -0.01 + 1 + 10."""
    from pacman_rl.env import NEIGHBOURS, TOTAL_GOLD

    env = PacmanEnv(STANDARD)
    env.reset(40001)
    action, nxt = next((a, int(NEIGHBOURS[env.agent, a - 1])) for a in range(1, 5) if NEIGHBOURS[env.agent, a - 1] >= 0)
    env.gold[:] = False
    env.gold[nxt] = True
    env.score = TOTAL_GOLD - 1
    env.ghosts[:] = env.agent  # on the current cell: the agent leaves it, and the win check precedes any ghost move
    _, r, term, trunc, info = env.step(action)
    return (r, term, trunc, bool(info["died"]), bool(info["won"]))


def test_the_real_environment_pays_a_win_without_a_death_penalty():
    r, term, trunc, died, won = winning_step()
    assert abs(r - (-0.01 + 1.0 + 10.0)) < 1e-9 and term and won and not died and not trunc


def test_a_win_is_terminated_but_not_a_death_and_has_no_penalty_component():
    ep = [(0.0, False, False, False, False), winning_step()]
    d = feed(ep).to_dict()
    assert d["totals"]["death_events"] == 0 and d["rates"]["run"]["all"]["counts"]["N_D"] == 0
    assert d["rates"]["run"]["all"]["death_component_sum_greedy_start_death"] == 0.0
    assert sum(c["end_kind_counts"]["win"] for c in d["cells"]) == 2 and sum(c["end_kind_counts"]["death"] for c in d["cells"]) == 0


def test_changing_the_recorders_death_constant_turns_the_contract_red(trajectories, monkeypatch):
    ep = trajectories[0][0]
    good = feed(ep).to_dict()["rates"]["run"]["all"]["death_component_sum_greedy_start_death"]
    assert abs(good - (-10.0 - 9.9 - 9.801)) < 1e-9
    monkeypatch.setattr(W, "DEATH_REWARD", -5.0)
    monkeypatch.setattr(W.classify_window, "__defaults__", (-5.0,))  # the constant is bound as a default argument
    bad = feed(ep).to_dict()["rates"]["run"]["all"]["death_component_sum_greedy_start_death"]
    assert abs(bad - (-10.0 - 9.9 - 9.801)) > 1.0  # the literal expectation above would now fail
    assert W.DEATH_REWARD != EnvConfig().r_death
