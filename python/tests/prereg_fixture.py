"""Synthetic study generator for the analysis acceptance tests (ANALYSIS_SPEC section 8).  Writes files only; it never calls
the analysis code and never produces an expected value."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
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
    def __init__(self, root: Path, d=None, score_fn=None, hard=False, hard_d=None, formal=False, best_fn=None, hard_fn=None, rec_fn=None,
                 best_step_fn=None, summary_fn=None, attempts=(), deviations=None, pre_f=None, side_branch_c=False):
        """formal=True builds the same fake study but labelled for formal mode (synthetic=false, status 'frozen', all mandatory files frozen) INSIDE A REAL
        TEMPORARY GIT REPOSITORY: the code files are committed as C, the configuration / manifest / texts as F (HEAD), and a valid final-evaluation
        environment file and protocol_evidence are sealed, so that the formal identity checks can be tested; the DATA are still invented.
        best_fn(a, n, si, e) / hard_fn(a, n, si, e): scores of the best checkpoint / of the hard scenario (default: best equals last, hard = d-based);
        best_step_fn(a, n, si): the selected validation step; rec_fn(kind, a, n, si, e) -> dict of record overrides (steps/died/won/truncated/score)
        for kind in last / best / hard; summary_fn(name, summary) edits the run summary; attempts / deviations: seal attempts / manifest deviations."""
        self.root, self.hard, self.formal = Path(root), hard, formal
        self.commit = COMMIT
        self.best_fn, self.hard_fn, self.rec_fn, self.best_step_fn, self.summary_fn = best_fn, hard_fn, rec_fn, best_step_fn, summary_fn
        self.attempts, self.deviations = list(attempts), deviations
        self.pre_f, self.side_branch_c = pre_f, side_branch_c  # formal studies: pre_f(study) edits the repository between C and F; side_branch_c: C is not an ancestor of F
        self.d = d or {a: [0] * 5 for a in ARCHS}
        self.score_fn = score_fn
        self.hard_d = hard_d or self.d
        self.rows = [typed(r) for r in matrix_rows()]
        self.prereg = self.root / "docs" / "prereg"
        self.runs = self.root / "results_prereg" / "runs"
        self.build()

    # --- scores
    def score(self, a, n, si, e, hard=False, best=False):
        if hard and self.hard_fn:
            return self.hard_fn(a, n, si, e)
        if best and self.best_fn:
            return self.best_fn(a, n, si, e)
        if self.score_fn:
            return self.score_fn(a, n, si, e)
        return 100 + (0 if n == 3 else (self.hard_d if hard else self.d)[a][si])

    def records(self, a, n, si, hard=False, best=False):
        recs = []
        kind = "hard" if hard else "best" if best else "last"
        for e in range(300):
            rec = {"seed": 30000 + e, "score": self.score(a, n, si, e, hard, best), "steps": 100, "died": True, "won": False, "truncated": False}
            if self.rec_fn:
                rec.update(self.rec_fn(kind, a, n, si, e) or {})
            recs.append(rec)
        return recs

    # --- files
    # --- the git side of a formal study
    def git(self, *a):
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "core.autocrlf=false", *a], cwd=self.root, check=True,
                              capture_output=True, text=True).stdout.strip()

    def commit_all(self, msg):
        self.git("add", "-A")
        self.git("commit", "-qm", msg)
        return self.git("rev-parse", "HEAD")

    def write_code_side(self):
        """Files that belong to the CODE commit C of a formal study (the analysis script, the snapshot, the diagnostic code, .gitattributes, the matrix)."""
        self.prereg.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO / "docs" / "prereg" / "matrix.csv", self.prereg / "matrix.csv")
        (self.prereg / "analysis.py").write_text((REPO / "python" / "scripts" / "prereg_analysis.py").read_text(), encoding="utf-8")
        (self.prereg / "dependency_lock.txt").write_text("matplotlib==0.0.0\nnumpy==0.0.0\npytest==0.0.0\ntorch==0.0.0\n")  # clearly fake pins
        shutil.copy(REPO / ".gitattributes", self.root / ".gitattributes")
        (self.root / ".gitignore").write_text("results_prereg/\n")  # the results are never part of C or F
        for rel, text in (("python/pacman_rl/window_diag.py", "# fake diagnostic definition\n"), ("python/scripts/window_diagnostics_summary.py", "# fake diagnostic summary\n"),
                          ("python/scripts/prereg_analysis.requirements.txt", "numpy==0.0.0\n")):
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.root / rel).write_text(text)

    def env_record(self, F):
        return {"utc": "2000-01-01T00:00:00Z", "machine_id": "synthetic", "evaluation_device": "cpu",
                "environment": {"python": "0", "torch": "0", "numpy": "0", "cuda_runtime": None, "cudnn": None, "device_type": "cpu", "gpu_name": None, "torch_threads": 1,
                                "deterministic_algorithms": False, "cudnn_deterministic": False, "cudnn_benchmark": False},
                "code_version": {"git_sha": F, "git_dirty": False}, "preflight": {"head": F, "code_commit": self.commit, "freeze_commit_of_runs": F}}

    def build(self):
        self.prereg.mkdir(parents=True, exist_ok=True)
        if self.formal:
            self.write_code_side()
            self.git("init", "-q")
            self.commit = self.commit_all("C: code side")
            if self.side_branch_c:  # the configuration will name a real commit that is NOT an ancestor of F
                main = self.git("rev-parse", "--abbrev-ref", "HEAD")
                self.git("checkout", "-q", "-b", "side")
                self.git("commit", "-q", "--allow-empty", "-m", "side branch commit")  # same trees as C: only the ancestry differs
                self.commit = self.git("rev-parse", "HEAD")
                self.git("checkout", "-q", main)
        else:
            shutil.copy(REPO / "docs" / "prereg" / "matrix.csv", self.prereg / "matrix.csv")
            (self.prereg / "analysis.py").write_text((REPO / "python" / "scripts" / "prereg_analysis.py").read_text(), encoding="utf-8")
            (self.prereg / "requirements.lock").write_text("numpy==2.5.3\n")
        frozen = json.loads((REPO / "docs" / "prereg" / "frozen_config_v0.3.2.json").read_text())
        frozen.update(status="frozen" if self.formal else "synthetic", code_commit=self.commit, machine_id="synthetic", worker_count=2, hard_enabled=self.hard)
        self.frozen = frozen
        for name, text in (("PREREG_ARCH_NSTEP_v0.3.2.md", "SYNTHETIC FAKE preregistration text (test fixture)\n"),
                           ("ANALYSIS_SPEC_v0.3.2.md", "SYNTHETIC FAKE analysis specification text (test fixture)\n")):
            (self.prereg / name).write_text(text)
        if self.formal:
            (self.prereg / "CLAUDE_HANDOFF_v0.3.2.md").write_text("SYNTHETIC FAKE hand-over text (test fixture)\n")
            (self.prereg / "FREEZE_CHECKLIST.md").write_text("SYNTHETIC FAKE checklist (test fixture)\n")
            lock_rel = "dependency_lock.txt"
        else:
            lock_rel = "requirements.lock"
        fill = frozen["to_fill_at_freeze"]
        fill.update(analysis_script_sha256=sha(self.prereg / "analysis.py"), preregistration_document_sha256=sha(self.prereg / "PREREG_ARCH_NSTEP_v0.3.2.md"),
                    dependency_lock_sha256=sha(self.prereg / lock_rel))
        write_json(self.prereg / "frozen_config_v0.3.2.json", frozen)
        self.fsha = sha(self.prereg / "frozen_config_v0.3.2.json")
        if self.formal:
            if self.pre_f:
                self.pre_f(self)
            self.write_manifest()
            self.freeze_commit = self.commit_all("F: freeze material")  # F = HEAD; the results below are ignored by git
            for r in self.rows:
                self.write_run(r)
            self.write_env()
            self.reseal()
        else:
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
        cfg.update(code_commit=self.commit, frozen_config_sha256=self.fsha, val_set="prereg_val")
        write_json(d / "config.json", cfg)
        init = hashlib.sha256(f"init-{a}-{s}".encode()).hexdigest()
        w = hashlib.sha256(f"weights-{name}".encode()).hexdigest()
        distinct = self.best_fn is not None  # a best checkpoint with its own weights and its own evaluation
        wb = hashlib.sha256(f"best-weights-{name}".encode()).hexdigest() if distinct else w
        bstep = self.best_step_fn(a, n, si) if self.best_step_fn else (100000 if distinct else 20000)
        summary = {"run_name": name, "total_env_steps": 300000, "replay": {"size": 100000}, "actual_updates": 74000,
                   "validation_steps": list(range(20000, 300001, 20000)), "validation_episodes_each": 50, "initial_state_dict_sha256": init,
                   "checkpoints": {"last": {"step": 300000, "weights_sha256": w}, "best": {"step": bstep, "weights_sha256": wb}}}
        if self.summary_fn:
            self.summary_fn(name, summary)
        write_json(d / "summary.json", summary)
        self.write_eval(d / "last" / "standard.json", r, "last", "standard", self.records(a, n, si), w)
        self.write_eval(d / "best" / "standard.json", r, "best", "standard", self.records(a, n, si, best=True), wb, reused=not distinct, step=bstep)
        if self.hard:
            self.write_eval(d / "last" / "hard.json", r, "last", "hard", self.records(a, n, si, hard=True), w)

    def write_eval(self, path, r, label, scenario, records, w, reused=False, step=None):
        meta = {"synthetic": not self.formal, "run_name": r["run_name"], "arch": r["arch"], "n_step": r["n_step"], "train_seed": r["seed"], "checkpoint": label,
                "checkpoint_step": 300000 if label == "last" else (step if step is not None else 20000), "weights_sha256": w, "code_commit": self.commit, "scenario": scenario,
                "device": "cpu", "torch_threads": 1}
        if reused:
            meta["reused_from"] = "last"
        write_json(path, {"schema_version": "prereg-eval-1", "meta": meta, "records": records})

    def required(self):
        rels = ["config.json", "summary.json", "last/standard.json", "best/standard.json"] + (["last/hard.json"] if self.frozen["hard_enabled"] else [])
        return [f"{r['run_name']}/{rel}" for r in self.rows for rel in rels]

    def write_manifest(self):
        if self.formal:
            names = ["matrix.csv", "frozen_config_v0.3.2.json", "analysis.py", "dependency_lock.txt", "PREREG_ARCH_NSTEP_v0.3.2.md", "ANALYSIS_SPEC_v0.3.2.md",
                     "CLAUDE_HANDOFF_v0.3.2.md", "FREEZE_CHECKLIST.md"]
            frozen_files = {f"docs/prereg/{n}": sha(self.prereg / n) for n in names}
            for rel in (".gitattributes", "python/pacman_rl/window_diag.py", "python/scripts/window_diagnostics_summary.py", "python/scripts/prereg_analysis.requirements.txt"):
                frozen_files[rel] = sha(self.root / rel)
            lock = "docs/prereg/dependency_lock.txt"
        else:
            frozen_files = {f"docs/prereg/{n}": sha(self.prereg / n) for n in ("matrix.csv", "frozen_config_v0.3.2.json", "analysis.py", "requirements.lock", "PREREG_ARCH_NSTEP_v0.3.2.md", "ANALYSIS_SPEC_v0.3.2.md")}
            lock = "docs/prereg/requirements.lock"
        manifest = {"schema_version": "prereg-freeze-1", "synthetic": not self.formal, "complete": True, "spec_version": "0.3.2", "code_commit": self.commit,
                    "project_root": str(self.root), "matrix_path": "docs/prereg/matrix.csv", "config_path": "docs/prereg/frozen_config_v0.3.2.json",
                    "analysis_script_path": "docs/prereg/analysis.py", "dependency_lock_path": lock,
                    "frozen_files": frozen_files, "seal_path": "results_prereg/evaluation_seal.json"}
        if self.deviations is not None:
            manifest["deviations"] = self.deviations
        write_json(self.prereg / "freeze_manifest.json", manifest)
        self.manifest = self.prereg / "freeze_manifest.json"

    def write_env(self):
        write_json(self.root / "results_prereg" / "final_eval_environment.json", self.env_record(self.freeze_commit))

    def write_manifest_and_seal(self, keep_missing=True):
        self.write_manifest()
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
        obj = {"schema_version": "prereg-seal-1", "synthetic": not self.formal, "freeze_manifest_sha256": sha(self.manifest), "all_training_complete": True,
               "all_checkpoint_checks_passed": True, "runs": [r["run_name"] for r in self.rows], "files": files, "attempts": self.attempts}
        if self.formal:
            env = self.root / "results_prereg" / "final_eval_environment.json"
            obj["protocol_evidence"] = {"code_commit": self.commit, "freeze_commit": self.freeze_commit,
                                        "final_eval_environment": {"path": "results_prereg/final_eval_environment.json", "sha256": sha(env)}}
        write_json(seal_path, obj)

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
