"""Synthetic study generator for the analysis acceptance tests (ANALYSIS_SPEC section 8).  Writes files only; it never calls
the analysis code and never produces an expected value."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ARCHS, NS, SEEDS = ("cnn2", "res4", "res8"), (1, 3), (100, 101, 102, 103, 104)
COMMIT = "a" * 40


def sha(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1), encoding="utf-8")


def matrix_rows():
    import csv

    with open(REPO / "docs" / "prereg" / "matrix.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def typed(row):
    t = dict(row)
    for k in ("order", "n_step", "seed", "total_env_steps", "width", "n_envs", "steps_per_update", "batch", "buffer", "learn_start", "eval_every", "threads"):
        t[k] = int(t[k])
    for k in ("lr", "gamma"):
        t[k] = float(t[k])
    for k in ("double", "dueling"):
        t[k] = t[k] == "true"
    return t


class Study:
    def __init__(self, root: Path, d=None, score_fn=None, hard=False, hard_d=None, formal=False):
        """formal=True builds the same fake study but labelled for formal mode (synthetic=false, status 'frozen', texts frozen) so that the
        formal-mode gates can be tested; the DATA are still invented."""
        self.root, self.hard, self.formal = Path(root), hard, formal
        self.d = d or {a: [0] * 5 for a in ARCHS}
        self.score_fn = score_fn
        self.hard_d = hard_d or self.d
        self.rows = [typed(r) for r in matrix_rows()]
        self.prereg = self.root / "docs" / "prereg"
        self.runs = self.root / "results_prereg" / "runs"
        self.build()

    # --- scores
    def score(self, a, n, si, e, hard=False):
        if self.score_fn:
            return self.score_fn(a, n, si, e)
        return 100 + (0 if n == 3 else (self.hard_d if hard else self.d)[a][si])

    def records(self, a, n, si, hard=False):
        recs = []
        for e in range(300):
            recs.append({"seed": 30000 + e, "score": self.score(a, n, si, e, hard), "steps": 100, "died": True, "won": False, "truncated": False})
        return recs

    # --- files
    def build(self):
        self.prereg.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO / "docs" / "prereg" / "matrix.csv", self.prereg / "matrix.csv")
        frozen = json.loads((REPO / "docs" / "prereg" / "frozen_config_v0.3.2.json").read_text())
        frozen.update(status="frozen" if self.formal else "synthetic", code_commit=COMMIT, machine_id="synthetic", worker_count=2, hard_enabled=self.hard)
        write_json(self.prereg / "frozen_config_v0.3.2.json", frozen)
        self.frozen = frozen
        (self.prereg / "analysis.py").write_text((REPO / "python" / "scripts" / "prereg_analysis.py").read_text(), encoding="utf-8")
        (self.prereg / "requirements.lock").write_text("numpy==2.5.3\n")
        (self.prereg / "PREREG_ARCH_NSTEP_v0.3.2.md").write_text("SYNTHETIC FAKE preregistration text (test fixture)\n")
        (self.prereg / "ANALYSIS_SPEC_v0.3.2.md").write_text("SYNTHETIC FAKE analysis specification text (test fixture)\n")
        self.fsha = sha(self.prereg / "frozen_config_v0.3.2.json")
        for r in self.rows:
            self.write_run(r)
        self.write_manifest_and_seal()

    def write_run(self, r):
        name, a, n, s = r["run_name"], r["arch"], r["n_step"], r["seed"]
        si = SEEDS.index(s)
        d = self.runs / name
        cfg = {k: r[k] for k in r}
        cfg.update({k: self.frozen[k] for k in ("eps_start", "eps_end", "eps_frac", "tau", "grad_clip", "val_seeds", "test_seeds", "smoke_eval_seeds", "smoke_run_seeds",
                                                "eval_episodes", "final_eval_device", "final_eval_threads", "hard_enabled", "machine_id", "train_device",
                                                "validation_device", "worker_count", "max_episode_steps", "train_scenario", "hard_chase_p")})
        cfg.update(code_commit=COMMIT, frozen_config_sha256=self.fsha, val_set="prereg_val")
        write_json(d / "config.json", cfg)
        init = hashlib.sha256(f"init-{a}-{s}".encode()).hexdigest()
        w = hashlib.sha256(f"weights-{name}".encode()).hexdigest()
        summary = {"run_name": name, "total_env_steps": 300000, "replay": {"size": 100000}, "actual_updates": 74000,
                   "validation_steps": list(range(20000, 300001, 20000)), "validation_episodes_each": 50, "initial_state_dict_sha256": init,
                   "checkpoints": {"last": {"step": 300000, "weights_sha256": w}, "best": {"step": 20000, "weights_sha256": w}}}
        write_json(d / "summary.json", summary)
        for label in ("last", "best"):
            self.write_eval(d / label / "standard.json", r, label, "standard", self.records(a, n, si), w, reused=(label == "best"))
        if self.hard:
            self.write_eval(d / "last" / "hard.json", r, "last", "hard", self.records(a, n, si, hard=True), w)

    def write_eval(self, path, r, label, scenario, records, w, reused=False):
        meta = {"synthetic": not self.formal, "run_name": r["run_name"], "arch": r["arch"], "n_step": r["n_step"], "train_seed": r["seed"], "checkpoint": label,
                "checkpoint_step": 300000 if label == "last" else 20000, "weights_sha256": w, "code_commit": COMMIT, "scenario": scenario,
                "device": "cpu", "torch_threads": 1}
        if reused:
            meta["reused_from"] = "last"
        write_json(path, {"schema_version": "prereg-eval-1", "meta": meta, "records": records})

    def required(self):
        rels = ["config.json", "summary.json", "last/standard.json", "best/standard.json"] + (["last/hard.json"] if self.frozen["hard_enabled"] else [])
        return [f"{r['run_name']}/{rel}" for r in self.rows for rel in rels]

    def write_manifest_and_seal(self, keep_missing=True):
        frozen_files = {f"docs/prereg/{n}": sha(self.prereg / n) for n in ("matrix.csv", "frozen_config_v0.3.2.json", "analysis.py", "requirements.lock", "PREREG_ARCH_NSTEP_v0.3.2.md", "ANALYSIS_SPEC_v0.3.2.md")}
        manifest = {"schema_version": "prereg-freeze-1", "synthetic": not self.formal, "complete": True, "spec_version": "0.3.2", "code_commit": COMMIT,
                    "project_root": str(self.root), "matrix_path": "docs/prereg/matrix.csv", "config_path": "docs/prereg/frozen_config_v0.3.2.json",
                    "analysis_script_path": "docs/prereg/analysis.py", "dependency_lock_path": "docs/prereg/requirements.lock",
                    "frozen_files": frozen_files, "seal_path": "results_prereg/evaluation_seal.json"}
        write_json(self.prereg / "freeze_manifest.json", manifest)
        self.manifest = self.prereg / "freeze_manifest.json"
        self.reseal()

    def reseal(self, stale=()):
        files = {k: sha(self.runs / k) for k in self.required() if (self.runs / k).exists() and k not in stale}
        old = {}
        seal_path = self.root / "results_prereg" / "evaluation_seal.json"
        if seal_path.exists():
            old = json.loads(seal_path.read_text())["files"]
        for k in self.required():
            if k not in files:
                files[k] = old.get(k, "0" * 64)  # a deleted / deliberately stale file keeps its sealed hash
        write_json(seal_path, {"schema_version": "prereg-seal-1", "synthetic": not self.formal, "freeze_manifest_sha256": sha(self.manifest), "all_training_complete": True,
                               "all_checkpoint_checks_passed": True, "runs": [r["run_name"] for r in self.rows], "files": files, "attempts": []})

    # --- helpers for the tests
    def path(self, run, rel):
        return self.runs / run / rel

    def edit_json(self, run, rel, fn, reseal=True):
        p = self.path(run, rel)
        d = json.loads(p.read_text())
        fn(d)
        p.write_text(json.dumps(d, indent=1))
        if reseal:
            self.reseal()
