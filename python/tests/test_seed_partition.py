"""Seed contract of the preregistered study, read from the ACTUAL constants and ``train_seed`` (not a copy):
evaluation partitions and the training-episode streams of every run_seed in use are pairwise disjoint, and no
training / selection path can reach the sealed final test seeds."""
import ast
import inspect
from itertools import combinations
from pathlib import Path

import numpy as np
import pytest

import pacman_rl.dqn as dqn
from pacman_rl import evaluate as ev
from pacman_rl.dqn import TrainConfig, train

K_MAX = 300_000 + 8  # fresh run: <= 300000 transitions, plus the 8 initial resets
RUN_SEEDS = (*range(5), *range(100, 105), 900, 901)  # old study 0-4, preregistered 100-104, smoke 900/901


def interval(seeds):
    seeds = list(seeds)
    assert seeds == list(range(seeds[0], seeds[-1] + 1)), "partitions are contiguous ranges"
    return seeds[0], seeds[-1]


def partitions(val_name="prereg_val"):
    parts = {"new_val": interval(ev.SEED_SETS[val_name]), "new_test": interval(ev.PREREG_TEST_SEEDS),
             "smoke_eval": interval(ev.SMOKE_EVAL_SEEDS), "equiv": interval(ev.EQUIV_SEEDS),
             "old_val": interval(ev.VAL_SEEDS), "old_test": interval(ev.TEST_SEEDS)}
    parts.update({f"train_run_{s}": (ev.train_seed(s, 0), ev.train_seed(s, K_MAX)) for s in RUN_SEEDS})
    return parts


def assert_disjoint(parts):
    for (na, (la, ha)), (nb, (lb, hb)) in combinations(parts.items(), 2):
        assert not (max(la, lb) <= min(ha, hb)), f"overlap: {na} / {nb}"


def test_actual_partitions_are_pairwise_disjoint():
    parts = partitions()
    assert len(parts) == 6 + len(RUN_SEEDS)
    assert_disjoint(parts)


def test_documented_values_of_the_constants():
    assert (ev.PREREG_VAL_SEEDS[0], ev.PREREG_VAL_SEEDS[-1], len(ev.PREREG_VAL_SEEDS)) == (21000, 21049, 50)
    assert (ev.PREREG_TEST_SEEDS[0], ev.PREREG_TEST_SEEDS[-1], len(ev.PREREG_TEST_SEEDS)) == (30000, 30299, 300)
    assert (ev.SMOKE_EVAL_SEEDS[0], ev.SMOKE_EVAL_SEEDS[-1], len(ev.SMOKE_EVAL_SEEDS)) == (40000, 40009, 10)
    assert (ev.EQUIV_SEEDS[0], ev.EQUIV_SEEDS[-1]) == (20000, 20299)  # legacy-fidelity use only, left unchanged
    assert (ev.VAL_SEEDS[0], ev.VAL_SEEDS[-1], ev.TEST_SEEDS[0], ev.TEST_SEEDS[-1]) == (5000, 5049, 10000, 10299)
    assert ev.train_seed(100, 0) == 101_000_000 and ev.train_seed(900, 0) == 901_000_000


def test_the_v02_validation_range_collides_with_equiv_and_is_rejected():
    """Regression: validating on 20000-20049 (the v0.2 range) overlaps EQUIV_SEEDS and must be caught."""
    parts = partitions()
    parts["new_val"] = (20_000, 20_049)
    with pytest.raises(AssertionError, match="new_val / equiv"):
        assert_disjoint(parts)


def test_closed_interval_boundaries_are_detected():
    with pytest.raises(AssertionError, match="overlap"):
        assert_disjoint({"a": (0, 10), "b": (10, 20)})
    assert_disjoint({"a": (0, 10), "b": (11, 20)})


def test_training_bound_matches_the_budget_and_stays_inside_the_block():
    assert K_MAX < ev.TRAIN_SEED_BASE
    for s in RUN_SEEDS:
        assert ev.train_seed(s, K_MAX) < ev.train_seed(s + 1, 0)


def test_runtime_episode_index_guard():
    cfg = TrainConfig(total_env_steps=1000, n_envs=8, seed=100)
    assert dqn.checked_train_seed(cfg, 1008) == ev.train_seed(100, 1008)
    with pytest.raises(AssertionError):
        dqn.checked_train_seed(cfg, 1009)  # more episodes than transitions + initial resets
    with pytest.raises(AssertionError):
        dqn.checked_train_seed(cfg, ev.TRAIN_SEED_BASE, resumed=True)  # would enter run_seed+1's stream
    assert dqn.checked_train_seed(cfg, 1500, resumed=True) == ev.train_seed(100, 1500)


def test_sealed_test_seeds_cannot_be_resolved_without_a_token():
    with pytest.raises(ev.SealedSetError):
        ev.seed_set("prereg_test")
    with pytest.raises(ev.SealedSetError):
        ev.seed_set("prereg_test", unseal=object())
    from pacman_rl import cli

    with pytest.raises(ev.SealedSetError):
        cli.split_seeds("prereg_test")
    with pytest.raises(KeyError):
        ev.seed_set("nope")


def _tiny(**kw):
    return TrainConfig(arch="mlp", total_env_steps=160, learn_start=32, eval_every=80, n_envs=4, buffer=1000, batch=8, seed=900, **kw)


@pytest.mark.parametrize("name", ["val", "prereg_val", "smoke_eval"])
def test_training_selection_reads_exactly_the_configured_set(tmp_path, monkeypatch, name):
    seen = []
    real = dqn.evaluate_batched
    monkeypatch.setattr(dqn, "evaluate_batched", lambda policy, cfg, seeds, observe, *a, **k: (seen.append(list(seeds)), real(policy, cfg, seeds, observe, *a, **k))[1])
    train(_tiny(val_set=name), tmp_path, log=lambda *_: None)
    assert seen and all(s == ev.SEED_SETS[name] for s in seen)
    others = set().union(*(set(v) for k, v in ev.SEED_SETS.items() if k != name))
    assert not {x for s in seen for x in s} & others


@pytest.mark.parametrize("name", ["test", "prereg_test", "equiv", "nope"])
def test_training_refuses_non_selection_sets(tmp_path, name):
    with pytest.raises(ValueError, match="may only select checkpoints"):
        train(_tiny(val_set=name), tmp_path, log=lambda *_: None)
    assert not (tmp_path / "train_log.jsonl").exists()


def test_training_modules_never_name_the_sealed_set():
    """Static guard on top of the dynamic ones: neither the trainer nor its entry point refers to the sealed seeds."""
    forbidden = {"PREREG_TEST_SEEDS", "TEST_SEEDS", "prereg_test"}
    for mod in (dqn,):
        tree = ast.parse(inspect.getsource(mod))
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        strings = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        assert not (names | strings) & forbidden, mod.__name__


def test_old_checkpoints_without_val_set_still_load(tmp_path):
    import torch

    from pacman_rl.dqn import load_checkpoint, save_checkpoint
    from dataclasses import asdict
    from pacman_rl.models import build_model

    cfg = _tiny()
    d = asdict(cfg)
    d.pop("val_set")  # as written by the code before this field existed
    path = tmp_path / "old.pt"
    torch.save({"state_dict": build_model("mlp", 16, True, 7).state_dict(), "cfg": d}, path)
    _, loaded, _ = load_checkpoint(path)
    assert loaded.val_set == "val"  # old default = the old validation seeds
