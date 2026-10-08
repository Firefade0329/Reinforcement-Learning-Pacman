"""(Double / Dueling / n-step) DQN trainer with vectorised environments, CPU-friendly."""
from __future__ import annotations

import copy
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from .env import FIELD_SHAPE, NUM_ACTIONS, OBS_SHAPE, STANDARD, PacmanEnv
from .evaluate import VAL_SEEDS, evaluate_batched, summarize, train_seed
from .features import FEATURE_DIM, feature_vector
from .models import build_model
from .replay import NStepReplay


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


def evaluate_model(model, cfg: "TrainConfig", scenario_cfg, seeds):
    return evaluate_batched(make_policy(model), scenario_cfg, seeds, observe_fn(cfg.arch, cfg.obs))


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


def train(cfg: TrainConfig, out_dir: Path, log=print) -> dict:
    torch.set_num_threads(cfg.threads)
    torch.manual_seed(cfg.seed)  # also seeds CUDA; GPU runs are statistically, not bitwise, reproducible
    device = resolve_device(cfg.device)
    rng = np.random.default_rng(cfg.seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "config.json").write_text(json.dumps(asdict(cfg), indent=1))

    observe = observe_fn(cfg.arch, cfg.obs)
    shape, dtype = obs_spec(cfg.arch, cfg.obs)
    online = build_model(cfg.arch, cfg.width, cfg.dueling, in_ch(cfg)).to(device)
    target = copy.deepcopy(online)
    target.eval()
    opt = torch.optim.Adam(online.parameters(), lr=cfg.lr)
    replay = NStepReplay(cfg.buffer, shape, dtype, cfg.n_envs, cfg.n_step, cfg.gamma)

    envs = [PacmanEnv(STANDARD) for _ in range(cfg.n_envs)]
    episode_k = 0
    ep_ret = np.zeros(cfg.n_envs)
    obs = []
    for e in envs:
        e.reset(train_seed(cfg.seed, episode_k))
        episode_k += 1
        obs.append(observe(e))

    train_log = open(out_dir / "train_log.jsonl", "w")
    best_val, best_step = -1.0, 0
    env_steps, updates, next_eval = 0, 0, cfg.eval_every
    recent_scores, recent_rets, recent_deaths, losses = [], [], [], []
    t0 = time.time()
    update_budget = 0.0

    def do_eval(tag: str):
        nonlocal best_val, best_step
        recs = evaluate_model(online, cfg, STANDARD, VAL_SEEDS)
        s = summarize(recs)
        online.train()
        row = {"type": "eval", "env_steps": env_steps, "updates": updates, "val_score": s["score_mean"],
               "val_death": s["death_rate"], "val_win": s["win_rate"], "minutes": (time.time() - t0) / 60}
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
        online.eval()
        with torch.no_grad():
            greedy = online(torch.from_numpy(np.stack(obs)).to(device)).argmax(dim=1).cpu().numpy()
        online.train()
        explore = rng.random(cfg.n_envs) < eps
        actions = np.where(explore, rng.integers(0, NUM_ACTIONS, cfg.n_envs), greedy)

        for i, e in enumerate(envs):
            _, r, term, trunc, info = e.step(int(actions[i]))
            nxt = observe(e)
            replay.add(i, obs[i], int(actions[i]), r, nxt, term, trunc)
            ep_ret[i] += r
            if term or trunc:
                recent_scores.append(info["score"])
                recent_rets.append(ep_ret[i])
                recent_deaths.append(float(info["died"]))
                ep_ret[i] = 0.0
                e.reset(train_seed(cfg.seed, episode_k))
                episode_k += 1
                nxt = observe(e)
            obs[i] = nxt
        env_steps += cfg.n_envs

        if replay.size >= cfg.learn_start:
            update_budget += cfg.n_envs / cfg.steps_per_update
            while update_budget >= 1.0:
                update_budget -= 1.0
                o, a, ret, o2, disc = (t.to(device, non_blocking=True) for t in replay.sample(cfg.batch, rng))
                with torch.no_grad():
                    if cfg.double:
                        a2 = online(o2).argmax(dim=1, keepdim=True)
                        q2 = target(o2).gather(1, a2).squeeze(1)
                    else:
                        q2 = target(o2).max(dim=1).values
                    y = ret + disc * q2
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
                losses.append(loss.detach())  # no per-update GPU sync
                if len(losses) > 1000:
                    del losses[:-500]

        if len(recent_scores) >= 20 and env_steps % (cfg.n_envs * 500) == 0:
            row = {"type": "train", "env_steps": env_steps, "updates": updates, "eps": eps,
                   "score": float(np.mean(recent_scores)), "return": float(np.mean(recent_rets)),
                   "death": float(np.mean(recent_deaths)), "loss": float(torch.stack(losses[-500:]).mean()) if losses else None}
            train_log.write(json.dumps(row) + "\n")
            train_log.flush()
            recent_scores, recent_rets, recent_deaths = [], [], []

        if env_steps >= next_eval:
            do_eval("val")
            next_eval += cfg.eval_every

    do_eval("final")
    train_log.close()
    save_checkpoint(out_dir / "last.pt", online, cfg, {"env_steps": env_steps})
    summary = {"best_val_score": best_val, "best_env_steps": best_step, "updates": updates,
               "minutes": (time.time() - t0) / 60}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1))
    return summary
