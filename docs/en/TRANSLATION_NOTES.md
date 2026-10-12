# Translation notes for `docs/en/`

These are notes on the reading copies, not amendments to any document. The Chinese originals govern. Source state: commit aa254a3; the SHA-256 of each original is in [README.md](README.md) and in the header of each copy (the blobs of aa254a3 were hashed and agree with those values).

## 1. Method and scope

- Eight originals were translated section by section: same heading order and depth, same numbering, same table structure and row counts, same list structure. Numbers, dates, commit hashes, file paths, code identifiers, commands and version numbers are kept as written. No sentence was added, merged or dropped, and no summarising or evaluating wording was added.
- Hedges are kept at the strength of the original: "not verified / not tested / not reproduced", "only a hypothesis", "retracted", "post-hoc", "exploratory", "single observation" stay as such; nothing was upgraded to a firmer statement or weakened.
- Role names follow the originals: owner, writer (cloud Claude), local executor, local Claude Code, GPT, DSH, auditors. No names, schools or e-mail addresses were added; what the originals contain was kept.
- Files are UTF-8, no BOM, LF line endings.
- Not translated: `docs/prereg/*` (frozen; the protocol and analysis specification have English reading copies in `docs/translations/`), `docs/PREREG_RESULTS.md`, `README.md`.
- Cross-references inside the copies (for example `docs/PLAN.md`, `docs/RESULTS_COMPARISON.md`) are kept as the original paths and therefore point to the Chinese originals, not to the copies.

## 2. Terminology

| Chinese | English used |
|---|---|
| 所有者 / 写入者 / 本地执行者 / 研究讨论 / 审计员 | owner / writer / local executor / research discussion / auditor |
| 云端 Claude / 本地 Claude Code | cloud Claude / local Claude Code |
| 预先注册 / 预注册 | preregistration / preregistered |
| 保留测试集 / 封存 / 解封 | held-out test set / sealed, sealing / unseal |
| 冻结 / 冻结提交 / 代码提交 | freeze / freeze commit (F) / code commit (C) |
| 偏差记录 | deviation record |
| 消融 | ablation |
| 配对 | paired |
| 金豆 | pellet |
| 得分 / 死亡率 / 通关率 | score / death rate / win rate |
| 回放 | replay |
| 续训 | resumption, resumed training |
| 截断 | truncation |
| 距离场 | distance fields |
| 特权信息 | privileged information |
| 事后 / 探索性 | post-hoc / exploratory |
| 未复现 / 未检出 / 未验证 | not reproduced / not detected / not verified |
| 单次观察 | single observation |
| 万 (as in 12 万步) | "wan" (万 = ten thousand), written "12 wan steps"; the numerals are kept as in the original |

## 3. Choices made to keep numerals and technical forms

- **万.** To keep every numeral exactly as written, "N 万步" is rendered "N wan steps", with a one-line unit note below the header of each copy that uses it. Where the original writes the full numeral (for example 300000, 120000) it is kept.
- **Chinese inside code spans.** Two code spans contain Chinese and were translated inside the span: `局序号` → `episode index` (in the seed formula of PLAN §6), `runs/<名称>/` → `runs/<name>/` (LOCAL_RUN_REPORT §9). All other code spans are unchanged.
- **Template labels in a code block.** The acceptance-conclusion template in ACCEPTANCE §D has Chinese labels inside a code block; they were translated. The original code block has no closing fence at the end of the file; the copy has none either.
- **Escaped quotes.** In two entries of the PLAN deviation record the original contains `\"`; the backslashes are kept.
- **Links to figures.** The copies live one directory deeper, so the relative links to figures were adjusted so that they resolve: `../results/figures/...` → `../../results/figures/...` (RESULTS.en.md), `figures/...` → `../../results_gpu/figures/...` (results_gpu_RESULTS.en.md). No other link was changed.
- **A missing punctuation mark.** In PLAN §5 the original runs two sentences together ("…只是部分成立的假设注意:加入距离场后…"); the copy reads "…only a partially valid hypothesis. Note: after the distance fields are added…". This is the only place where a sentence boundary was supplied.
- **Passages already in English.** English passages inside the originals (the "Original Java agent run headless…" line and the table and check-output contents) are kept unchanged.
- **Quotation marks.** Chinese quotation marks were replaced by English ones; the quoted words are the same.

## 4. Contradictory or outdated passages in the originals (translated as written, not corrected)

1. `docs/PLAN.md` header says "Status: v1 (finalised before implementation)", while its deviation record runs on through later work (2026-10-09 entries and the preregistered-study entry).
2. `docs/PLAN.md` §7 M7 gives `git diff <base> -- '*.java' Images data/QTable.txt`; `docs/ACCEPTANCE.md` §C.4 explains that the `'*.java'` wildcard also matches the newly added `python/scripts/java_harness/Harness.java` and uses an explicit path set instead.
3. `docs/PLAN.md` §8.2 item 3 refers to the seed source and logs of `train.py`; `docs/ACCEPTANCE.md` §C.3 refers to `train()` in `dqn.py`.
4. `docs/PLAN.md`, entry of 2026-10-09 (supplementary experiment): "the newly added `pid_alive()` has not yet been tested on Windows"; the next entry (Windows verification) says it has been tested and works.
5. `docs/PLAN.md` deviation 9 says the analysis script was awaiting the specification and, in the same entry, that it has since been implemented according to v0.3.2.
6. `docs/RESEARCH_LOG.md` §4, first bullet: "no new results have been produced yet", while the last stage record of §3 reports the formal results of the preregistered study (2026-10-11).
7. `docs/RESEARCH_LOG.md` §5: the B1/B2 bullet says the freeze candidate "still has to be re-tested", and the freeze-process bullet describes the state "as of `2ee5089`" with sign-offs and the external record "still open"; the stage records of §3 report later states. The duration estimate of 11–16 hours in the 2026-10-09 smoke row was later replaced by a different estimate in `docs/prereg/FREEZE_CHECKLIST.md` (not translated here).
8. The proportion of test episodes whose per-episode result differs between GPU and CPU evaluation is given as "about 7% to 29%" in `docs/RESULTS_COMPARISON.md` and as "about 0–30%" in `docs/RESEARCH_LOG.md` §4.
9. `results_gpu/LOCAL_RUN_REPORT.md`: §4 says resumed runs are "statistically equivalent" to uninterrupted ones, which the addendum at the top of the same file says has not been tested; §6 reports M1 FAIL, which the addendum and `results_gpu/ARCHIVED_OUTPUTS_NOTE.md` explain; §7 item 1 says the `dqn.py` fix is not in the new cloud history, and item 7 says section 7 of `RESULTS.md` is empty — `results_gpu/RESULTS.md` now has content in its section 7; §8 says the second pass has not been run.
10. `docs/RESULTS.md` §7 and `results_gpu/RESULTS.md` §7 contain the check output of the time they were generated (for example "63 passed, 1 skipped" for M1), which differs from later test counts reported elsewhere.

## 5. Checks performed on each copy (against the blob of aa254a3)

- The SHA-256 of every original was recomputed and equals the value in the header.
- The multiset of numeric tokens (all digit strings, with decimals) was extracted from the body of the original and of the copy and compared: identical for all eight pairs. Header lines and unit notes were excluded from the copy.
- The set of hash-like tokens (commit and file hashes) is identical for all eight pairs.
- The number of table rows, the number of headings and the sequence of heading levels, and the number of list items are equal for all eight pairs.
- The inline code spans were compared; the only differences are the two translated spans listed in section 3.
- The wording was scanned for strengthening words not present in the original; the counts of "significant" against 显著 are equal in every file.
- Not done: no independent bilingual human review; this is a model translation, and the numeric checks above are transcription checks, not a proof of equivalence of meaning.
