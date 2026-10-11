"""Evaluation of one checkpoint into its own output directory (the new, overwrite-proof path of ``eval-model``).

Outputs go to ``<out_dir>/<label>/<scenario>.json`` (label defaults to the checkpoint's stem: ``last`` / ``best``), so
evaluating last.pt and best.pt can never overwrite each other and nothing is written next to the checkpoints.  An
existing output is never replaced unless ``force``.  Every file records the checkpoint's identity (file hash and
canonical weight hash, training step), the seed range, the device and the torch thread count actually used.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import torch

from .dqn import evaluate_model, load_checkpoint
from .evaluate import SCENARIOS, save_eval, seed_set
from .provenance import environment_info, file_sha256, state_hash


PREREG_EVAL_SCHEMA = "prereg-eval-1"


def prereg_eval_payload(records, *, run_name, cfg, label, step, weights_sha256, code_commit, scenario, device, threads,
                        synthetic=False, reused_from=None) -> dict:
    """The fixed wrapper read by the analysis script (ANALYSIS_SPEC section 2.2): schema_version + meta + records."""
    meta = {"synthetic": synthetic, "run_name": run_name, "arch": cfg.arch, "n_step": cfg.n_step, "train_seed": cfg.seed,
            "checkpoint": label, "checkpoint_step": step, "weights_sha256": weights_sha256, "code_commit": code_commit,
            "scenario": scenario, "device": device, "torch_threads": threads}
    if reused_from:
        meta["reused_from"] = reused_from
    return {"schema_version": PREREG_EVAL_SCHEMA, "meta": meta, "records": records}


def evaluate_checkpoint(ckpt, split: str, scenarios, out_dir, *, label: str | None = None, device: str = "cpu",
                        threads: int = 1, force: bool = False, unseal=None, prereg_meta: dict | None = None) -> dict[str, Path]:
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
        if prereg_meta is not None:  # preregistered format: wrapper object with meta + records, nothing else
            payload = prereg_eval_payload(records, run_name=prereg_meta["run_name"], cfg=cfg, label=label, step=ck.get("env_steps"),
                                          weights_sha256=identity["state_sha256"], code_commit=prereg_meta["code_commit"], scenario=sc,
                                          device=device, threads=torch.get_num_threads(), synthetic=prereg_meta.get("synthetic", False))
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w" if force else "x", encoding="utf-8", newline="\n") as f:  # "x": never replaces an existing file
                json.dump(payload, f, indent=1)
        else:
            save_eval(path, f"{ckpt.parent.name}/{label}", sc, split, records, extra=extra)
    return targets
