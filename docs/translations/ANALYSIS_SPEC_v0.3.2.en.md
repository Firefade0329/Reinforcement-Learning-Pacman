> This is a translation for readers. The Chinese original (SHA-256 a4d64d46ed72d0c6e83cb1276f09e136a0639ee2db92954044a22cc642225100) is the frozen, authoritative text; in case of any difference the original governs. Frozen commit F: `92bf82eca0dae731f7396ed5b4e887e4f3b200e4`.

# Architecture × n-step: complete analysis specification v0.3.2 (Revision 1 + Rehearsal Addendum A + DSH Literal Corrections)

**Status: awaiting freeze; this is the complete implementation contract, not freeze approval or a real-results report. Date 2026-10-10.** Main implementation exists at 6023b1a; this round integrates documents without running repository code or rechecking current main. New gates depend on final implementation/local acceptance, not purported passage here. Version/fixed filenames remain 0.3.2; revision/hash distinguish content. Companion protocol: PREREG_ARCH_NSTEP_v0.3.2.md. Implementers need not rely on chat explanations; this specification details original statistical methods without changing H1/H2,30-run matrix, or last@300k primary endpoint.


Relative to original:§1 adds non-self-referential C/F/independent-machine-evidence binding;§2.3 resolves cross-file ordering and confirms finite noninteger-score error code;§3 specifies unique Fraction path;§7 adds provenance fields;§8 retains literal expectations/adds identity/order/nonzero-best cases;§9 specifies independent descriptive analysis of adopted B1/B2. H1/H2/matrix/endpoints/all statistical rules/random streams/thresholds unchanged. Rehearsal R1–R3 integrated directly:§1.1 fixes raw bytes/-text/fresh clones/dependency snapshots;§1.2 fixes training/final-evaluation binding/external records;§8.6 adds independent acceptance. See complete CODE_IMPACT_v0.3.2_r1.md(C1–C7/T1–T2/D1–D2) for new code work; this constrains final implementation, not a claim 6023b1a satisfies everything.

## 1. Execution boundaries and file locations

Preregistration materials go in repository docs/prereg/; run outputs in results_prereg/. This delivery generates documents outside the repository without modifying it. Target locations:

~~~text
docs/prereg/
  PREREG_ARCH_NSTEP_v0.3.2.md
  ANALYSIS_SPEC_v0.3.2.md
  CLAUDE_HANDOFF_v0.3.2.md
  matrix.csv
  dependency_lock.txt        # Complete runtime-environment version snapshot, committed with C
  frozen_config_v0.3.2.json
  freeze_manifest.json
results_prereg/
  runs/<run_name>/
    config.json
    summary.json
    last/standard.json
    best/standard.json
    last/hard.json          # Optional; all 30 enabled together or omitted together
  final_eval_environment.json   # Independent machine/execution identity, hash-bound by protocol_evidence
  window_diagnostics_seal.json # Auxiliary sealing, separate from the core files set
  window_diagnostics_summary/  # Secondary descriptive summary
  analysis/<analysis_id>/
    REPORT.md
    analysis.json
    bootstrap_indices.sha256
    bootstrap_replicates.csv
    input_manifest.json
~~~

Freeze analysis-script path/file SHA-256/dependency lock/command in freeze_manifest.json. CLI supports at least:

~~~text
analyze --mode synthetic --manifest <synthetic manifest> --input-root <synthetic directory> --output-dir <new directory>
analyze --mode formal --manifest docs/prereg/freeze_manifest.json --input-root results_prereg/runs --output-dir results_prereg/analysis/<analysis_id>
~~~

No fallback automatically scanning old results/results_gpu/, and no .pt/training scores/per-episode validation data loaded to select analysis. Prefreeze synthetic data only; reading any real results,including old ones,is prohibited. Synthetic mode requires manifest.synthetic=true/every evaluation meta.synthetic=true; formal mode requires both false,freeze record complete=true, and passed completion/configuration/checkpoint checks for 30 runs. Manifest supplies explicit paths; never automatically treat real directories as synthetic.

Formal sequence: synthetic acceptance/code freeze→complete matrix→centralized testing/seal all outputs→one frozen analysis generating all planned tables together. Do not revise scripts/select metrics after viewing individual results. Failed integrity produces no statistical report; retain failure logs and only repair objective file/evaluation infrastructure under original weights/protocol,recording attempts/input hashes. This authorizes neither training changes nor repeated analysis seeking favorable results.

### 1.1 Minimum freeze and evaluation-seal manifest formats

Resolve all paths from explicit root, not guessed cwd. Minimum formal freeze_manifest.json follows; all hashes use actual 64-character lowercase hex values, without formal-run placeholders:

~~~json
{
  "schema_version":"prereg-freeze-1",
  "synthetic":false,
  "complete":true,
  "spec_version":"0.3.2",
  "code_commit":"<full 40-character commit>",
  "project_root":".",
  "matrix_path":"docs/prereg/matrix.csv",
  "config_path":"docs/prereg/frozen_config_v0.3.2.json",
  "analysis_script_path":"<frozen analysis script path relative to project root>",
  "dependency_lock_path":"docs/prereg/dependency_lock.txt",
  "frozen_files":{
    "docs/prereg/matrix.csv":"<sha256>",
    "docs/prereg/frozen_config_v0.3.2.json":"<sha256>",
    "docs/prereg/PREREG_ARCH_NSTEP_v0.3.2.md":"<sha256>",
    "docs/prereg/ANALYSIS_SPEC_v0.3.2.md":"<sha256>",
    "docs/prereg/CLAUDE_HANDOFF_v0.3.2.md":"<sha256>",
    "docs/prereg/FREEZE_CHECKLIST.md":"<sha256>",
    "python/pacman_rl/window_diag.py":"<sha256>",
    "python/scripts/window_diagnostics_summary.py":"<sha256>",
    "<analysis script path>":"<sha256>",
    "docs/prereg/dependency_lock.txt":"<sha256>",
    "python/scripts/prereg_analysis.requirements.txt":"<sha256>",
    ".gitattributes":"<sha256>"
  },
  "seal_path":"results_prereg/evaluation_seal.json"
}
~~~

complete=true means generator structural/machine conditions passed, not human sign-off or existing training/test results. Formal launch still needs external freeze-record evidence that all gates passed; external record holds freeze_manifest's own hash to avoid self-reference. Synthetic manifests use synthetic=true/root/paths to synthetic fixtures, with same schema/numerical constraints; synthetic code_commit/weight hashes may be fictitious but must satisfy format/cross-file consistency.

After testing,evaluation_seal.json minimally contains schema_version="prereg-seal-1", synthetic(mode-consistent),freeze_manifest_sha256,all_training_complete=true,all_checkpoint_checks_passed=true,runs(30 run_name values in CSV order),files(all required config/summary/evaluation paths relative to run root→actual sha256),attempts(per-run objective failure/rerun arrays,empty if none). Include seal's own SHA in analysis provenance. Analyzer verifies files contains exactly declared required files; undeclared hard is excluded. Two true flags alone do not replace per-run budget/config/checkpoint/evaluation identity checks.

Prefreeze synthetic analysis materials also have synthetic seals; malformed cases change only the target file/recompute its synthetic-seal hash. CLI input root must resolve seal-relative paths consistently. Effective-configuration sha refers only to frozen configuration-file hash, not a self-hash embedded in config.json.

#### 1.1.1 Unique hash object and cross-platform byte rules (R2)

**This round hashes only raw working-tree file bytes, using SHA-256.** Read binary bytes, without normalizing LF, stripping BOM, reserializing JSON, or ignoring trailing newlines/spaces; identical content with different line endings constitutes different files. Apply this to freeze_manifest itself, dependency snapshots, all documents/scripts/matrix. Git object IDs are not the SHA-256 meant here.

Set **-text** in repository .gitattributes for files bound by frozen hashes, preventing Git text-line-ending cleaning/checkout conversion. Commit it with code C, outside the 6 permitted F files; include its actual bytes in manifest.frozen_files. The formal machine need not set personal global core.autocrlf to false to pass.

The following project rules may cover current files; any new extra-frozen path must also have a confirmed -text rule before freeze:

~~~gitattributes
/.gitattributes -text
/docs/prereg/** -text
/python/**/*.py -text
/python/*requirements*.txt -text
/python/scripts/*requirements*.txt -text
~~~

Rules cover the fixed matrix, configuration, manifest, protocol/specification/handoff/checklist, docs/prereg/dependency_lock.txt, actual analysis/diagnostic scripts, and existing requirements files. This does not reprocess all repository experiment data; existing bytes in results/, results_gpu/, and matrix.csv remain unchanged. -text is not the binary alias; ordinary text remains reviewable.

**Rationale:** the protocol already fixes matrix.csv's CRLF bytes/hash; enforcing LF globally or git add --renormalize could change the matrix and violate invariance. -text preserves direct consistency of “actual bytes→hash→checkout identical bytes,” matching the current implementation's working-tree reads. Uniform LF is possible in principle but requires preserving matrix bytes separately and recalculating other materials, adding migration; this round does not offer two schemes for post-hoc selection.

-text controls subsequent Git conversion and **does not automatically restore an old working tree already checked out as CRLF**. Before C, check intended committed bytes against the expected blob; do not globally normalize matrix. In F, each frozen file's raw Git-blob SHA-256 must match its recorded working-tree SHA-256, confirming cross-platform checkout of the same F yields identical bytes. This is byte-consistency acceptance, not a switch to runtime blob hashing.

**Unique byte identity of matrix.csv:** the Git blob of `docs/prereg/matrix.csv` in F must be the agreed original bytes with SHA-256 `5cbd4e7b2cf79f65c96180acfc61b1914fe2e8521c036218bc7c9a4db59f0dfe` (including existing CRLF endings). This is a fixed input, not a matrix regenerated or redefined on freeze day. `/docs/prereg/** -text` covers matrix.csv; accept an effective `unset` result from `git check-attr text -- docs/prereg/matrix.csv`. Git does not convert this file's text line endings; checked-out working-tree bytes must exactly match the blob in the same F. Do not rewrite CSV, change ordering/encoding/line endings, or renormalize it; do not redefine another recalculated value as the “new expected hash.” Freeze/run/analysis may and must recalculate the **actual** SHA-256 to verify equality with the fixed value above; this is integrity verification, not recalculation/revision of the protocol's matrix hash. On mismatch, stop and restore the fixed blob rather than accept a new value.

Formal-identity acceptance's temporary Git repository must copy actual `matrix.csv` raw bytes with fixed SHA-256 `5cbd4e7b2cf79f65c96180acfc61b1914fe2e8521c036218bc7c9a4db59f0dfe`. Do not reserialize CSV/convert line endings. Run/machine/evaluation records remain synthetic fixtures, no real scores; “synthetic” does not exempt formal mode's fixed matrix-hash check. Synthetic-mode contract is unchanged by this paragraph.

#### 1.1.2 Fresh-clone acceptance on the formal freeze machine

After F is formed but before external-record approval and the first formal run, **fresh-clone F and check out the exact F** on the formal A1000/Windows machine. Do not manually adjust line endings in an old tree and call that fresh-clone acceptance. Recalculate every frozen_files SHA-256 against the manifest, then recalculate manifest's own SHA-256 against the preparation record. Record F, anonymous machine_id, Git version, core.autocrlf state, effective text attributes of controlled paths, each file's expected/actual, and overall passage; omit absolute clone paths.

Any mismatch halts freeze; do not automatically “update to the current hash” on site. Diagnose byte differences, repair the C candidate, regenerate F/manifest, and repeat fresh-clone acceptance. Do not skip other files just because matrix happens to match.

Additional automated acceptance: put literal LF document/script/dependency fixtures and a CRLF matrix fixture in a temporary Git repository, set -text, and commit. Fresh-checkout with core.autocrlf=true and false respectively; each file must match committed blob/manifest bytes exactly. Matrix expected values use original literal CRLF bytes, not a “normalized” oracle. Linux Git settings can simulate the conversion, but **the local executor must still actually perform fresh-clone acceptance on formal Windows**; GPT has not run it in this round.

#### 1.1.3 Complete runtime-dependency snapshot (R3)

The exact-version snapshot of the complete Python training/validation/final-evaluation environment is fixed as:

~~~text
docs/prereg/dependency_lock.txt
~~~

Generated by the **local executor** on formal A1000 using the Python training/final-evaluation environment accepted through candidate smoke/resource checks; cloud implementer checks format/field wiring and includes it with code/.gitattributes in **code commit C**. Human researchers check environment provenance/acceptance records; AI does not sign for them. Generate before final C; F neither adds nor updates this file. It is not added to FREEZE_MATERIALS; permitted set remains 6 files.

Generate it using python -m pip freeze --all in that environment; the chosen interpreter must belong to the accepted environment. Do not generate the A1000 snapshot from another cloud CPU environment. Record the generation command (without absolute local paths), UTC, Python/pip versions, anonymous machine_id, and candidate-code SHA. Do not implicitly upgrade software just to fill the lock file; environment changes require renewed acceptance and a regenerated lock/new C.

Commit a UTF-8, no-BOM, LF snapshot of fixed-order name==exact_version entries, retaining local build suffixes (e.g., +cu…). Final SHA hashes actual committed bytes, not unsorted original stdout. Resolve and record sources for any editable entry, local file URL, private repository/token, or uncertain version before freeze; do not publish them directly or silently delete actual dependencies. **Only the repository project's own editable entry may be excluded**, because C/F already bind its code; record excluded package name/reason in the generation record, without extending exclusion to other local dependencies. The executor may privately retain generation records/raw stdout; committed snapshots and external records omit local paths/credentials.

This snapshot fixes exact versions of installed Python packages, **not a complete cross-platform resolution lock with all wheel hashes/download sources**. Record Python interpreter, CUDA runtime/driver, OS, hardware, and numerical switches separately as environment evidence; pip freeze does not establish cross-machine bitwise reproducibility. Rebuilding/checking a candidate environment against the snapshot still requires acceptance. Retain currently accepted software in this round; do not select “newer” versions because of specification wording.

| Material / field | Bound object |
|---|---|
| manifest.dependency_lock_path | Fixed docs/prereg/dependency_lock.txt |
| manifest.frozen_files[this path] | Actual SHA-256 of complete runtime-dependency snapshot |
| frozen_config.to_fill_at_freeze.dependency_lock_sha256 | Same as preceding entry, not the NumPy-only file |
| manifest.frozen_files[python/scripts/prereg_analysis.requirements.txt] | Separate actual SHA-256 of existing analysis dependency file |

>= in python/requirements.txt specifies installation requirements, not the runtime-dependency snapshot. python/scripts/prereg_analysis.requirements.txt retains its existing pinned NumPy version and analysis purpose, fixed with C and included as an additional required frozen file; **do not use it for the complete runtime-dependency snapshot field**. The two files have distinct purposes, without a second new configuration hash field. If formal analysis uses a separate environment, prepare and verify the specified NumPy version/random stream before C and record Python/pip versions and purpose; do not select the analysis environment after running.

The freeze generator/run/final-evaluation binding checks reject incorrect dependency_lock_path; verify the snapshot already exists in C's Git tree, its blob is unchanged in F, and working-tree hash matches the manifest. Exact entries must at least cover numpy, torch, matplotlib, and pytest in current installation requirements; reject missing top-level dependencies or nonexact entries such as>=. This minimum check does not replace package-by-package completeness checking against the accepted environment. The dependency lock cannot be added only in F, even within docs/prereg/, because it is outside the 6 permitted files. Analysis still reads files through the manifest mapping; statistical methods remain unchanged.

Acceptance: a snapshot committed in C with F changing only permitted files passes; adding/modifying the snapshot only in F is rejected; an >= installation file or NumPy-only file masquerading as the complete snapshot is rejected. Format checks may reject nonexact entries, but filename/few pinned versions alone cannot prove “complete”; package-by-package correspondence with the accepted environment's pip freeze is supported by local generation/check records.

### 1.2 C/F identity, machine evidence, and protocol-based sealing (unique formal path)

**C is code commit,F unique freeze/execution commit; no freeze_commit field added to frozen_config/freeze_manifest contained in F.** code_commit in configuration/manifest/config/evaluation meta means C. run_complete records C/F; code_version.git_sha/diagnostic meta.git_sha record F. External timestamped records predating first training retain F/manifest's own hash; human approval separate. Formal analysis must not infer human sign-off from complete=true.

F permits C→F endpoint differences only in 6 files:docs/prereg/{frozen_config_v0.3.2.json,freeze_manifest.json,PREREG_ARCH_NSTEP_v0.3.2.md,ANALYSIS_SPEC_v0.3.2.md,CLAUDE_HANDOFF_v0.3.2.md,FREEZE_CHECKLIST.md}. Matrix/python tree/dependency lock unchanged. Later document commits are not automatically approved new F.

freeze_manifest.frozen_files binds at least matrix/configuration/protocol/specification/handoff/FREEZE_CHECKLIST/analysis script,docs/prereg/dependency_lock.txt,python/scripts/prereg_analysis.requirements.txt,.gitattributes,python/pacman_rl/window_diag.py, and python/scripts/window_diagnostics_summary.py. F need not contain its own SHA; check manifest's own SHA against external record/evaluation seal. Preparation-only dirty permitted materials are not allowed during training/evaluation/formal analysis.

project_root may be “.”; CLI explicitly passes --project-root(actual project root),resolving manifest paths from it. Absolute machine paths not committed; anonymous machine_id/environment records link formal machine/software.

**Separate final-evaluation file contract:** results_prereg/final_eval_environment.json retains utc/evaluation_device/environment/code_version/preflight, and adds top-level machine_id(nonempty anonymous string matching frozen configuration). environment.torch_threads=1; evaluation_device/environment.device_type=cpu. code_version.git_sha=F,git_dirty=false; preflight.head=preflight.freeze_commit_of_runs=F,preflight.code_commit=C. Preserve actual software/numerical settings; frozen environment descriptions supply CPU/GPU model/OS/driver/TF32/power details absent automatic fields. machine_id is not automatic hardware authentication. Existing prereg-eval-1 meta contract unchanged.

**Add evaluation_seal top-level provenance object without changing exact core files set:**

~~~json
"protocol_evidence": {
  "code_commit":"<full 40-character SHA of C>",
  "freeze_commit":"<full 40-character SHA of F>",
  "final_eval_environment": {
    "path":"results_prereg/final_eval_environment.json",
    "sha256":"<actual 64-character SHA-256 of the separate environment file>"
  }
}
~~~

Seal producer derives protocol_evidence from rechecked 30-run run_complete identities/evaluation prechecks, with consistent C/F, not arbitrary manually entered F. Reject missing environment file,wrong machine_id/CPU/threads/C/F,dirty tracked files/current-material drift; generate actual environment hash. Diagnostics enter neither this object nor core files.

**Add formal-analysis stage 1 checks below, all before score statistics:**

1. protocol_evidence exists/valid C/F format; C matches frozen manifest/config; independent environment file exists/parses/hash matches, and identities/machine/device/threads agree.
2. Current project is real Git repository with HEAD=F; C exists/is F ancestor; C:python/F:python tree objects match; git diff C F endpoint paths lie in permitted 6-file set; tracked working tree clean. Unavailable/timed-out/failed Git relations reject formal analysis, without silently falling back to hashes alone. Analyzer may use stdlib subprocess for Git, without importing training modules/Torch.
3. Actual analysis script/all frozen-file raw-byte hashes match manifest; frozen-material byte identities in F agree. Operator checks external F/manifest hash/predating-training time. Scripts cannot technically prove historical nonaccess; protocol/execution records address that.
4. Record C/F/environment evidence in analysis.json.provenance/REPORT/input_manifest source index. Analysis does not reread .pt/per-episode validation scores; seal producer checks current training/checkpoint integrity,while analyzer verifies seal-bound identity/config/summary/evaluation records it requires.

New-check errors: missing files E_MISSING_FILE; hash mismatches E_HASH_MISMATCH; environment/identity/Git relations/missing protocol_evidence E_MANIFEST; invalid JSON/duplicate key/tree-wide nonfinite numbers retain original parse codes. Do not swallow infrastructure errors in try/except and continue calculating.

Synthetic mode needs no actual machine/Git repository/real results; original F1–F8/E1–E13 may retain old minimal synthetic seals without new formal protocol_evidence. New formal-identity fixtures use temporary Git/fake machines/complete synthetic scores; check public formal entry or actual helper wiring, not allow_unfrozen as formal acceptance.

One formal execution/recovery retains§1: one centralized analysis after valid core input; objective file-infrastructure repair after output failure keeps same weights/protocol/frozen code,logs/hashes. Directory nonoverwrite is not unbypassable one-shot security; lower-level APIs/public seed constants/source can bypass safeguards. Training/selection must not read sealed partitions; recheck all current materials before formal unsealing. Distinguish “own static review,executor report,done(code),own execution,human sign-off”; one AI implementing/writing tests is not an independent-person audit.

#### 1.2.1 Shared binding prechecks for training and final evaluation (R1)

Retain C/F relationships, the permitted 6 files, clean working tree, fixed parameters/machine/workers, environment-variable checks, and matrix checks; **additionally, both before training and before final evaluation call the same “frozen-file binding check.”** Final evaluation rechecks common F across 30 runs and current training materials; other unsealing gates remain unchanged.

Do not defer binding checks to manifest/analysis after training. Formal run completes them before creating training tasks/models, starting training subprocesses, or collecting environment transitions; final-eval completes them before obtaining permission to use sealed tests or performing any actual evaluation. Any failure exits nonzero through the runner's Refused path, providing relative path, field, expected/actual, or missing-item reason; do not continue training/evaluation or generate success receipts.

The sole data sources are docs/prereg/frozen_config_v0.3.2.json and docs/prereg/freeze_manifest.json under the explicit project root; do not guess other manifests, generate them automatically, or repair them. Check:

1. freeze_manifest.json exists, is valid JSON without duplicate keys; schema/spec_version are correct, synthetic is false, and complete is strictly true. complete means only structural/machine checks are complete, not human sign-off.
2. manifest.code_commit equals current frozen configuration code_commit, i.e., code commit C; manifest.config_path/matrix_path reference this protocol's configuration/matrix. Verify existing formal-mode identity conditions; this paragraph adds no manifest.status or other fields.
3. frozen_files is an object mapping “project-relative path→64-character lowercase SHA-256,” containing every required file in accompanying analysis specification §§1.1/1.2 (including .gitattributes and the complete runtime-dependency snapshot); omitted protocol/specification/configuration/dependencies or other required entries cannot bypass verification.
4. Every frozen_files entry exists and its current **raw working-tree bytes** have the recorded SHA-256. Paths must be relative, not absolute or resolved outside the project root. Check all listed files, including extra-frozen entries, not just three main files.
5. Each of the three configuration fields below equals the corresponding file's hash in the manifest; actual file hashes have already been checked in item 4. Nonempty/64-character format checks alone are insufficient; all-zero values do not constitute valid binding.

| Configuration field (all in to_fill_at_freeze) | Required corresponding manifest.frozen_files entry |
|---|---|
| analysis_script_sha256 | Actual frozen analysis script referenced by manifest.analysis_script_path |
| preregistration_document_sha256 | docs/prereg/PREREG_ARCH_NSTEP_v0.3.2.md |
| dependency_lock_sha256 | manifest.dependency_lock_path, fixed as docs/prereg/dependency_lock.txt |

The manifest must bind actual bytes of **the current configuration file itself**; fill the three fields before calculating the configuration hash and generating the manifest. Do not include freeze_manifest itself in its frozen_files, avoiding self-reference; the external freeze record binds its own SHA-256.

Successful checks record checked_utc, actual HEAD/F, C, freeze_manifest_sha256, and binding-check passage for launch logs/final-evaluation evidence. Record identity/integrity only, without reading scores or adding training RNG/forward/per-step operations. Formal analysis still performs file-hash and C/F checks under accompanying specification §1.2, without skipping them because training prechecks passed.

freeze-manifest is a **materials-preparation generator**, not formal run: it may generate a new manifest while permitted freeze materials remain uncommitted and cannot require an existing valid old manifest to generate itself. The generator checks actual files, required entries, and correspondence of the three fields, then writes the manifest; formal run/final-eval only read the manifest committed in F and never refresh hashes automatically.

After a valid F, document/configuration changes within the C→F permitted set are not thereby authorized changes to the original freeze. Files no longer matching the manifest must be rejected before training begins. Regenerating the manifest as well to obtain F′ constitutes only an explicit, newly approved freeze revision; do not misrepresent F′ as the F in the external record. **Checking external-record F and manifest hash remains a prelaunch protocol gate**; do not claim C→HEAD permitted differences alone identify every post-hoc refreeze.

#### 1.2.2 External freeze record and launch sequence

##### 1.2.2.1 Two stages, avoiding self-reference and backfilling

**Prelaunch records** contain C/F, manifest/all frozen-file hashes, machine/software sources, approval, and commands; at that point only candidate/frozen environment evidence and planned final CPU settings can be retained. Actual final_eval_environment.json arises only during final evaluation and cannot be inserted into a record claimed to predate launch.

**Post-final-evaluation receipts** separately retain actual final_eval_environment/evaluation_seal paths/hashes, C/F, and prelaunch-record SHA. Preserve previous record bytes without overwriting/backdating; core evaluation_seal.protocol_evidence still binds the actual environment file under the original integrated version.

##### 1.2.2.2 Minimum prelaunch FREEZE_RECORD.json fields

| Field | Minimum requirement |
|---|---|
| schema_version / spec_version / document_revision | prereg-external-freeze-1 / 0.3.2 / 修订1+彩排追加A+DSH 字面修正 |
| repository | Public repository URL; no local path |
| code_commit / freeze_commit | Full 40-character SHAs of C and F |
| freeze_manifest | {path:"docs/prereg/freeze_manifest.json", sha256: actual 64-character hash} |
| frozen_files | Copy manifest mapping; matrix hash must be the fixed 5cbd4e7b…0dfe |
| checkout_verification | Relative identifier/hash, passage status, and date of fresh-F-clone acceptance on formal machine |
| dependency_snapshot | path/hash of docs/prereg/dependency_lock.txt, anonymous machine, generation/check-record identifier, Python/pip versions; analysis dependency-file identity separately listed |
| environment_evidence | Relative identifier/hash of frozen environment description; OS/driver/software/numerical switches, anonymous machine_id, train/validation_device; no username/hostname/absolute path |
| execution_plan | worker_count=2, actual formal launch command without absolute paths, window_diagnostics enabled 30/30, hard_enabled decided, final CPU/1-thread settings |
| human_approval | Identifier/hash of human approval record, approved_utc, and approved scope; do not fabricate approved if not yet approved |
| prepared_utc | Executor-reported UTC; not independent timing proof |

Use the full matrix value, not the table's abbreviation, in JSON:

~~~text
5cbd4e7b2cf79f65c96180acfc61b1914fe2e8521c036218bc7c9a4db59f0dfe
~~~

Do not put the record's own hash inside itself; retain uploaded SHA-256/third-party timestamp in a separate publication/storage receipt. Original human sign-off may be retained separately; public records reference identifier/hash without requiring personal information to be published.

##### 1.2.2.3 Fixed storage location

Default storage in this round is a **GitHub Releases asset** for the repository, with entry/tag prereg-v0.3.2-r1-freeze-<first 12 characters of F>, tag pointing to full F, and asset FREEZE_RECORD.json. Release may initially remain draft; this is third-party timestamped storage evidence, not a requirement for additional public registration. When later publishing, retain original asset ID/bytes; do not delete/reupload and misrepresent the original time. This recommendation is procedural only; **delivery of this file does not create a Release/tag or upload anything; these actions belong to the owner**.

The executor retains relative location freeze_records/<full F SHA>/ in research materials outside the repository working tree, containing FREEZE_RECORD.json, FREEZE_PUBLICATION_RECEIPT.json, launch records, and later FINAL_EVAL_RECEIPT.json. Records use only relative identifiers/public URLs, not this directory's absolute local address; the directory is outside F's permitted set and does not create F self-reference.

FREEZE_PUBLICATION_RECEIPT minimally retains repository/Release/tag URLs or IDs, full F, GitHub asset ID, asset created_at (third-party UTC), actual download URL, downloaded-file SHA-256, and manifest SHA-256. Verify using actual GitHub API/asset downloads, not just a self-declared JSON. If Release.published_at follows training, it indicates only later publication; evidence that “bytes were stored by a third party” uses original asset created_at/download hash, without claiming they were public at that time. Independent review requires the same asset identity and original server metadata.

##### 1.2.2.4 Checking “record first, formally launch afterwards”

1. After F is formed and fresh-clone acceptance on the formal machine passes, obtain human approval, generate/store FREEZE_RECORD and third-party receipt, and check current HEAD=external F and manifest raw-byte hash=external value.
2. **Only afterwards** invoke the first formal run. Prelaunch logs retain actual C/F, manifest SHA, FREEZE_RECORD SHA, third-party asset ID/time, precheck passage time, and first training-task submission time (UTC), plus original CLI output. A local executor's launch recorder may retain this; no training-algorithm network access/new configuration field is required.
3. Later verify downloaded bytes/hash for the same asset ID, C/F/manifest mapping, and third-party created_at before first formal task launch; calibrate local clock and record timezone/offset. Archive receipts/launch records as research evidence without changing the core analysis files set.

**Evidence boundary:** self-entered UTC, file mtime, and Git author dates are mutable and alone do not independently prove ordering. Third-party asset time/download hash show these bytes were stored no later than that time; actual first-training timing still depends on launch/execution records, and public source safeguards cannot prove there were never unrecorded runs. This is a traceable research protocol, not purportedly unforgeable security certification.

Historical formal seed100/res4/n1 short rehearsals/one early prereg_val validation are separately disclosed in protocol§7.4; outputs are excluded from formal inputs/selection/weight reuse. “First formal training” here means approved runs after these gates, not erasure of historical rehearsal starts. Protocol§7.5/handoff§5 specify roles/handoff order.

## 2. Fixed input contract

### 2.1 Matrix, configuration, and run identity

Complete runtime-dependency snapshot fixed as `docs/prereg/dependency_lock.txt`,existing in C/unchanged in F;`dependency_lock_sha256` matches manifest/actual bytes. Analysis NumPy requirements separately bound, not masquerading as full snapshot. See§1.1.3 for format/generation/minimum completeness checks; no new configuration fields/matrix columns.

Retain filename matrix.csv, without byte/encoding/line-ending/column changes; SHA-256:

~~~text
5cbd4e7b2cf79f65c96180acfc61b1914fe2e8521c036218bc7c9a4db59f0dfe
~~~

All 30 run_name values come from CSV,the Cartesian product arch∈{cnn2,res4,res8},n_step∈{1,3},seed∈{100,101,102,103,104}. CSV order determines scheduling; analysis tensor order separately fixed arch=[cnn2,res4,res8],n=[1,3],s=[100,101,102,103,104],e=[30000,…,30299]. **Sort episode records before computing; file row numbers are not test seeds.**

Check CSV hash,30 unique identities, and 6 distinct configurations per consecutive training-seed block. No scheduling-RNG reconstruction;271828 is only for bootstrap below.

frozen_config_v0.3.2.json includes explicit CSV-external eps_start=1.0,eps_end=0.05,eps_frac=0.4,tau=0.01,grad_clip=10; val_seeds=21000–21049,test_seeds=30000–30299,smoke_eval_seeds=40000–40009,smoke_run_seeds=[900,901],eval_episodes=50,final_eval_device="cpu",final_eval_threads=1,hard_enabled(boolean),full frozen code commit/dependency/machine identifiers. Explicitly pass these to training/evaluation, not unrecorded defaults.

val_seeds/test_seeds/smoke_eval_seeds are ascending JSON integer arrays expanded from those closed intervals; reject interval strings/half-open interpretations. Additional fixed names:code_commit,machine_id,train_device,validation_device,worker_count,max_episode_steps=1000,train_scenario="standard",hard_chase_p=0.7(if hard enabled). Freeze worker_count from smoke before formal launch,uniform across matrix. Validation/training devices match chosen common GPU condition; final CPU/threads separate rather than conflated device field. Follow main protocol train_seed formula/k bound, not reverse inference from tests.

Each config.json is merged effective configuration,containing at least all CSV column values/supplements/run_name/code_commit/frozen_config_sha256(hash of frozen configuration file). Allow explicit JSON/CSV type conversions,e.g.,CSV "true"→JSON true; no approximate string comparisons/ignored fields. CSV device is training device; separately verify final cpu.

Each summary.json records at least:

~~~json
{
  "run_name": "prereg_cnn2_n1_s100",
  "total_env_steps": 300000,
  "replay": {"size": 100000},
  "actual_updates": 74000,
  "validation_steps": [20000,40000,60000,80000,100000,120000,140000,160000,180000,200000,220000,240000,260000,280000,300000],
  "validation_episodes_each": 50,
  "initial_state_dict_sha256": "<64-character hexadecimal>",
  "checkpoints": {
    "last": {"step": 300000, "weights_sha256": "<64-character hexadecimal>"},
    "best": {"step": 20000, "weights_sha256": "<64-character hexadecimal>"}
  }
}
~~~

Example 74000/best.step=20000 are format illustrations, **not required actual values**. actual_updates is nonnegative integer; replay.size integer with 0≤size≤100000. Report actual, not estimated values. Validation steps exactly those 15 entries,50 episodes each; last=300000; best belongs to those 15. Canonical n=1/3 initial hashes match for 15 same-architecture/seed pairs. Use frozen state_dict canonical bytes, not checkpoint-file hashes with serialization metadata.

replay.size is final occupancy, not cumulative insertions after saturation; n=3/8 active environments may have 16 pending tails, not 16 fewer training transitions. actual_updates is actual gradient-update count. Output both; also retain separately recorded cumulative insertions/pending_horizons without using them to extend training.

### 2.2 New evaluation JSON format

Only for new prereg evaluation path; old paths/JSON/experiment data unchanged. Each standard/hard file uses this wrapper, with episode array records:

~~~json
{
  "schema_version": "prereg-eval-1",
  "meta": {
    "synthetic": true,
    "run_name": "prereg_cnn2_n1_s100",
    "arch": "cnn2",
    "n_step": 1,
    "train_seed": 100,
    "checkpoint": "last",
    "checkpoint_step": 300000,
    "weights_sha256": "<64-character hexadecimal>",
    "code_commit": "<full 40-character SHA of code commit C>",
    "scenario": "standard",
    "device": "cpu",
    "torch_threads": 1
  },
  "records": [
    {"seed":30000,"score":100,"steps":100,"died":true,"won":false,"truncated":false}
  ]
}
~~~

Single-record format example; valid files have 300 entries. meta matches path/CSV/summary/code commit C/mode exactly; best.step is selected summary step, not forced 300k. hard.scenario="hard", with chase probability 0.7 recorded in frozen configuration.

seed/steps are JSON integers, not bool; score is finite integer pellet count, allowing numerically integral 100.0 before int64 conversion,but not strings/bool. died/won/truncated are JSON bool. Do not infer score from reward. truncated means time limit, not death; exactly one of died/won/truncated true; truncated=true requires steps=1000. Death/win exactly at 1000 still retains actual cause; steps=1000 alone does not fabricate truncated.

Identical best/last weights may be evaluated once/records copied; both logical files still exist with correct meta.checkpoint/identical weight hashes/reuse provenance. Analyzer must not infer missing best equals last.

hard_enabled=false: no hard reading; existing hard files with disabled configuration trigger E_UNDECLARED_HARD,to prevent selective ignoring. If true, all 30 last/hard.json required with same 300 seeds, not partial architectures/seeds; no best/hard analysis. Synthetic mode uses identical checks.

### 2.3 Mandatory failing integrity checks and order

Validate every input before any statistics. Exit code 2; stderr JSON error object includes code,path,run_name(if determinable),record_index/seed(if applicable),expected, actual,message. **No skipping runs/records,interpolating episodes, or partial-statistics output.** Nonfinite actual values represented as strings "NaN"/"Infinity"; error JSON itself has no NaN. Target output directory must not exist; failure leaves no apparently successful REPORT.md/analysis.json.

**Unique order:global stages 1–4 across all files first, then CSV run order,within each run last/standard→best/standard→enabled last/hard,completing 5,6,7 per file before next file.** Not 5 across all files before 6/7. config/summary participate only in first 4 stages; record semantics only apply to evaluation. Nonfinite numbers recursively rejected at stage 3. Stage 6 per-record order:object type→six required keys(seed,score,steps,died,won,truncated order)→seed/steps integer types→score numeric/nonbool→finite-score integrality→three final-state bool types→score range→steps range→won score→end-state logic. Therefore score=1.5 alongside nonbool end fields first gives E_SCORE_RANGE; do not switch to all-field-types-first. Global 15 initialization-pair comparisons belong to stage 4, before any records semantics. Report only first error under this order, not necessarily all errors per failed invocation.

Specific stages:

1. manifest/matrix/frozen_config exist/parse/hashes/version agree,hard declaration/formal freeze conditions; errors E_MISSING_FILE / E_JSON_PARSE / E_HASH_MISMATCH / E_MANIFEST / E_CONFIG_MISMATCH / E_UNDECLARED_HARD.
2. Enumerate config/summary/last/standard/best/standard/enabled last/hard in CSV order; first check existence of all required files. Missing→E_MISSING_FILE. Verify 30 identities, reject extra prereg runs(E_RUN_SET), without recursively reading historical directories.
3. Parse in same order. Reject duplicate JSON keys(E_JSON_DUPLICATE_KEY), invalid JSON(E_JSON_PARSE); NaN/Infinity/-Infinity constants and overflow 1e999 must give E_NONFINITE, not hidden behind type/range errors. Recursively check all JSON numbers,including extra fields, not just score. Parsing/tree-wide finiteness precedes field/array-length/semantic checks.
4. Required config/summary/meta fields/types,frozen values,budget/validation/hash relationships; E_REQUIRED_FIELD / E_FIELD_TYPE / E_CONFIG_MISMATCH / E_METADATA_MISMATCH / E_TRAIN_BUDGET / E_VALIDATION_SCHEDULE / E_INIT_PAIR_MISMATCH.
5. records must be array, else E_SCHEMA; exactly 300 entries, else E_EPISODE_COUNT. Isolated cases below assume 300 entries already passed.
6. Check each record in fixed detailed order:object/type E_FIELD_TYPE,missing key E_REQUIRED_FIELD,score integrality/range E_SCORE_RANGE,steps range E_STEPS_RANGE,won⇒score=377 E_WON_SCORE,end logic E_END_FLAGS. Nonfinite numbers already give global-stage 3 E_NONFINITE. Integer identity fields cannot be float/bool; finite score=1.5 gives E_SCORE_RANGE,100.0 valid.
7. Duplicate seeds E_DUPLICATE_SEED; validation 21000–21049 seeds E_VAL_TEST_MIXED; smoke 40000–40009/EQUIV 20000–20299/old val-test seeds E_RESERVED_SEED_MIXED. Finally verify exact 30000–30299 set, else E_TEST_SEED_SET. Mixed-partition errors precede ordinary set mismatch,duplicates precede mixing.
8. After all files pass 5–7,sort by seed/build tensor. Save each file's SHA-256/original path/generate input manifest; formal mode also checks sealed evaluation/config/summary hashes,distinct from nonexistent prefreeze result hashes.

Two hash layers:freeze manifest binds protocol/matrix/configuration/analysis code; post-test seal binds evaluation files. Malformed synthetic acceptance updates its synthetic seal so semantic errors are actually reached; stale hashes must not masquerade as NaN coverage. Parsing-safety checks precede semantics, with global/per-file priority above. Each E1–E13 introduces one anomaly;§8.6 separately uses two-error fixtures to lock cross-file priority.

## 3. Exact computation contract

Let endpoint q∈{last_standard,best_standard,last_hard},a∈{cnn2,res4,res8},n∈{1,3},s∈{100,…,104},e∈{30000,…,30299}; Y[q,a,n,s,e] is integer score. Primary q=last_standard. Report other endpoints separately, **without pooling observations or replacing primary analysis**.

Per model:

~~~text
S[q,a,n,s] = Σ_e Y[q,a,n,s,e]
m[q,a,n,s] = S[q,a,n,s]/300
~~~

For each q:

~~~text
D[a,s] = S[a,1,s] − S[a,3,s]
d[a,s] = D[a,s]/300
c[s] = (D[res8,s] − D[cnn2,s])/300
u[s] = (D[res4,s] − D[cnn2,s])/300
v[s] = (D[res8,s] − D[res4,s])/300
~~~

d is n=1−n=3; c primary interaction; u/v prespecified auxiliary interactions. Retain integer numerators before subtraction, not rounded m. For any training-seed vector x=[x100,…,x104]:

~~~text
mean(x) = (Σ_s x_s)/5
sd(x) = sqrt(Σ_s (x_s − mean(x))² / 4)      # Sample standard deviation, ddof=1
se(x) = sd(x)/sqrt(5)
positive_count(x) = #{s: x_s > 0}
zero_count(x) = #{s: x_s = 0}
negative_count(x) = #{s: x_s < 0}
~~~

Output 5 raw values/corresponding seeds/mean/sd/se/three sign counts per vector. Determine d/c/u/v signs/zeros exactly from integer numerators, not adjustable epsilon. **Unique computation path: exact rational fractions→float64.** For common denominator D/integer numerators p_i(N=5):

~~~text
M = Fraction(sum(p_i), D*N)
V = Fraction(sum((N*p_i - sum(p_i))**2), D**2*N**2*(N-1))
mean = float(M)
sd = math.sqrt(float(V)) if V > 0 else 0.0
se = sd / math.sqrt(N)
CI = [mean - t*se, mean + t*se]
raw_values[i] = float(Fraction(p_i,D))
~~~

Means/ddof=1 variances use exact rational arithmetic; first floating conversion only for output mean/raw values and before variance square root. Python math.sqrt converts Fraction to float,matching explicit float(V). se/t intervals use float64/operation order above; no math.fsum or coexisting/result-selected paths. Signed int64 for score/episode contrasts; Python arbitrary-precision integers for square sums/rational numerators avoid int64 square overflow. Signs/zeros use integer numerators; display-rounded values never determine decisions.

Statistical formulas/ddof/t/coverage/bootstrap/labels unchanged. Existing F1–F8 literal expectations/stream hashes/counts/labels/1e−12/1e−11 acceptance tolerances **unchanged**. Old/new floating paths may differ in last-place rounding for arbitrary data; do not claim universal bitwise equality. Freeze implemented Fraction path before formal data appears.

Also output 5 m values/mean/ddof=1 sd for 6 configurations. Optional within-model 300-episode score sd is episode_sd(ddof=1),distinct from training-seed sd.

### 3.1 Secondary metrics and exploratory contrasts

Per-model death/win/truncation rates equal respective bool sums/300; mean steps=steps sum/300. Configuration summaries average 5 model rates/steps and ddof=1 sd;1500 episodes are not 1500 trainings.

Prespecified exploratory outputs, all reported without result-dependent selection:

| Question | Computation/reporting |
|---|---|
| Does n=1 benefit cnn2/res8? | Corresponding d's 5 values,mean/sd,95%t/95% crossed bootstrap,positive count, fixed direction-signal label; no new p values/confirmatory hypotheses |
| Absolute res8/cnn2 ranking under n=1 | r[s]=(S[res8,1,s]−S[cnn2,1,s])/300;5 values,mean/sd,95%t/95%bootstrap;95%t lower>0 labels res8 higher,upper<0 cnn2 higher,otherwise ranking uncertain. Only these two architectures/endpoint/budget, not complete ranking or “ranking unchanged” |
| Best versus last | b[a,n,s]=m[best,a,n,s]−m[last,a,n,s];6 groups'5 values/mean/sd/95%t/95%bootstrap; best selection steps/GPU selection-CPU testing; also best_standard d/c/u/v/95%intervals alongside corresponding last differences/directions |
| Does selection change n-step effects? | g[a,s]=d[best,a,s]−d[last,a,s];5 values/mean/sd/95%t/95%bootstrap; configuration/architecture mean-effect signs positive/negative/zero via exact numerators, no new significance threshold |
| Auxiliary interactions | u/v 5 values,mean/sd,95%t/95%bootstrap, no additional confirmatory labels |
| Optional hard | If enabled,similarly report m/d/c/u/v/rates/steps/95%intervals; no new H1/H2 decisions; if disabled,not_run |

Report replay.size/actual_updates/resource metadata/attempts unchanged for all endpoints. Equal means do not imply identical episodes; episode-identity claims require per-seed comparisons/numbers.

## 4. Intervals and reproducible bootstrap

### 4.1 Training-seed t intervals

95% paired t intervals for all 5-seed vectors:

~~~text
CI95(x) = [mean(x) − 2.7764451051977944 × se(x),
           mean(x) + 2.7764451051977944 × se(x)]
~~~

H1/H2 decisions additionally use 97.5% two-sided t intervals:

~~~text
CI975(x) = [mean(x) − 3.4954059325164377 × se(x),
            mean(x) + 3.4954059325164377 × se(x)]
~~~

df=4, corresponding t quantiles 0.975/0.9875. Bonferroni assigns α=.025 to each of two confirmatory predictions;95% intervals display effects. Independently check using scipy.stats.t.ppf(0.9875,4) or R qt(0.9875,df=4)(SciPy/R not invoked this round). Independent numerical source here is analytic df=4 CDF:

~~~text
F4(t) = 1/2 + t(t²+6) / [2(t²+4)^(3/2)]
~~~

Implementation/acceptance use float64 constants `2.7764451051977944` and `3.4954059325164377`, corresponding to df=4 quantiles 0.975/0.9875. Longer decimal approximations are reference only, not digitwise acceptance criteria.

This is numerical approximation of mathematical quantiles, not fabricated literature-page references. Use those float64 constants/independently verify CDF residual<1e−14. If sd=0,CI=[mean,mean], without division errors/NaN; apply unchanged decisions and mark degenerate=true, not infinite real-study precision. CIs may exceed physical score-difference boundaries; **do not clip**.

Training seeds are independent units; t intervals conditional on fixed tests assume approximately normal differences,unreliably testable at small sample. Bootstrap is sensitivity analysis, not replacement for training seeds.

### 4.2 Crossed-bootstrap random-stream contract

10000 replicates,B=10000; NumPy Generator＋**PCG64**, not RandomState/Python random/PCG64DXSM/unspecified default_rng. Analysis lock records NumPy version; check values generated with NumPy 2.5.3, other versions freeze only if every check matches.

Create exactly one fresh RNG per analysis; do not change loop order:

~~~python
rng = numpy.random.Generator(numpy.random.PCG64(271828))
for b in range(10000):
    I = rng.integers(0, 5, size=5, dtype=numpy.int64, endpoint=False)
    J = rng.integers(0, 300, size=300, dtype=numpy.int64, endpoint=False)
    # Draw I first, then J; make no further random-method calls before the next iteration.
~~~

I/J independently sample with replacement,0-based s indices and 0-based e indices; repeats count repeatedly. Same b's I/J shared across all architectures/n/last/best/hard/exploratory contrasts. No per-configuration redraws, no drawing all I before all J, no preaveraging test axis across models. Indices may be prestored for parallel pure computation,but generation stream stays as above.

~~~text
m_b*[q,a,n] = Σ_{i=0..4} Σ_{j=0..299} Y[q,a,n,s[I_i],e[J_j]] / 1500
d_b*[q,a] = m_b*[q,a,1] − m_b*[q,a,3]
c_b* = d_b*[res8] − d_b*[cnn2]      # u/v/r/b/g follow the original formulas
~~~

Form per-episode signed contrasts from integer Y first, then integer sums over I/J divided by 1500,so identical pairing cancels without floating-subtraction-order artifacts; equivalent mathematical formula above. Best−last also shares I/J. No t intervals per bootstrap replicate required.

For each statistic's 10000 estimates,take percentile 95%:

~~~python
numpy.quantile(values, [0.025, 0.975], method="linear")
~~~

Explicit type 7:sorted z0≤…≤z9999,h=9999p,k=floor(h),Qp=(1−(h−k))zk+(h−k)z(k+1). Thus lower=0.025z249+0.975z250,upper=0.975z9749+0.025z9750. No nearest/basic/BCa/other default percentile interpolation. Do not prematurely round replicate estimates.

Before freeze,cloud implementation must verify:

| 0-based replicate index | I | First 12 J entries | Last 3 J entries |
|---|---|---|---|
| 0 | [4,3,2,4,0] | [66,136,166,3,27,281,0,57,286,162,259,184] | [40,277,99] |
| 1 | [4,0,2,3,1] | [68,44,215,23,198,263,116,26,292,237,173,150] | [175,261,212] |

Each replicate writes 5 I values then 300 J values,unsigned 32-bit little-endian,concatenating 10000 replicates **without separators/header/newlines**,total 12,200,000 bytes; SHA-256 must be:

~~~text
f3c35599fe764bf0a2c124544930609b643c2d5aa33ee0acc5b34454d91c9f69
~~~

This binds random indices, not statistical results; actually compute the hash rather than hardcode it. Cloud may independently write an index-only short program, without scores/analyzer, and check statistics with§8 hand formulas,to detect “correct stream,incorrect statistics.” Formal output records actual computed hash.

## 5. Res4 one-sided exact sign test

Report only for last_standard d[res4] as prespecified direction check. N_eff=positive_count+negative_count,excluding exact zeros; K=positive_count.

~~~text
p = Σ_{j=K..N_eff} C(N_eff,j) / 2^N_eff
H0: conditional on nonzero differences, positive probability≤0.5; H1: >0.5
~~~

Compute integer binomial sum; output numerator,denominator,p,N_eff,K,zero_count. If N_eff=0,define p=1/status="no_effective_samples", not valid support. 5/5 positive gives 1/32=.03125;4/5 gives 6/32=.1875;3 positive/1 negative/1 zero gives 5/16=.3125. Tests directional probability, not zero mean; p does not replace H1/H2 intervals. No additional p values for other directions.

## 6. Machine decisions that cannot be adjusted post hoc

All decisions use unrounded values; strict inequalities interpreted literally, no adjustable tolerance. Treatment of boundaries±10/0 follows. Incomplete/invalid input terminates with error, **not “insufficient evidence” followed by continued statistics**.

| Field | Rules,matched in order | Output enumeration / meaning |
|---|---|---|
| H1 | d[res4] CI975=[L,U],L>10 | supported / supported |
| H1 | Otherwise U<10 | refuted / refuted; positive_gain_refuted=(U<0) additionally indicates positive gain itself refuted |
| H1 | Otherwise | uncertain / uncertain |
| H2 | c CI975=[L,U],L>10 or U<−10 | supported / supported |
| H2 | Otherwise L>−10 and U<10 | refuted / prespecified magnitude refuted |
| H2 | Otherwise | uncertain / uncertain |
| direction_signal[a] | mean(d[a])≥10 and CI95 lower>0 and positive_count≥4 | supported_signal / direction signal supported |
| direction_signal[a] | Otherwise | insufficient_evidence / insufficient evidence |
| interaction_signal | abs(mean(c))≥10 and(CI95 lower>0 or CI95 upper<0) | supported_signal / interaction signal supported |
| interaction_signal | Otherwise | insufficient_evidence / insufficient evidence |

**H1/H2 have three labels; direction/interaction signals have two.** No post-hoc signal-refutation criterion; signal support is not H1/H2 support. Example c=[10,…,10]:interaction signal supported,H2 uncertain; d[res4] estimate 10/interval spanning 10 may support direction signal while H1 uncertain.

Report raw effects for every endpoint; formal H1/H2/signal fields above belong only to last_standard. Best/hard produce no second confirmatory decisions. Exploratory r ranking labels fixed in§3.1.

Fixed sensitivity labels:

1. For each d/c/u/v,interval_sign(CI)=positive(L>0)/negative(U<0)/contains_zero(otherwise); method_sensitive_zero=true if 95%t/95%bootstrap interval_sign differs. Report both without changing signal/H1/H2 labels.
2. For H1/H2 also apply same magnitude rules to 95%bootstrap as bootstrap95_magnitude_check; when different from formal 97.5%t,magnitude_check_differs=true and describe as “sensitive to method or interval coverage.” **95%/97.5% are different levels, not strict same-confidence revalidation.** Formal labels always from 97.5%t.
3. If interaction_signal supported but bootstrap95 contains 0, retain label/method_sensitive_zero=true. Do not choose either method as final acceptance condition.

A sign p<.05 may output descriptive p_lt_0_05 boolean, not a new formal pass/fail/stopping rule.

## 7. Output contract and numerical provenance

Success generates REPORT.md,analysis.json,bootstrap_replicates.csv,bootstrap_indices.sha256,input_manifest.json. Write temporary directory first,publish atomically after complete success; reject overwriting existing analysis_id. No filled numerical template masquerading as successful analysis without real data.

analysis.json top level contains at least:

~~~json
{
  "schema_version":"prereg-analysis-1",
  "analysis_spec_version":"0.3.2",
  "mode":"synthetic",
  "complete":true,
  "provenance":{},
  "integrity":{},
  "parameters":{},
  "endpoints":{},
  "primary_decisions":{},
  "exploratory":{},
  "resource_records":[],
  "deviations":[],
  "limitations":[]
}
~~~

provenance:hashes of analysis script/specification/protocol/matrix/frozen configuration/full runtime snapshot/analysis dependencies/.gitattributes,code_commit=C,freeze_commit=F, current analysis HEAD,C/F checks,final_eval_environment relative path/SHA-256/machine_id,input manifest,seal,evaluation device,mode,timestamp. integrity: expected/actual run/file counts,300 records/file,seed range,15 initial pairs,15×50 validation checks. parameters:t constants/df,ddof,bootstrap B/RNG/call order/quantile method/actual index hash,H1/H2 magnitude thresholds.

endpoints keyed last_standard,best_standard,optional last_hard, each containing model_metrics(6 configurations×5 seeds),config_summaries(6),effects.d(3 vectors),effects.c/u/v,rates/steps. Each statistical object contains at least:

~~~json
{
  "metric_id":"last_standard.d.res4",
  "training_seeds":[100,101,102,103,104],
  "raw_values":[20,20,20,20,20],
  "mean":20,
  "sd_ddof1":0,
  "se":0,
  "positive_count":5,
  "zero_count":0,
  "negative_count":0,
  "ci95_t":[20,20],
  "ci975_t":[20,20],
  "ci95_cross_bootstrap":[20,20],
  "degenerate":true,
  "source_metric_ids":["last_standard.m.res4.n1","last_standard.m.res4.n3"],
  "formula_id":"d_n1_minus_n3"
}
~~~

Example is synthetic constant difference, not real results. Provide ci975_t at least for H1 d.res4/H2 c; others may be uniformly calculated without new confirmatory labels. Each m's sources include run_name,evaluation source_id/sha256,seed set,integer score_sum; d/c/u/v/r/b/g sources include upstream metric_id/integer numerators; CIs reference raw_values/formulas/constants; bootstrap lists sampling method/replicates column. Sign test cites d.res4/exact binomial counts. Configuration summaries reference 5 m values, not rounded Markdown tables.

Every number is traceable:data values to record field/seed,derived values to formulas/parent metric_id,constants to frozen protocol,resources to summary fields. “Source=experiment” or final means alone are insufficient.

bootstrap_replicates.csv has 10000 rows,first replicate_index=0..9999,remaining columns at least all d/c/u/v/r/b/g estimates. Names contain endpoint/contrast identity; fixed order endpoints last_standard,best_standard,last_hard(if present),within each d.cnn2,d.res4,d.res8,c,u,v,r, then 6 configuration b/3 architecture g. JSON/CSV retain float64 round-trip precision(recommend 17 significant digits),Markdown 4 decimals,p exact fractions plus decimals allowed; decisions precede formatting.

REPORT.md order:

1. Freeze identity,integrity/deviations,completion/failed attempts,prominent synthetic/formal marker;
2. Primary 6-configuration table(5 m values,mean,seed sd,death/win/truncation rates,steps);
3. d/c/u/v table(5 values,mean/sd,positive count,95%t/95%bootstrap; H1/H2 additionally 97.5%t);
4. Formal H1/H2,direction/interaction signals,sensitivity labels,Res4 sign test;
5. All exploratory/secondary tables; disabled hard marked not run;
6. replay.size/actual_updates,budget,wall time/CPU-GPU memory(if available);
7. Source index/small-sample/single-map/privileged-input/device/different-compute limitations.

Unavailable optional resources=null with reason, no NaN; required statistics cannot hide errors with null. Avoid ambiguous comma-packed raw 5-value table cells; Markdown uses 5 “seed100…104” columns or ordered-array text,JSON retains seed sequence.

## 8. Synthetic-data acceptance: independent expected values

### 8.1 Common fixture generation and acceptance criteria

Each valid fixture generates all 30 runs/required last-best files,300 episodes each; default best copies last records with identity-correct metadata. seed=30000+e(e=0..299),steps=100,died=true,won=false,truncated=false. n=3 default score 100; n=1 score 100+specified integer difference. Valid scores/config/summary/hashes independently generated, synthetic=true;15 same-architecture initial-hash pairs match. Hard may be disabled. Tested analyzer must not generate expected values.

Oracle sources: hand calculations,binomial sums,analytic df 4 CDF,closed scalar formulas below; independent index/numerical checks come from earlier records. This integration did not run index generator/tested analyzer. Floating-statistic absolute tolerance≤1e−12(long t numbers≤1e−11); labels/counts/hashes/error codes exact. Tolerance applies only to tests, **not formal label logic**.

### 8.2 Valid statistical cases

| Case | d per training seed | Exact expectations and labels |
|---|---|---|
| F1 Constant differences | cnn2 all 10,res4 all 20,res8 all 30 | All d sd=0,positive 5 each; c all 20,u/v all 10,sd=0; all t/bootstrap intervals degenerate at constants; H1 supported,H2 supported,3 direction signals supported,interaction supported; Res4 N=5,K=5,p=1/32; r all 20; b/g all 0 |
| F2 Zero interaction | All three architectures 20 | c/u/v all 0,sd=0, all corresponding intervals[0,0]; H1 supported,H2 refuted; all directions supported,interaction insufficient evidence; sign p=1/32; r all 0 |
| F3 Reversed signs | cnn2 all −10,res4 all −20,res8 all −30 | c all −20,u/v all −10,sd=0; H1 refuted with U<0,H2 supported;3 directions insufficient evidence,interaction supported; positive 0 each; Res4 N=5,K=0,p=32/32=1; r all −20 |
| F4 Variance/boundaries | cnn2 all 10; res4 seed-order[8,9,10,11,12]; res8 all 20 | d.res4 mean=10,sd=√(5/2),se=1/√2;95%t=[8.036756838522443,11.963243161477557];97.5%t=[7.528374762117939,12.471625237882062]; H1 uncertain,direction supported; c all 10,H2 uncertain,interaction supported; u=[−2,−1,0,1,2],mean 0,sd√(5/2),positive 2; v=[12,11,10,9,8],mean 10, same sd,positive 5 |
| F5 Zero differences in sign test | res4=[0,1,2,3,−1]; others all 0 | Res4 mean=1,sd=√(5/2),positive 3,negative 1,zero 1,N_eff=4,p=(C(4,3)+C(4,4))/16=5/16=.3125; H1 refuted,direction insufficient evidence; zero is neither negative nor fifth effective sample |
| F6 All-zero sign test | All three architectures 0 | N_eff=0,K=0,zero_count=5,p=1,status=no_effective_samples; H1/H2 refuted; both signals insufficient evidence |
| F8 Degenerate boundaries/negative interaction | cnn2 all 0,res4 all 10,res8 all −10 | d.res4 CI975 exactly[10,10],H1 uncertain; c CI975 exactly[−10,−10],H2 uncertain; res4 direction supported, other directions insufficient evidence; interaction supported; u all 10,v all −20,Res4 sign p=1/32 |

These intervals follow§3's unique computation path,including `se=sd/math.sqrt(5)`; compare floating expectations at fixed `1e-12` tolerance, not digitwise equality.

F4 bootstrap needs no analyzer-derived oracle:each replicate d.res4*=8+(ΣI)/5,u*=−2+(ΣI)/5,v*=12−(ΣI)/5,c*=10; check against specified indices. Hand-calculated t intervals use Σ(x−10)²=10 with denominator 4, not bootstrap estimates.

Check m,d/c/u/v,secondary endpoints for F1–F6; when best copies last,b/g exactly zero/CI[0,0]. F1 configuration m=[110,100],[120,100],[130,100](n1,n3), same seed means/sd=0; death rate 1,win/truncation 0,mean steps 100. Other m similarly hand-calculated per seed as 100+d.

### 8.3 F7 must detect test-axis sampling/pairing errors

i=s−100,h(e)=1 if e≥150,else 0. Every architecture n=3 score 100; n=1 score 100+B_a+i+h(e),B_cnn2=10,B_res4=20,B_res8=30; i=0..4,e=0..299. All records valid.

Hand calculation:

~~~text
d[a,s] = B_a+i+1/2
mean(d[a]) = B_a+5/2
sd(d[a]) = sqrt(5/2)
c=20, u=v=10, r=20 (identical for every seed)
bootstrap d_b*[a] = B_a + (Σ I)/5 + #{J_j≥150}/300
~~~

Replicate 0 has ΣI=13 and 151 second-half test draws, with offset 931/300; replicate 1 has ΣI=10 and 142 second-half draws, with offset 742/300. Thus d.res4*=6931/300 and 6742/300; c* exactly 20 every replicate. Resampling only training axis,losing test axis,configuration-independent draws, or unpaired draws fail at least one check.

Independent scalar oracle for all 10000 replicates: calculate integer T_b=60ΣI+#{J≥150}, without Y/analyzer. Sorted 0-based T249=384,T250=385,T9749=T9750=1116; type 7 offset lower=(384+39×385)/(40×300)=5133/4000=1.28325,upper 1116/300=93/25=3.72. Thus d[a] bootstrap95% exactly[B_a+1.28325,B_a+3.72]; c=[20,20],u/v=[10,10],b/g=[0,0]. Positions verified by independent count formula for prescribed stream, **not reverse-engineered from tested script**;10000 random outcomes cannot be hand-calculated alone,so verification separates stream hash/closed statistics.

Independently verify quantile tool with fixed[1,…,10000],type 7 95%=[250.975,9750.025]. Quantile-unit fixture only, not simulated-training bootstrap.

Compare closed-form/float64 values at same `1e-12` tolerance. F7 Res4 lower `21.28325`/`21.283250000000002`,quantile lower `250.975`/`250.97500000000002` count as consistent; computation path/quantile method unchanged.

### 8.4 Malformed-input cases (modify valid F1 independently each time)

| Case | Sole change | Required outcome |
|---|---|---|
| E1 Missing file | Delete one best/standard.json | E_MISSING_FILE,specific run/path,exit 2, no statistical report |
| E2 Duplicate seed | Change last 30299 to 30298,still 300 records | E_DUPLICATE_SEED,identify 30298 |
| E3 NaN | JSON score NaN; separately test Infinity/1e999 | E_NONFINITE, no silently dropped episodes/conversion to 0 |
| E4 Bad set |30299→30300,300 unique seeds | E_TEST_SEED_SET,missing=[30299],unexpected=[30300] |
| E5 Fewer than 300 | Delete last entry,299 remain | E_EPISODE_COUNT,expected=300, actual=299 |
| E6 val/test mixing | seed30000→21000,still 300 unique | E_VAL_TEST_MIXED,identify 21000/validation partition |
| E7 Missing field | Remove any record truncated | E_REQUIRED_FIELD, no steps-based imputation |
| E8 Impossible win | score=376,won=true,died=false | E_WON_SCORE, other types/ranges valid |
| E9 Score/steps range | score=378/steps=0(separate tests) | E_SCORE_RANGE / E_STEPS_RANGE |
| E10 Incomplete hard | frozen hard_enabled=true, one last/hard.json absent,others complete | E_MISSING_FILE, no 29-hard-only analysis |
| E11 Configuration drift | One config tau=0.02, synthetic hashes updated | E_CONFIG_MISMATCH,equal means do not permit passage |
| E12 Duplicate validation | Append 300000 to summary.validation_steps | E_VALIDATION_SCHEDULE, reject 16 records |
| E13 Undeclared hard | hard_enabled=false but last/hard.json exists | E_UNDECLARED_HARD |

Separate duplicate/bad-set cases,otherwise duplicates mask set checking. val/test mixing checks seed semantics, without loading actual validation scores. Randomly reorder 300 records and require identical statistics/labels/bootstrap estimates(file hashes may differ),verifying seed alignment.

### 8.5 Personnel and sign-off

Cloud agent implements/tests; its “tests passed” is not another person's independent review. This document provides mathematical oracles/random-stream contracts separate from tested code:independent expected values, not independent personnel audit. Human acceptance table retains:

~~~text
Implementer: ____
Test author: ____ (explicitly state if the same as the implementer)
Human reviewer: ____
Human review date: ____
Actual fixtures / numbers / code commit / results checked: ____
Freeze-approval record: ____
~~~

Humans fill these fields; AI does not sign or mark “human reviewed.” Independent small-MDP target checking remains a separate freeze gate; synthetic analysis fixtures do not replace training-target oracle.

### 8.6 Additional acceptance: order, noninteger score, nonzero best, and formal identity

These do not replace F1–F8/E1–E13; tested outputs must not reverse-generate oracles.

Formal-identity acceptance's temporary Git repository must copy actual `matrix.csv` raw bytes with fixed SHA-256 `5cbd4e7b2cf79f65c96180acfc61b1914fe2e8521c036218bc7c9a4db59f0dfe`. Do not reserialize CSV/convert line endings. Run/machine/evaluation records remain synthetic fixtures, no real scores; “synthetic” does not exempt formal mode's fixed matrix-hash check. Synthetic-mode contract is unchanged by this paragraph.

| Case | Synthetic change/independent expectation |
|---|---|
| Finite noninteger score | Only score=1.5/all hashes updated,E_SCORE_RANGE;100.0 allowed; bool/string E_FIELD_TYPE; NaN/Infinity/1e999 E_NONFINITE,parse rejection first |
| Cross-file error order | First CSV run's last has 300 entries/score=378,best 299,hashes updated/others valid; E_SCORE_RANGE(last) before E_EPISODE_COUNT(best). Moving former to later run gives earlier CSV run's best-count error first |
| Global parse priority | Earlier run score=378,later any JSON NaN/hashes updated→E_NONFINITE(later),because global stage 3 precedes all record semantics; later config tau drift similarly gives E_CONFIG_MISMATCH first,global stage 4 |
| Nonzero best−last | F7 last,n1 best=last+7+h(e),n3 best=last+2; best seed-order steps[60000,80000,100000,120000,140000]. b[n1]=7.5 all 5,b[n3]=2 all 5,g=5.5 all 5,sd=0; d_best=B_a+i+6. Each K=#{J≥150},b_n1*=7+K/300,b_n3*=2,g*=5+K/300,d_best*=B_a+ΣI/5+5+2K/300; c/u/v remain 20/10/10. Check each replicate with same independent indices, no new RNG |
| Formal C/F pass | Throwaway Git commits all code/lock/fake configuration as C, then only permitted freeze materials as F; complete synthetic results/anonymous machine/environment/protocol seal agree. Formal identity may pass then compute F1 expectations; no real seed results read |
| Formal C/F rejection | Independently:nonancestor C,F modifies python/matrix/nonpermitted README,HEAD not sealed F,dirty tracked files,missing Git. E_MANIFEST(or earlier actual-hash E_HASH_MISMATCH); synchronize prior hashes in isolated fixtures to avoid stale-hash masking |
| Formal environment rejection | Missing separate file→E_MISSING_FILE; wrong hash→E_HASH_MISMATCH; updated-hash wrong machine_id/CPU/threads/C/F→E_MANIFEST; missing protocol_evidence→E_MANIFEST |
| Formal provenance success | provenance contains exact C/F/current HEAD=F/environment path/hash/machine_id; core F1 numbers/labels match original oracle,new provenance does not alter them |

#### 8.6.1 Training/final-evaluation binding acceptance (R1)

All use temporary Git/synthetic freeze materials/launch-evaluation spies, no real scores/sealed seeds; positive checks need not start actual 300 k training.

| Independent change to valid fixture | Expected training / final-evaluation prechecks |
|---|---|
| Commit changed protocol text,manifest unchanged | Both reject, report actual protocol hash/manifest mismatch |
| Set one configuration hash to all zeros; also update fixture config-file hash to prevent stale-hash masking | Both reject,identify field/corresponding manifest mismatch; test all three independently |
| Delete freeze_manifest.json | Both reject,explicit missing-file reason |
| complete=false / synthetic=true / wrong code_commit, separate tests | Both reject corresponding formal-manifest/identity condition |
| Remove required frozen_files entry/change extra-frozen file/delete actual file, separate tests | Both reject, not only checking three fixed files |
| Valid C/F/three configuration values/all actual files match manifest | Both wired paths pass binding; other gates still control launch/evaluation |

Counterexamples assert 0 training-entry/subprocess/environment-step calls; final-evaluation counterexamples assert 0 permission/test-partition calls. Use at least real-CLI negative cases for nonzero exits plus wired preflight spies for timing. Manifest-generation positives need no old manifest; do not skip formal binding to eliminate circularity.

#### 8.6.2 Byte checkout and dependency-snapshot acceptance (R2/R3)

- Temporary Git LF documents/scripts/dependencies/literal CRLF matrix fixture; after -text,fresh core.autocrlf=true/false checkouts have identical raw bytes/blob/known hashes. Independent SHA-256 of original fixture bytes yields expectations, not tested checker/normalized files.
- Positive:complete snapshot committed in C,F changes only permitted files,paths/three main hashes/actual files agree.
- Negative:snapshot added/modified only in F; wrong dependency_lock_path;>= installation file/NumPy-only file substituted; nonexact entries/missing any original top-level dependency. Formal generator/prechecks reject; formal analysis retains file/identity contract, no statistics with misplaced dependencies.
- Synchronize hashes preceding tested C/F/format checks to avoid stale-hash masking. Local executor accepts actual A1000 fresh Windows clone/package correspondence; temporary Git tests do not replace it.
- R1/R2/R3 supplement, not replace F1–F8/E1–E13 or alter literals/tolerances; runner Refused nonzero and analyzer E_* classifications are distinct entry-point contracts, without fabricated cross-entry error codes.

### 8.7 Source/execution evidence records

6023b1a's test_prereg_analysis_expected.py statically shows F1–F6/F8 complete m/effect/rate/steps/nonzero-best shared-index expectations; separate file placement does not require duplicate relocation into test_prereg_analysis.py. Integrated acceptance considers fixture content/actual collected execution. GPT did not run that test file;415 passed is a local report, not proof new pending§8.6 passed. Human fields remain under§8.5.

## 9. Independent B1/B2 descriptive-analysis contract

### 9.1 Inputs, definitions, and boundaries

Adopted secondary metrics,entirely independent of§§2–8 core data/labels. Inputs only matrix.csv/frozen manifest/two frozen diagnostic-code files/30 runs/<run_name>/window_diagnostics.json; no standard/hard tests/.pt/train-val scores/coreanalysis for metric selection. Freeze identity/code hashes are nonscore evidence compatible with isolation.

schema=window-diagnostics-1,definition_version="1"(string),counting_source=emitted_once,indicator=action_mismatch_to_selected_greedy,descriptive_only=true; n_envs=8,n_step from CSV,gamma=.99,transition_budget=300000,bin_size=20000,15 bins numbered from 0,0–14. meta contains run_name/arch/n_step/run_seed/git_sha=F, not C. 30/30 --window-diagnostics fixed by F checklist/external record/actual commands, no frozen_config field. Resumption lacks complete diagnostics and is formally prohibited.

Reuse existing g=greedy_actions for actual preupdate online batch(no_grad/eval/restored train),executed A from original ε-greedy; U=1[A≠g],G=1−U. No target/final/update-time recomputation. Another tied equal-valued action may give U=1, not strictly suboptimal/zero ties. Random branch A=g gives U=0, no explore_mask needed, no forwards/RNG/per-step tensor synchronization.

Count actual inserted windows once, not per sample/update.W=[t,…,t+h−1],h=1..n, same env/episode; L=any(U_j,j=1..h−1),excluding start,h1 empty L=0. Actual NStepReplay term/trunc rules flush all short h; term discount 0,trunc actual final observation/γ^h,reset never concatenates old windows; budget stop no extra flush,at most 16 pending. Batch global_id=batch_start_env_steps+i+1,assign to **start**15 bins/backfill across bins; h>=2 excludes tails without later actions.

D=window info.died, not inferred from reward/term/trunc. Final death offset j_D=h−1; T=D∧G_start∧L; J=D∧G_start∧j_D≥1∧U_death; P=D∧G_start∧any(U_j,1≤j<j_D).T=J OR P,overlapping J/P not additive.Z=−10*.99^j_D(D1),otherwise 0; known death component only, not total ret/TD error/causal effect. Independent tests verify −10 penalty; death＋pellet total −9.01 is not D criterion.

Per-bin/h cells contain n,nonnegative 2×2×2 C_g_l_d[g][l][d],integer J/P,matching-layout float64 death_component_sum_g_l_d,end_kind_counts={nonterminal,death,win,truncated},start_eps={sum,min,max,count}. Directly reuse actual batch eps; zero-window min/max may be null. Raw files retain pending_by_start_bin/pending_total/totals.collected_transitions/emitted_windows/death_events/death_events_by_transition_bin/rates.run.h1..hn/all/rates.by_bin.0..14.h1..hn/all/integrity.complete/checks/errors/verified_against_replay.

Integrity: actual collected=300000,emitted+pending=collected,sum all C=emitted,endkind sum=n/death equals D-cell sum,death_events≤N_D≤n*death_events,pending≤8(n−1),n1 L/T/J/P=0,verify_against_replay=true with actual emit count/h/order/action/ret/disc verified. Atomic final publication; partial not complete, no per-transition disk writes. Array floats/values finite,counts nonnegative, no NaN.

Protocol§11 expands definitions; all statistics/expectations here suffice for independent implementation. For any run/bin-h/all group,N=ΣC,N_G=ΣC[1,l,d],N_L=ΣC[g,1,d],N_D=ΣC[g,l,1],N_GL=ΣC[1,1,d],N_GD=ΣC[1,l,1],N_T=C[1,1,1],summing selected group; J/P use same records.

| Output key | Numerator/denominator |
|---|---|
| p_later_mismatch | N_L/N |
| p_greedy_start | N_G/N |
| p_later_mismatch_given_greedy_start | N_GL/N_G |
| p_later_mismatch_hge2 | Σ_h≥2 N_L / Σ_h≥2 N |
| p_later_mismatch_given_greedy_start_hge2 | Σ_h≥2 N_GL / Σ_h≥2 N_G |
| full_horizon_fraction | N_h=n/N |
| death_window_fraction | N_D/N |
| greedy_start_death_window_fraction | N_GD/N |
| cooccurrence_given_greedy_start_death | N_T/N_GD |
| cooccurrence_given_any_death | N_T/N_D |
| cooccurrence_of_all_windows | N_T/N |
| death_step_mismatch_given_greedy_start_death | N_J/N_GD |
| earlier_mismatch_given_greedy_start_death | N_P/N_GD |
| death_given_later_mismatch_greedy_start | N_T/N_GL |
| death_given_no_later_mismatch_greedy_start | N_GnotLD/N_GnotL |
| death_component_abs_share_T | abs(sum Z_T)/Σ_g,l abs(sum Z_g,l,D=1) |

Also save death_component_sum_greedy_start_death=ΣZ_GD,death_component_sum_T=ΣZ_T,death_component_mean_greedy_start_death=ΣZ_GD/N_GD,death_component_mean_T=ΣZ_T/N_T. Z nonpositive,so absolute cell sums equal window absolute sums; denominator is all death-window absolute components, not GD.

rate={numerator,denominator,rate,status}; denominator 0 gives rate=null/status=no_eligible_windows; h1/n1 h≥2 0/0 is not zero rate. Z means with denominator 0=null. Individual h1 full_horizon counts numerator only if h equals run n,otherwise 0; all h≥2 rates select actual h≥2 cells. Death may recur across overlapping windows, not independent death transitions.

### 9.2 Independent sealing and identity verification (remaining minimal code additions)

Auxiliary seal:results_prereg/window_diagnostics_seal.json; schema=window-diagnostics-seal-1, fixed matrix_sha256,exact 30 CSV-ordered runs,exact 30 files mapping<run_name>/window_diagnostics.json→actual hash,transition_budget=300000,descriptive_only=true,code_sha256 exactly window_diag.py and window_diagnostics_summary.py. Add code_commit=C,freeze_commit=F,freeze_manifest_sha256; no core evaluation_seal.files additions.

Add explicit --freeze-manifest(same F manifest)/--freeze-commit(full external F) to seal/summarize as **auxiliary-tool** parameters, not training/core-analysis/configuration fields. Seal verifies two manifest code hashes/actual code/current HEAD=F/permitted C/F relationship; all 30 meta.git_sha=F/matrix identity/integrity/budget/actual emit checks under§9.1; code_sha256 bound to frozen hashes and actual matches, not merely contemporary unknown-version hashes. Summarize rechecks manifest hash/external F/current=sealed=frozen code hashes/30 file hashes/meta-F/structure; do not ignore recorded code_sha256 while checking file hashes. Both parsers recursively reject nonfinite numbers(including 1e999),check fixed headers/integrity, not just NaN constants. Missing files/wrong F/code drift/incomplete counts cause DiagError,stderr/exit 2/no apparently successful summary; not core E_* errors.

Missing/failed diagnostics are separate auxiliary deviations, not core run_problems/final-eval/H1/H2 dependencies or permission to retrain valid runs. Without all 30 auxiliary inputs,do not publish complete=true 30-run summary; retain omissions, not incomplete samples disguised as full 5 seeds. Record engineering-repair timing/identity; do not recollect/tamper with original counts.

### 9.3 Aggregation, numerical path, and outputs

Fixed arch=[cnn2,res4,res8],n=[1,3],training seed100..104 columns. Configuration JSON outputs all 16 proportions/2 Z means for run_level h1..hn/all, all 15 by_start_bin_all_h bins(including h≥2),5 raw values/numerators/denominators/identities,effective k/5,mean,ddof 1 sd,pooled. Raw diagnostics retain per-bin/h details; no additional bin/h inference. Also pending_total/death_events 5 values/summaries,window N, each source hash/JSON path/formula key. Raw Z tables/component sums remain source-linked; summary reports means/absolute fraction without losing provenance.

Integer ratios use Fraction for exact mean/variance, then float→math.sqrt; retain null/identity for zero denominators,exclude only for metric mean/report k. k=0 mean=null; k<2 sd=null/reason; pooled=Σnum/Σden differs from run mean. Recorder Z components accumulate float64 in frozen emit/traversal order; convert finite recorded means using Fraction(float) for exact binary values,compute seed means/variance then float. No counterfactual rebuilding/observational-overlap CIs. Integer proportions/Z absolute fractions distinct; floating-component denominator is not integer window count.

Atomically publish separate window_diagnostics_summary.json and window_diagnostics_summary.md, no overwriting; JSON includes all fields/C/F/freeze_manifest/auxiliary seal/raw-file/code hashes/definition version. Fixed Markdown columns:p_later_mismatch,p_later_mismatch_hge2,p_later_mismatch_given_greedy_start,full_horizon_fraction,death_window_fraction,cooccurrence_given_greedy_start_death,death_given_later_mismatch_greedy_start; also 15-bin h≥2 mean/pooled curves and links to all JSON J/P/Z/other proportions. **Accept existing fixed summary selection; no result-based columns or claims undisplayed metrics were unmeasured.** No need to duplicate all 16 rates in Markdown; all prespecified metrics traceable in JSON/raw data.

No new p/confirmatory labels/bootstrap/correlation/regression/diagnostic ranking/risk ratios/binwise significance. U/D co-occurrence is not causal,window frequency not impact magnitude, and bin differences do not establish effects only in first 40%. Core report may link auxiliary report without reading it for numbers/labels.

### 9.4 Independent expectations and remaining tests

Retain all protocol§11.6 hand/wiring cases:random A=g,tied alternative,G chains,death J/P, two-step truncation/win/death＋pellet,nongreedy start,pending,environment isolation,cross-bin,replay wraparound,zero denominators,overlapping deaths, no RNG/forward/synchronization side effects,core-sidecar isolation. Independent example:1/2 and 9/10 run mean 7/10,sd=√(2/25)=0.282842712474619,pooled 5/6; G=[1,1,0],death step 3,h3 T=J=1,P=0,Z=−9.801; h2 T=J=1,P=0,Z=−9.9; h1 nongreedy start T=0,Z=−10; death transitions 1/windows 3.G=[1,0,1],death step 3,h3 T=P=1,J=0; zero denominator null, not NaN.

New tests:correct formal F passes seal/summary; individual wrong meta.git_sha/seal F/current-sealed code_sha256 mismatch with frozen rejects; missing diagnostics leave core F1/H1/H2 unchanged but auxiliary rejects; unattached actual emit cannot seal formally; wrong definition_version/nonfinite overflow rejects; independent Pacman −10 death-component contract(including death＋pellet −9.01 total)passes and turns red with changed constant. All inputs/formal identities synthetic/throwaway, no real tests read.

**Diagnostic-structure defects/seal-summary-only changes do not authorize rewriting old training results**. This round accepts executor records only for actual A1000 overhead/weight equality; human oracle/analysis/literature/freeze sign-off belongs to humans. Do not mark this integrated document frozen without final acceptance.
