"""eval-model's overwrite-proof path (--out-dir): separate last / best outputs, no replacement, full seed sets,
checkpoint identity, 1 torch thread, truncated flag only on the new path."""
import json
import sys
from argparse import Namespace

import pytest
import torch

from pacman_rl import cli
from pacman_rl import evaluate as ev
from pacman_rl import provenance as P
from pacman_rl.dqn import TrainConfig, train
from pacman_rl.evalrun import evaluate_checkpoint


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    d = tmp_path_factory.mktemp("run")
    train(TrainConfig(arch="mlp", total_env_steps=480, learn_start=64, eval_every=160, n_envs=4, buffer=2000, batch=8, seed=3, threads=1,
                      val_set="smoke_eval"), d, log=lambda *_: None)
    return d


def read(p):
    return json.loads(p.read_text())


def test_last_and_best_go_to_separate_files_and_nothing_is_written_next_to_the_checkpoint(run, tmp_path):
    before = sorted(x.name for x in run.iterdir())
    out = tmp_path / "eval"
    a = evaluate_checkpoint(run / "last.pt", "smoke_eval", ["standard"], out)
    b = evaluate_checkpoint(run / "best.pt", "smoke_eval", ["standard"], out)
    assert a["standard"] == out / "last" / "standard.json" and b["standard"] == out / "best" / "standard.json"
    assert sorted(x.name for x in run.iterdir()) == before
    assert read(a["standard"])["agent"].endswith("/last") and read(b["standard"])["agent"].endswith("/best")


def test_second_call_does_not_overwrite_and_leaves_the_first_output_intact(run, tmp_path):
    out = tmp_path / "eval"
    evaluate_checkpoint(run / "last.pt", "smoke_eval", ["standard"], out)
    f = out / "last" / "standard.json"
    first = f.read_bytes()
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        evaluate_checkpoint(run / "last.pt", "smoke_eval", ["standard"], out)
    assert f.read_bytes() == first
    # one scenario already present blocks the whole call before anything is computed or written
    with pytest.raises(FileExistsError):
        evaluate_checkpoint(run / "last.pt", "smoke_eval", ["standard", "hard"], out)
    assert not (out / "last" / "hard.json").exists()
    evaluate_checkpoint(run / "last.pt", "smoke_eval", ["standard"], out, force=True)  # explicit opt-in only
    assert f.exists()


def test_full_test_seed_set_checkpoint_identity_and_environment(run, tmp_path):
    out = tmp_path / "eval"
    evaluate_checkpoint(run / "last.pt", "test", ["standard", "hard"], out)
    std = read(out / "last" / "standard.json")
    assert [r["seed"] for r in std["records"]] == ev.TEST_SEEDS and len(std["records"]) == 300
    assert std["split"] == "test" and std["summary"]["episodes"] == 300
    ck = std["extra"]["checkpoint"]
    assert ck["file_sha256"] == P.file_sha256(run / "last.pt")
    assert ck["state_sha256"] == P.state_hash(torch.load(run / "last.pt", weights_only=False)["state_dict"]) and ck["env_steps"] == 480
    assert std["extra"]["torch_threads"] == 1 and std["extra"]["eval_device"] == "cpu"
    assert std["extra"]["seeds"] == {"first": 10000, "last": 10299, "count": 300}
    assert set(std["extra"]["environment"]) == set(P.ENV_KEYS)
    assert (out / "last" / "hard.json").exists()
    best = read(evaluate_checkpoint(run / "best.pt", "smoke_eval", ["standard"], out)["standard"])
    assert best["extra"]["checkpoint"]["label"] == "best" and ck["label"] == "last"


def test_truncated_flag_is_consistent_and_only_on_the_new_path(run, tmp_path):
    out = tmp_path / "eval"
    recs = read(evaluate_checkpoint(run / "last.pt", "test", ["standard"], out)["standard"])["records"]
    assert all(set(r) == {"seed", "score", "steps", "died", "won", "truncated"} for r in recs)
    assert all(r["truncated"] == (r["steps"] >= 1000 and not r["died"] and not r["won"]) for r in recs)
    assert not any(r["truncated"] and (r["died"] or r["won"]) for r in recs)
    # the historical path keeps its exact record layout and its location (next to the checkpoint)
    import shutil

    legacy = tmp_path / "legacy"
    shutil.copytree(run, legacy)
    cli.cmd_eval_model(Namespace(ckpt=str(legacy / "best.pt"), split="val", scenarios=["standard"], device="cpu", out_dir=None,
                                 label=None, threads=1, force=False))
    old = read(legacy / "val_standard.json")["records"]
    assert all(set(r) == {"seed", "score", "steps", "died", "won"} for r in old)


def test_threads_are_applied(run, tmp_path):
    torch.set_num_threads(2)
    evaluate_checkpoint(run / "last.pt", "smoke_eval", ["standard"], tmp_path / "e", threads=1)
    assert torch.get_num_threads() == 1


def test_cli_entry_point_and_sealed_split(run, tmp_path, monkeypatch, capsys):
    out = tmp_path / "e"
    monkeypatch.setattr(sys, "argv", ["cli", "eval-model", "--ckpt", str(run / "best.pt"), "--split", "smoke_eval", "--out-dir", str(out)])
    cli.main()
    assert (out / "best" / "standard.json").exists() and "best standard/smoke_eval" in capsys.readouterr().out
    monkeypatch.setattr(sys, "argv", ["cli", "eval-model", "--ckpt", str(run / "best.pt"), "--split", "prereg_test", "--out-dir", str(tmp_path / "x")])
    with pytest.raises(ev.SealedSetError):
        cli.main()
    assert not (tmp_path / "x").exists()
    with pytest.raises(ev.SealedSetError):
        evaluate_checkpoint(run / "best.pt", "prereg_test", ["standard"], tmp_path / "y")
    assert not (tmp_path / "y").exists()
