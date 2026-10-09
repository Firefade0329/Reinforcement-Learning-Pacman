"""Deliberately broken variants of the pipeline pieces, built by patching the SOURCE of the real code (so they
stay in sync with it).  Each entry returns kwargs for ``nstep_harness.run_pipeline``."""
from __future__ import annotations

import inspect
import textwrap

import pacman_rl.dqn as dqn
import pacman_rl.replay as replay_mod


def _patched_replay(old: str, new: str):
    src = inspect.getsource(replay_mod.NStepReplay)
    assert old in src, f"mutation anchor not found: {old!r}"
    ns = dict(vars(replay_mod))
    exec(compile(src.replace(old, new), "<mutant replay>", "exec"), ns)
    return ns["NStepReplay"]


def _patched_function(fn, old: str, new: str, extra_globals=None):
    src = textwrap.dedent(inspect.getsource(fn))
    assert old in src, f"mutation anchor not found: {old!r}"
    ns = dict(vars(dqn))
    exec(compile(src.replace(old, new), "<mutant>", "exec"), ns)
    return ns[fn.__name__]


MUTANTS = {
    # Double DQN lost: the target network also chooses the action
    "plain_max_instead_of_double": lambda: {"td_target": _patched_function(dqn.td_target, "if double:", "if False:")},
    # time-limit truncation treated like a true terminal (nothing bootstrapped)
    "truncation_not_bootstrapped": lambda: {"replay_cls": _patched_replay("disc = 0.0 if terminated else self.gamma ** k", "disc = 0.0")},
    # discount exponent n instead of the real (shorter) horizon at episode ends
    "discount_exponent_n_instead_of_h": lambda: {"replay_cls": _patched_replay("self.gamma ** k", "self.gamma ** self.n")},
    # shorter-horizon tail samples are dropped when an episode ends
    "tail_not_flushed": lambda: {"replay_cls": _patched_replay("for start in range(len(items)):", "for start in range(min(1, len(items))):")},
    # all environments share one pending queue
    "queue_shared_across_envs": lambda: {"replay_cls": _patched_replay("q = self.pending[env_i]", "q = self.pending[0]")},
    # the observation after the RESET is stored as the transition's next observation
    "reset_observation_stored_as_next": lambda: {"collect_step": _reset_obs_mutant()},
}


def _reset_obs_mutant():
    src = textwrap.dedent(inspect.getsource(dqn.collect_step))
    add = "        replay.add(i, obs[i], int(actions[i]), r, nxt, term, trunc)\n"
    assert add in src and "        obs[i] = nxt\n" in src
    mutated = src.replace(add, "").replace("        obs[i] = nxt\n", add + "        obs[i] = nxt\n")
    ns = dict(vars(dqn))
    exec(compile(mutated, "<mutant collect_step>", "exec"), ns)
    return ns["collect_step"]
