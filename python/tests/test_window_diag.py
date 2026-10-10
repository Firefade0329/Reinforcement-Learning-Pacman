"""Window diagnostics B1 / B2: the recorder against hand-computed windows (proposal section 8 table).

Expected values are written out by hand below: for each scripted episode the list of windows (h, G_start, L, D, T, J, P, Z, end kind) that a
reader derives from the definitions -- they are never taken from the recorder.  The implementer of the recorder and the author of these
tests are the SAME AI model; the independent hand computations are not an independent human audit (reviewer / date fields stay empty).

Notation: a script step is (G, reward, term, trunc, died, won) with G = the executed action equals the selected greedy action (U = 1 - G)."""
import json
import math

import numpy as np
import pytest
import torch

from pacman_rl import window_diag as W
from pacman_rl.replay import NStepReplay

GAMMA = 0.99
ORIGINAL = W.classify_window  # the unmutated classifier, captured at import


def G(g=1, r=0.0, term=False, trunc=False, died=False, won=False):
    return (g, r, term, trunc, died, won)


DEATH = dict(r=-10.0, term=True, died=True)


def drive(scripts, n=3, start0=0, eps=0.5, replay=None, total=100_000):
    """Feed one script (a list of steps) per environment, one step per environment and batch, in lock step.  Environments whose script
    is shorter just stop.  Returns the recorder."""
    rec = W.WindowRecorder(len(scripts), n, GAMMA, total)
    if replay is not None:
        replay.on_emit = rec.on_emit
    env_steps = start0
    for t in range(max(len(s) for s in scripts)):
        live = [i for i, s in enumerate(scripts) if t < len(s)]
        mism = np.array([(not scripts[i][t][0]) if i in live else False for i in range(len(scripts))])
        rec.begin_batch(env_steps, eps, mism)
        for i in live:
            g, r, term, trunc, died, won = scripts[i][t]
            rec.step(i, 0, r, term, trunc, died, won)
            if replay is not None:
                replay.add(i, np.zeros(1, np.float32), 0, r, np.zeros(1, np.float32), term, trunc)
        env_steps += len(scripts)
    return rec


def tally(windows):
    """Aggregate hand-listed windows (h, g, l, d, t, j, p, z, end) per h into the recorder's cell layout."""
    out = {}
    for h, g, l, d, t, j, p, z, end in windows:
        c = out.setdefault(h, {"n": 0, "C": np.zeros((2, 2, 2), int), "z": np.zeros((2, 2, 2)), "J": 0, "P": 0, "end": dict.fromkeys(W.END_KINDS, 0)})
        c["n"] += 1
        c["C"][g, l, d] += 1
        c["z"][g, l, d] += z
        c["J"] += j
        c["P"] += p
        c["end"][end] += 1
        assert t == (g and l and d)  # the hand table itself is consistent: T = G_start AND L AND D
    return out


def expect(rec, windows, pending=0, bin_=0):
    want = tally(windows)
    got = {h: c for (b, h), c in rec.cells.items() if b == bin_}
    assert set(got) == set(want), (sorted(got), sorted(want))
    for h, w in want.items():
        c = got[h]
        assert c["n"] == w["n"] and np.array(c["C"]).tolist() == w["C"].tolist() and c["J"] == w["J"] and c["P"] == w["P"] and c["end"] == w["end"], h
        assert np.allclose(np.array(c["z"]), w["z"], atol=1e-12), h
    assert sum(rec.pending_by_bin().values()) == pending
    assert rec.integrity()["complete"] is True, rec.integrity()


# (h, G_start, L, D, T, J, P, Z, end kind)
def row_full_greedy_chain():
    rec = drive([[G(), G(), G()]])
    expect(rec, [(3, 1, 0, 0, 0, 0, 0, 0.0, "nonterminal")], pending=2)  # one h3 window, two starts still queued (n=3)
    return rec


def row_death_same_step_deviation():
    rec = drive([[G(), G(), G(0, **DEATH)]])
    expect(rec, [(3, 1, 1, 1, 1, 1, 0, -9.801, "death"), (2, 1, 1, 1, 1, 1, 0, -9.9, "death"), (1, 0, 0, 1, 0, 0, 0, -10.0, "death")])
    assert rec.death_events == 1 and rec.to_dict()["rates"]["run"]["all"]["counts"]["N_D"] == 3
    return rec


def row_deviation_then_death():
    rec = drive([[G(), G(0), G(1, **DEATH)]])
    expect(rec, [(3, 1, 1, 1, 1, 0, 1, -9.801, "death"), (2, 0, 0, 1, 0, 0, 0, -9.9, "death"), (1, 1, 0, 1, 0, 0, 0, -10.0, "death")])
    assert rec.to_dict()["rates"]["run"]["all"]["counts"]["N_D"] == 3
    return rec


def row_two_step_truncation():
    rec = drive([[G(), G(0, trunc=True)]])
    expect(rec, [(2, 1, 1, 0, 0, 0, 0, 0.0, "truncated"), (1, 0, 0, 0, 0, 0, 0, 0.0, "truncated")])
    assert rec.death_events == 0
    return rec


def row_win():
    rec = drive([[G(), G(1, r=5.0, term=True, won=True)]])
    expect(rec, [(2, 1, 0, 0, 0, 0, 0, 0.0, "win"), (1, 1, 0, 0, 0, 0, 0, 0.0, "win")])  # terminated is not died
    assert rec.death_events == 0
    return rec


def row_death_with_pellet():
    rec = drive([[G(), G(1, r=-9.01, term=True, died=True)]])  # the pellet eaten on the death step: total reward -9.01, not -10
    expect(rec, [(2, 1, 0, 1, 0, 0, 0, -9.9, "death"), (1, 1, 0, 1, 0, 0, 0, -10.0, "death")])  # Z is the death penalty alone, discounted
    return rec


def row_non_greedy_start():
    rec = drive([[G(0), G(), G(1, **DEATH)]])
    expect(rec, [(3, 0, 0, 1, 0, 0, 0, -9.801, "death"), (2, 1, 0, 1, 0, 0, 0, -9.9, "death"), (1, 1, 0, 1, 0, 0, 0, -10.0, "death")])
    assert rec.to_dict()["rates"]["run"]["all"]["counts"]["N_T"] == 0  # a non-greedy start is never a T window
    return rec


def row_training_tail():
    rec3 = drive([[G(), G()]], n=3)
    expect(rec3, [], pending=2)  # nothing emitted yet; the budget stops here and nothing is flushed for the diagnostics
    assert rec3.emitted == 0
    rec1 = drive([[G(), G()]], n=1)
    expect(rec1, [(1, 1, 0, 0, 0, 0, 0, 0.0, "nonterminal")] * 2, pending=0)
    return rec3


def row_two_interleaved_envs():
    a = [G(), G(), G(0, **DEATH)]
    b = [G(), G(0, trunc=True), G()]  # env 1: truncated after two steps, then a fresh episode whose first step is still queued
    both = drive([a, b])
    only_a, only_b = drive([a]), drive([b])
    for h in (1, 2, 3):  # each cell of the joint run is the sum of the two single-environment runs
        parts = [x.cells[(0, h)] for x in (only_a, only_b) if (0, h) in x.cells]
        joint = both.cells[(0, h)]
        assert joint["n"] == sum(p["n"] for p in parts)
        assert np.array(joint["C"]).tolist() == sum(np.array(p["C"]) for p in parts).tolist()
        assert joint["J"] == sum(p["J"] for p in parts) and joint["P"] == sum(p["P"] for p in parts)
        assert {k: joint["end"][k] for k in W.END_KINDS} == {k: sum(p["end"][k] for p in parts) for k in W.END_KINDS}
        assert np.allclose(np.array(joint["z"]), sum(np.array(p["z"]) for p in parts))
    assert both.pending_by_bin() == {0: 1}  # only env 1's third step is queued; the queues are independent
    return both


def row_cross_bin():
    rec = drive([[G(), G(), G(), G()]], n=3, start0=19_999)  # start ids 20000, 20001, 20002, 20003
    w = rec.to_dict()
    assert {(c["bin"], c["h"]): c["n"] for c in w["cells"]} == {(0, 3): 1, (1, 3): 1}  # the h3 window starting at 20000 belongs to bin 0, the one at 20001 to bin 1
    assert w["pending_by_start_bin"]["1"] == 2 and w["pending_by_start_bin"]["0"] == 0
    return rec


def row_capacity_wraps_but_counts_do_not():
    rep = NStepReplay(5, (1,), np.float32, 1, 2, GAMMA)
    rec = drive([[G()] * 20], n=2, replay=rep)
    assert rep.size == 5 and rec.emitted == 19 and rec.collected == 20  # replay.size is occupancy, not the number of windows
    assert rec.emitted + sum(rec.pending_by_bin().values()) == rec.collected and rec.integrity()["complete"] and rec.hook_emitted == 19
    return rec


def row_death_windows_bounds():
    scripts = [[G(), G(), G(0, **DEATH)] + [G(), G(1, **DEATH)] + [G(), G(), G(), G(0, **DEATH)], [G(1, **DEATH)] + [G(), G(0, trunc=True)]]
    rec = drive(scripts)
    c = rec.to_dict()["rates"]["run"]["all"]["counts"]
    assert rec.death_events == 4 and rec.death_events <= c["N_D"] <= 3 * rec.death_events
    assert sum(x["n"] for x in rec.cells.values()) == rec.emitted
    return rec


def row_zero_denominators():
    rec = drive([[G(), G(), G()]], n=1)  # n = 1: nothing has a later action
    r = rec.to_dict()["rates"]["run"]["all"]
    for k in ("p_later_mismatch_hge2", "p_later_mismatch_given_greedy_start_hge2"):
        assert r[k] == {"numerator": 0, "denominator": 0, "rate": None, "status": "no_eligible_windows"}, k
    assert r["p_later_mismatch"] == {"numerator": 0, "denominator": 3, "rate": 0.0, "status": "ok"}
    for k in ("cooccurrence_given_greedy_start_death", "cooccurrence_given_any_death", "death_given_later_mismatch_greedy_start"):  # no deaths / no L
        assert r[k]["rate"] is None and r[k]["status"] == "no_eligible_windows"
    assert r["death_component_mean_T"] is None and r["death_component_abs_share_T"]["rate"] is None
    text = json.dumps(rec.to_dict(), allow_nan=False)  # no NaN / Infinity anywhere
    assert "NaN" not in text and "Infinity" not in text
    return rec


def row_rates_of_the_hand_example():
    """Rates of the death-on-a-deviating-step script (row 4): 3 windows, 2 greedy-start death windows, both T."""
    rec = drive([[G(), G(), G(0, **DEATH)]])
    r = rec.to_dict()["rates"]["run"]
    a = r["all"]
    assert (a["p_later_mismatch"]["numerator"], a["p_later_mismatch"]["denominator"]) == (2, 3)
    assert (a["p_greedy_start"]["numerator"], a["p_greedy_start"]["denominator"]) == (2, 3)
    assert (a["p_later_mismatch_given_greedy_start"]["numerator"], a["p_later_mismatch_given_greedy_start"]["denominator"]) == (2, 2)
    assert (a["p_later_mismatch_hge2"]["numerator"], a["p_later_mismatch_hge2"]["denominator"]) == (2, 2)  # h1 is excluded from the denominator
    assert (a["full_horizon_fraction"]["numerator"], a["full_horizon_fraction"]["denominator"]) == (1, 3)
    assert (a["death_window_fraction"]["numerator"], a["death_window_fraction"]["denominator"]) == (3, 3)
    assert (a["greedy_start_death_window_fraction"]["numerator"], a["greedy_start_death_window_fraction"]["denominator"]) == (2, 3)
    assert (a["cooccurrence_given_greedy_start_death"]["numerator"], a["cooccurrence_given_greedy_start_death"]["denominator"]) == (2, 2)
    assert (a["cooccurrence_given_any_death"]["numerator"], a["cooccurrence_given_any_death"]["denominator"]) == (2, 3)
    assert (a["death_step_mismatch_given_greedy_start_death"]["numerator"], a["death_step_mismatch_given_greedy_start_death"]["denominator"]) == (2, 2)
    assert (a["earlier_mismatch_given_greedy_start_death"]["numerator"], a["earlier_mismatch_given_greedy_start_death"]["denominator"]) == (0, 2)
    assert (a["death_given_later_mismatch_greedy_start"]["numerator"], a["death_given_later_mismatch_greedy_start"]["denominator"]) == (2, 2)
    assert (a["death_given_no_later_mismatch_greedy_start"]["numerator"], a["death_given_no_later_mismatch_greedy_start"]["denominator"]) == (0, 0)
    assert math.isclose(a["death_component_sum_T"], -9.801 - 9.9, abs_tol=1e-12) and math.isclose(a["death_component_mean_T"], (-9.801 - 9.9) / 2, abs_tol=1e-12)
    assert math.isclose(a["death_component_abs_share_T"]["rate"], (9.801 + 9.9) / (9.801 + 9.9 + 10.0), abs_tol=1e-12)  # denominator = all death windows' components
    assert r["h1"]["p_later_mismatch_hge2"]["status"] == "no_eligible_windows"  # a single-h group h=1 has no later action
    return rec


ROWS = [row_full_greedy_chain, row_death_same_step_deviation, row_deviation_then_death, row_two_step_truncation, row_win, row_death_with_pellet,
        row_non_greedy_start, row_training_tail, row_two_interleaved_envs, row_cross_bin, row_capacity_wraps_but_counts_do_not, row_death_windows_bounds,
        row_zero_denominators, row_rates_of_the_hand_example]


@pytest.mark.parametrize("row", ROWS, ids=[r.__name__ for r in ROWS])
def test_hand_computed_row(row):
    row()


# ------------------------------------------------------------------ action indicator
class FixedQ(torch.nn.Module):
    def __init__(self, row):
        super().__init__()
        self.register_buffer("q", torch.tensor([row], dtype=torch.float32))

    def forward(self, x):
        return self.q.expand(len(x), -1)


def test_random_branch_that_hits_the_greedy_action_is_not_a_deviation():
    greedy = np.array([1, 1, 1, 1])
    explore = np.array([True, True, False, False])
    random_draw = np.array([1, 3, 0, 0])  # env 0 explores and happens to draw the greedy action; env 1 explores and draws another
    actions = np.where(explore, random_draw, greedy)
    assert W.action_mismatch(actions, greedy).tolist() == [False, True, False, False]  # explore=True alone says nothing


def test_tie_between_maximal_q_values_counts_a_mismatch_with_the_selected_argmax():
    from pacman_rl import dqn

    g = dqn.greedy_actions(FixedQ([0, 2, 2, 1, 0]), [np.zeros(1, np.float32)], "cpu")  # the frozen torch.argmax picks the first maximal index
    assert g.tolist() == [1]
    assert W.action_mismatch(np.array([2]), g).tolist() == [True]  # the other maximal action IS a mismatch to the SELECTED greedy action
    assert W.action_mismatch(np.array([1]), g).tolist() == [False]


# ------------------------------------------------------------------ the replay hook sees exactly what the recorder expects
def test_recorder_agrees_with_the_real_replay_on_every_emitted_window():
    rep = NStepReplay(50, (1,), np.float32, 2, 3, GAMMA)
    scripts = [[G(), G(), G(0), G(1, **DEATH), G(), G(0, trunc=True), G(), G(), G(), G(), G(1, r=3.0, term=True, won=True)],
               [G(0), G(), G(), G(), G(1, **DEATH), G(), G(), G(0, trunc=True)]]
    rec = drive(scripts, replay=rep)
    assert rec.integrity()["complete"] and rec.hook_emitted == rec.emitted == rep.size + 0 and rec.errors == []
    # a replay that differs from the recorder's rules is reported, not hidden
    rec2 = W.WindowRecorder(1, 3, GAMMA, 100)
    rec2.begin_batch(0, 0.5, np.array([False]))
    rec2.on_emit(0, 1, 0, 0.0, 0.0)
    assert rec2.integrity()["complete"] is False and rec2.errors


# ------------------------------------------------------------------ planted errors must be caught by the table above
def run_all_rows():
    for row in ROWS:
        row()


def mutant_start_counted_in_l(steps, gamma, death_reward=W.DEATH_REWARD):
    w = ORIGINAL(steps, gamma, death_reward)
    w["l"] = any(s[W.U] for s in steps)  # BUG: the start action is counted among the later actions
    w["t"] = bool(w["d"] and w["g"] and w["l"])
    return w


def mutant_term_instead_of_died(steps, gamma, death_reward=W.DEATH_REWARD):
    flipped = [s[:W.DIED] + (s[W.TERM],) + s[W.DIED + 1:] for s in steps]  # BUG: death := terminated (a win counts as death)
    return ORIGINAL(flipped, gamma, death_reward)


@pytest.mark.parametrize("mutant", [mutant_start_counted_in_l, mutant_term_instead_of_died], ids=lambda m: m.__name__)
def test_planted_bug_turns_the_hand_computed_table_red(monkeypatch, mutant):
    monkeypatch.setattr(W, "classify_window", lambda steps, gamma, death_reward=W.DEATH_REWARD: mutant(steps, gamma, death_reward))
    with pytest.raises(AssertionError):
        run_all_rows()


def test_the_unmutated_table_is_green():
    run_all_rows()
