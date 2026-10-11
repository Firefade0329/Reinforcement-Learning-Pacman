# Translation notes and source correspondence

> These are reading-copy notes, not amendments to the protocol. The frozen Chinese originals govern. Frozen commit F: `92bf82eca0dae731f7396ed5b4e887e4f3b200e4`.

## 1. Source identities and scope

The supplied archive, not a later repository version, supplies the authoritative source bytes for this translation. The three supplied Chinese files match their entries in the supplied SHA256SUMS:

| Chinese source | Verified SHA-256 | Treatment |
|---|---|---|
| PREREG_ARCH_NSTEP_v0.3.2.md | `3030e3eee70eca95ecf03d70ea94d97e2bf0163c4bf07f5bc0dc70ad2c362dcc` | Full prose translation; all sections retained |
| ANALYSIS_SPEC_v0.3.2.md | `a4d64d46ed72d0c6e83cb1276f09e136a0639ee2db92954044a22cc642225100` | Full prose translation, including §8 fixtures and §9 B1/B2 |
| CLAUDE_HANDOFF_v0.3.2.md | `5078ad49177a0106d27bc912cccded91fc8529a2ef239a3a65fd5acfcd4abb74` | Hash checked; deliberately not translated, as requested |

README_RESULTS.md was supplied only as terminology/style reference. No formal-study outcomes from it are incorporated into either translation or the protocol summary. Historical observations, resource estimates, and provisional statuses already present in the frozen originals remain in their translated locations; they are not new formal results.

The supplied source checksum list additionally names FINAL_INTEGRATION_CHANGES_v0.3.2_r2_DSH_LITERAL_20261010.md with hash `1d80019db7096f6426e382d87b426721dfa9c7907a9cd5ce15f9b7248a052460`. That file is absent from the supplied archive; its contents/hash were not verified and it is not translated. It is not needed to establish the identities of the three supplied originals.

Canonical requested output filenames are retained inside a uniquely named delivery folder/ZIP. Output SHA256SUMS.txt describes the English delivery files, not replacements for the frozen Chinese source checksums. Source files were not edited or reencoded.

## 2. Terminology

| Chinese | English used | Distinction retained |
|---|---|---|
| 预注册 | preregistration | Frozen prospective rules, distinct from later interpretation |
| 预注册方案 | preregistration protocol | The main study document |
| 分析规格 / 合同 | analysis specification / contract | Implementation requirements, not outcome interpretation |
| 冻结 / 冻结提交 | freeze / freeze commit | Binding code/material identity; F remains distinct from C |
| 代码提交 | code commit | C |
| 封存 | sealing / sealed | Protocol-based restricted access and hash-bound outputs |
| 解封 | unsealing / unseal | Explicit transition to formal evaluation; CLI --unseal unchanged |
| 护栏 | safeguards / guards | Not an unbypassable security boundary |
| 特权输入 | privileged input | Information supplied by distance fields, not a causal conclusion |
| 事后解释 | post-hoc explanation | Explanation developed after viewing data |
| 事后探索 | post-hoc exploration | Not a confirmatory result |
| 确认性 | confirmatory | Prespecified H1/H2 decision rules only |
| 探索性 | exploratory | Prespecified exploratory questions remain exploratory |
| 描述性 / 次要 | descriptive / secondary | B1/B2 do not determine H1/H2 |
| 方向信号 | direction signal | direction_signal; two-label rule |
| 交互信号 | interaction signal | interaction_signal; distinct from H2 |
| 交互对比 | interaction contrast | c, with u/v auxiliary contrasts |
| 支持 / 反驳 / 不确定 | supported / refuted / uncertain | Machine enumerations unchanged |
| 支持信号 / 证据不足 | supported_signal / insufficient_evidence | Machine enumerations unchanged; no third signal label |
| 方法敏感 | method-sensitive / sensitive to interval method | Report both intervals without switching formal rules |
| 配对 | paired | Training-seed blocks and shared test initial states, not identical trajectories |
| 交叉 bootstrap | crossed bootstrap | Independently resampled training/test axes with shared indices |
| 保留测试集 | holdout / held-out test set | Previously viewed data cannot become a new independent holdout |
| 豆子 / 金豆 | pellet / power pellet | Pellet score is separate from reward |
| 通关 | win / winning | won field unchanged |
| 真正终止 | true termination | No bootstrap; distinct from time truncation |
| 时间截断 | time truncation | Bootstrap actual final observation using γ^h |
| 尾项 / 待发尾项 | tail samples / pending tails | Not missing environment transitions |
| 入库 / 发出窗口 | replay insertion / emitted window | Count once at emission, not per gradient use |
| 回放 | replay | Capacity and occupancy distinct from cumulative insertion count |
| 续训 | resumption / resumed training | Excluded from formal runs under the default protocol |
| 选模 | model selection / selection | GPU validation selects secondary best |
| 初态 | initial state | Not a claim of identical full episodes |
| 贪心 / 非贪心 | greedy / nongreedy | Operationally selected-argmax mismatch for B1 |
| 偏离 / 动作不匹配 | mismatch / action mismatch | A≠g, not necessarily strictly suboptimal Q |
| 共现 | co-occurrence | Not a causal effect or risk ratio |
| 复核 / 验收 | review / acceptance | Evidence levels remain distinct |
| 执行者报告 | executor report | Not GPT execution |
| 静态复核 | static review | Code/text read, not executed |
| 人类签核 | human sign-off | Humans fill human identity/date fields |
| 独立预期 / 手算 oracle | independent expectation / hand-calculated oracle | Mathematical independence is not personnel independence |
| 字面预期 | literal expected value | Test tolerance is distinct from decision logic |
| 工作树字节 / blob | working-tree bytes / blob | Runtime SHA-256 is not a Git object ID |
| 完整运行依赖快照 | complete runtime-dependency snapshot | Exact installed-package versions, not a wheel-hashed resolution lock |
| 彩排 | rehearsal | Disclosed historical starts, excluded from formal outputs |
| 万 | ten thousand | Counting unit retained without changing the source numeral |

Noisy Nets, Double DQN, Dueling, Expected Sarsa, Tree Backup, Retrace, PCG64, state_dict, all path/field names, and all machine labels retain their technical forms. “Online” and “target” distinguish networks rather than imply identical behavior and target policies.

## 3. Ambiguities and historical wording retained

1. **Historical status versus later frozen identity.** Both originals say “awaiting freeze,” reference 6023b1a static checks, and list work or human gates as pending. The translation's authority banner identifies the supplied frozen F, while the body retains those historical statements. Nothing is silently upgraded to completed acceptance, current main, or successful execution. (Protocol opening/§7.3–7.4; Analysis opening/§8.7.)
2. **Hypothesis prediction versus support boundary.** The prose prediction is ≥10; formal support requires an interval strictly outside 10, and H2 refutation strictly inside (−10,+10). These are retained as different statements, not harmonized into ≥ or ≤ decision rules. Zero variance still leaves the strict boundary. (Protocol §1; Analysis §6.)
3. **Different interval purposes.** Primary effect display/direction signals use 95% t, H1/H2 use 97.5% t, and bootstrap sensitivity uses 95%. A different bootstrap magnitude check is not a same-coverage replication or authority to change labels. (Protocol §5; Analysis §§4, 6.)
4. **Numerical-path history.** Statements that literal expectations/tolerances are unchanged coexist with the r2 literal corrections. The supplied r2 values are translated as supplied; no independent statistical redesign or numerical recalculation is inserted. Float64 t constants govern, with the specified fixture tolerances. (Analysis §§3, 4.1, 8.2–8.3.)
5. **General train-path validation wording.** The original requirement concerning non-validation-boundary budgets contains “750 episodes” beside the all-train-path deduplication discussion. The translation retains it without asserting that every arbitrary budget entails 750 episodes; the formal budget's separate 15×50 requirement remains unchanged. (Protocol §6, requirement 7.)
6. **Synthetic versus formal fixtures.** Ordinary synthetic mode can use its minimal synthetic seal without real Git. Formal-identity synthetic records require a temporary Git repository and the actual fixed matrix bytes. “Synthetic” does not relax formal identity or fixed matrix hashes. (Analysis §§1.1.1, 1.2, 8.6.)
7. **Initial-state sharing.** Paired seed blocks do not imply identical collected trajectories or identical whole test episodes. Likewise equal means do not prove per-episode equality. (Protocol §§1–3; Analysis §3.1.)
8. **Noninteger scores.** Finite noninteger score maps to E_SCORE_RANGE; numeric integral 100.0 is allowed, while bool/string score maps to E_FIELD_TYPE. Recursive nonfiniteness rejection precedes these. The ordering is translated without an alternative field-first path. (Analysis §2.3.)
9. **Selected greedy action and ties.** Nongreedy in B1 is operational A≠g, including a tied equal-valued alternative. The rough probability illustrations require unique greedy actions and do not establish zero observed tie frequency. (Protocol §§9, 11; Analysis §9.)
10. **Death timing.** T is death on or after subsequent mismatch; P is mismatch strictly before the death step; J is mismatch on that step. J/P can overlap. Neither translation merges them nor labels co-occurrence as causation. (Protocol §11.4; Analysis §9.1.)
11. **Null versus zero.** n=1 all-window later-mismatch fraction may be zero; h≥2 has no eligible windows and therefore a null rate. No eligible samples are not evidence of an observed zero frequency. (Protocol §11.3; Analysis §9.)
12. **Hash identity.** Raw working-tree bytes are the unique runtime hash object. Blob equality is checkout acceptance, not a second interchangeable hashing path. CRLF in this English delivery does not authorize normalization of matrix.csv's fixed CRLF bytes or any Chinese original. (Protocol §7.1.3; Analysis §1.1.1.)
13. **Code/freeze identity and external timing.** C/F permitted endpoint differences are not an automatic authorization for later refreezing. complete=true is not human approval. Self-entered timestamps are not independent timing proof, and final environment evidence arises after evaluation rather than before training. (Protocol §7; Analysis §1.2.)
14. **Personnel/evidence independence.** The same cloud agent implements and writes tests. “Independent oracle” denotes separately derived expectations, not an independent human audit. Original reports, static reading, execution, and sign-off levels remain distinct. (Protocol §§6, 7.3; Analysis §8.5.)
15. **Resource estimates and units.** Existing estimates and limitations are retained, including unmeasured architectures/load conditions and MB versus MiB distinctions. Chinese 万 is rendered as units of ten thousand where needed to preserve the original written numeral; this is a unit translation, not a changed budget. The concatenated source phrase res439分钟 in Protocol A2 is retained as res439 minutes rather than silently repairing the source typography; surrounding original resource passages give res4 timing separately. No hardware speedup is newly inferred. (Protocol §§2, 11.6, 12.)
16. **Future research and literature levels.** A1–A7 predictions are candidates for later registration. Full-text, abstract, and secondary reading levels describe supplied records, not GPT independently rereading those papers. Citation claims/locations were not upgraded or verified afresh. (Protocol §§9, 12.)
17. **Diagnostic integrity spelling.** The original input-field list says verified_against_replay, while the integrity requirement later says verify_against_replay=true. Both spellings are retained in their respective passages; this translation does not choose or repair a field name. (Analysis §9.1.)

The translations retain all procedural and historically superseded paragraphs in the supplied authoritative texts. No apparent contradiction is resolved by deleting a passage, adding a new rule, selecting a different interval, or importing later results.

## 4. Literal blocks retained and English glosses

In r2, Chinese comments, descriptive placeholders, form labels, and verbal formula annotations inside fenced blocks are translated into English. Command names/options, actual field names/JSON keys, identifiers, numerical values, and mathematical expressions are unchanged. Translated angle-bracket items such as <synthetic manifest> are literal placeholders in examples, not executable argument values or renamed schema fields; the illustrative <analysis script path> mapping key is likewise a path placeholder, not an actual JSON field name. Inline code is unchanged. The bilingual table below records the original Chinese text and its English reading.

| Location | Original Chinese comment, placeholder, or annotation | English gloss |
|---|---|---|
| Protocol §11.1.1 | g_t definition | Actual argmax action of the online network used for collection at that time, on the current input |
| Protocol §11.1.1 | A_t definition | Action actually executed after the original trainer's ε-greedy sampling |
| Protocol §11.2 | 起点动作 / 后续动作 / h−1个 | Starting action / subsequent actions / h−1 actions |
| Protocol §11.2 | L_t indicator prose | At least one subsequent action has U=1 |
| Protocol §11.4.1 | P indicator prose | There exists an offset 1≤j<j_D with U_(t+j)=1 |
| Protocol §11.4.2 | Z_t conditional prose | When D=1 use −10×γ^j_D; otherwise 0 |
| Analysis §1 layout | dependency_lock.txt comment | Complete runtime-environment version snapshot, committed with C |
| Analysis §1 layout | last/hard.json comment | Optional; all 30 enabled together or omitted together |
| Analysis §1 layout | environment/seal/summary comments | Independent machine/execution identity hash-bound by protocol_evidence; auxiliary sealing separate from core files; secondary descriptive summary |
| Analysis §1 CLI | 合成manifest / 合成目录 / 新目录 | Synthetic manifest / synthetic directory / new directory; these remain literal placeholders, not new paths |
| Analysis §1.1 JSON | 40位完整提交 / 分析脚本路径 | Full 40-character commit / frozen analysis script path relative to project root |
| Analysis §1.2 JSON | C/F的40位SHA / 独立环境文件实际64位SHA-256 | C/F full 40-character SHA / actual 64-character SHA-256 of the separate environment file |
| Analysis §2 examples | 64位十六进制 / 代码提交C的40位SHA | 64-character hexadecimal / full 40-character SHA of code commit C |
| Analysis §3 | 样本标准差，ddof=1 | Sample standard deviation, ddof=1 |
| Analysis §4.2 RNG comment | 先抽I，再抽J；进入下一次循环前不再调用任何随机方法 | Draw I first, then J; make no additional random-method calls before the next iteration |
| Analysis §4.2 formula comment | u/v/r/b/g同原公式 | u/v/r/b/g follow their original formulas |
| Analysis §5 hypothesis text | 在非零差值条件下，正向概率≤0.5；H1：>0.5 | Conditional on nonzero differences, positive probability≤0.5 under the null and >0.5 under the alternative; this is the sign-test alternative, not a redefinition of the study's H1 |
| Analysis §8.3 | 每seed完全相同 | Identical for every training seed |
| Analysis §8.5 form | 实现者 / 测试作者（如同实现者，明确填写相同） | Implementer / test author; explicitly state if the same as implementer |
| Analysis §8.5 form | 人类复核人 / 人类复核日期 | Human reviewer / human review date |
| Analysis §8.5 form | 实际核对的fixture / 数值 / 代码提交 / 结果；冻结批准记录 | Actual fixtures/numbers/code commit/results checked; freeze-approval record |
| Analysis §1 CLI | `<合成manifest>` | `<synthetic manifest>` |
| Analysis §1 CLI | `<合成目录>` | `<synthetic directory>` |
| Analysis §1 CLI | `<新目录>` | `<new directory>` |
| Analysis §1.1 JSON | `<40位完整提交>` | `<full 40-character commit>` |
| Analysis §1.1 JSON | `<冻结的分析脚本相对项目根目录路径>` | `<frozen analysis script path relative to project root>` |
| Analysis §1.1 JSON | `<分析脚本路径>` | `<analysis script path>` |
| Analysis §1.2 JSON | `<C的40位SHA>` | `<full 40-character SHA of C>` |
| Analysis §1.2 JSON | `<F的40位SHA>` | `<full 40-character SHA of F>` |
| Analysis §1.2 JSON | `<独立环境文件实际64位SHA-256>` | `<actual 64-character SHA-256 of the separate environment file>` |
| Analysis §2 examples | `<64位十六进制>` | `<64-character hexadecimal>` |
| Analysis §2 examples | `<代码提交C的40位SHA>` | `<full 40-character SHA of code commit C>` |

The external-record document_revision field keeps the literal `修订1+彩排追加A+DSH 字面修正`. Its English reading is “Revision 1 + Rehearsal Addendum A + DSH Literal Corrections,” as used in titles and prose. Chinese counting-unit characters within written formulas such as Δ_(100万) are retained as part of the original formula spelling; 万 means ten thousand. Placeholders such as “this path” in explanatory table cells do not rename a JSON key or a file.

## 5. Verification performed and limits

Performed for r2: restored missing spaces; translated only Chinese comments/placeholders/form labels/verbal annotations; normalized the requested full-width punctuation in the protocol; checked every original table against its translated counterpart and restored source indentation; removed the summary page-break divs in favor of horizontal rules; checked numerical-literal multisets and identifiers against the first edition; verified all three supplied source hashes remain unchanged; recomputed the delivery hashes and checked the ZIP contents. All four r2 documents and SHA256SUMS.txt use UTF-8, CRLF line endings, and no BOM. Direct byte inspection of the supplied translation_inputs.zip shows LF line endings in both authoritative source documents (987 and 813 LF characters respectively, with no CRLF), so r2 follows the requested CRLF output format but differs from the supplied source bytes in line endings. No source file was converted. Numerical-token checking is a transcription check, not a mathematical proof.

Not performed: repository-code execution, training/testing, formal-analysis reruns, independent review of real results, fresh literature reading or citation verification, reconstruction of the repository's historical freeze/access records, or human sign-off. The supplied source identities were checked against the archive checksum list, not independently downloaded from Git commit F in this translation task. Translation meaning and summary selections have been reviewed against the supplied texts, but these notes do not claim an independent bilingual human certification. The summary retains its five-part structure with ordinary horizontal rules and no forced pagination; page geometry remains renderer-dependent.


### r2 table and spacing audit

All 33 authoritative-source tables were checked row by row: 22 in the protocol and 11 in the analysis specification. The protocol's small-MDP-oracle table (original source line 283, §6 requirement 6) uses three leading spaces on every row, including its header and separator; all other authoritative-source tables use zero leading spaces. Table row counts and pipe structures are unchanged. The summary's two tables and the notes' five tables were also checked for uniform indentation; they have no Chinese-original counterpart beyond the existing first-edition layouts.

Protocol table starts in the supplied Chinese original: 9, 30, 73, 90, 99, 132, 160, 283, 332, 394, 429, 469, 517, 560, 583, 644, 674, 753, 790, 857, 957, 969. Analysis table starts: 140, 207, 231, 425, 500, 528, 629, 669, 708, 723, 766.

The English-letter/digit adjacency scan exempts identifiers, mathematical/index labels, configuration/column labels, versions, hash strings, filenames/paths, and scientific notation, including float64, uint8, PCG64, cnn2/res4/res8, n1/n3, h1/h2/h3, CI95/CI975, H1/H2, F1–F8, seed100, and v0.3.2. The original concatenated token res439 remains the unresolved source spelling described in §3 item 15: splitting it into res4 and 39 would change the numeric-token multiset, so it is not silently repaired. No English sentence is rewritten to resolve that ambiguity.

Outside the bilingual translation notes, retained Chinese is limited to the exact frozen document_revision value and the counting unit 万 inside unchanged formulas. They are data/formula literals, not untranslated comments or prose; translating that metadata value or rewriting the formulas is outside the authorized formatting corrections. Bilingual Chinese source headings and glossary entries remain intentionally in these notes.

## 6. Section correspondence

Each body retains the original heading order, heading depth, numbering, and table structure; only the reading-copy authority banner precedes the title. Unnumbered source headings remain unnumbered. Links and document paths inside the texts retain their source forms, rather than being changed to .en.md paths.

The complete heading correspondence follows.

### Protocol heading correspondence

| Chinese original heading | English reading-copy heading |
|---|---|
| 架构 × n-step：完整预注册方案 v0.3.2（修订1+彩排追加A+DSH 字面修正） | Architecture × n-step: complete preregistration protocol v0.3.2 (Revision 1 + Rehearsal Addendum A + DSH Literal Corrections) |
| 相对原 v0.3.2 的变更清单 | Changes relative to the original v0.3.2 |
| 相对“修订1”合并版的彩排追加及本次集成变更 | Rehearsal additions and integration changes relative to the “Revision 1” integrated version |
| 来源与本次核验范围 | Sources and scope of this verification |
| 1. 问题、范围与已有证据 | 1. Question, scope, and existing evidence |
| 预先定义的研究目标 | Predefined research objectives |
| 可被数据否定的预先假设 | Prespecified, falsifiable hypotheses |
| 2. 正式矩阵与固定条件 | 2. Formal matrix and fixed conditions |
| RTX A1000（6GB）资源、开销与正式机器 | RTX A1000 (6GB): resources, overhead, and formal machine |
| 3. 新数据划分与测试封存 | 3. New data partitions and sealed tests |
| 4. 终点、选模与指标 | 4. Endpoints, model selection, and metrics |
| 主要终点 | Primary endpoint |
| 次要终点 | Secondary endpoints |
| 5. 分析：训练种子是统计单位 | 5. Analysis: training seeds are the statistical units |
| 不确定性报告 | Reporting uncertainty |
| 显著性与结论边界 | Significance and boundaries of conclusions |
| 6. 试运行、故障与续训 | 6. Trial runs, failures, and resumption |
| 冻结实现必须满足的要求与验收证据 | Requirements and acceptance evidence for the frozen implementation |
| 7. 冻结身份、最终评估与开跑清单 | 7. Freeze identity, final evaluation, and launch checklist |
| 7.1 代码提交C与冻结提交F：非自引用流程 | 7.1 Code commit C and freeze commit F: a non-self-referential process |
| 7.1.1 训练与最终评估前的冻结文件绑定（R1） | 7.1.1 Binding freeze records to files before training and final evaluation (R1) |
| 7.1.2 生成清单与正式运行分离，避免自引用 | 7.1.2 Separate manifest generation from formal execution to avoid self-reference |
| 7.1.3 唯一哈希对象、-text 与全新克隆验收（R2） | 7.1.3 Unique hash object, -text, and fresh-clone acceptance (R2) |
| 7.1.4 完整运行依赖快照的责任、提交和字段（R3） | 7.1.4 Responsibility, commit, and fields for the complete runtime-dependency snapshot (R3) |
| 7.2 解封、最终评估与分析分别核验什么 | 7.2 Separate checks for unsealing, final evaluation, and analysis |
| 7.2.1 外部冻结记录、保存位置与时间证据 | 7.2.1 External freeze record, storage location, and timing evidence |
| 7.2.1.1 两阶段，避免自引用与倒填 | 7.2.1.1 Two stages, avoiding self-reference and backfilling |
| 7.2.1.2 开跑前FREEZE_RECORD.json最小字段 | 7.2.1.2 Minimum prelaunch FREEZE_RECORD.json fields |
| 7.2.1.3 固定保存位置 | 7.2.1.3 Fixed storage location |
| 7.2.1.4 验证“先记下，再正式开跑” | 7.2.1.4 Checking “record first, formally launch afterwards” |
| 7.3 证据等级 | 7.3 Evidence levels |
| 7.4 完整冻结清单（每项有来源；人类字段留空） | 7.4 Complete freeze checklist (sources for each item; human fields left blank) |
| 7.5 冻结当天的责任与操作顺序 | 7.5 Responsibilities and sequence on freeze day |
| 8. 输出与报告模板 | 8. Output and reporting template |
| 9. n-step回报的文献依据与未确定事项 | 9. Literature basis for n-step returns and unresolved matters |
| 核对状态：阅读记录与GPT独立核验分开列 | Verification status: reading records separate from GPT independent checks |
| 目标形式与教材算法的区别 | Target form and differences from textbook algorithms |
| Rainbow与本项目的方向对比 | Comparing directions in Rainbow and this project |
| 两类候选解释，均不确认 | Two categories of candidate explanation, neither confirmed |
| Retrace的启示与适用边界 | Lessons from Retrace and applicability limits |
| 真实参考文献与定位待办 | Actual references and source-location tasks |
| 本轮明确不确定的地方 | Explicit uncertainties this round |
| 扩展文献核对表与撤回主张 | Extended literature-verification table and withdrawn claims |
| 10. 修订、命名与不变项 | 10. Revisions, naming, and invariants |
| 11. 已采用的B1/B2：次要、观察性、不干预 | 11. Adopted B1/B2: secondary, observational, noninterventional |
| 11.1 “非贪心”的精确定义 | 11.1 Precise definition of “nongreedy” |
| 11.1.1 用实际决策时的online网络，不事后重算 | 11.1.1 Use the online network at the actual decision, without retrospective recomputation |
| 11.1.2 这不是什么测量 | 11.1.2 What this does not measure |
| 11.2 窗口单位、边界与时间归属 | 11.2 Window units, boundaries, and temporal assignment |
| 11.3 B1指标与分母 | 11.3 B1 metrics and denominators |
| 11.4 B2指标：死亡、后续偏离与贪心起点的共现 | 11.4 B2 metrics: death, subsequent mismatch, and greedy-start co-occurrence |
| 11.4.1 死亡来自环境info，不能从总reward猜测 | 11.4.1 Death comes from environment info, not inferred from total reward |
| 11.4.2 必须输出的比例 | 11.4.2 Required proportions |
| 11.5 实现接口、保存与汇总 | 11.5 Implementation interface, storage, and aggregation |
| 11.5.1 本次明确接受的实现差异与留痕 | 11.5.1 Explicitly accepted implementation differences and records |
| 11.6 开销与无副作用验收 | 11.6 Overhead and no-side-effect acceptance |
| 12. 后续研究A1–A7与样本量/预算规划（不进入本轮） | 12. Future research A1–A7 and sample-size/budget planning (outside this round) |
| A1：n-step × 回放容量 | A1: n-step × replay capacity |
| A2：n-step × 探索日程 | A2: n-step × exploration schedule |
| A3：明确的off-policy处理对照 | A3: Explicit off-policy treatment controls |
| A4：输入表示与网络结构分离 | A4: Separate input representation from network structure |
| A5：深度与参数量/计算量分离 | A5: Separate depth from parameter count/computation |
| A6：预算缩放，先控制探索日程 | A6: Budget scaling, controlling exploration first |
| A7：更多训练seed用于估计/复核 | A7: More training seeds for estimation/replication |
| 12.8 A6/A7的种子数与功效规划依据 | 12.8 Basis for A6/A7 seed-count and power planning |

### Analysis heading correspondence

| Chinese original heading | English reading-copy heading |
|---|---|
| 架构 × n-step：完整分析规格 v0.3.2（修订1+彩排追加A+DSH 字面修正） | Architecture × n-step: complete analysis specification v0.3.2 (Revision 1 + Rehearsal Addendum A + DSH Literal Corrections) |
| 1. 执行边界与文件位置 | 1. Execution boundaries and file locations |
| 1.1 冻结与封存清单的最小格式 | 1.1 Minimum freeze and evaluation-seal manifest formats |
| 1.1.1 唯一哈希对象与跨平台字节规则（R2） | 1.1.1 Unique hash object and cross-platform byte rules (R2) |
| 1.1.2 正式冻结机器全新克隆验收 | 1.1.2 Fresh-clone acceptance on the formal freeze machine |
| 1.1.3 完整运行依赖快照（R3） | 1.1.3 Complete runtime-dependency snapshot (R3) |
| 1.2 C/F身份、机器证据与协议封存（唯一正式路径） | 1.2 C/F identity, machine evidence, and protocol-based sealing (unique formal path) |
| 1.2.1 训练和最终评估的共同绑定预检（R1） | 1.2.1 Shared binding prechecks for training and final evaluation (R1) |
| 1.2.2 外部冻结记录和启动顺序 | 1.2.2 External freeze record and launch sequence |
| 1.2.2.1 两阶段，避免自引用与倒填 | 1.2.2.1 Two stages, avoiding self-reference and backfilling |
| 1.2.2.2 开跑前FREEZE_RECORD.json最小字段 | 1.2.2.2 Minimum prelaunch FREEZE_RECORD.json fields |
| 1.2.2.3 固定保存位置 | 1.2.2.3 Fixed storage location |
| 1.2.2.4 验证“先记下，再正式开跑” | 1.2.2.4 Checking “record first, formally launch afterwards” |
| 2. 固定输入合同 | 2. Fixed input contract |
| 2.1 矩阵、配置与运行身份 | 2.1 Matrix, configuration, and run identity |
| 2.2 评估 JSON 的新格式 | 2.2 New evaluation JSON format |
| 2.3 必须失败的完整性检查与顺序 | 2.3 Mandatory failing integrity checks and order |
| 3. 精确计算合同 | 3. Exact computation contract |
| 3.1 次要指标和探索性对比 | 3.1 Secondary metrics and exploratory contrasts |
| 4. 区间与可复现 bootstrap | 4. Intervals and reproducible bootstrap |
| 4.1 训练种子 t 区间 | 4.1 Training-seed t intervals |
| 4.2 交叉 bootstrap 的随机流合同 | 4.2 Crossed-bootstrap random-stream contract |
| 5. Res4 单侧精确符号检验 | 5. Res4 one-sided exact sign test |
| 6. 不可事后调整的机器判读 | 6. Machine decisions that cannot be adjusted post hoc |
| 7. 输出合同与数字溯源 | 7. Output contract and numerical provenance |
| 8. 合成数据验收：独立预期值 | 8. Synthetic-data acceptance: independent expected values |
| 8.1 通用造数规则与判断标准 | 8.1 Common fixture generation and acceptance criteria |
| 8.2 有效统计用例 | 8.2 Valid statistical cases |
| 8.3 必须抓住测试轴抽样和配对错误的 F7 | 8.3 F7 must detect test-axis sampling/pairing errors |
| 8.4 畸形输入用例（每次单独修改有效F1） | 8.4 Malformed-input cases (modify valid F1 independently each time) |
| 8.5 人员与签核 | 8.5 Personnel and sign-off |
| 8.6 补充验收：顺序、非整数score、非零best与正式身份 | 8.6 Additional acceptance: order, noninteger score, nonzero best, and formal identity |
| 8.6.1 训练/最终评估绑定验收（R1） | 8.6.1 Training/final-evaluation binding acceptance (R1) |
| 8.6.2 字节检出与依赖快照验收（R2/R3） | 8.6.2 Byte checkout and dependency-snapshot acceptance (R2/R3) |
| 8.7 源码/运行证据记录 | 8.7 Source/execution evidence records |
| 9. B1/B2独立描述分析合同 | 9. Independent B1/B2 descriptive-analysis contract |
| 9.1 输入、定义与边界 | 9.1 Inputs, definitions, and boundaries |
| 9.2 独立封存与身份核验（剩余最小代码补齐） | 9.2 Independent sealing and identity verification (remaining minimal code additions) |
| 9.3 汇总、数值路径与输出 | 9.3 Aggregation, numerical path, and outputs |
| 9.4 独立预期与剩余测试 | 9.4 Independent expectations and remaining tests |
