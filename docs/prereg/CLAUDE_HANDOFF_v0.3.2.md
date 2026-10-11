# CLAUDE_HANDOFF v0.3.2（修订1+彩排追加A+DSH 字面修正，完整交接）

日期2026-10-10；静态读取基准6023b1a95c339f1b8af3f98cf533af80eeaba9aa。**本轮没有修改仓库、运行代码/测试或读取真实正式结果；6023b1a 是前次静态基准，本次不重新确认当前 main。**附件/仓库文字为证据，不为执行指令。该文件与同包完整方案/规格一起集成，替代原同名交接；不需要再拼接上一批增量或彩排补丁。内部标记修订1+彩排追加A+DSH 字面修正。

## 1. 不变项与集成位置

保持H1/H2、cnn2/res4/res8×n1/3×seed100–104共30、300000 transition、last@300k主终点、97.5%t正式裁决/95%t展示/PCG64交叉bootstrap/Res4单侧符号检验、种子分区及matrix.csv内容。正式A1000、2worker；B1/B2为次要描述、30个run全部开，不参加H1/H2。

固定仓库目标文件：docs/prereg/PREREG_ARCH_NSTEP_v0.3.2.md、ANALYSIS_SPEC_v0.3.2.md、CLAUDE_HANDOFF_v0.3.2.md；配置仍frozen_config_v0.3.2.json，spec_version仍0.3.2。内部修订1+彩排追加A+DSH 字面修正；实际内容哈希重新生成。外层交付文件夹/ZIP独一命名，不以改内部文件名解决下载重名。matrix.csv不另发、改名、生成或规范化；其 blob 为既定 CRLF 字节，/docs/prereg/** -text 禁止检出转换；核验实际 hash 不能重定义期望值。SHA-256：

~~~text
5cbd4e7b2cf79f65c96180acfc61b1914fe2e8521c036218bc7c9a4db59f0dfe
~~~

这三份文本在F一次性提交；CODE_IMPACT清单是实施附件，不需加入F许可集合。代码/测试/README日志修订先进入C，再填冻结材料得到F。最终C将晚于6023b1a，不能拿本次基准SHA当未来冻结批准。

## 2. Q1–Q8明确决定与理由

| 问题 | 决定 | 静态依据与剩余工作 |
|---|---|---|
| Q1 冻结身份 | **接受C＋F，无需给冻结配置/manifest新增freeze_commit。分析须核验两者。**许可6文件合适；端点差异，不是要求每个中间提交没有临时改动 | provenance.py::freeze_state、prereg.py::finalize/final_eval_preflight、seal.py::run_problems已有C/F关系；prereg_analysis.py::validate_inputs尚未核验F/Git。补核心seal.protocol_evidence、分析C/F校验。F/manifest自身hash外部记录，早于训练，不自引用；运行F固定，不能事后换文档后代 |
| Q2 方差路径 | **接受精确Fraction均值/方差，再float64开方；撤回math.fsum可选路径。**成绩出现前锁定 | prereg_analysis.py::vec_stats已有Fraction；math.sqrt(Fraction)的隐式float与规格显式sqrt(float(V))一致。保留全部F1–F8数字/容差/标签，不承诺旧浮点路径对任意输入位级相同 |
| Q3 错误顺序 | **接受现实现：全局1–4；CSV run→last/best/hard，每文件依次5–7。** | validate_inputs/check_run_documents/check_records的分层与此相符；规格§2.3消除歧义。不是全体先5再6。补双错误优先级测试即可，原代码不必改 |
| Q4 非整数score | **确认有限非整数为E_SCORE_RANGE** | check_records已如此；100.0允许并转整数；bool/字符串E_FIELD_TYPE；NaN/Inf/溢出数字第3解析阶段E_NONFINITE |
| Q5 B1/B2差异 | **接受meta.git_sha=F、U=A≠g且不核explore_mask、续训不写完整诊断。开关不加冻结配置字段。** | dqn.train与WindowRecorder当前接线可支持这些定义（静态）。采用写F清单/外部冻结记录/固定命令30/30开，并按辅助seal核验。缺点是CLI遗漏不能由配置schema自动防住，不能宣称全自动强制。独立辅助seal须核验F/冻结代码hash；−10硬编码仅在环境合同测试通过时接受，不允许不检验奖励常数对应 |
| Q6 封存/证据 | **采用协议护栏措辞与分级证据，现README/RESEARCH_LOG/PLAN核心封存文字一致。** | prereg.py::final_eval说明低层API可绕；RESEARCH_LOG规则4、PLAN偏差9及README/prereg说明限默认入口。执行历史/次数/未提前读test仍靠协议记录；done(code)、执行者报告、GPT静态、本人运行、人类签核分开。旧资源/采用状态与Fraction待定文字需更新 |
| Q7 评估环境文件 | **接受独立文件、评估meta不改；当前还缺机器标识与封存hash关联。** | prereg.py::save_final_eval_environment有UTC/device/software/code_version/preflight，缺machine_id；seal.py::build_evaluation_seal未绑定它。加匿名machine_id并在seal.protocol_evidence绑定path/hash，分析核验。OS/驱动/电源/TF32说明仍本地留证；别名不证明真实硬件 |
| Q8 文件/版本 | **接受内部修订1，保留固定三个文件名、冻结配置名及spec_version=0.3.2。** | 无需更新固定名称常量；F的哈希锁定实际新文本。冻结后不能借版本不变静默替换。下载只用唯一外层包/目录 |

不同意直接保留的两点：核心分析只核C而不核F不够；最终环境记录没有machine_id/hash绑定不能称完整机器身份封存证据。诊断记录meta为F本身合理，但辅助封存忽略code_sha256核验也不够。以上都列为最后一轮小修，不改变算法或核心统计。

## 3. 一轮代码/测试修订范围

以同包完整 CODE_IMPACT_v0.3.2_r1.md（C1–C7/T1–T2/D1–D2）为唯一剩余代码/测试范围。重点是元数据/冻结核验，不改训练target、探索/回放、H1/H2、矩阵、score分析公式、RNG、t/type7或种子。

1. seal-eval生成protocol_evidence（C/F、独立环境path/hash），从当前已核验30运行和final-eval预检取值；final_eval_environment补匿名machine_id。核心files精确集合与prereg-eval-1 meta保持。
2. formal分析在成绩统计前核验C/F和当前HEAD/Git关系、machine_id/CPU1线程、环境hash与冻结文件/实际脚本；输出同一溯源字段。使用stdlib Git查询，不导入训练/Torch；synthetic原fixture不需要真机器/Git，新formal测试用throwaway Git＋完整合成结果。
3. 冻结manifest/正式分析明确包含方案/规格/交接/FREEZE_CHECKLIST/两份诊断代码/依赖的实际哈希；可继续extra-frozen接口，不另起文件名或配置字段。F允许集合仍只6个文件，matrix不入。
4. 辅助window_diagnostics_summary的seal/summarize增加显式--freeze-manifest/--freeze-commit，核验每份diag的F、真实emit标志、冻结诊断代码hash及seal中保存的hash。封存与汇总两端都检查；只保存当前代码hash不等于冻结核验。错误只影响辅助输出，不能增加核心run_problems对diag的依赖。
5. 测试补正式C/F与环境证据、跨文件错误顺序、辅助F/hash拒绝、独立−10奖励分量合同；复用已完整实现的手算/非零best fixture，不为了编号新增镜像测试。新增断言从独立定义推导，不能调用被测实现生成期望。

6. R1：formal run/final-eval 共用完整冻结绑定检查，启动/许可签发前核验 manifest 存在且正式 complete、C 一致、所有必需/额外文件实际 hash、三个配置主 hash；生成 manifest 不要求先有有效旧 manifest。反例不得调用训练/测试，保留非零 CLI 和接线证据。
7. R2：`.gitattributes` 随 C 提交并入 frozen_files，全部冻结文件 -text；hash 唯一对象为原始工作树字节。matrix 既定 blob 不变。临时 Git 的 autocrlf 双设置/字面 LF–CRLF fixture 验收，以及正式机全新 F 克隆逐文件验收。
8. R3：完整运行快照固定 `docs/prereg/dependency_lock.txt`，由本地 A1000 被验收环境生成并交云端随 C 提交，F 不得添/改；现有 dependency_lock_sha256 指它，分析 NumPy 文件另冻。拒绝错误路径/非精确格式/顶层缺项；逐包完整性依本地来源记录。

Q2/Q3/Q4所选行为已经实现，不要求重写方差/记录循环；Markdown摘要列固定且完整JSON保留全部B1/B2指标，接受现有取列，无需重复展示16率。语义或主流程变更如超出此清单，应显式报告理由，不悄悄扩大本轮。

## 4. 文档、清单与证据更新

三份完整文本代替旧文件，以下清单/README/日志表述同步：

- FREEZE_CHECKLIST的P1-02“待修复”已过期：当前seal.run_problems/current_material_problems重读summary/train_log的机制已存在；状态写done(code)，列当前测试与执行者证据，实际冻前清单仍open。
- 分析F2–F6逐项断言不足旧partial已过期：test_prereg_analysis_expected.py已有完整m/效应/率/步数及非零best配对预期。可改done(code)，人类复核保持open；新增本修订身份测试尚不算已通过。
- B1/B2“GPU未测、采用待定”改为“本地A1000报告过门槛、所有者已决定30/30开启；最终候选重测/完整冻结待做”。RESEARCH_LOG相应实现行仍写GPU未测，要同步，不把人类冻结批准代填。
- Fraction“待决定”改为已定唯一路径；误把done(code)等同独立审计的文字继续收紧。
- hard_enabled首个正式训练前冻结，不只解封前；最终CPU同机/1线程，CPU评估并行方案提前记录；无成绩选机/调参。
- 增补最终分析C/F、独立机器环境hash、B1/B2固定命令及辅助F/代码hash核验；外部时间戳/manifest自身hash/一次正式分析执行记录明确。
- 原冻结清单差额完整保留：人类论文原文核对；与旧阶段环境/配方差异；全软件/命令/设备/TF32/determinism；正式15对仅构造＋target副本；checkpoint往返；计数/资源/失败管理；tiny覆盖范围；旧局限限定历史；变异6/4/2分开；quick真实updates、load与正式val/ε差异；VRAM统计单位及系统内存；整轮长时稳定未证实。

**冻结前彩排的已披露事实（所有者提供，本轮 GPT 未独立运行核实）：**本地执行者曾在一次性克隆的流程彩排中，真实启动正式训练种子块 100 的 `res4, n=1` 若干次，每次至多约 75 秒；其中一次到过第一个验证点，在 `prereg_val` 上做过一次早期模型验证。产物位于一次性目录，不并入本轮正式 30 次运行，不复用其权重、checkpoint 或日志，也不用于选择算法、超参数、模型、机器或正式尝试。这里“正式运行”专指本节冻结门槛完成、所有者批准后的运行，不声称此前从未启动过这些种子。该验证属于可用于选模的 prereg_val 分区，不能据此声称读过封存测试集；本轮 GPT 也未核实封存测试的完整访问历史。历史彩排的次数、命令、开始/结束时间、已知步数和验证情况应按可获得记录归档，未知项标未知；不能补造日志或把已删的一次性产物写成仍可复核。不得因这次披露改变矩阵、种子或 H1/H2；后续护栏彩排用合成材料/调用 spy，避免再真实启动正式种子作 smoke。

外部 FREEZE_RECORD、GitHub 原资产/第三方时间/下载 hash 回执及首个启动日志必须先于批准后的正式启动；可以 draft，不声称已公开注册。实际最终评估环境另存后期回执，不覆盖开跑前材料。具体最小字段和路径直接列于方案§7.2.1与规格§1.2.2。

截至6023b1a基准冻结配置的9个null：hard_enabled、code_commit、machine_id、worker_count，to_fill_at_freeze.analysis_script_sha256/preregistration_document_sha256/dependency_lock_sha256/driver_and_os_note/power_and_sleep_settings_confirmed。其它种子/超参已填、status=draft。全部待填与方案§7.4对应。machine_id用匿名别名，worker_count=2；不要加B1开关字段。review人/日期/内容/批准在外部记录或F清单，由人填写。

## 5. 冻结当天操作顺序与交接责任

这是一页执行分工，**不是已执行回执，也不是开跑批准**。角色：云端＝实现/测试作者；本地执行者＝A1000 操作者；所有者＝研究责任人、冻结批准与外部记录保存者。角色由实际人员认领，不假定另一个 AI 代签或某步已经完成。若前置验收需跨日，照顺序执行，不为赶“当天”跳步骤。

| 顺序 / 时点 | 负责角色 | 做什么及交给下一角色的证据 |
|---|---|---|
| 1，形成 C 之前 | 云端 | 完成 C1–C7/T1–T2/D1–D2 的代码、测试与常规文档；设置并验收 -text，保留矩阵原 blob；只用合成数据验收分析/护栏。交候选 SHA、测试命令/原输出、差异清单。 |
| 2，候选验收之后、最终 C 之前 | 本地执行者 | 在 A1000/2 worker 验收候选资源、初始化 15 对、保存/读取与 CPU 评估，按方案记录所有架构/正式预算负担；不读封存测试，不用分数选配方。用被验收解释器生成精确 `docs/prereg/dependency_lock.txt`，交生成命令、Python/pip、匿名机器、候选 SHA、逐包核对及资源记录；锁内不含本机路径。 |
| 3，依赖快照交接后 | 云端 | 集成依赖快照、.gitattributes、代码/测试/README 等为最终 C；核对快照确实在 C、matrix 未变；确认最后改动是否需重做步骤 2。将完整 C 和接收的证据交所有者/本地执行者；不能替本地生成 GPU 环境锁。 |
| 4，准备 F 之前 | 所有者＋本地执行者 | 所有者核对设计及人类 oracle/数学/文献复核状态、历史彩排披露；本地填写实际机器/软件/电源。锁定 hard、2 worker、30/30 诊断命令、CPU/1 线程和评估并行安排。人工签核缺项保持 open，不由 AI 代填。 |
| 5，C 固定后 | 本地执行者准备，云端可检查 | 填 C 与三个实际 hash；先定三份集成文本/清单，再算配置 hash、生成 complete manifest。不要使 manifest hash 自引用。只提交 6 个许可材料得到 F，依赖快照和属性文件不得到 F 才添加/修改。交完整 C/F、manifest 与文件 hash；此时还不能训练。 |
| 6，F 形成之后 | 本地执行者 | 在正式 Windows/A1000 **全新克隆准确 F**，验证 clean/C→F、有效 -text、每个冻结文件的 blob/工作树/hash、manifest 自身 hash、配置三主 hash、两个入口的预检接线。只做预检，不启动训练。交无本机路径的逐文件验收记录；失败返回候选修复，不现场改 hash 放行。 |
| 7，全新克隆通过后、开跑前 | 所有者 | 审阅并批准该 C/F；保存 FREEZE_RECORD 至约定 GitHub Release 原资产（可 draft），校验 tag 指 F，取得服务器 created_at/原资产 ID/下载字节 hash 回执；仓库外 `freeze_records/<F>/` 归档。把批准、外部 F/manifest hash 和回执交本地执行者。无人负责上传或未取得真实回执时不得假定这步完成。 |
| 8，收到批准及回执之后 | 本地执行者 | 再核对 HEAD=外部 F、manifest/记录 hash、时钟和全部预检；保存首个任务启动 UTC、资产 ID、原 CLI 输出。按 matrix 固定顺序启动 30 个 fresh 运行、2 worker、全部开诊断；彩排产物不复用。先存后启动，程序不需要联网。 |
| 9，30 个运行全部完成之后 | 本地执行者 | 重读完整性材料并通过解封门槛；final-eval 再执行绑定预检，集中 CPU/1 线程评估；保存实际环境文件、核心/辅助封存及另行 FINAL_EVAL_RECEIPT。冻结分析集中一次，保留失败/恢复记录；不覆盖开跑前外部记录。 |

每次交接须接收方明确核对“提交/文件 hash、证据范围、未完成项”；资源、人工签核、外部存储或 fresh-clone 任一缺失均不得开跑。Git 日期、自填 UTC 与文件 mtime 单独不证明先后；第三方存储时间只证明那些字节已存在，历史运行仍靠执行记录。既有 seed100/res4/n1 短彩排及一次 prereg_val 验证已单独披露，不计正式尝试。细节唯一以方案§7及规格§1为准。

快照和 `.gitattributes` 固定在 C 中，三份集成文档及其配置/manifest/清单只在 F 的许可集合中。若最后改动影响采集接线/记录器或运行环境，先回本地重做对拍/开销和资源验收；仅 seal/汇总/文档改动可以保留来源清楚的已有开销记录，但不免除候选资源/正式机克隆门槛。完整人类原文核对/数学复核/批准不能被“云端已测试”代替。

本交接不是正式开跑许可；只有所有者在步骤7明确批准，且执行者核验收到真实回执后才能开始步骤8。

## 6. 资源、未来研究与文献的保留决策

正式训练规划A1000 2worker约11–16h，CPU必需18000模型回合约1–2h量级非上限，可选hard9000另计；cnn2/res4满回放正式负担未测，以冻结候选重测为准。ABBA短load墙钟中位off1104.25s/on1098.30s，约−0.54%；进程训练时间−0.6%，工作集+1.5MB；都是执行者数据的算术转述，不能称GPT GPU实验或提速。

未来A1–A7、每格20seed预算起点（12为探索下限、40或更多依功效算）、百万前缀复用/固定120k绝对ε日程及百万种子guard重审保留完整在方案§12。旧5seed的σ估计不稳定，20不保证H2支持或反驳；不可用更多测试局替代训练seed。最新短开销不改变未来机制预测，不改变本轮5seed。

方案§9保留全文/摘要/二手的来源等级以及GPT本人前轮实现核验范围；本轮未重读原论文/教材，不升级消融数字、公式页码、Fedus方差二手线索为独立核实。所有者/导师亲读并记录核对人仍是冻前待办；有限检索不判断新意。

## 7. 本轮没有验证的事项

- 没有运行pytest415项、acceptance/check_acceptance、GPU smoke、off/on权重比较、真实Git集成fixture或源代码撤销变异；全部实际结果来自执行者附件。4个skip未算执行通过。
- 没有重算旧实验score、读取真实本轮test、正式30运行或解读H1/H2。静态检查matrix/hash和Git对象差异不等于训练验收。
- 没有取得并逐条复核原始smoke报告/系统采样/每个哈希日志；ABBA时间/峰值来自汇总，算术可核对但字段的采样时点/长期代表性不能确认。
- 没有实测cnn2/res4满回放、正式15×50耗时、长时campaign稳定性、同时写盘峰值、完整18000 CPU回合、最终15对正式初始化或B机兼容性/吞吐。
- 没有重读论文全文/书章、核对消融53/57/公式位置/页码/二手机制，也未做系统文献检索或新意判断。
- 未证明历史上未提前读封存seed或从未多次分析；护栏存在不能证明执行历史。没有人类oracle/分析/文献签核或冻结批准。
- 新增protocol_evidence、分析F核验、machine_id/hash绑定、辅助F/代码hash检查、R1绑定/-text/完整锁及本修订测试在6023b1a基准尚未齐，不能标已通过；最终修订需执行者用合成材料实际验收。
- 本轮是合并规范与关键接口静态核查，不是完整全仓第三轮行为/隐私审计；未做全历史作者/隐私扫描。附件的noreply/零隐私命中只作来源记录。

## 8. 相对修订1的集成变更清单

| 变更 | 是否改变核心设计 | 是否要求代码/测试再改 | 位置 |
|---|---|---|---|
| R1：两个入口完整冻结绑定与拒绝时点 | 否 | 是，C5 | 方案§7.1.1/7.2；规格§1.2.1/8.6.1 |
| R2：原始工作树字节、-text、冻结机器全新检出验收 | 否 | 是，C6 | 方案§7.1.3/7.4；规格§1.1.1–1.1.2/8.6.2 |
| R3：固定完整运行依赖快照、随 C 提交及唯一字段对应 | 否 | 是，C7 | 方案§7.1.4；规格§1.1.3/2.1 |
| 外部冻结记录、第三方回执和实际启动顺序 | 否 | C5 记录接线；D2 流程/清单 | 方案§7.2.1；规格§1.2.2/7 |
| 披露 seed100/res4/n1 短彩排及一次早期 prereg_val 验证 | 否 | 无算法改动；D2 文档/归档 | 方案§7.4；交接§4/5 |
| matrix blob 为原既定字节，-text 覆盖且不重定义期望 hash | 否 | C6 已涵盖，不增条目 | 方案§7.1.3/10；规格§1.1.1 |
| 按角色与时点固定冻结当天交接 | 否 | D2 已涵盖，不增条目 | 方案§7.5；交接§5；操作顺序单页 |

所有约定已经写入完整方案/规格/本交接，无需另读补丁。C1–C4/T1–T2/D1 原条目保留；新增只为 C5–C7/D2。没有新训练超参、配置字段、统计路径、种子、文件名或 spec_version。

## 9. DSH 字面修正登记（r2）

本次仅登记已核对的文档补丁：分析规格§4.1以既定float64 t常数为准，删除不准确的长十进制串；§8.2修正F4区间末位并明确1e-12容差，§8.3说明F7/分位数fixture的同一容差；§1.1.1/8.6明确formal合成fixture复制真实matrix.csv原始字节；方案§1补充H1支持门槛随种子间sd变化的说明。代码影响清单：**无新增**。不改设计、矩阵、统计、种子、固定文件名或spec_version。

三份文档的实际字节已变化，冻结前提交F之前统一重算SHA-256并更新配置/manifest绑定；matrix.csv仍为既定字节和既定哈希。DSH盲复现数值/标签一致为所有者提供的记录，本次GPT没有运行DSH或仓库实现、没有独立确认其高精度求根。除上述补丁、文内修订标记与本登记外，其余文字逐字保持当前最终集成版不变。
