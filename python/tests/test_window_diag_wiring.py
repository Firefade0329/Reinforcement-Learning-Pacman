"""The window recorder, wired into the REAL training loop, changes nothing the run computes.

One CPU training is executed with the diagnostics off and one with them on (same configuration, same seed); everything the algorithm
produces is captured by spying on the real code paths (collect_step, NStepReplay._emit, the numpy generator, the torch RNG, the loss, the model
forward, Tensor.item / Tensor.cpu) and compared.  Implementer and test author are the same AI model."""
import copy
import json
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pytest
import torch

import pacman_rl.dqn as dqn
from pacman_rl import window_diag as W
from pacman_rl.replay import NStepReplay

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


def cfg_for(n_step):
    return dqn.TrainConfig(arch="cnn2", n_step=n_step, total_env_steps=480, learn_start=64, eval_every=240, n_envs=4, buffer=200, batch=8,
                           seed=7, threads=1, device="cpu", val_set="smoke_eval")


class RngProxy:
    """Delegates to the real numpy Generator, logging every call (method, argument shapes)."""

    def __init__(self, real, log):
        self._real, self._log = real, log

    def __getattr__(self, name):
        attr = getattr(self._real, name)
        if not callable(attr):
            return attr

        def call(*a, **k):
            self._log.append((name, tuple(np.shape(x) if hasattr(x, "shape") else x for x in a), tuple(sorted(k))))
            return attr(*a, **k)

        return call


def run_training(tmp_path, monkeypatch, name, n_step, diag, extra_spy=None):
    cap = {"greedy": [], "finished": [], "actions": [], "windows": [], "rng_calls": [], "losses": [], "forwards": [0], "item": [0], "cpu": [0], "models": {}, "rngs": []}
    real_collect, real_emit, real_default_rng = dqn.collect_step, NStepReplay._emit, np.random.default_rng

    def collect(envs, obs, actions, *a, **k):
        cap["actions"].append(np.array(actions).copy())
        out = real_collect(envs, obs, actions, *a, **k)
        cap["finished"] += out
        return out

    real_greedy = dqn.greedy_actions

    def greedy(*a, **k):
        out = real_greedy(*a, **k)
        cap["greedy"].append(out.copy())
        return out

    def emit(self, obs, action, ret, next_obs, disc):
        cap["windows"].append((np.array(obs).copy(), int(action), float(ret), np.array(next_obs).copy(), float(disc)))
        return real_emit(self, obs, action, ret, next_obs, disc)

    def default_rng(*a, **k):
        g = real_default_rng(*a, **k)
        cap["rngs"].append(g)
        return RngProxy(g, cap["rng_calls"]) if not cap["rngs"][1:] else g  # only the training generator (the first one created) is logged

    real_build = dqn.build_initial_models

    def build(cfg, device):
        online, target = real_build(cfg, device)
        for label, m in (("online", online), ("target", target)):
            m.register_forward_hook(lambda mod, i, o, label=label: cap["forwards"].__setitem__(0, cap["forwards"][0] + 1))
        cap["models"] = {"online": online, "target": target}
        return online, target

    real_loss, real_adam = torch.nn.functional.smooth_l1_loss, torch.optim.Adam

    def loss(*a, **k):
        out = real_loss(*a, **k)
        cap["losses"].append(float(out.detach()))
        return out

    class Adam(real_adam):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            cap["opt"] = self

    real_item, real_cpu = torch.Tensor.item, torch.Tensor.cpu
    monkeypatch.setattr(dqn, "collect_step", collect)
    monkeypatch.setattr(dqn, "greedy_actions", greedy)
    monkeypatch.setattr(NStepReplay, "_emit", emit)
    monkeypatch.setattr(np.random, "default_rng", default_rng)
    monkeypatch.setattr(dqn, "build_initial_models", build)
    monkeypatch.setattr(torch.nn.functional, "smooth_l1_loss", loss)
    monkeypatch.setattr(torch.optim, "Adam", Adam)
    monkeypatch.setattr(torch.Tensor, "item", lambda self: (cap["item"].__setitem__(0, cap["item"][0] + 1), real_item(self))[1])
    monkeypatch.setattr(torch.Tensor, "cpu", lambda self, *a, **k: (cap["cpu"].__setitem__(0, cap["cpu"][0] + 1), real_cpu(self, *a, **k))[1])
    if extra_spy:
        extra_spy(monkeypatch, cap)
    torch.manual_seed(0)
    out = tmp_path / name
    summary = dqn.train(cfg_for(n_step), out, log=lambda *_: None, resume=False, window_diagnostics=diag)
    cap["np_rng_state"] = cap["rngs"][0].bit_generator.state
    cap["torch_rng_state"] = torch.get_rng_state().clone()
    cap["summary"] = summary
    cap["dir"] = out
    cap["online_state"] = {k: v.clone() for k, v in cap["models"]["online"].state_dict().items()}
    cap["target_state"] = {k: v.clone() for k, v in cap["models"]["target"].state_dict().items()}
    cap["opt_state"] = copy.deepcopy(cap["opt"].state_dict())
    monkeypatch.undo()
    return cap


def assert_same_algorithm(a, b):
    assert len(a["actions"]) == len(b["actions"]) and all(np.array_equal(x, y) for x, y in zip(a["actions"], b["actions"]))
    assert a["np_rng_state"] == b["np_rng_state"]
    assert torch.equal(a["torch_rng_state"], b["torch_rng_state"])
    assert len(a["windows"]) == len(b["windows"]) > 0
    for (o1, a1, r1, n1, d1), (o2, a2, r2, n2, d2) in zip(a["windows"], b["windows"]):  # stored windows, in storage order
        assert np.array_equal(o1, o2) and a1 == a2 and r1 == r2 and np.array_equal(n1, n2) and d1 == d2
    assert a["losses"] == b["losses"] and len(a["losses"]) > 0
    for k in a["online_state"]:
        assert torch.equal(a["online_state"][k], b["online_state"][k]) and torch.equal(a["target_state"][k], b["target_state"][k])
    sa, sb = a["opt_state"], b["opt_state"]
    assert sa["param_groups"] == sb["param_groups"] and sa["state"].keys() == sb["state"].keys()
    for k in sa["state"]:
        for name, v in sa["state"][k].items():
            assert torch.equal(torch.as_tensor(v), torch.as_tensor(sb["state"][k][name])), (k, name)
    ma, mb = a["summary"], b["summary"]
    for k in ("updates", "env_steps", "replay_size", "best_env_steps", "best_val_score", "episodes_started", "actual_updates"):
        assert ma[k] == mb[k], k
    assert ma["checkpoints"] == mb["checkpoints"] and ma["validation_steps"] == mb["validation_steps"]
    rows = lambda cap: [{k: v for k, v in json.loads(x).items() if k != "minutes"} for x in (cap["dir"] / "train_log.jsonl").read_text().splitlines()]  # noqa: E731
    assert rows(a) == rows(b)
    assert (a["dir"] / "config.json").read_text() == (b["dir"] / "config.json").read_text()  # the configuration (and its hash) is untouched
    ba, bb = (torch.load(c["dir"] / "best.pt", weights_only=False)["state_dict"] for c in (a, b))
    assert all(torch.equal(ba[k], bb[k]) for k in ba)  # the best checkpoint's weights


def assert_same_call_counts(a, b):
    assert a["rng_calls"] == b["rng_calls"] and len(a["rng_calls"]) > 0  # every rng.random / rng.integers call of the training generator, in order
    assert a["forwards"] == b["forwards"] and a["forwards"][0] > 0      # model forwards (online + target) are not increased
    assert a["item"] == b["item"] and a["cpu"] == b["cpu"]              # no extra Tensor.item() / .cpu() synchronisation


@pytest.fixture(scope="module", params=[3, 1], ids=["n3", "n1"])
def pair(request, tmp_path_factory):
    mp = pytest.MonkeyPatch()
    base = tmp_path_factory.mktemp(f"wiring{request.param}")
    try:
        off = run_training(base, mp, "off", request.param, False)
        on = run_training(base, mp, "on", request.param, True)
        off2 = run_training(base, mp, "off2", request.param, False)
    finally:
        mp.undo()
    return off, on, off2, request.param


def test_control_two_runs_with_the_diagnostics_off_are_identical(pair):
    off, _, off2, _ = pair
    assert_same_algorithm(off, off2)
    assert_same_call_counts(off, off2)


def test_logging_on_changes_no_action_rng_stored_window_update_loss_state_or_best_checkpoint(pair):
    off, on, _, _ = pair
    assert_same_algorithm(off, on)


def test_logging_on_adds_no_model_call_torch_random_training_rng_call_or_tensor_sync(pair):
    off, on, _, _ = pair
    assert_same_call_counts(off, on)


def test_the_diagnostic_file_is_written_verified_against_the_replay_and_matches_what_was_stored(pair):
    off, on, _, n = pair
    d = json.loads((on["dir"] / "window_diagnostics.json").read_text())
    assert d["schema_version"] == "window-diagnostics-1" and d["integrity"]["complete"] is True and d["integrity"]["verified_against_replay"] is True
    assert d["totals"]["collected_transitions"] == 480 and d["totals"]["emitted_windows"] == len(on["windows"])
    assert d["totals"]["emitted_windows"] + d["pending_total"] == 480 and d["pending_total"] <= 4 * (n - 1)
    assert d["meta"]["run_name"] == "on" and d["meta"]["n_step"] == n and d["meta"]["run_seed"] == 7 and len(d["meta"]["git_sha"]) == 40
    assert not (on["dir"] / "window_diagnostics.partial.json").exists() and not (off["dir"] / "window_diagnostics.json").exists()
    assert sorted(p.name for p in on["dir"].iterdir() if p.is_file()) == sorted(p.name for p in off["dir"].iterdir() if p.is_file()) + ["window_diagnostics.json"]
    json.dumps(d, allow_nan=False)
    # the start-action mismatch the recorder saw is the real one of the real batches: count the deviations of the executed actions from the greedy ones
    assert sum(c["n"] for c in d["cells"]) == d["totals"]["emitted_windows"]


def test_the_recorded_counts_are_the_ones_of_the_real_batches(pair):
    """Independent re-count from what the real loop produced: executed vs greedy actions of every batch, and the died flags of the finished episodes."""
    _, on, _, n = pair
    d = json.loads((on["dir"] / "window_diagnostics.json").read_text())
    assert len(on["greedy"]) == len(on["actions"]) == 120  # 480 transitions / 4 environments
    u_total = sum(int((a != g).sum()) for a, g in zip(on["actions"], on["greedy"]))
    deaths = int(sum(died for _, _, died in on["finished"]))
    assert d["totals"]["death_events"] == deaths > 0
    if n == 1:  # every transition is its own window: the start-action mismatches are exactly the deviations of the executed actions
        run = d["rates"]["run"]["h1"]
        assert run["p_greedy_start"]["numerator"] == 480 - u_total and run["p_greedy_start"]["denominator"] == 480
        assert u_total > 0  # the study has deviations at all (eps starts at 1.0)
    else:
        assert d["rates"]["run"]["all"]["counts"]["N"] == d["totals"]["emitted_windows"]
        assert d["rates"]["run"]["all"]["counts"]["N_D"] >= deaths


def test_summary_json_and_run_files_other_than_the_diagnostic_file_are_unchanged_in_shape(pair):
    off, on, _, _ = pair
    assert set(json.loads((off["dir"] / "summary.json").read_text())) == set(json.loads((on["dir"] / "summary.json").read_text()))


# ------------------------------------------------------------------ the harness really is sensitive
def test_a_recorder_that_draws_a_torch_random_number_is_caught(tmp_path, monkeypatch):
    off = run_training(tmp_path, monkeypatch, "off", 3, False)
    real_begin = W.WindowRecorder.begin_batch

    def intrusive(self, *a, **k):
        torch.rand(1)  # BUG planted: a diagnostic that consumes torch randomness
        return real_begin(self, *a, **k)

    on = run_training(tmp_path, monkeypatch, "on", 3, True, extra_spy=lambda mp, cap: mp.setattr(W.WindowRecorder, "begin_batch", intrusive))
    with pytest.raises(AssertionError):
        assert_same_algorithm(off, on)


def planted(kind):
    """A recorder that, on every emitted window, does one forbidden thing."""
    def spy(mp, cap):
        real_on_emit = W.WindowRecorder.on_emit

        def noisy(self, *a, **k):
            if kind == "sync":
                torch.zeros(1).item()
                torch.zeros(1).cpu()
            elif kind == "model":
                shape, _ = dqn.obs_spec("cnn2", "fields")
                cap["models"]["online"](torch.zeros(1, *shape))
            elif kind == "rng":
                cap["rngs"][0].random()  # an extra draw from the TRAINING generator
            return real_on_emit(self, *a, **k)

        mp.setattr(W.WindowRecorder, "on_emit", noisy)
    return spy


@pytest.mark.parametrize("kind", ["sync", "model", "rng"])
def test_a_recorder_with_an_extra_sync_model_call_or_training_rng_draw_is_caught(tmp_path, monkeypatch, kind):
    off = run_training(tmp_path, monkeypatch, "off", 3, False)
    on = run_training(tmp_path, monkeypatch, "on", 3, True, extra_spy=planted(kind))
    with pytest.raises(AssertionError):
        assert_same_call_counts(off, on)
        assert_same_algorithm(off, on)


# ------------------------------------------------------------------ resumed runs and the runner flag
def test_a_resumed_run_skips_the_diagnostics_instead_of_writing_a_partial_history(tmp_path):
    cfg = cfg_for(3)
    out = tmp_path / "r"
    dqn.train(cfg, out, log=lambda *_: None, resume=False, _stop_after=240)
    msgs = []
    dqn.train(cfg, out, log=msgs.append, resume=True, window_diagnostics=True)
    assert any("skipped" in m for m in msgs) and not (out / "window_diagnostics.json").exists()


def test_the_diagnostic_file_names_do_not_fall_into_the_forbidden_prefixes():
    for name in ("window_diagnostics.json", "window_diagnostics.partial.json"):
        assert not name.startswith(("test", "final", "resume")) and name not in ("last", "best")


def test_runner_passes_the_switch_and_does_not_touch_the_configuration():
    import prereg as runner
    from pacman_rl import prereg as PR

    freeze, rows = PR.load_freeze(), PR.load_matrix()
    cfg = PR.train_config(rows[0], freeze)
    assert "--window-diagnostics" not in PR.train_args(cfg, "x")  # the switch is not a configuration field
    assert asdict(cfg) == asdict(PR.train_config(rows[0], freeze))
    assert "window_diagnostics" not in PR.expected_config_json(cfg) and "window_diagnostics" not in json.dumps(freeze)
