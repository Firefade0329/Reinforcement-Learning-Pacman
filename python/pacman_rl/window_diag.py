"""Descriptive record of the n-step windows that enter the replay: B1 / B2 of the window-diagnostics proposal.

B1 = share of windows whose LATER actions deviate from the greedy action selected at their time (``U = 1[A != g]``, g = the argmax the
trainer actually used for that collection batch); B2 = co-occurrence of an actual death (``info["died"]``) with such a deviation.
Both are descriptions of the training stream.  They are not a measure of bias, say nothing about which action caused a death, never feed
back into training, and are not part of the H1 / H2 decision.

The recorder only receives scalars the trainer already has (the greedy / executed actions of the batch, reward, terminated, truncated,
died, won) BEFORE the environment is reset.  It owns small per-environment queues that mirror ``NStepReplay.add``; it stores no
observation, Q value or state_dict, draws no random number and calls no model.  A window is counted once, when it enters the replay;
windows still queued when the training budget ends are reported as pending (nothing is flushed for the diagnostics).

``NStepReplay.on_emit`` (read-only) lets the recorder verify that the replay emitted exactly the windows it expected.
"""
from __future__ import annotations

import json
import math
import os
from collections import deque
from pathlib import Path

import numpy as np

SCHEMA = "window-diagnostics-1"
DEFINITION_VERSION = "1"
BIN_SIZE = 20_000
DEATH_REWARD = -10.0
END_KINDS = ("nonterminal", "death", "win", "truncated")

# one executed step: (start_id, eps, U, died, won, terminated, truncated, action, reward)
SID, EPS, U, DIED, WON, TERM, TRUNC, ACT, REW = range(9)


def action_mismatch(actions, greedy) -> np.ndarray:
    """U_t for a collection batch: the executed action differs from the greedy action selected for this batch (also when a random-branch
    draw happens to equal it: then U = 0; ties are NOT treated specially -- g is the deterministic argmax the trainer used)."""
    return np.asarray(actions) != np.asarray(greedy)


def classify_window(steps, gamma: float, death_reward: float = DEATH_REWARD) -> dict:
    """Description of one window = the steps from its start up to the step that ended it.  ``steps[0]`` is the start action."""
    h = len(steps)
    g_start = not steps[0][U]
    later = any(s[U] for s in steps[1:])                     # the start action is NOT part of L
    j_d = next((j for j, s in enumerate(steps) if s[DIED]), None)
    d = j_d is not None
    t = d and g_start and later
    j = bool(d and g_start and j_d >= 1 and steps[j_d][U])
    p = bool(d and g_start and any(steps[k][U] for k in range(1, j_d)))
    z = death_reward * gamma ** j_d if d else 0.0
    last = steps[-1]
    end_kind = "death" if last[DIED] else "win" if last[TERM] else "truncated" if last[TRUNC] else "nonterminal"
    return {"h": h, "start_id": steps[0][SID], "eps": steps[0][EPS], "g": g_start, "l": later, "d": d, "t": bool(t), "j": j, "p": p, "z": z, "end_kind": end_kind}


class WindowRecorder:
    def __init__(self, n_envs: int, n_step: int, gamma: float, total_env_steps: int, bin_size: int = BIN_SIZE):
        self.n_envs, self.n, self.gamma, self.total, self.bin_size = n_envs, n_step, gamma, total_env_steps, bin_size
        self.queues = [deque() for _ in range(n_envs)]
        self.cells: dict[tuple[int, int], dict] = {}
        self.collected = 0
        self.emitted = 0
        self.death_events = 0
        self.death_events_by_bin: dict[int, int] = {}
        self._expected: deque = deque()
        self.hook_attached = False
        self.hook_emitted = 0
        self.errors: list[str] = []
        self._start, self._eps, self._mismatch = 0, 0.0, None

    # ---- feeding
    def begin_batch(self, start_env_steps: int, eps: float, mismatch) -> None:
        self._start, self._eps, self._mismatch = int(start_env_steps), float(eps), mismatch

    def bin_of(self, start_id: int) -> int:
        return (start_id - 1) // self.bin_size

    def step(self, i: int, action: int, reward: float, term: bool, trunc: bool, died: bool, won: bool) -> None:
        """One executed transition of environment ``i`` (call BEFORE ``replay.add`` and before the environment is reset)."""
        sid = self._start + i + 1
        step = (sid, self._eps, bool(self._mismatch[i]), bool(died), bool(won), bool(term), bool(trunc), int(action), float(reward))
        self.collected += 1
        if died:
            self.death_events += 1
            b = self.bin_of(sid)
            self.death_events_by_bin[b] = self.death_events_by_bin.get(b, 0) + 1
        q = self.queues[i]
        q.append(step)
        if term or trunc:  # same rule as NStepReplay.add: every pending start leaves with the horizon that is left; nothing crosses a reset
            items = list(q)
            for start in range(len(items)):
                self._window(i, items[start:], 0.0 if term else self.gamma ** (len(items) - start))
            q.clear()
        elif len(q) == self.n:
            self._window(i, list(q), self.gamma ** self.n)
            q.popleft()

    def _window(self, env_i: int, steps: list, disc: float) -> None:
        w = classify_window(steps, self.gamma)
        ret = 0.0
        for j, s in enumerate(steps):
            ret += (self.gamma ** j) * s[REW]
        self._expected.append((env_i, w["h"], steps[0][ACT], ret, disc))
        self.emitted += 1
        c = self.cells.setdefault((self.bin_of(w["start_id"]), w["h"]), {
            "n": 0, "C": [[[0, 0], [0, 0]], [[0, 0], [0, 0]]], "z": [[[0.0, 0.0], [0.0, 0.0]], [[0.0, 0.0], [0.0, 0.0]]], "J": 0, "P": 0,
            "end": dict.fromkeys(END_KINDS, 0), "eps_sum": 0.0, "eps_min": math.inf, "eps_max": -math.inf})
        g, l, d = int(w["g"]), int(w["l"]), int(w["d"])
        c["n"] += 1
        c["C"][g][l][d] += 1
        c["z"][g][l][d] += w["z"]
        c["J"] += int(w["j"])
        c["P"] += int(w["p"])
        c["end"][w["end_kind"]] += 1
        c["eps_sum"] += w["eps"]
        c["eps_min"] = min(c["eps_min"], w["eps"])
        c["eps_max"] = max(c["eps_max"], w["eps"])

    def on_emit(self, env_i: int, h: int, action: int, ret: float, disc: float) -> None:
        """Read-only verification hook (``NStepReplay.on_emit``): the replay must emit exactly the windows expected, in this order."""
        self.hook_attached = True
        self.hook_emitted += 1
        if not self._expected:
            self.errors.append("the replay emitted a window the recorder did not expect")
            return
        env, eh, ea, eret, edisc = self._expected.popleft()
        if (env, eh, ea) != (env_i, h, int(action)) or abs(eret - float(ret)) > 1e-9 or abs(edisc - float(disc)) > 1e-12:
            self.errors.append(f"emitted window (env {env_i}, h {h}, action {action}, ret {ret}, disc {disc}) differs from the expected "
                               f"(env {env}, h {eh}, action {ea}, ret {eret}, disc {edisc})")

    # ---- output
    def pending_by_bin(self) -> dict[int, int]:
        out: dict[int, int] = {}
        for q in self.queues:
            for s in q:
                b = self.bin_of(s[SID])
                out[b] = out.get(b, 0) + 1
        return out

    def n_bins(self) -> int:
        last = max([self.total] + [s[SID] for q in self.queues for s in q] + [k[0] * self.bin_size + 1 for k in self.cells])
        return (last - 1) // self.bin_size + 1

    def integrity(self) -> dict:
        pend = sum(self.pending_by_bin().values())
        n_cells = sum(c["n"] for c in self.cells.values())
        n_d = sum(sum(c["C"][g][l][1] for g in (0, 1) for l in (0, 1)) for c in self.cells.values())
        checks = {
            "cells_sum_to_emitted": n_cells == self.emitted,
            "emitted_plus_pending_equals_collected": self.emitted + pend == self.collected,
            "end_kind_counts_sum_to_windows": all(sum(c["end"].values()) == c["n"] for c in self.cells.values()),
            "death_end_kind_equals_death_cells": sum(c["end"]["death"] for c in self.cells.values()) == n_d,
            "death_windows_within_bounds": self.death_events <= n_d <= self.n * self.death_events,
            "pending_within_bound": pend <= self.n_envs * (self.n - 1),
            "replay_emitted_the_expected_windows": (not self.hook_attached) or (not self.errors and self.hook_emitted == self.emitted and not self._expected),
        }
        return {"complete": all(checks.values()) and not self.errors, "checks": checks, "errors": list(self.errors),
                "verified_against_replay": self.hook_attached}

    def to_dict(self, meta: dict | None = None) -> dict:
        cells = []
        for (b, h), c in sorted(self.cells.items()):
            cells.append({"bin": b, "h": h, "n": c["n"], "C_g_l_d": c["C"], "J": c["J"], "P": c["P"], "death_component_sum_g_l_d": c["z"],
                          "end_kind_counts": c["end"], "start_eps": {"sum": c["eps_sum"], "min": c["eps_min"], "max": c["eps_max"], "count": c["n"]}})
        pend = self.pending_by_bin()
        nb = self.n_bins()
        return {
            "schema_version": SCHEMA, "definition_version": DEFINITION_VERSION, "counting_source": "emitted_once",
            "indicator": "action_mismatch_to_selected_greedy", "descriptive_only": True,
            "meta": dict(meta or {}), "n_step": self.n, "n_envs": self.n_envs, "gamma": self.gamma, "transition_budget": self.total,
            "bin_size": self.bin_size, "bins": [{"index": b, "first": b * self.bin_size + 1, "last": (b + 1) * self.bin_size} for b in range(nb)],
            "cell_layout": "C_g_l_d[g][l][d]: g = start action equals the selected greedy action, l = a later action deviates, d = window holds the death",
            "cells": cells,
            "pending_by_start_bin": {str(b): pend.get(b, 0) for b in range(nb)}, "pending_total": sum(pend.values()),
            "totals": {"collected_transitions": self.collected, "emitted_windows": self.emitted, "death_events": self.death_events,
                       "death_events_by_transition_bin": {str(b): self.death_events_by_bin.get(b, 0) for b in range(nb)}},
            "rates": self.rates(nb), "integrity": self.integrity(),
        }

    def rates(self, nb: int) -> dict:
        hs = list(range(1, self.n + 1))
        pairs = lambda sel: [(k, c) for (b, k), c in self.cells.items() if sel(b, k)]  # noqa: E731
        run = {f"h{h}": metrics(pairs(lambda b, k, h=h: k == h), self.n) for h in hs}
        run["all"] = metrics(pairs(lambda b, k: True), self.n)
        by_bin = {}
        for b in range(nb):
            d = {f"h{h}": metrics(pairs(lambda bb, k, h=h, b=b: bb == b and k == h), self.n) for h in hs}
            d["all"] = metrics(pairs(lambda bb, k, b=b: bb == b), self.n)
            by_bin[str(b)] = d
        return {"run": run, "by_bin": by_bin}


def _rate(num: int, den: int) -> dict:
    return {"numerator": int(num), "denominator": int(den), "rate": (num / den) if den else None, "status": "ok" if den else "no_eligible_windows"}


def metrics(pairs: list, n_step: int) -> dict:
    """B1 / B2 rates of a group of cells, ``pairs`` = [(h, cell)], with their numerators and denominators (rate null + status when the
    denominator is 0).  The h >= 2 figures use only the cells with h >= 2 of the group; the full-horizon fraction counts h == n_step."""

    def tot(hmin=None):
        s = {"n": 0, "C": [[[0, 0], [0, 0]], [[0, 0], [0, 0]]], "z": [[[0.0, 0.0], [0.0, 0.0]], [[0.0, 0.0], [0.0, 0.0]]], "J": 0, "P": 0}
        for h, c in pairs:
            if hmin is not None and h < hmin:
                continue
            s["n"] += c["n"]
            s["J"] += c["J"]
            s["P"] += c["P"]
            for g in (0, 1):
                for l in (0, 1):
                    for d in (0, 1):
                        s["C"][g][l][d] += c["C"][g][l][d]
                        s["z"][g][l][d] += c["z"][g][l][d]
        return s

    a = tot()
    C = a["C"]
    N = a["n"]
    allc = lambda **kw: sum(C[g][l][d] for g in (0, 1) for l in (0, 1) for d in (0, 1) if all({"g": g, "l": l, "d": d}[k] == v for k, v in kw.items()))  # noqa: E731
    n_d, n_gd, n_t = allc(d=1), allc(g=1, d=1), allc(g=1, l=1, d=1)
    n_gl, n_gnl = allc(g=1, l=1), allc(g=1, l=0)
    C2 = tot(hmin=2)["C"]
    hge2 = lambda num_sel, den_sel: _rate(sum(C2[g][l][d] for g in (0, 1) for l in (0, 1) for d in (0, 1) if num_sel(g, l, d)),  # noqa: E731
                                           sum(C2[g][l][d] for g in (0, 1) for l in (0, 1) for d in (0, 1) if den_sel(g, l, d)))
    full = sum(c["n"] for h, c in pairs if h == n_step)
    z_gd = sum(a["z"][1][l][1] for l in (0, 1))
    z_all_abs = sum(abs(a["z"][g][l][1]) for g in (0, 1) for l in (0, 1))
    out = {
        "n_windows": N,
        "p_later_mismatch": _rate(allc(l=1), N),
        "p_greedy_start": _rate(allc(g=1), N),
        "p_later_mismatch_given_greedy_start": _rate(n_gl, allc(g=1)),
        "p_later_mismatch_hge2": hge2(lambda g, l, d: l == 1, lambda g, l, d: True),
        "p_later_mismatch_given_greedy_start_hge2": hge2(lambda g, l, d: g == 1 and l == 1, lambda g, l, d: g == 1),
        "full_horizon_fraction": _rate(full, N),
        "death_window_fraction": _rate(n_d, N),
        "greedy_start_death_window_fraction": _rate(n_gd, N),
        "cooccurrence_given_greedy_start_death": _rate(n_t, n_gd),
        "cooccurrence_given_any_death": _rate(n_t, n_d),
        "cooccurrence_of_all_windows": _rate(n_t, N),
        "death_step_mismatch_given_greedy_start_death": _rate(a["J"], n_gd),
        "earlier_mismatch_given_greedy_start_death": _rate(a["P"], n_gd),
        "death_given_later_mismatch_greedy_start": _rate(n_t, n_gl),
        "death_given_no_later_mismatch_greedy_start": _rate(allc(g=1, l=0, d=1), n_gnl),
        "death_component_sum_greedy_start_death": z_gd,
        "death_component_sum_T": a["z"][1][1][1],
        "death_component_mean_greedy_start_death": (z_gd / n_gd) if n_gd else None,
        "death_component_mean_T": (a["z"][1][1][1] / n_t) if n_t else None,
        "death_component_abs_share_T": {"numerator": abs(a["z"][1][1][1]), "denominator": z_all_abs, "rate": (abs(a["z"][1][1][1]) / z_all_abs) if z_all_abs else None,
                                        "status": "ok" if z_all_abs else "no_eligible_windows"},
        "counts": {"N": N, "N_D": n_d, "N_GD": n_gd, "N_T": n_t, "N_J": a["J"], "N_P": a["P"], "N_GL": n_gl, "N_GnL": n_gnl},
    }
    return out


def write_atomic(path: Path, obj: dict) -> None:
    """JSON without NaN / Infinity, published atomically."""
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, allow_nan=False), encoding="utf-8", newline="\n")
    os.replace(tmp, path)
