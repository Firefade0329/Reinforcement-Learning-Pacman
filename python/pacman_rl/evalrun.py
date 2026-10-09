"""Evaluation of one checkpoint into its own output directory (the new, overwrite-proof path of ``eval-model``).

Outputs go to ``<out_dir>/<label>/<scenario>.json`` (label defaults to the checkpoint's stem: ``last`` / ``best``), so
evaluating last.pt and best.pt can never overwrite each other and nothing is written next to the checkpoints.  An
existing output is never replaced unless ``force``.  Every file records the checkpoint's identity (file hash and
canonical weight hash, training step), the seed range, the device and the torch thread count actually used.
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import torch

from .dqn import evaluate_model, load_checkpoint
from .evaluate import SCENARIOS, save_eval, seed_set
from .provenance import environment_info, file_sha256, state_hash


def evaluate_checkpoint(ckpt, split: str, scenarios, out_dir, *, label: str | None = None, device: str = "cpu",
                        threads: int = 1, force: bool = False, unseal=None) -> dict[str, Path]:
    ckpt, out_dir = Path(ckpt), Path(out_dir)
    label = label or ckpt.stem
    dest = out_dir / label
    targets = {sc: dest / f"{sc}.json" for sc in scenarios}
    clash = [str(p.relative_to(out_dir)) for p in targets.values() if p.exists()]
    if clash and not force:
        raise FileExistsError(f"refusing to overwrite existing evaluation output(s) in {out_dir.name}: {clash} (use force)")
    seeds = seed_set(split, unseal)  # sealed sets raise here unless a verified token is given
    torch.set_num_threads(threads)
    model, cfg, ck = load_checkpoint(ckpt, device)
    identity = {"label": label, "file_sha256": file_sha256(ckpt), "state_sha256": state_hash(model),
                "env_steps": ck.get("env_steps"), "run": ckpt.parent.name}
    extra = {"checkpoint": identity, "cfg": asdict(cfg), "split": split,
             "seeds": {"first": seeds[0], "last": seeds[-1], "count": len(seeds)},
             "eval_device": device, "torch_threads": torch.get_num_threads(), "environment": environment_info(torch.device(device)),
             "records_have_truncated_field": True}
    for sc, path in targets.items():
        records = evaluate_model(model, cfg, SCENARIOS[sc], seeds, record_truncated=True)
        save_eval(path, f"{ckpt.parent.name}/{label}", sc, split, records, extra=extra)
    return targets
