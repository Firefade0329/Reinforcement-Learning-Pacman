"""Command line entry point:  python -m pacman_rl.cli <command> ...  (run from python/)."""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import fields
from pathlib import Path

from .baselines import make_agent
from .evaluate import SCENARIOS, TEST_SEEDS, VAL_SEEDS, evaluate_named, save_eval, summarize

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS = Path(os.environ.get("PACMAN_RESULTS_DIR") or REPO_ROOT / "results")
SPLITS = {"val": VAL_SEEDS, "test": TEST_SEEDS}


def rel(path) -> str:
    """Path for log output: relative to the repository (or just the name), never an absolute machine path."""
    p = Path(path)
    try:
        return str(p.resolve().relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return p.name  # outside the repository (e.g. a throw-away results dir): the name only


def fmt(s: dict) -> str:
    return (f"score {s['score_mean']:.1f} [{s['score_ci'][0]:.1f}, {s['score_ci'][1]:.1f}]  "
            f"death {s['death_rate']:.2f}  win {s['win_rate']:.2f}  steps {s['steps_mean']:.0f}")


def cmd_baseline(a):
    recs = evaluate_named(a.agent, SCENARIOS[a.scenario], SPLITS[a.split], workers=a.workers)
    out = Path(a.out) if a.out else RESULTS / "eval" / f"{a.agent}__{a.scenario}__{a.split}.json"
    p = save_eval(out, a.agent, a.scenario, a.split, recs)
    print(f"{a.agent:15s} {a.scenario}/{a.split}: {fmt(p['summary'])}")


def cmd_tabular(a):
    from .evaluate import evaluate_batched
    from .tabular import TabularAgent, save_q, train_tabular

    q, curve = train_tabular(a.episodes, a.seed, log=print)
    run = RESULTS / "runs" / f"tabular_s{a.seed}"
    save_q(run / "q.json", q, curve)
    agent = TabularAgent(q)
    for split in ("val", "test") if a.test else ("val",):
        for scen in ("standard", "hard") if split == "test" else ("standard",):
            from .evaluate import play_episode
            recs = [play_episode(agent, SCENARIOS[scen], s) for s in SPLITS[split]]
            p = save_eval(run / f"{split}_{scen}.json", f"tabular-q_s{a.seed}", scen, split, recs)
            print(f"tabular-q s{a.seed} {scen}/{split}: {fmt(p['summary'])}")


def cmd_train(a):
    from .dqn import TrainConfig, train

    kw = {f.name: getattr(a, f.name) for f in fields(TrainConfig) if getattr(a, f.name, None) is not None}
    cfg = TrainConfig(**kw)
    name = a.name or f"{cfg.arch}_s{cfg.seed}"
    out = RESULTS / "runs" / name
    print(f"training {name} -> {rel(out)}\n{cfg}", flush=True)
    print(json.dumps(train(cfg, out, log=lambda m: print(m, flush=True), resume=not a.no_resume)))


def cmd_eval_model(a):
    from .dqn import evaluate_model, load_checkpoint

    model, cfg, _ = load_checkpoint(Path(a.ckpt), a.device)
    ck_dir = Path(a.ckpt).parent
    for scen in a.scenarios:
        recs = evaluate_model(model, cfg, SCENARIOS[scen], SPLITS[a.split])
        p = save_eval(ck_dir / f"{a.split}_{scen}.json", ck_dir.name, scen, a.split, recs)
        print(f"{ck_dir.name} {scen}/{a.split}: {fmt(p['summary'])}", flush=True)


def cmd_bench(a):
    import time

    import torch

    from .dqn import in_ch, resolve_device, TrainConfig
    from .env import FIELD_SHAPE
    from .features import FEATURE_DIM
    from .models import build_model

    dev = resolve_device(a.device)
    print(f"device: {dev}" + (f" ({torch.cuda.get_device_name(dev)})" if dev.type == "cuda" else ""))
    for arch in a.archs:
        cfg = TrainConfig(arch=arch)
        model = build_model(arch, cfg.width, cfg.dueling, in_ch(cfg)).to(dev)
        opt = torch.optim.Adam(model.parameters(), lr=1e-4)
        shape = (FEATURE_DIM,) if arch == "mlp" else FIELD_SHAPE
        x = torch.rand(a.batch, *shape, device=dev)
        if arch != "mlp":  # a valid one-hot Pacman plane, as in real observations
            x[:, 2] = 0
            x[:, 2, 5, 5] = 1
        def step():
            opt.zero_grad(set_to_none=True)
            model(x).sum().backward()
            opt.step()
        for _ in range(3):
            step()
        if dev.type == "cuda":
            torch.cuda.synchronize()
        t = time.time()
        for _ in range(a.iters):
            step()
        if dev.type == "cuda":
            torch.cuda.synchronize()
        print(f"{arch:5s} batch {a.batch}: {(time.time() - t) / a.iters * 1000:7.1f} ms/update")


def cmd_replay(a):
    from .render import record

    cfg = SCENARIOS[a.scenario]
    if a.agent.endswith(".pt"):
        import numpy as np
        import torch

        from .dqn import load_checkpoint, observe_fn

        model, tcfg, _ = load_checkpoint(Path(a.agent))
        model.eval()
        observe = observe_fn(tcfg.arch, tcfg.obs)

        def act(env):
            with torch.no_grad():
                return int(model(torch.from_numpy(observe(env))[None]).argmax(1))

        label = Path(a.agent).parent.name
    else:
        agent = make_agent(a.agent, a.seed)
        agent.reset()
        act, label = agent.act, a.agent
    out = Path(a.out) if a.out else RESULTS / "replays" / f"{label}__{a.scenario}__seed{a.seed}.gif"
    print(label, a.scenario, "-> score/steps/died/won", record(act, cfg, a.seed, out, label), rel(out))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("baseline")
    p.add_argument("--agent", required=True, choices=["random", "greedy-bfs", "legacy", "safe-heuristic"])
    p.add_argument("--scenario", default="standard", choices=list(SCENARIOS))
    p.add_argument("--split", default="val", choices=list(SPLITS))
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--out")
    p.set_defaults(fn=cmd_baseline)

    p = sub.add_parser("tabular")
    p.add_argument("--episodes", type=int, default=3000)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--test", action="store_true", help="also evaluate on the test split (final runs only)")
    p.set_defaults(fn=cmd_tabular)

    p = sub.add_parser("train")
    p.add_argument("--name")
    p.add_argument("--arch", choices=["mlp", "cnn2", "res2", "res4", "res8"])
    p.add_argument("--obs", choices=["fields", "grid"])
    p.add_argument("--device", choices=["cpu", "cuda", "auto"])
    for k, t in [("width", int), ("n_step", int), ("batch", int), ("buffer", int), ("learn_start", int),
                 ("n_envs", int), ("steps_per_update", int), ("total_env_steps", int), ("eval_every", int),
                 ("seed", int), ("threads", int), ("lr", float), ("gamma", float), ("tau", float),
                 ("eps_end", float), ("eps_frac", float)]:
        p.add_argument(f"--{k}", type=t)
    p.add_argument("--no-resume", action="store_true", help="ignore resume.pt and start from scratch")
    p.add_argument("--no-double", dest="double", action="store_false", default=None)
    p.add_argument("--no-dueling", dest="dueling", action="store_false", default=None)
    p.set_defaults(fn=cmd_train)

    p = sub.add_parser("eval-model")
    p.add_argument("--ckpt", required=True)
    p.add_argument("--split", default="val", choices=list(SPLITS))
    p.add_argument("--scenarios", nargs="+", default=["standard"], choices=list(SCENARIOS))
    p.add_argument("--device", default="cpu", choices=["cpu", "cuda", "auto"])
    p.set_defaults(fn=cmd_eval_model)

    p = sub.add_parser("bench", help="time gradient updates per architecture on a device")
    p.add_argument("--device", default="auto", choices=["cpu", "cuda", "auto"])
    p.add_argument("--archs", nargs="+", default=["mlp", "cnn2", "res2", "res4", "res8"])
    p.add_argument("--batch", type=int, default=32)
    p.add_argument("--iters", type=int, default=30)
    p.set_defaults(fn=cmd_bench)

    p = sub.add_parser("replay")
    p.add_argument("--agent", required=True, help="random|greedy-bfs|legacy|safe-heuristic or path to best.pt")
    p.add_argument("--seed", type=int, default=10000)
    p.add_argument("--scenario", default="standard", choices=list(SCENARIOS))
    p.add_argument("--out")
    p.set_defaults(fn=cmd_replay)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
