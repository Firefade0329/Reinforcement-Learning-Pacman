"""(Double / Dueling / n-step) DQN trainer with vectorised environments, CPU-friendly."""
from __future__ import annotations

import copy
import json
import os
import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from .env import FIELD_SHAPE, GHOST_FIELD_RANGE, GOLD_FIELD_RANGE, NUM_ACTIONS, OBS_SHAPE, STANDARD, PacmanEnv
from .evaluate import SELECTION_SETS, TRAIN_SEED_BASE, evaluate_batched, seed_set, summarize, train_seed
from .features import FEATURE_DIM, feature_vector
from .models import build_model
from .provenance import ROOT as REPO_ROOT, code_version, environment_info, peak_memory, state_hash
from .replay import NStepReplay
from .window_diag import WindowRecorder, action_mismatch, write_atomic


@dataclass
class TrainConfig:
    arch: str = "res4"            # mlp | cnn2 | res2 | res4 | res8
    obs: str = "fields"           # conv input: "fields" (7 ch, BFS distance fields) | "grid" (5 raw planes)
    width: int = 16
    double: bool = True
    dueling: bool = True
    n_step: int = 3
    gamma: float = 0.99
    lr: float = 5e-4
    batch: int = 32
    buffer: int = 100_000
    learn_start: int = 4_000
    n_envs: int = 8
    steps_per_update: int = 4     # env transitions collected per gradient update
    total_env_steps: int = 120_000
    tau: float = 0.01             # Polyak coefficient for the target network
    eps_start: float = 1.0
    eps_end: float = 0.05
    eps_frac: float = 0.4         # fraction of training over which eps is annealed
    grad_clip: float = 10.0
    eval_every: int = 20_000
    seed: int = 0
    threads: int = 1
    device: str = "cpu"           # cpu | cuda | auto (cuda if available)
    val_set: str = "val"          # named seed set used for checkpoint selection (evaluate.SELECTION_SETS); test sets are refused


def observe_fn(arch: str, obs: str = "fields"):
    if arch == "mlp":
        return feature_vector
    return (lambda env: env.observation_fields()) if obs == "fields" else (lambda env: env.observation())


def obs_spec(arch: str, obs: str = "fields"):
    if arch == "mlp":
        return (FEATURE_DIM,), np.float32
    return (FIELD_SHAPE if obs == "fields" else OBS_SHAPE), np.float32


def resolve_device(name: str = "cpu") -> torch.device:
    if name == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if name.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("--device cuda requested but torch.cuda.is_available() is False "
                           "(install a CUDA build of PyTorch, see python/README.md)")
    return torch.device(name)


def make_policy(model: torch.nn.Module):
    model.eval()
    device = next(model.parameters()).device

    @torch.no_grad()
    def policy(batch: np.ndarray) -> np.ndarray:
        return model(torch.from_numpy(batch).to(device)).argmax(dim=1).cpu().numpy()

    return policy


def evaluate_model(model, cfg: "TrainConfig", scenario_cfg, seeds, record_truncated: bool = False):
    return evaluate_batched(make_policy(model), scenario_cfg, seeds, observe_fn(cfg.arch, cfg.obs), record_truncated)


def quant_scale(arch: str, obs: str):
    """Per-channel constants making every conv observation value an integer (see replay.py)."""
    if arch == "mlp":
        return None
    base = [1.0] * 5
    return np.array(base + [GOLD_FIELD_RANGE, GHOST_FIELD_RANGE] if obs == "fields" else base, dtype=np.float32)


def in_ch(cfg: "TrainConfig") -> int:
    return obs_spec(cfg.arch, cfg.obs)[0][0]


def save_checkpoint(path: Path, model, cfg: TrainConfig, extra: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": model.state_dict(), "cfg": asdict(cfg), **extra}, path)


def load_checkpoint(path: Path, device: str = "cpu"):
    """Checkpoints are device-agnostic; ``device`` only says where the returned model lives."""
    ck = torch.load(path, map_location="cpu", weights_only=False)
    cfg = TrainConfig(**ck["cfg"])
    model = build_model(cfg.arch, cfg.width, cfg.dueling, in_ch(cfg))
    model.load_state_dict(ck["state_dict"])
    return model.to(resolve_device(device)), cfg, ck


def _backup_path(path: Path) -> Path:
    """First unused ``<log>.partial-tail.bak[.N]`` next to the log (an earlier backup is never overwritten)."""
    cand, i = path.with_name(path.name + ".partial-tail.bak"), 1
    while cand.exists():
        i += 1
        cand = path.with_name(f"{path.name}.partial-tail.bak.{i}")
    return cand


def truncate_log_to(path: Path, upto_env_steps: int) -> tuple[int, int]:
    """Prepare a training log for resuming at ``upto_env_steps``; returns ``(dropped, partial)``.

    * ``dropped``: complete rows after ``upto_env_steps``.  They belong to the interrupted segment, which is
      regenerated, so keeping them would duplicate rows and make the log go backwards.
    * ``partial``: 1 if the LAST line was an unfinished write (a process killed mid-``write``), else 0.  The
      original log is copied to ``<log>.partial-tail.bak`` first, then that line is discarded.
    * An unreadable line anywhere else is not an interrupted write: ``ValueError`` naming the line number,
      and the log is left untouched."""
    if not path.exists():
        return 0, 0
    lines = [(n, line) for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1) if line.strip()]
    rows, partial = [], 0
    for i, (n, line) in enumerate(lines):
        try:
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError("not a JSON object")
        except ValueError as e:  # json.JSONDecodeError is a ValueError
            if i < len(lines) - 1:
                raise ValueError(f"{path.name}: line {n} is not valid JSON ({e}) and it is not the last line, so this is "
                                 f"not an interrupted write; refusing to repair the log automatically") from e
            partial = 1
        else:
            rows.append((line, row))
    kept = [line for line, row in rows if row.get("env_steps", 0) <= upto_env_steps]
    if partial:
        shutil.copy2(path, _backup_path(path))
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text("".join(x + "\n" for x in kept), encoding="utf-8", newline="\n")
    os.replace(tmp, path)
    return len(rows) - len(kept), partial


def build_initial_models(cfg: "TrainConfig", device):
    """Seed torch and build the online network and its target copy.  Nothing else consumes torch's RNG between the
    seeding and the construction, so equal (arch, width, dueling, obs, seed) gives equal initial weights whatever
    n_step / lr / ... are; the model is built on the CPU and then moved, so the values do not depend on the device."""
    torch.manual_seed(cfg.seed)  # also seeds CUDA; GPU runs are statistically, not bitwise, reproducible
    online = build_model(cfg.arch, cfg.width, cfg.dueling, in_ch(cfg)).to(device)
    target = copy.deepcopy(online)
    target.eval()
    return online, target


@torch.no_grad()
def greedy_actions(online, obs_batch, device) -> np.ndarray:
    """Greedy action of every observation in the batch: ``torch.argmax`` over the Q values.  Ties are NOT broken by this
    code: the frozen torch.argmax behaviour decides (on the CPU of torch 2.14.1 the first maximal index; see
    tests/test_tie_break.py).  The same rule applies to the Double-DQN end action (td_target) and to evaluation."""
    online.eval()
    out = online(torch.from_numpy(np.stack(obs_batch)).to(device)).argmax(dim=1).cpu().numpy()
    online.train()
    return out


@torch.no_grad()
def td_target(online, target, ret, disc, o2, double: bool):
    """Bootstrapped TD target ``y = ret + disc * Q_target(o2, a*)`` for a batch from the n-step replay.
    ``ret`` is the discounted reward sum over the stored horizon h and ``disc`` is gamma^h (0 after a true
    terminal, so nothing is bootstrapped there).  Double DQN: the action a* is chosen by the ONLINE network and
    valued by the TARGET network; otherwise a* is the target network's own maximiser."""
    if double:
        a2 = online(o2).argmax(dim=1, keepdim=True)
        q2 = target(o2).gather(1, a2).squeeze(1)
    else:
        q2 = target(o2).max(dim=1).values
    return ret + disc * q2


def collect_step(envs, obs, actions, replay, observe, ep_ret, reset_env, observer=None):
    """Advance every environment by one transition and feed the replay.  The replay always receives the
    observation REACHED by the step (also at an episode end: the real terminal / time-limit observation,
    which truncated episodes bootstrap from); only afterwards is the environment reset and ``obs[i]`` replaced
    by the first observation of the new episode.  Returns ``(score, return, died)`` of every episode that ended.
    ``observer`` (window diagnostics, optional) receives the scalars of the transition before the replay and before any reset."""
    finished = []
    for i, e in enumerate(envs):
        _, r, term, trunc, info = e.step(int(actions[i]))
        nxt = observe(e)
        if observer is not None:
            observer.step(i, int(actions[i]), r, term, trunc, info["died"], info["won"])
        replay.add(i, obs[i], int(actions[i]), r, nxt, term, trunc)
        ep_ret[i] += r
        if term or trunc:
            finished.append((info["score"], ep_ret[i], float(info["died"])))
            ep_ret[i] = 0.0
            reset_env(e)
            nxt = observe(e)
        obs[i] = nxt
    return finished


def checked_train_seed(cfg: "TrainConfig", k: int, resumed: bool = False) -> int:
    """``train_seed`` plus the runtime check that this run's episode stream cannot leave its own block: a fresh run
    starts n_envs episodes and every further episode needs at least one environment transition, so
    k <= total_env_steps + n_envs (a resumed run restarts n_envs episodes per resume, so only the block bound applies)."""
    if k >= TRAIN_SEED_BASE or (not resumed and k > cfg.total_env_steps + cfg.n_envs):
        raise AssertionError(f"training episode index {k} is outside this run's seed block "
                             f"(total_env_steps={cfg.total_env_steps}, n_envs={cfg.n_envs}, resumed={resumed})")
    return train_seed(cfg.seed, k)


def train(cfg: TrainConfig, out_dir: Path, log=print, resume: bool = True, _stop_after: int | None = None, window_diagnostics: bool = False) -> dict:
    """Train ``cfg``.  Every eval boundary writes resume.pt + resume_replay.npz in ``out_dir``; calling
    train() again on the same directory continues from there (episodes restart, RNG streams continue),
    so a killed or suspended machine loses at most ``eval_every`` steps.  ``_stop_after`` is for tests.
    ``window_diagnostics`` (default off) writes the descriptive B1/B2 record ``window_diagnostics.json`` next to the run (see window_diag.py);
    it is not part of the configuration, changes nothing the run computes, and is skipped for a resumed run."""
    if cfg.val_set not in SELECTION_SETS:
        raise ValueError(f"val_set={cfg.val_set!r}: a training run may only select checkpoints on {list(SELECTION_SETS)}")
    val_seeds = seed_set(cfg.val_set)  # resolved here, at run time, from the config (not bound at import)
    torch.set_num_threads(cfg.threads)
    device = resolve_device(cfg.device)
    rng = np.random.default_rng(cfg.seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "config.json").write_text(json.dumps(asdict(cfg), indent=1), newline="\n")

    observe = observe_fn(cfg.arch, cfg.obs)
    shape, dtype = obs_spec(cfg.arch, cfg.obs)
    online, target = build_initial_models(cfg, device)
    opt = torch.optim.Adam(online.parameters(), lr=cfg.lr)
    replay = NStepReplay(cfg.buffer, shape, dtype, cfg.n_envs, cfg.n_step, cfg.gamma, quant_scale(cfg.arch, cfg.obs))

    envs = [PacmanEnv(STANDARD) for _ in range(cfg.n_envs)]
    episode_k = 0
    ep_ret = np.zeros(cfg.n_envs)
    obs = []
    for e in envs:
        e.reset(checked_train_seed(cfg, episode_k))
        episode_k += 1
        obs.append(observe(e))

    state_path, replay_path = out_dir / "resume.pt", out_dir / "resume_replay.npz"
    best_val, best_step = -1.0, 0
    env_steps, updates, next_eval = 0, 0, cfg.eval_every
    update_budget, minutes0, resumed = 0.0, 0.0, False
    if resume and state_path.exists() and replay_path.exists():
        ck = torch.load(state_path, map_location="cpu", weights_only=False)
        strip = lambda d: {k: v for k, v in d.items() if k != "device"}  # noqa: E731
        if strip(ck["cfg"]) == strip(asdict(cfg)):
            online.load_state_dict(ck["online"])
            target.load_state_dict(ck["target"])
            opt.load_state_dict(ck["opt"])
            env_steps, updates, next_eval = ck["env_steps"], ck["updates"], ck["next_eval"]
            best_val, best_step, update_budget, minutes0 = ck["best_val"], ck["best_step"], ck["update_budget"], ck["minutes"]
            episode_k = ck["episode_k"]
            rng.bit_generator.state = ck["rng"]
            torch.set_rng_state(ck["torch_rng"])
            n = int(ck["replay_size"])
            with np.load(replay_path) as data:  # close it: Windows cannot os.replace an open file
                for name in ("obs", "next_obs", "act", "ret", "disc"):
                    getattr(replay, name)[:n] = data[name]
            replay.pos, replay.size = int(ck["replay_pos"]), n
            for i, e in enumerate(envs):  # fresh episodes with unused seeds
                e.reset(checked_train_seed(cfg, episode_k, resumed=True))
                episode_k += 1
                obs[i] = observe(e)
            resumed = True
            dropped_rows, partial_rows = truncate_log_to(out_dir / "train_log.jsonl", env_steps)
            log(f"[resume] continuing from env_steps={env_steps} updates={updates}")
        else:
            log("[resume] saved state does not match this config; starting from scratch")
    recorder = None
    if window_diagnostics and resumed:
        log("[window diagnostics] skipped: a resumed run has no complete window history")
    elif window_diagnostics:
        recorder = WindowRecorder(cfg.n_envs, cfg.n_step, cfg.gamma, cfg.total_env_steps)
        replay.on_emit = recorder.on_emit  # read-only verification that the replay emits exactly the windows the recorder counted
    train_log = open(out_dir / "train_log.jsonl", "a" if resumed else "w", newline="\n")
    if resumed:  # explicit marker so a reader of the log can see where the run was interrupted
        train_log.write(json.dumps({"type": "resume", "env_steps": env_steps, "updates": updates,
                                    "dropped_rows": dropped_rows, "partial_rows": partial_rows}) + "\n")
        train_log.flush()
    if not resumed:  # fresh start: record what is about to be trained, before the first update
        online_hash, target_hash = state_hash(online), state_hash(target)
        assert online_hash == target_hash, "the target network must start as an exact copy of the online network"
        train_log.write(json.dumps({"type": "init", "arch": cfg.arch, "seed": cfg.seed, "n_step": cfg.n_step,
                                    "online_hash": online_hash, "target_hash": target_hash}) + "\n")
        train_log.flush()
        (out_dir / "code_version.json").write_text(json.dumps(code_version(REPO_ROOT), indent=1), encoding="utf-8", newline="\n")
        (out_dir / "environment.json").write_text(json.dumps(environment_info(device), indent=1), encoding="utf-8", newline="\n")
    recent_scores, recent_rets, recent_deaths, losses = [], [], [], []
    bad_loss = torch.zeros((), device=device)  # number of non-finite losses this session, accumulated on the device (no sync)
    t0 = time.time() - minutes0 * 60

    def reset_env(e):
        nonlocal episode_k
        e.reset(checked_train_seed(cfg, episode_k, resumed))
        episode_k += 1

    def save_state():
        n = replay.size
        tmp = out_dir / "resume_replay.tmp.npz"
        np.savez(tmp, obs=replay.obs[:n], next_obs=replay.next_obs[:n], act=replay.act[:n], ret=replay.ret[:n], disc=replay.disc[:n])
        torch.save({"cfg": asdict(cfg), "online": online.state_dict(), "target": target.state_dict(), "opt": opt.state_dict(),
                    "env_steps": env_steps, "updates": updates, "next_eval": next_eval, "best_val": best_val,
                    "best_step": best_step, "update_budget": update_budget, "minutes": (time.time() - t0) / 60,
                    "episode_k": episode_k, "rng": rng.bit_generator.state, "torch_rng": torch.get_rng_state(),
                    "replay_size": n, "replay_pos": replay.pos}, out_dir / "resume.tmp.pt")
        os.replace(tmp, replay_path)
        os.replace(out_dir / "resume.tmp.pt", state_path)  # the state file is the commit marker

    last_eval_step = env_steps if resumed else -1  # a resume state is only ever written right after an evaluation
    diag_meta = {"run_name": out_dir.name, "arch": cfg.arch, "n_step": cfg.n_step, "run_seed": cfg.seed, "git_sha": code_version(REPO_ROOT)["git_sha"]} if recorder is not None else None

    def do_eval(tag: str):
        nonlocal best_val, best_step, last_eval_step
        last_eval_step = env_steps
        recs = evaluate_model(online, cfg, STANDARD, val_seeds)
        s = summarize(recs)
        online.train()
        if recorder is not None:  # low-frequency snapshot (one per validation), atomically replaced
            write_atomic(out_dir / "window_diagnostics.partial.json", recorder.to_dict({**diag_meta, "snapshot_env_steps": env_steps}))
        row = {"type": "eval", "env_steps": env_steps, "updates": updates, "val_score": s["score_mean"],
               "val_death": s["death_rate"], "val_win": s["win_rate"], "minutes": (time.time() - t0) / 60,
               "weights_finite": all(bool(torch.isfinite(p).all()) for p in online.parameters())}
        train_log.write(json.dumps(row) + "\n")
        train_log.flush()
        log(f"[{tag}] steps={env_steps} updates={updates} val_score={s['score_mean']:.1f} "
            f"death={s['death_rate']:.2f} win={s['win_rate']:.2f} ({row['minutes']:.1f} min)")
        if s["score_mean"] > best_val:
            best_val, best_step = s["score_mean"], env_steps
            save_checkpoint(out_dir / "best.pt", online, cfg, {"val_score": best_val, "env_steps": env_steps})

    while env_steps < cfg.total_env_steps:
        frac = min(1.0, env_steps / (cfg.eps_frac * cfg.total_env_steps))
        eps = cfg.eps_start + (cfg.eps_end - cfg.eps_start) * frac
        greedy = greedy_actions(online, obs, device)
        explore = rng.random(cfg.n_envs) < eps
        actions = np.where(explore, rng.integers(0, NUM_ACTIONS, cfg.n_envs), greedy)
        if recorder is not None:  # numpy only: the greedy array and eps are the ones this batch really used
            recorder.begin_batch(env_steps, eps, action_mismatch(actions, greedy))

        for score, ep_return, died in collect_step(envs, obs, actions, replay, observe, ep_ret, reset_env, recorder):
            recent_scores.append(score)
            recent_rets.append(ep_return)
            recent_deaths.append(died)
        env_steps += cfg.n_envs

        if replay.size >= cfg.learn_start:
            update_budget += cfg.n_envs / cfg.steps_per_update
            while update_budget >= 1.0:
                update_budget -= 1.0
                o, a, ret, o2, disc = (t.to(device, non_blocking=True) for t in replay.sample(cfg.batch, rng))
                y = td_target(online, target, ret, disc, o2, cfg.double)
                q = online(o).gather(1, a.unsqueeze(1)).squeeze(1)
                loss = F.smooth_l1_loss(q, y)
                opt.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(online.parameters(), cfg.grad_clip)
                opt.step()
                with torch.no_grad():
                    for tp, op in zip(target.parameters(), online.parameters()):
                        tp.mul_(1 - cfg.tau).add_(op.detach(), alpha=cfg.tau)
                updates += 1
                bad_loss += (~torch.isfinite(loss.detach())).to(bad_loss.dtype)
                losses.append(loss.detach())  # no per-update GPU sync
                if len(losses) > 1000:
                    del losses[:-500]

        if len(recent_scores) >= 20 and env_steps % (cfg.n_envs * 500) == 0:
            row = {"type": "train", "env_steps": env_steps, "updates": updates, "eps": eps,
                   "score": float(np.mean(recent_scores)), "return": float(np.mean(recent_rets)),
                   "death": float(np.mean(recent_deaths)), "replay": replay.size, "loss": float(torch.stack(losses[-500:]).mean()) if losses else None}
            train_log.write(json.dumps(row) + "\n")
            train_log.flush()
            recent_scores, recent_rets, recent_deaths = [], [], []

        if env_steps >= next_eval:
            do_eval("val")
            next_eval += cfg.eval_every
            save_state()
            if _stop_after is not None and env_steps >= _stop_after:
                train_log.close()
                return {"interrupted": True, "env_steps": env_steps}

    if last_eval_step != env_steps:  # the budget ended on an evaluation boundary: that evaluation is the final one
        do_eval("final")
    train_log.close()
    if recorder is not None:
        final = recorder.to_dict(diag_meta)
        write_atomic(out_dir / "window_diagnostics.json", final)
        (out_dir / "window_diagnostics.partial.json").unlink(missing_ok=True)
        if not final["integrity"]["complete"]:
            log(f"[window diagnostics] INTEGRITY ERROR: {final['integrity']['errors'] or final['integrity']['checks']}")
    save_checkpoint(out_dir / "last.pt", online, cfg, {"env_steps": env_steps})
    for f in (state_path, replay_path):  # finished: the resume state is no longer needed
        f.unlink(missing_ok=True)
    summary = {"best_val_score": best_val, "best_env_steps": best_step, "updates": updates,
               "minutes": (time.time() - t0) / 60, "env_steps": env_steps, "replay_size": replay.size,
               "episodes_started": episode_k, "nonfinite_loss_updates_this_session": int(bad_loss.item()),
               "weights_finite": all(bool(torch.isfinite(p).all()) for p in online.parameters()), **peak_memory(device)}
    # fields of the preregistered summary contract (docs/prereg/): budget, final replay occupancy, updates, validation schedule, hashes
    log_rows = [json.loads(x) for x in (out_dir / "train_log.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    init_rows = [r for r in log_rows if r.get("type") == "init"]
    summary.update({
        "run_name": out_dir.name, "total_env_steps": cfg.total_env_steps, "replay": {"size": replay.size}, "actual_updates": updates,
        "validation_steps": [r["env_steps"] for r in log_rows if r.get("type") == "eval"], "validation_episodes_each": len(val_seeds),
        "initial_state_dict_sha256": init_rows[0]["online_hash"] if init_rows else None,
        "checkpoints": {"last": {"step": env_steps, "weights_sha256": state_hash(online)},
                        "best": {"step": best_step, "weights_sha256": state_hash(torch.load(out_dir / "best.pt", weights_only=False, map_location="cpu")["state_dict"])}}})
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1), newline="\n")
    return summary
