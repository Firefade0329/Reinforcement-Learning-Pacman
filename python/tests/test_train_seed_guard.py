"""F1 (external review of 3337db7): the training-episode seed guard checked the episode INDEX only, not the seed VALUE.
``train_seed(-1, 30000) == 30000`` is inside the sealed final-test seeds, and ``cli train --seed -1`` passed the old guard.
These tests read the real constants and the real functions; the throw-away seeds are 50000-50004 (never a sealed one)."""
import copy
import json

import pytest

import pacman_rl.dqn as dqn
from pacman_rl import cli, evaluate as ev
from pacman_rl import prereg as PR
from pacman_rl.dqn import TrainConfig

FREEZE = json.loads(PR.FREEZE_FILE.read_text(encoding="utf-8"))


def old_train_seed(run_seed, k):  # the arithmetic of the code before the fix
    return ev.TRAIN_SEED_BASE * (run_seed + 1) + k


def test_the_old_arithmetic_really_hit_every_partition():
    """Documents the defect so the guards below are not tested against a strawman."""
    for name, seeds in ev.SEED_SETS.items():
        k = seeds[0]
        assert old_train_seed(-1, k) == seeds[0] and old_train_seed(-1, k) in seeds, name
    assert old_train_seed(-1, 30000) in ev.PREREG_TEST_SEEDS


@pytest.mark.parametrize("bad", [-1, -2, -100, True, 1.0, "100", None])
def test_train_seed_refuses_an_undefined_run_seed(bad):
    with pytest.raises(ValueError, match="run seed"):
        ev.train_seed(bad, 30000)


@pytest.mark.parametrize("k", [-1, ev.TRAIN_SEED_BASE, ev.TRAIN_SEED_BASE + 5, 1.5, True])
def test_train_seed_refuses_an_index_outside_the_block(k):
    with pytest.raises(ValueError, match="episode index"):
        ev.train_seed(100, k)


def test_train_seed_is_unchanged_for_the_registered_seeds():
    assert ev.train_seed(100, 0) == 101_000_000 and ev.train_seed(104, 300_008) == 105_300_008 and ev.train_seed(900, 7) == 901_000_007


def test_a_whole_block_of_run_seed_minus_one_overlaps_every_partition():
    problems = ev.train_seed_block_problems(-1)
    assert problems  # a negative run seed is refused outright
    for seed in (*range(5), *range(100, 105), 900, 901, 50000):
        assert ev.train_seed_block_problems(seed) == [], seed
    # the interval check itself (independent of the run-seed rule): every partition is detected, both closed ends
    for name, seeds in ev.SEED_SETS.items():
        lo, hi = min(seeds), max(seeds)
        for first, last in ((lo, lo), (hi, hi), (lo - 5, lo), (hi, hi + 5), (lo - 5, hi + 5)):
            assert any(repr(name) in p for p in ev.train_seed_interval_problems(first, last)), (name, first, last)
        assert not any(repr(name) in p for p in ev.train_seed_interval_problems(lo - 10, lo - 1))
        assert not any(repr(name) in p for p in ev.train_seed_interval_problems(hi + 1, hi + 10))
    assert ev.evaluation_partition_of(30000) == "prereg_test" and ev.evaluation_partition_of(1_000_000) is None


@pytest.mark.parametrize("bad", [-1, -3, True])
def test_train_config_refuses_a_bad_seed(bad):
    with pytest.raises(ValueError, match="run seed"):
        TrainConfig(seed=bad)
    assert TrainConfig(seed=0).seed == 0 and TrainConfig(seed=50000).seed == 50000


def test_cli_train_seed_minus_one_is_refused_before_anything_is_trained(monkeypatch, tmp_path):
    """The reproduction of the review: ``cli train --seed -1`` used to build a config and start the training."""
    calls = []
    monkeypatch.setattr(dqn, "train", lambda *a, **k: calls.append((a, k)))
    monkeypatch.setattr(cli, "RESULTS", tmp_path)
    args = cli.build_parser().parse_args(["train", "--seed", "-1", "--arch", "mlp", "--val_set", "smoke_eval"])
    with pytest.raises(ValueError, match="run seed"):
        args.fn(args)
    assert calls == [] and not list(tmp_path.iterdir())


def _cfg_with_seed(seed):
    cfg = TrainConfig(total_env_steps=1000, n_envs=8, seed=50000)
    object.__setattr__(cfg, "seed", seed)  # bypass __post_init__: simulates a config object built or mutated by other means
    return cfg


def test_checked_train_seed_value_guard_is_the_one_that_fires(monkeypatch):
    """Even if ``train_seed`` were the old arithmetic and the config check were bypassed, the per-episode guard refuses
    a seed VALUE inside any partition (a negative run seed with the episode index inside the old bound)."""
    monkeypatch.setattr(dqn, "train_seed", old_train_seed)
    cfg = _cfg_with_seed(-1)
    assert dqn.checked_train_seed(cfg, 10) == 10  # outside every partition: the value guard has nothing to say
    for k in (5000, 5049, 10000, 20299, 21000, 30000, 30299, 40009):
        with pytest.raises(AssertionError, match="evaluation partition"):
            dqn.checked_train_seed(cfg, k, resumed=True)


def test_checked_train_seed_with_the_real_train_seed_refuses_a_bad_config_object():
    with pytest.raises(ValueError, match="run seed"):
        dqn.checked_train_seed(_cfg_with_seed(-1), 30000, resumed=True)


def test_registered_run_seeds_pass_the_per_episode_guard():
    for s in (100, 104, 900):
        cfg = TrainConfig(total_env_steps=300000, n_envs=8, seed=s)
        assert dqn.checked_train_seed(cfg, 0) == ev.train_seed(s, 0)
        assert dqn.checked_train_seed(cfg, 300008) == ev.train_seed(s, 300008)


# ------------------------------------------------------------------ frozen configuration
def test_frozen_config_checks_train_episode_index_max():
    assert PR.check_frozen_config(FREEZE) == [] and FREEZE["train_episode_index_max"] == 300008
    for bad in (300007, 300009, None, 0, "300008"):
        problems = PR.check_frozen_config({**FREEZE, "train_episode_index_max": bad})
        assert any("train_episode_index_max" in p for p in problems), bad


@pytest.mark.parametrize("key", ["formal_run_seeds", "smoke_run_seeds"])
def test_frozen_config_refuses_a_run_seed_whose_block_touches_a_partition(key):
    f = copy.deepcopy(FREEZE)
    f[key] = [-1, *f[key]]
    problems = PR.check_frozen_config(f)
    assert any(key in p and "run seed -1" in p for p in problems)


# ------------------------------------------------------------------ summary contract
def _summary_and_cfg(seed=100):
    cfg = PR.train_config({"arch": "res4", "obs": "fields", "width": 16, "double": True, "dueling": True, "n_step": 3, "gamma": 0.99, "lr": 0.0005,
                           "batch": 32, "buffer": 100000, "learn_start": 4000, "n_envs": 8, "steps_per_update": 4, "total_env_steps": 300000,
                           "eval_every": 20000, "seed": seed, "threads": 1, "device": "cuda"}, FREEZE)
    steps = list(range(20000, 300001, 20000))
    h = "a" * 64
    first = ev.train_seed(seed, 0)
    summary = {"run_name": "r", "total_env_steps": 300000, "env_steps": 300000, "replay": {"size": 100000}, "actual_updates": 74000,
               "validation_steps": steps, "validation_episodes_each": 50, "initial_state_dict_sha256": h, "episodes_started": 1300,
               "best_val_score": 1.0, "training_episode_seeds": {"first": first, "last": first + 1299, "count": 1300},
               "checkpoints": {"last": {"step": 300000, "weights_sha256": h}, "best": {"step": 20000, "weights_sha256": h}}}
    return summary, cfg


def test_summary_contract_accepts_the_seed_interval_of_the_run():
    s, cfg = _summary_and_cfg()
    assert PR.summary_contract_problems(s, cfg, "r") == []


def _mut(f):
    s, cfg = _summary_and_cfg()
    f(s)
    return PR.summary_contract_problems(s, cfg, "r")


def test_summary_contract_demands_and_checks_the_training_episode_seeds():
    assert any("training_episode_seeds" in p for p in _mut(lambda s: s.pop("training_episode_seeds")))
    assert any("training_episode_seeds" in p for p in _mut(lambda s: s["training_episode_seeds"].update(first=100_000_000)))  # another run's block
    assert any("training_episode_seeds" in p for p in _mut(lambda s: s["training_episode_seeds"].update(last=101_000_000 + 5)))
    assert any("training_episode_seeds" in p for p in _mut(lambda s: s["training_episode_seeds"].update(count=1300.0)))
    assert any("count" in p for p in _mut(lambda s: s["training_episode_seeds"].update(count=300_010, last=101_000_000 + 300_009)))  # beyond total + n_envs
    assert any("episodes_started" in p for p in _mut(lambda s: s.update(episodes_started=1301)))


def test_summary_contract_refuses_an_interval_inside_a_partition():
    def into_sealed(s):
        s["training_episode_seeds"].update(first=29990, last=30010, count=21)

    problems = _mut(into_sealed)
    assert any("prereg_test" in p for p in problems) and any("training_episode_seeds" in p for p in problems)
    s, cfg = _summary_and_cfg()
    s["training_episode_seeds"].update(first=30000, last=30000 + 1299)
    assert any("prereg_test" in p for p in PR.summary_contract_problems(s, cfg, "r"))


def test_a_real_training_run_writes_the_interval_it_used(tmp_path):
    """The summary records the first/last/count of the episodes the run actually started, and the contract accepts them."""
    cfg = TrainConfig(arch="mlp", total_env_steps=160, learn_start=32, eval_every=80, n_envs=4, buffer=1000, batch=8, seed=900, val_set="smoke_eval")
    seen = []
    real = dqn.checked_train_seed
    dqn.checked_train_seed = lambda c, k, resumed=False: (seen.append(k), real(c, k, resumed))[1]
    try:
        s = dqn.train(cfg, tmp_path, log=lambda *_: None)
    finally:
        dqn.checked_train_seed = real
    ts = s["training_episode_seeds"]
    assert ts == {"first": ev.train_seed(900, 0), "last": ev.train_seed(900, max(seen)), "count": max(seen) + 1} and s["episodes_started"] == ts["count"]
    assert seen == list(range(len(seen))) and ts["count"] >= cfg.n_envs
    assert not [p for p in PR.summary_contract_problems(s, cfg, tmp_path.name) if "training_episode_seeds" in p or "episodes_started" in p]
