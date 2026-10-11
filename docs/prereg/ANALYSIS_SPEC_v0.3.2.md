# 架构 × n-step：完整分析规格 v0.3.2（修订1+彩排追加A+DSH 字面修正）

**状态：待冻结；本文件为完整实现合同，不是冻结批准或真实结果报告。日期2026-10-10。**主体在6023b1a已有实现；本轮为文档集成，没有运行仓库代码，也没有重新核验当前 main。新门槛以最终实现/本地验收为准，不据此声称已通过。版本/固定文件名保持0.3.2，内容由修订号及实际哈希区分。配套方案为 PREREG_ARCH_NSTEP_v0.3.2.md。实现者无需依赖聊天解释；本规格只细化原统计方法，不改变 H1/H2、30 次矩阵或 last@300k 主要终点。


相对原文：§1新增非自引用C/F及独立机器证据绑定；§2.3消除跨文件顺序歧义并确认非整数有限score错误码；§3唯一Fraction路径；§7补溯源字段；§8保留全部字面预期并增加身份/顺序/非零best用例；§9为已采用B1/B2的独立描述分析合同。H1/H2、矩阵、终点、所有统计规则/随机流/阈值不变。彩排 R1–R3 已直接集成：§1.1固定原始字节、-text、全新克隆与依赖快照；§1.2固定训练/最终评估绑定和外部记录；§8.6补独立验收。新增需改代码之处见完整 CODE_IMPACT_v0.3.2_r1.md（C1–C7/T1–T2/D1–D2）；本文件约束最终实现，不声称6023b1a已全部满足。

## 1. 执行边界与文件位置

预注册材料进入仓库 docs/prereg/；运行产物进入 results_prereg/。本轮交付在仓库外生成文档，未修改仓库。目标位置：

~~~text
docs/prereg/
  PREREG_ARCH_NSTEP_v0.3.2.md
  ANALYSIS_SPEC_v0.3.2.md
  CLAUDE_HANDOFF_v0.3.2.md
  matrix.csv
  dependency_lock.txt        # 完整运行环境版本快照，随 C 提交
  frozen_config_v0.3.2.json
  freeze_manifest.json
results_prereg/
  runs/<run_name>/
    config.json
    summary.json
    last/standard.json
    best/standard.json
    last/hard.json          # 可选；全30个一起启用或一起省略
  final_eval_environment.json   # 独立机器/执行身份，protocol_evidence绑定哈希
  window_diagnostics_seal.json # 辅助封存，与核心files集合分开
  window_diagnostics_summary/  # 次要描述汇总
  analysis/<analysis_id>/
    REPORT.md
    analysis.json
    bootstrap_indices.sha256
    bootstrap_replicates.csv
    input_manifest.json
~~~

分析脚本自身的路径、文件 SHA-256、依赖锁文件和命令在 freeze_manifest.json 中冻结。CLI 至少支持：

~~~text
analyze --mode synthetic --manifest <合成manifest> --input-root <合成目录> --output-dir <新目录>
analyze --mode formal --manifest docs/prereg/freeze_manifest.json --input-root results_prereg/runs --output-dir results_prereg/analysis/<analysis_id>
~~~

不得提供自动扫描旧 results/、results_gpu/ 的后备路径，不得加载 .pt、训练成绩或验证逐局数据来选择分析。冻结前只用合成数据；禁止读取任何真实实验结果，包括旧结果。synthetic 模式要求 manifest.synthetic=true，且每个评估文件有 meta.synthetic=true；正式模式要求二者 false，冻结记录 complete=true，30 个训练的完成/配置/checkpoint 核验记录均通过。路径由 manifest 显式给定，不能把真实数据目录自动当合成目录。

正式流程：先完成合成验收和代码冻结，再完成全矩阵，集中测试并封存全体输出，然后一次性运行冻结的分析，所有预定表一起生成。不得逐个看结果后改脚本或挑指标。若完整性检查失败，不生成统计报告；保留失败日志，只允许修复客观文件/评估基础设施问题后以原权重、原协议执行，记录尝试和输入哈希。这不授权改训练或反复分析寻找有利结果。

### 1.1 冻结与封存清单的最小格式

所有路径从显式 root 解析，不依赖工作目录猜测。正式 freeze_manifest.json 最少如下；所有哈希填写实际64位小写十六进制值，不允许占位符正式运行：

~~~json
{
  "schema_version":"prereg-freeze-1",
  "synthetic":false,
  "complete":true,
  "spec_version":"0.3.2",
  "code_commit":"<40位完整提交>",
  "project_root":".",
  "matrix_path":"docs/prereg/matrix.csv",
  "config_path":"docs/prereg/frozen_config_v0.3.2.json",
  "analysis_script_path":"<冻结的分析脚本相对项目根目录路径>",
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
    "<分析脚本路径>":"<sha256>",
    "docs/prereg/dependency_lock.txt":"<sha256>",
    "python/scripts/prereg_analysis.requirements.txt":"<sha256>",
    ".gitattributes":"<sha256>"
  },
  "seal_path":"results_prereg/evaluation_seal.json"
}
~~~

complete=true表示生成器完成结构/机器条件校验，不表示人类签核完成，也不表示已经有训练/测试结果；正式开跑仍须外部冻结记录证明全部门槛通过；freeze_manifest 自身哈希由外部冻结记录保存，避免自我引用。合成manifest用synthetic=true，其root/paths指合成fixture材料，schema与数值约束保持相同；合成code_commit和权重哈希可以是假身份，但须满足格式及跨文件一致性。

测试完成后 evaluation_seal.json 最少包含 schema_version="prereg-seal-1"、synthetic（与模式一致）、freeze_manifest_sha256、all_training_complete=true、all_checkpoint_checks_passed=true、runs（CSV顺序的30个run_name）、files（所有必需config/summary/评估文件的run根目录相对路径→实际sha256）、attempts（逐run的客观失败及重跑记录数组，零故障可为空数组）。seal文件自身SHA写入分析溯源。分析器必须验证files恰含本次声明必需的文件集合；未声明hard不纳入集合。不可只信两个true而不核对各run预算/配置/检查点/评估身份。

冻前分析合成材料也有对应合成seal；畸形用例只改目标文件，并重算合成seal中该文件哈希。CLI输入root必须与seal相对路径解析一致。有效配置sha字段只指冻结配置文件的哈希，不在config.json内嵌它自身哈希。

#### 1.1.1 唯一哈希对象与跨平台字节规则（R2）

**本轮唯一哈希对象是文件在工作树中的原始字节，算法SHA-256。**读取二进制字节，不统一LF、不剥BOM、不重新序列化JSON、不忽略末尾换行/空格；同样内容不同换行就是不同文件。freeze_manifest本身、依赖快照、全部文档/脚本/矩阵均按此规则。Git对象ID不是这里的SHA-256。

选择仓库.gitattributes对被冻结哈希的文件设置**-text**，禁止Git的文本换行清理/检出转换。它随代码C提交，不在F许可6文件集合；其实际字节也进入manifest.frozen_files。正式机器无须把个人全局core.autocrlf设为false才能通过。

可用下述项目规则覆盖当前文件；任何新增extra-frozen路径必须在冻结前确认也有-text规则：

~~~gitattributes
/.gitattributes -text
/docs/prereg/** -text
/python/**/*.py -text
/python/*requirements*.txt -text
/python/scripts/*requirements*.txt -text
~~~

规则覆盖固定matrix、配置、manifest、方案/规格/交接/清单、docs/prereg/dependency_lock.txt、实际分析/诊断脚本与现有requirements文件。不是把所有仓库实验数据都重新处理；results/、results_gpu/与matrix.csv现有字节不改。-text不是binary别名，普通文本仍可审阅。

**理由：**当前协议已锁定matrix.csv的CRLF字节与哈希；对全体文件强制LF或git add --renormalize会可能改变矩阵并违反不变约束。-text使“实际字节→哈希→检出同字节”保持直接一致，也与现实现读取工作树文件的方式相同。统一LF方案原则上可行，但必须对matrix单独保留字节并重算其它材料，增加额外迁移；本轮不采用两套方案供事后选择。

-text只约束后续Git转换，**不会自动还原已经被检出成CRLF的旧工作树**。在C之前核对要提交的实际字节与预期blob；不要对matrix做全仓规范化。F上每个被冻结文件的原始Git blob字节SHA-256须等于记录的工作树SHA-256，以确认同F跨平台检出会得到同字节；这是字节一致性验收，不把运行时改成另一条blob哈希路径。

**matrix.csv 的唯一字节身份：**F 中 `docs/prereg/matrix.csv` 的 Git blob 必须就是已约定、SHA-256 为 `5cbd4e7b2cf79f65c96180acfc61b1914fe2e8521c036218bc7c9a4db59f0dfe` 的原始字节（包括既有 CRLF 行尾）。这是既定输入，不是冻结当天重新生成或重新定义的矩阵。`/docs/prereg/** -text` 已覆盖 matrix.csv；应以 `git check-attr text -- docs/prereg/matrix.csv` 的有效结果为 `unset` 验收。Git 不对该文件做文本换行转换，检出后工作树字节必须与同 F 的 blob 完全一致。不得重写 CSV、改变排序/编码/行尾或执行针对它的 renormalize；不得把新算出的其它值改成“新的期望哈希”。冻结/运行/分析仍可且必须重算**实际** SHA-256 来验证它等于上述既定值；这叫完整性核验，不是重算或修订协议中的矩阵哈希。若不一致，停止并恢复既定 blob，而非接受新值。

formal 身份验收的临时 Git 仓库必须复制真实 `matrix.csv` 的原始字节，其 SHA-256 必须等于既定 `5cbd4e7b2cf79f65c96180acfc61b1914fe2e8521c036218bc7c9a4db59f0dfe`。不得重新序列化 CSV 或转换行尾。运行、机器和评估记录仍使用合成 fixture，不读取真实成绩；“合成”不豁免 formal 模式的固定矩阵哈希检查。synthetic 模式合同不因本条改变。

#### 1.1.2 正式冻结机器全新克隆验收

F形成后、外部记录批准和首个正式运行前：在正式A1000/Windows上**全新克隆F并切到准确F**，不得先用旧工作树手动换行再称新克隆通过；逐项重算frozen_files全部SHA-256并与manifest一致，再重算manifest自身SHA-256与准备记录一致。记录F、匿名machine_id、Git版本、core.autocrlf状态、受控路径的有效text属性、逐文件expected/actual及整体通过状态；不记录绝对克隆路径。

一项不一致就停止冻结，不在现场自动“更新成当前hash”。先诊断字节差异、修复C候选并重新生成F/清单、重新全新克隆验收。不得因为matrix碰巧一致而跳过其它文件。

追加自动验收：临时Git仓库同时放LF文档/脚本/依赖及CRLF矩阵字面fixture，设置-text后提交；用core.autocrlf=true及false分别全新检出，逐文件字节与已提交blob/清单完全相同。矩阵expected使用原字面CRLF字节，不能用“规范化后”值生成oracle。可在Linux以Git设置模拟此转换，但**正式Windows全新克隆仍须本地执行者实际做**，GPT本轮没有运行。

#### 1.1.3 完整运行依赖快照（R3）

完整训练/验证/最终评估Python环境的精确版本快照固定为：

~~~text
docs/prereg/dependency_lock.txt
~~~

由**本地执行者**在正式A1000上、使用经过候选版本smoke/资源验收的训练与最终评估Python环境生成；云端实现者检查格式/字段接线并将它与代码及.gitattributes一起纳入**代码提交C**。人类研究者核对环境来源与验收记录；AI不代签。生成时点在最终C形成前，F不添加、不更新这个文件。它不加入FREEZE_MATERIALS，许可集合仍为原6文件。

来源为该环境的python -m pip freeze --all；选择的interpreter确为被验收环境，不从另一个云端CPU环境代生成A1000快照。记录生成命令（不含本机绝对路径）、UTC、Python/pip版本、匿名machine_id与候选代码SHA。不得为了填锁文件而隐含升级软件；环境变化需重新验收，再生成锁/形成新C。

提交快照采用UTF-8无BOM、LF、固定排序的name==exact_version条目，保留版本的本地构建后缀（例如+cu…）；最终SHA按实际提交字节，不按未经排序的原stdout。pip freeze中若有editable、本机file URL、私人仓库/token或不确定版本，须在冻结前解决并记录来源，不能直接公开，也不能静默删除真实依赖。**仅仓库自身的editable项目条目可排除**，因为代码已由C/F锁定；排除包名与理由写生成记录，不能推广为排除其它本地依赖。生成记录/原始stdout可由执行者私下保存，提交快照和外部记录不含本机路径或凭据。

这种快照锁定已安装Python包的精确版本，**不是含所有wheel哈希与下载源的完整跨平台解析锁**。Python解释器、CUDA运行时/驱动、OS、硬件和数值开关另在环境证据记录；不能称有pip freeze就可跨机器位级复现。候选环境按快照重建/核对后仍须验收。本轮保持当前已验收软件，不因规范文字选择更“新”的版本。

| 材料 / 字段 | 绑定对象 |
|---|---|
| manifest.dependency_lock_path | 固定docs/prereg/dependency_lock.txt |
| manifest.frozen_files[该路径] | 完整运行依赖快照实际SHA-256 |
| frozen_config.to_fill_at_freeze.dependency_lock_sha256 | 与上一项相同，不指NumPy单文件 |
| manifest.frozen_files[python/scripts/prereg_analysis.requirements.txt] | 已有分析依赖文件单独的实际SHA-256 |

python/requirements.txt中的>=只是安装需求，不替代运行依赖快照。python/scripts/prereg_analysis.requirements.txt继续保留现有NumPy固定版本及分析用途，随C锁定、作为额外必需冻结文件；**不得拿它填完整运行依赖快照字段**。两者各有用途，不新增第二个配置哈希字段。若正式分析使用独立环境，须在C之前准备并核验既定NumPy版本/随机流，记录其Python/pip版本及用途；不能运行后才选择分析环境。

冻结生成器/运行与最终评估绑定检查拒绝错误dependency_lock_path；核对快照在C的Git树中已经存在，F的同文件blob不变，工作树hash与清单一致。精确条目至少覆盖现有安装需求中的numpy、torch、matplotlib、pytest；缺少这些顶层依赖或含>=等非精确条目拒绝。这个最低检查不替代与被验收环境逐包核对完整性。依赖锁不能在F才新增，即使位于docs/prereg/，也不属于那6个许可文件。分析仍以manifest映射读文件，原统计方法不变。

验收：快照在C提交、F只改许可文件可通过；F才新增/修改快照拒绝；以>=安装文件或仅NumPy文件冒充完整快照拒绝。格式校验可拒绝非精确条目，但不能仅凭一个文件名或几条固定版本证明“完整”，其与被验收环境pip freeze的逐包对应由本地生成/核对记录支持。

### 1.2 C/F身份、机器证据与协议封存（唯一正式路径）

**C是代码提交，F是唯一冻结/执行提交；不在F所包含的frozen_config或freeze_manifest内新增freeze_commit字段。**配置、manifest、config及评估meta中的code_commit均指C。run_complete记录C与F；code_version.git_sha及诊断meta.git_sha记录F。F和manifest自身哈希由仓库外、早于首个训练的带时间戳冻结记录保存，人类批准另存。正式分析不能凭complete=true推定有人类签核。

生成F只允许C→F两个端点的差异位于以下6文件：docs/prereg/{frozen_config_v0.3.2.json,freeze_manifest.json,PREREG_ARCH_NSTEP_v0.3.2.md,ANALYSIS_SPEC_v0.3.2.md,CLAUDE_HANDOFF_v0.3.2.md,FREEZE_CHECKLIST.md}。矩阵、python树与依赖锁不许改变。后续任意文档提交不是自动获准的新F。

freeze_manifest.frozen_files至少锁定矩阵、配置、方案、规格、交接、FREEZE_CHECKLIST、分析脚本、docs/prereg/dependency_lock.txt、python/scripts/prereg_analysis.requirements.txt、.gitattributes、python/pacman_rl/window_diag.py、python/scripts/window_diagnostics_summary.py。F不用自包含自己的SHA；manifest自身SHA从外部记录/评估seal核对。准备阶段允许dirty许可材料不延伸到训练、评估和正式分析。

project_root可为“.”；CLI必须显式传--project-root（实际项目根目录），从该root解析manifest中的路径。绝对机器路径不提交；正式机器和软件通过匿名machine_id及环境记录关联。

**最终评估独立文件合同：**results_prereg/final_eval_environment.json保留现有utc、evaluation_device、environment、code_version、preflight，增加顶层machine_id（与冻结配置相等的非空匿名字符串）。environment.torch_threads必须1，evaluation_device和environment.device_type必须cpu。code_version.git_sha=F、git_dirty=false；preflight.head=preflight.freeze_commit_of_runs=F、preflight.code_commit=C。环境软件/数值开关保留实际值；CPU/GPU型号/OS/驱动/TF32/电源等缺自动字段由冻结环境说明补充，不把machine_id当自动硬件认证。现有prereg-eval-1 meta合同不变。

**evaluation_seal新增顶层溯源对象，不改变核心files恰含集合：**

~~~json
"protocol_evidence": {
  "code_commit":"<C的40位SHA>",
  "freeze_commit":"<F的40位SHA>",
  "final_eval_environment": {
    "path":"results_prereg/final_eval_environment.json",
    "sha256":"<独立环境文件实际64位SHA-256>"
  }
}
~~~

protocol_evidence由封存生产者从已经重新核验的30个run_complete身份及评估预检提取，必须一致C/F，不能手工填一个任意F。封存生产者拒绝缺环境文件、错误machine_id/CPU/线程/C/F、已跟踪dirty及当前材料漂移；生成实际环境文件哈希。诊断文件不进入这个对象或核心files。

**正式分析第1阶段增加以下校验，全部早于成绩统计：**

1. protocol_evidence存在且C/F格式有效；C与冻结manifest/config相同；独立环境文件存在/解析/哈希一致，其上述身份、机器、设备/线程都一致。
2. 当前项目是真实Git仓库且HEAD=F；C是仓库提交并为F祖先；C:python与F:python树对象相同；git diff C F端点路径集合包含于许可6文件；已跟踪工作树干净。任何Git调用不可用/超时/关系失败都拒绝正式分析，不静默退回只比文件哈希。分析器可用stdlib subprocess读取Git，不导入训练模块/Torch。
3. 当前实际分析脚本、全部冻结文件实际字节哈希与manifest一致；冻结材料在F中的字节身份须一致，外部冻结记录由操作者核对F及manifest哈希/早于训练的时间。脚本不能技术上证明文件历史上从未被提前读过；那是协议与执行记录事项。
4. C/F及环境证据写入analysis.json.provenance和REPORT/input_manifest来源索引。分析不重新读取.pt或验证逐局分数；封存生产者负责训练材料和checkpoint的当前完整性，分析核验seal绑定身份与自己需要的config/summary/评估记录。

新增检查错误：缺文件E_MISSING_FILE；实际哈希不符E_HASH_MISMATCH；环境/身份/Git关系或缺protocol_evidence为E_MANIFEST；非法JSON/重复key/全树非有限数仍归原解析码。不能用try/except吞掉基础设施错误继续算。

synthetic模式不需要真实机器或Git仓库，不读真实结果；原F1–F8/E1–E13仍可用旧合成最小seal，不强求新增正式protocol_evidence。新正式身份fixture使用临时Git仓库、假机器记录和完整合成成绩；通过/失败门槛须从公开formal入口或实际helper接线验证，不能把allow_unfrozen当正式验收。

一次正式运行及恢复规则保持§1：核心输入合法后集中一次分析；输出失败可在同权重/协议/冻结代码下修客观文件基础设施，留失败日志/哈希。目录防覆盖不是不可绕过的一次性安全保证；底层API、公开种子常量或源码可以绕过协议护栏。训练/选模禁读封存分区，正式解封前重新核验全体当前材料；“本人静态复核、执行者报告、done(code)、本人运行、人类签核”分开，不把同一个AI实现＋写测试称独立人员审计。

#### 1.2.1 训练和最终评估的共同绑定预检（R1）

保留C/F关系、许可6文件、clean工作树、固定参数/机器/worker、环境变量及matrix检查；**另外，训练运行前与最终评估前都必须调用同一套“冻结文件绑定检查”。**最终评估再核验30运行共同F及当前训练材料，其余解封门槛不变。

绑定检查不得推迟到训练完成后的manifest或分析阶段。formal run在创建训练任务/模型、启动训练子进程或收集环境transition之前完成；final-eval在取得使用封存测试的许可及任何实际评估之前完成。任一失败按runner的Refused路径退出非零，给出相对文件路径、字段、expected/actual或缺失原因；不得继续训练、评估或生成成功回执。

检查的唯一数据源为显式项目根目录下的docs/prereg/frozen_config_v0.3.2.json与docs/prereg/freeze_manifest.json，不猜测其它清单，不自动生成或修补清单。必须检查：

1. freeze_manifest.json存在、合法JSON、无重复键；schema/spec_version正确，synthetic为false且complete严格为true。complete只表示结构/机器检查完成，不代替人类签核。
2. manifest.code_commit等于当前冻结配置code_commit，即代码提交C；manifest.config_path/matrix_path指向本协议配置/矩阵。核验既有正式模式身份条件；本段不新增manifest.status等字段。
3. frozen_files是“项目相对路径→64位小写SHA-256”的对象，包含配套分析规格§1.1/1.2规定的全部必需文件（含.gitattributes与完整运行依赖快照）；不得通过漏列方案/规格/配置/依赖等必需项规避校验。
4. 对frozen_files的每一项，文件存在且当前**原始工作树字节**SHA-256等于记录值。相对路径不得为绝对路径、不得解析到项目根目录外。检查所有列出的文件，包括extra-frozen项，不只抽查三个主文件。
5. 下表三个配置字段分别等于清单中对应文件的哈希；对应文件实际哈希已由第4项核对。只检查非空/64位格式不够；全零也不能被当作有效绑定。

| 配置字段（均位于to_fill_at_freeze） | 必须对应的manifest.frozen_files条目 |
|---|---|
| analysis_script_sha256 | manifest.analysis_script_path所指的实际冻结分析脚本 |
| preregistration_document_sha256 | docs/prereg/PREREG_ARCH_NSTEP_v0.3.2.md |
| dependency_lock_sha256 | manifest.dependency_lock_path，固定为docs/prereg/dependency_lock.txt |

清单必须锁定**当前配置文件本身**的实际字节；三个字段填好之后才计算配置哈希、生成manifest。不把freeze_manifest自身放进其frozen_files，避免自引用；其自身SHA-256由外部冻结记录绑定。

成功检查记录checked_utc、实际HEAD/F、C、freeze_manifest_sha256及绑定检查通过状态，供启动日志/最终评估证据引用。只记录身份与完整性，不读取成绩，不增加训练RNG/前向/每step操作。正式分析继续执行配套分析规格§1.2的文件哈希与C/F核验，不因训练预检通过而省略。

freeze-manifest是**准备材料的生成命令**，不是formal run：它可以在许可冻结材料尚未提交时生成新的清单，不能被要求先存在一份有效的旧manifest才能生成自己。生成器应检查实际文件、必需项、三个字段对应关系，再写manifest；formal run/final-eval只读取已提交F的清单，不自动刷新哈希。

合法F之后的文档/配置变化即使属于C→F许可集合，也不因此成为原冻结的授权修改。当前文件若不再匹配manifest，必须在训练开始前拒绝。若有人连清单一并重生成得到F′，只能作为一次显式、重新批准的冻结修订；不能把F′冒称外部记录中的F。**外部记录F与manifest哈希的核对仍为启动前协议门槛**，不声称仅靠C→HEAD许可差异就能识别所有事后重冻结。

#### 1.2.2 外部冻结记录和启动顺序

##### 1.2.2.1 两阶段，避免自引用与倒填

**开跑前记录**包含C/F及manifest/全部冻结文件hash、机器/软件来源、批准和命令；此时只能保存候选/冻结环境证据及最终CPU评估的计划设置。真正final_eval_environment.json在最终评估时才产生，不能填进一份声称开跑前已经存在的记录。

**最终评估后回执**另存实际final_eval_environment与evaluation_seal的path/hash、C/F以及开跑前记录SHA。保留先前记录原字节，不覆盖、不回填日期；核心evaluation_seal.protocol_evidence仍按原合并版绑定实际环境文件。

##### 1.2.2.2 开跑前FREEZE_RECORD.json最小字段

| 字段 | 最小要求 |
|---|---|
| schema_version / spec_version / document_revision | prereg-external-freeze-1 / 0.3.2 / 修订1+彩排追加A+DSH 字面修正 |
| repository | 公开仓库URL；不含本机路径 |
| code_commit / freeze_commit | C与F完整40位SHA |
| freeze_manifest | {path:"docs/prereg/freeze_manifest.json", sha256:实际64位hash} |
| frozen_files | 拷贝manifest映射；矩阵hash必须为既定5cbd4e7b…0dfe |
| checkout_verification | 正式机器全新F克隆验收记录的相对标识/hash、通过状态与日期 |
| dependency_snapshot | docs/prereg/dependency_lock.txt的path/hash、匿名机器、生成/核对记录标识、Python/pip版本；分析依赖文件身份另列 |
| environment_evidence | 冻结环境说明的相对标识/hash；OS/驱动/软件/数值开关、匿名machine_id、train/validation_device；不得含用户名/主机名/绝对路径 |
| execution_plan | worker_count=2、实际正式启动命令的无绝对路径形式、30/30开启window_diagnostics、hard_enabled已定、最终CPU/1线程设置 |
| human_approval | 人类批准记录标识/hash与approved_utc、批准范围；尚未批准时不得造approved |
| prepared_utc | 执行者自报UTC；不是独立时间证明 |

矩阵必须使用完整值，不把表中的简称写入JSON：

~~~text
5cbd4e7b2cf79f65c96180acfc61b1914fe2e8521c036218bc7c9a4db59f0dfe
~~~

记录自身hash不放回记录自身；上传后的SHA-256与第三方时间戳保存在独立发布/存储回执中。人类复核的原签核可单独保留，公开记录引用编号/hash，不要求公开个人信息。

##### 1.2.2.3 固定保存位置

本轮默认存储在该仓库的**GitHub Releases资产**，对应条目/tag为prereg-v0.3.2-r1-freeze-<F前12位>，tag实际指向完整F，资产名FREEZE_RECORD.json。Release可以先保持draft；这是第三方存储留时证据，不要求新增公开注册。后续公开时保留原资产ID及字节，不删除后重传冒充原时间。此建议仅写入流程，**本文件交付不包含创建Release、tag或上传操作；这些动作由所有者负责**。

执行者在研究材料目录（仓库工作树之外）保存相对位置freeze_records/<F完整SHA>/，包含FREEZE_RECORD.json、FREEZE_PUBLICATION_RECEIPT.json、启动记录及之后FINAL_EVAL_RECEIPT.json。记录里只写相对标识/公共URL，不写这个目录的本机绝对地址；该目录不加入F许可集合，不产生F自引用。

FREEZE_PUBLICATION_RECEIPT最少保存：仓库/Release/tag URL或ID、完整F、GitHub资产ID、资产created_at（第三方UTC）、实际下载URL、下载文件的SHA-256与manifest SHA-256。要从真实GitHub API/资产下载核对，不仅填一份自述JSON。Release.published_at若晚于训练，只说明公开较晚；证明“字节已在第三方保存”使用对应原资产created_at及下载hash，不能冒称当时已公开。独立复核需查看同一资产身份及原始服务器元数据。

##### 1.2.2.4 验证“先记下，再正式开跑”

1. F形成且全新正式机器克隆验收通过后，人类批准，生成/存储FREEZE_RECORD与第三方回执；核对当前HEAD=外部F、manifest原始字节hash=外部值。
2. **之后**才调用第一次正式run。启动前日志保留实际C/F、manifest SHA、FREEZE_RECORD SHA、第三方资产ID/时间、预检通过时间及首个训练任务提交时间（UTC），并保留原CLI输出。可由本地执行者的启动记录器保存，不要求训练算法联网或新增配置字段。
3. 后续核对同一资产ID下载字节/hash、C/F与manifest映射，以及第三方created_at早于首个正式任务启动；本地时钟应校准、记录时区/偏差。回执和启动记录进入研究证据归档，不改变核心分析files集合。

**证据边界：**自填UTC、文件mtime或Git作者日期可修改，单独不足以独立证明先后。第三方资产时间与下载hash可证明这些字节至迟在该时点已存储；实际首次训练时点仍依赖启动/执行记录，公开源码护栏不能证明历史上绝无未记录运行。这是可追查的研究协议，不声称不可伪造的安全认证。

历史正式 seed100/res4/n1 短彩排及一次 prereg_val 早期验证按方案§7.4单独披露；这些产物不属于正式分析输入，不能用于选择或复用权重。本节“首个正式训练”指通过本节门槛、批准后的正式运行，不能用该术语抹去历史彩排启动。执行角色和交接顺序在方案§7.5及交接§5中明确。

## 2. 固定输入合同

### 2.1 矩阵、配置与运行身份

完整运行依赖快照固定 `docs/prereg/dependency_lock.txt`，必须在 C 中已存在，F 不改；`dependency_lock_sha256` 与该文件的 manifest/实际字节一致。分析 NumPy requirements 单独锁定，不能冒充完整运行快照。格式、生成责任与最低完整性校验见§1.1.3；不新增配置字段或矩阵列。

沿用原文件名 matrix.csv，不改字节、编码、换行或列；SHA-256：

~~~text
5cbd4e7b2cf79f65c96180acfc61b1914fe2e8521c036218bc7c9a4db59f0dfe
~~~

30 个 run_name 逐项取自 CSV，恰为 arch∈{cnn2,res4,res8}、n_step∈{1,3}、seed∈{100,101,102,103,104} 的笛卡尔积。CSV 行序是调度依据；数值分析张量顺序另固定为 arch=[cnn2,res4,res8]、n=[1,3]、s=[100,101,102,103,104]、e=[30000,…,30299]。**排序逐局记录后再计算，不能把文件行号当测试种子。**

检查 CSV 哈希、30 个不重复身份、每个训练种子连续块恰含6种不同配置。不得重建调度 RNG；271828 只用于后文 bootstrap。

frozen_config_v0.3.2.json 含 CSV 未列出的显式参数：eps_start=1.0、eps_end=0.05、eps_frac=0.4、tau=0.01、grad_clip=10；以及 val_seeds=21000–21049、test_seeds=30000–30299、smoke_eval_seeds=40000–40009、smoke_run_seeds=[900,901]、eval_episodes=50、final_eval_device="cpu"、final_eval_threads=1、hard_enabled（布尔）、冻结代码完整提交和依赖/机器标识。这些值由冻结配置显式传给训练/评估，不能依赖未记录的默认值。

其中val_seeds/test_seeds/smoke_eval_seeds均为JSON整数数组，按上述闭区间升序展开；不接受区间字符串或半开区间误解。另外字段名固定为code_commit、machine_id、train_device、validation_device、worker_count、max_episode_steps=1000、train_scenario="standard"、hard_chase_p=0.7（启用hard时）；worker_count按smoke测量在正式训练前冻结，全矩阵一致。验证/训练设备须符合所选统一GPU条件，最终CPU设备/线程另列，不能共用一个device字段混淆。train_seed公式和k边界按主方案，不从测试文件倒推训练种子流。

每个 config.json 是合并后的有效配置，至少包含 CSV 每列对应值、上述补充值、run_name、code_commit、frozen_config_sha256（冻结配置文件的哈希）。比较时允许 JSON 与 CSV 的明确类型转换，例如 CSV "true"→JSON true；不得按字符串近似或忽略字段。CSV 的 device 是训练设备，最终评估设备另核对 cpu。

每个 summary.json 至少记录：

~~~json
{
  "run_name": "prereg_cnn2_n1_s100",
  "total_env_steps": 300000,
  "replay": {"size": 100000},
  "actual_updates": 74000,
  "validation_steps": [20000,40000,60000,80000,100000,120000,140000,160000,180000,200000,220000,240000,260000,280000,300000],
  "validation_episodes_each": 50,
  "initial_state_dict_sha256": "<64位十六进制>",
  "checkpoints": {
    "last": {"step": 300000, "weights_sha256": "<64位十六进制>"},
    "best": {"step": 20000, "weights_sha256": "<64位十六进制>"}
  }
}
~~~

例中的 74000 与 best.step=20000 只是格式示例，**不是要求实际运行达到这些值**。actual_updates 为非负整数；replay.size 为整数且 0≤size≤100000；实际数值如实报告，不能填估计值。验证步数必须正好上述15项，每项50局；last 步数必须300000；best 步数属于15项。15 对同架构/训练种子的 n=1/3 初始权重规范哈希须一致。哈希比较采用冻结的 state_dict 规范字节算法；不能用带序列化元数据的 checkpoint 文件哈希替代初始状态规范哈希。

replay.size 是结束时缓冲区占用量，达到容量后不表示累计入库量；n=3 在8个活跃环境中最多16个尾项尚待凑齐，不代表训练少了16个 transition。actual_updates 是实际梯度更新次数。这两项都必须输出；若另外记录累计入库和 pending_horizons，也原样输出，不以它们补齐训练。

### 2.2 评估 JSON 的新格式

本格式只供新增 prereg 评估路径；不改旧路径、旧 JSON 或旧实验数据。每个 standard/hard 文件为以下包装对象，逐局数组名固定为 records：

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
    "weights_sha256": "<64位十六进制>",
    "code_commit": "<代码提交C的40位SHA>",
    "scenario": "standard",
    "device": "cpu",
    "torch_threads": 1
  },
  "records": [
    {"seed":30000,"score":100,"steps":100,"died":true,"won":false,"truncated":false}
  ]
}
~~~

这是一条记录的格式示例；有效文件必须有300条。meta 各项须与文件路径、CSV、summary、代码提交C及模式完全一致；best.step 取 summary 中选择的步数，非强制300k。hard.scenario="hard"，其追击概率0.7在冻结配置中记录。

seed、steps 为 JSON 整数且不是 bool；score 是有限整数豆子数，允许 JSON 数字 100.0 但须数值恰为整数，再转 int64；不接受字符串或 bool。died/won/truncated 必须是 JSON bool。score 不得由 reward 推断。新增 truncated 意味时间限制，不能把死亡写成截断；died、won、truncated 恰有一个 true；truncated=true 须 steps=1000。死亡/通关恰在1000步仍按真正终局原因记录。不能由 steps=1000 自动补造 truncated。

best/last 权重相同时可以只评估一次、复制 records；两个逻辑文件仍必须存在，meta.checkpoint 各自正确，权重哈希相同且记录复用来源。不能缺 best 文件然后由分析脚本猜它与 last 一样。

hard_enabled=false 时不读取 hard；若输入存在 hard 文件却冻结配置关闭，报 E_UNDECLARED_HARD，防止选择性忽略。true 时30个 last/hard.json 都必需，要求同一300种子，不接受部分架构或部分训练种子；无 best/hard 分析。合成模式也使用相同完整性检查。

### 2.3 必须失败的完整性检查与顺序

所有输入先验证完，再做任何统计。错误退出码2，stderr 输出 JSON 错误对象，包含 code、path、run_name（可确定时）、record_index/seed（适用时）、expected、actual、message。**不得跳过 run/记录、插值补局或继续输出部分统计。**非有限实际值以字符串 "NaN"/"Infinity" 表示，错误 JSON 自身不得有 NaN。目标输出目录须不存在，失败时不留下貌似成功的 REPORT.md/analysis.json。

**唯一顺序：先跨全部文件完成全局阶段1–4，然后按CSV run顺序、各run内last/standard→best/standard→启用的last/hard，逐文件完成5、6、7，再进入下一文件。**不是先对全体文件做5、再对全体做6/7。config/summary只参加前4阶段；逐记录语义阶段只用于评估文件。非有限数在第3阶段已递归拒绝。第6步逐记录按现实现固定细序：对象类型→六个必需键（seed,score,steps,died,won,truncated顺序）→seed/steps整数类型→score数值且非bool→有限score的整数性→三个终局bool类型→score数值范围→steps范围→won分数→终局逻辑。因此同时出现score=1.5与非bool终局字段时，先报E_SCORE_RANGE；不要另换全体字段类型先行的路径。全局初始化15对比较属于第4阶段，发生在任何records语义计算前。只报告该顺序的首个错误，不承诺在一次失败中列出所有错误。

具体阶段：

1. manifest/matrix/frozen_config 存在、可解析、哈希与版本吻合，hard 声明、正式冻结条件；错误 E_MISSING_FILE / E_JSON_PARSE / E_HASH_MISMATCH / E_MANIFEST / E_CONFIG_MISMATCH / E_UNDECLARED_HARD。
2. 按 CSV order 枚举 config、summary、last/standard、best/standard、启用时last/hard；先检查全体必需文件存在。任何缺文件 E_MISSING_FILE。核对30个运行身份，不接受多出的 prereg run（E_RUN_SET），不得递归读取历史目录。
3. 同序解析文件。拒绝重复 JSON key（E_JSON_DUPLICATE_KEY）、不合法 JSON（E_JSON_PARSE）；NaN、Infinity、-Infinity 常量以及溢出数字1e999必须报 E_NONFINITE，不能在类型/范围错误中隐藏。递归核对整个JSON中的数字有限性，包括额外字段；不得只检查score。该解析/全树有限性检查先于字段、数组长度和语义检查。
4. config/summary/meta 的必需字段与类型、冻结值、预算/验证次数/哈希关系；E_REQUIRED_FIELD / E_FIELD_TYPE / E_CONFIG_MISMATCH / E_METADATA_MISMATCH / E_TRAIN_BUDGET / E_VALIDATION_SCHEDULE / E_INIT_PAIR_MISMATCH。
5. records 为数组，否则 E_SCHEMA；长度恰300，否则 E_EPISODE_COUNT。对于孤立测试用例，下述检查均在300条已通过的前提下。
6. 按上文固定细序逐条检查：对象/类型错误E_FIELD_TYPE、缺键E_REQUIRED_FIELD、score的整数性/范围E_SCORE_RANGE、steps范围E_STEPS_RANGE、won⇒score=377为E_WON_SCORE、终局逻辑E_END_FLAGS。非有限数已经全局第3阶段报E_NONFINITE。整数型身份字段不得为浮点/布尔；有限score=1.5为E_SCORE_RANGE，100.0合法。
7. 种子重复 E_DUPLICATE_SEED；若种子属于验证21000–21049，报 E_VAL_TEST_MIXED；若属于smoke40000–40009、EQUIV20000–20299或旧val/test分区，报 E_RESERVED_SEED_MIXED。最后核对集合恰为30000–30299，否则 E_TEST_SEED_SET。上述混用错误优先于普通集合不匹配，但重复错误优先于混用。
8. 所有文件均完成5–7后，按 seed 排序构造张量。对每个文件保存 SHA-256 和原路径，生成输入 manifest；正式模式还核对已封存的评估文件/配置/summary 哈希，不与冻结前尚不存在的结果哈希混淆。

哈希检查分两层：冻结清单锁定方案/矩阵/配置/分析代码；测试完成的封存清单锁定评估文件。合成畸形文件的验收须更新其合成封存清单哈希，让测试确实走到对应语义错误；不得因为陈旧哈希而误认已覆盖 NaN 等检查。解析安全检查先于文件语义检查，错误优先级按上述全局/逐文件顺序；每个E1–E13坏输入用例一次只引入一种异常，§8.6另用双错误fixture锁定跨文件优先级。

## 3. 精确计算合同

令 q∈{last_standard,best_standard,last_hard} 为终点，a∈{cnn2,res4,res8}，n∈{1,3}，s∈{100,…,104}，e∈{30000,…,30299}；Y[q,a,n,s,e] 为整数得分。主分析 q=last_standard。其他终点分组报告，**不合并观测，也不替换主分析**。

每个模型：

~~~text
S[q,a,n,s] = Σ_e Y[q,a,n,s,e]
m[q,a,n,s] = S[q,a,n,s]/300
~~~

对每个 q：

~~~text
D[a,s] = S[a,1,s] − S[a,3,s]
d[a,s] = D[a,s]/300
c[s] = (D[res8,s] − D[cnn2,s])/300
u[s] = (D[res4,s] − D[cnn2,s])/300
v[s] = (D[res8,s] − D[res4,s])/300
~~~

d 是 n=1−n=3；c 是主要交互；u/v 是预定辅助交互。保留整数分子再相减，不先把 m 四舍五入。对任一训练种子向量 x=[x100,…,x104]：

~~~text
mean(x) = (Σ_s x_s)/5
sd(x) = sqrt(Σ_s (x_s − mean(x))² / 4)      # 样本标准差，ddof=1
se(x) = sd(x)/sqrt(5)
positive_count(x) = #{s: x_s > 0}
zero_count(x) = #{s: x_s = 0}
negative_count(x) = #{s: x_s < 0}
~~~

输出每个向量的5个原始值、对应 seed、mean、sd、se、三种符号数量。d/c/u/v 的符号和零值通过整数分子精确判断，不能用可调 epsilon。**唯一计算路径：精确有理分数→float64。**对共同分母D、整数分子p_i（N=5）：

~~~text
M = Fraction(sum(p_i), D*N)
V = Fraction(sum((N*p_i - sum(p_i))**2), D**2*N**2*(N-1))
mean = float(M)
sd = math.sqrt(float(V)) if V > 0 else 0.0
se = sd / math.sqrt(N)
CI = [mean - t*se, mean + t*se]
raw_values[i] = float(Fraction(p_i,D))
~~~

均值与ddof=1方差完全有理运算；第一次浮点转换只在输出mean/raw值及对方差开方之前。Python math.sqrt接受Fraction时先转为float，与这里显式写float(V)一致。se/t区间为float64按上述操作次序；无需math.fsum，不允许两条路径并存或按结果选择。score/逐局对比用有符号int64，平方和/有理分子使用Python任意精度整数，避免int64平方溢出；符号/零值由整数分子判断。不用显示舍入值作裁决。

这不改变统计公式、ddof、t/区间覆盖、bootstrap或标签规则。F1–F8所有既有字面预期、流哈希、计数/标签以及1e−12/1e−11验收容差**均不修改**。任意浮点旧路径与新路径可能有末位舍入差异，不能声称所有任意数据位级相同；本轮在正式数据出现前固定现实现Fraction路径。

6个配置的 m 也输出5值、均值、ddof=1标准差；模型内300局 score 标准差若额外报告，命名 episode_sd（ddof=1），不能与训练种子 sd 混淆。

### 3.1 次要指标和探索性对比

每个模型死亡/通关/截断率分别为相应 bool 之和/300；平均步数为 steps 之和/300。配置级汇总对5个模型率/步数取均值及 ddof=1 标准差；不把1500局当1500次训练。

预定探索性输出，全部报告，不按结果选：

| 问题 | 计算及报告 |
|---|---|
| n=1 对 cnn2、res8 是否有增益 | 对应 d 的5值、mean/sd、95%t/95%交叉bootstrap、正向数、固定方向信号标签；不新增p值/确认性假设 |
| n=1 下 res8 与 cnn2 的绝对排序 | r[s]=(S[res8,1,s]−S[cnn2,1,s])/300；5值、mean/sd、95%t/95%bootstrap；95%t下界>0标res8较高，上界<0标cnn2较高，否则排序不确定。只指这两个架构、该终点/预算，不宣称完整排序或“排序没变” |
| best 与 last 差异 | b[a,n,s]=m[best,a,n,s]−m[last,a,n,s]，6组各5值及mean/sd、95%t/95%bootstrap；报告best选择步数及GPU选模/CPU测试设备；对best_standard另报告d/c/u/v及其95%区间，与last的差值/方向逐项并列 |
| 选模是否改变n-step效应 | g[a,s]=d[best,a,s]−d[last,a,s]；5值及mean/sd、95%t/95%bootstrap；配置或架构平均效应方向用精确分子标正/负/零，无新显著性门槛 |
| 辅助交互 | u、v 的5值、mean/sd、95%t/95%bootstrap，无新增确认性判读 |
| 可选 hard | 启用时同样报告m、d、c、u、v、率和步数及95%区间；不输出新的H1/H2裁决；未启用写not_run |

所有终点按原样报告 replay.size、actual_updates 等资源元数据及尝试记录。不通过均值相同推断逐局相同；任何逐局一致主张都要逐 seed 比较且给出数值。

## 4. 区间与可复现 bootstrap

### 4.1 训练种子 t 区间

所有5种子向量的95%配对t区间：

~~~text
CI95(x) = [mean(x) − 2.7764451051977944 × se(x),
           mean(x) + 2.7764451051977944 × se(x)]
~~~

H1/H2裁决另用97.5%双侧t区间：

~~~text
CI975(x) = [mean(x) − 3.4954059325164377 × se(x),
            mean(x) + 3.4954059325164377 × se(x)]
~~~

df=4，分别为 t 的0.975、0.9875分位数。两个确认性预测按Bonferroni各α=.025；95%区间作效应展示。可用 scipy.stats.t.ppf(0.9875,4) 或 R qt(0.9875,df=4) 独立核对（本轮未调用SciPy/R）。本规格的独立数值来源是 df=4 的解析分布函数：

~~~text
F4(t) = 1/2 + t(t²+6) / [2(t²+4)^(3/2)]
~~~

实现与验收以 float64 常数 `2.7764451051977944` 和 `3.4954059325164377` 为准，分别对应 df=4 的 0.975、0.9875 分位数。更长十进制近似仅作参考，不作为逐位验收依据。

这是数学分布分位数的数值近似，不是捏造文献页码。用上述float64常数即可，独立验证 CDF 残差<1e−14。sd=0 时 CI=[mean,mean]，不报除零/不生成NaN；该退化区间仍按规则判读，并标 degenerate=true，不代表真实研究具有无限精度。CI可超出物理得分差边界，**不裁剪**。

训练种子是独立单位；固定测试集合下的 t 区间依赖差值近似正态，小样本不能可靠检验该假设。bootstrap 是敏感性分析，不补足训练种子数。

### 4.2 交叉 bootstrap 的随机流合同

10000次，B=10000；使用 NumPy Generator + **PCG64**，不是 RandomState、Python random、PCG64DXSM 或 default_rng 的未指明默认实现。分析依赖锁必须记录 NumPy 版本；本规格随机核对值由 NumPy 2.5.3 生成，其他版本只在核对值全部相同时可冻结。

每次分析新建且只建一次以下 RNG；循环顺序不得更改：

~~~python
rng = numpy.random.Generator(numpy.random.PCG64(271828))
for b in range(10000):
    I = rng.integers(0, 5, size=5, dtype=numpy.int64, endpoint=False)
    J = rng.integers(0, 300, size=300, dtype=numpy.int64, endpoint=False)
    # 先抽I，再抽J；进入下一次循环前不再调用任何随机方法。
~~~

I、J 独立有放回抽取，分别对应 s 的0基索引和 e 的0基索引；重复抽到的项重复计数。同一 b 的 I/J 对全部架构、n、last/best/hard 和探索性对比共用。不能每个配置重抽，不能先一次性抽完所有 I 再抽 J，不能先按模型平均掉测试轴。可以预存索引后并行做纯计算，但生成流必须如上。

~~~text
m_b*[q,a,n] = Σ_{i=0..4} Σ_{j=0..299} Y[q,a,n,s[I_i],e[J_j]] / 1500
d_b*[q,a] = m_b*[q,a,1] − m_b*[q,a,3]
c_b* = d_b*[res8] − d_b*[cnn2]      # u/v/r/b/g同原公式
~~~

实现求对比时先对整数 Y 形成逐局有符号对比，再按 I/J 求整数和并除1500，使完全相同的配对抵消不会受不同浮点减法顺序影响；等价数学式如上。best−last 等也共用 I/J。无需对每个bootstrap样本计算t区间。

每个统计量的10000个估计取 percentile95%：

~~~python
numpy.quantile(values, [0.025, 0.975], method="linear")
~~~

明确为type7：排序z0≤…≤z9999，h=9999p，k=floor(h)，Qp=(1−(h−k))zk+(h−k)z(k+1)。因此下界为0.025z249+0.975z250，上界为0.975z9749+0.025z9750。不得用nearest、basic、BCa或percentile的另一个默认插值方法。不要对抽样估计提前四舍五入。

冻结前云端实现必须验证：

| 0基重复编号 | I | J前12项 | J末3项 |
|---|---|---|---|
| 0 | [4,3,2,4,0] | [66,136,166,3,27,281,0,57,286,162,259,184] | [40,277,99] |
| 1 | [4,0,2,3,1] | [68,44,215,23,198,263,116,26,292,237,173,150] | [175,261,212] |

每轮依次写 I 的5项、J的300项，各项转无符号32位、小端序，连续拼接10000轮，**不加分隔符、header或换行**，共12,200,000字节；SHA-256必须：

~~~text
f3c35599fe764bf0a2c124544930609b643c2d5aa33ee0acc5b34454d91c9f69
~~~

这锁定随机索引而不是统计结果；不能只把这个哈希写死而不实际计算。云端可独立写仅生成索引的短程序核对，不读取成绩、不调用分析器；再以第8节手算公式核验统计量，防止“随机流对但统计错”。正式输出记录实际算出的哈希。

## 5. Res4 单侧精确符号检验

只在 last_standard 的 d[res4] 上作为预先指定的方向复核报告。N_eff=positive_count+negative_count，剔除精确零差值；K=positive_count。

~~~text
p = Σ_{j=K..N_eff} C(N_eff,j) / 2^N_eff
H0：在非零差值条件下，正向概率≤0.5；H1：>0.5
~~~

计算整数二项式和，输出 numerator、denominator、p、N_eff、K、zero_count。N_eff=0 定义p=1且status="no_effective_samples"，不是有效的支持证据。5/5正向为1/32=.03125；4/5为6/32=.1875；3正1负1零为5/16=.3125。此检验检验方向概率，不是均值零检验；不会用p值替代H1/H2区间门槛。无其他方向的新增p值。

## 6. 不可事后调整的机器判读

所有裁决使用未舍入值；严格不等号按字面执行，不加可调容差。边界等于±10或0的处理如下。输入不全/非法是错误终止，**不能输出“证据不足”并继续统计**。

| 字段 | 规则，按顺序匹配 | 输出枚举/中文 |
|---|---|---|
| H1 | 对d[res4]的CI975=[L,U]，L>10 | supported / 支持 |
| H1 | 否则U<10 | refuted / 反驳；另positive_gain_refuted=(U<0)表示正向增益本身也受反驳 |
| H1 | 否则 | uncertain / 不确定 |
| H2 | 对c的CI975=[L,U]，L>10 或 U<−10 | supported / 支持 |
| H2 | 否则L>−10 且 U<10 | refuted / 反驳预定幅度 |
| H2 | 否则 | uncertain / 不确定 |
| direction_signal[a] | mean(d[a])≥10 且 CI95下界>0 且positive_count≥4 | supported_signal / 支持方向信号 |
| direction_signal[a] | 否则 | insufficient_evidence / 证据不足 |
| interaction_signal | abs(mean(c))≥10 且(CI95下界>0 或 CI95上界<0) | supported_signal / 支持交互信号 |
| interaction_signal | 否则 | insufficient_evidence / 证据不足 |

**H1/H2是三分标签；方向/交互信号是二分标签。**不能为信号额外创造事后“反驳”标准，也不能把信号支持写成H1/H2支持。例如 c=[10,…,10]：交互信号支持，而H2不确定；d[res4]点估计10且区间跨10：可有方向信号，但H1仍不确定。

所有终点都报告原始效应；以上正式H1/H2及signal字段只属于 last_standard。best/hard不生成第二套确认性裁决。探索性的r排序标签在第3.1节固定。

敏感性标签固定为：

1. 对每个d/c/u/v，interval_sign(CI)=positive（L>0）/negative（U<0）/contains_zero（其他）；method_sensitive_zero=true 当其95%t与95%bootstrap的interval_sign不同。报告两种区间，不改变信号/H1/H2标签。
2. H1/H2另将同一幅度规则应用到95%bootstrap，字段命名 bootstrap95_magnitude_check；与97.5%t正式标签不同时，magnitude_check_differs=true，文字标“方法或区间覆盖水平敏感”。**这是95%与97.5%的不同层级，不能称严格同置信水平复验。**正式标签永远来自97.5%t。
3. interaction_signal已支持而bootstrap95包含0时，保留信号标签，method_sensitive_zero=true。不在两种方法间挑一个作为最终通过条件。

sign p<.05可输出布尔 p_lt_0_05 作为描述，不能变成新的正式“通过/不通过”或停止标准。

## 7. 输出合同与数字溯源

成功生成 REPORT.md、analysis.json、bootstrap_replicates.csv、bootstrap_indices.sha256、input_manifest.json。所有文件先写临时目录，全部成功后原子发布；拒绝覆盖既有 analysis_id。不存在真实数据时不能填数字模板假装分析成功。

analysis.json 顶层至少有：

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

provenance：分析脚本/规格/方案/矩阵/冻结配置/完整运行依赖快照/分析依赖/.gitattributes 哈希、code_commit=C、freeze_commit=F、当前分析HEAD、C/F核验结果、final_eval_environment的相对路径/SHA-256/machine_id、输入清单、封存清单、评估设备、模式、运行时间戳。integrity：预期/实际run数、文件数、每文件300条、种子区间、初始哈希15对、验证15×50等检查结果。parameters：t常数/df、ddof、bootstrap B/RNG/调用顺序/quantile方法/实际索引哈希、H1/H2幅度门槛。

endpoints 以 last_standard、best_standard、可选 last_hard 为键，均含 model_metrics（6配置×5seed）、config_summaries（6配置）、effects.d（3向量）、effects.c/u/v、率/步数。每个统计对象至少：

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

例是合成常数差，不是真实结果。ci975_t 至少为 H1 的 d.res4 和 H2 的 c 提供，其余可统一计算但不得增加确认性判读。每个 m 的来源列 run_name、评估文件 source_id/sha256、种子集合及整数score_sum；d/c/u/v/r/b/g 的来源列上游metric_id与整数分子，置信区间列raw_values引用和公式/常数，bootstrap列抽样方法与replicates列名。符号检验列直接来源d.res4、精确二项式计数。配置汇总从5个m引用得到，不从已舍入MD表格反算。

每个数字都有可追溯来源：数据数字对应记录字段/seed、派生数字对应上述公式和父metric_id、常数对应冻结协议、资源数字对应summary中的字段。不能仅写“来源=实验”或只给最终均值。

bootstrap_replicates.csv 固定10000行，首列replicate_index=0..9999，其余至少含全部d/c/u/v及r/b/g的抽样估计；列名含终点和对比身份，顺序冻结为终点last_standard,best_standard,last_hard（如有），每终点先d.cnn2,d.res4,d.res8,c,u,v,r，最后6配置b及3架构g。JSON/CSV保留float64可往返精度（推荐17位有效数字），Markdown显示4位小数、p可显示精确分数加小数；判读在格式化之前执行。

REPORT.md 顺序：

1. 冻结身份、完整性/偏离清单、完成和故障尝试、合成/正式醒目标记；
2. 主终点6配置表（5个m、均值、种子sd、死亡/通关/截断率、步数）；
3. d/c/u/v表（5值、mean/sd、正向数、95%t、95%bootstrap；H1/H2另97.5%t）；
4. H1/H2正式标签、方向/交互信号、敏感性标签、Res4符号检验；
5. 全部探索性和次要终点表；hard关闭写未运行；
6. replay.size/actual_updates、预算、wall time/CPU-GPU内存（若有）；
7. 数字来源索引及小样本/单图/特权输入/设备差异/不同算力限制。

无法获得的可选资源字段用null并附原因，不输出NaN；必需统计值不能用null掩盖错误。为避免原始5值塞进多个含逗号表格歧义，Markdown用“seed100…104”5列或有序数组文本，JSON同时保存训练seed序列。

## 8. 合成数据验收：独立预期值

### 8.1 通用造数规则与判断标准

下述每套有效fixture都生成全部30个run、必需last/best文件，每个文件300局；默认best记录复制last且元数据符合其身份。记录seed=30000+e（e=0..299），steps=100，died=true、won=false、truncated=false。n=3 score默认100；n=1 score=100+指定整数差。所有分数合法、配置/summary/哈希均由fixture生成器独立准备，synthetic=true；同架构seed初始哈希按15对相等。hard可关闭。不得调用被测分析器生成预期值。

oracle数值来源是手算、二项式和、df4解析CDF及以下闭式标量公式；独立索引/数值核对来自前轮记录。本合并轮未运行索引生成器或被测分析脚本。比较浮点统计用绝对误差≤1e−12（t长数值≤1e−11），标签、计数、哈希、错误码须完全相同；容差只供测试比较，**不进入正式标签逻辑**。

### 8.2 有效统计用例

| 用例 | 每训练种子的d设定 | 精确预期与标签 |
|---|---|---|
| F1 常数差 | cnn2全10，res4全20，res8全30 | d的sd均0、每组正向5；c全20，u/v全10，各sd=0；所有t/bootstrap区间退化为相应常数；H1支持、H2支持、3个方向信号支持、交互信号支持；Res4 N=5,K=5,p=1/32；r全20；全部b/g为0 |
| F2 零交互 | 三架构全20 | c/u/v全0，sd=0，所有相应区间[0,0]；H1支持、H2反驳；方向信号均支持、交互证据不足；符号p=1/32；r全0 |
| F3 符号反向 | cnn2全−10，res4全−20，res8全−30 | c全−20，u/v全−10，各sd=0；H1反驳且U<0，H2支持；3个方向均证据不足、交互信号支持；各正向0，Res4 N=5,K=0,p=32/32=1；r全−20 |
| F4 方差及边界 | cnn2全10；res4按seed顺序[8,9,10,11,12]；res8全20 | d.res4 mean=10，sd=√(5/2)，se=1/√2；95%t=[8.036756838522443,11.963243161477557]；97.5%t=[7.528374762117939,12.471625237882062]；H1不确定，但方向信号支持；c全10，H2不确定、交互信号支持；u=[−2,−1,0,1,2]，mean0、sd√(5/2)、正向2；v=[12,11,10,9,8]，mean10、同sd、正向5 |
| F5 零差值符号检验 | res4=[0,1,2,3,−1]；另两架构全0 | Res4 mean=1，sd=√(5/2)，正向3、负向1、零1，N_eff=4，p=(C(4,3)+C(4,4))/16=5/16=.3125；H1反驳，方向证据不足；零不是负值也不是第五个有效样本 |
| F6 全零符号检验 | 三架构全0 | N_eff=0,K=0,zero_count=5,p=1,status=no_effective_samples；H1反驳，H2反驳；两个信号均证据不足 |
| F8 退化边界与负交互 | cnn2全0、res4全10、res8全−10 | d.res4的CI975恰[10,10]，H1不确定；c的CI975恰[−10,−10]，H2不确定；res4方向信号支持、其他方向证据不足；交互信号支持；u全10、v全−20，Res4符号p=1/32 |

上述区间按 §3 的唯一计算路径计算，包括 `se=sd/math.sqrt(5)`；浮点预期按既定 `1e-12` 容差比较，不要求逐位相等。

F4的bootstrap无需用分析器产生oracle：每次d.res4*=8+(ΣI)/5，u*=−2+(ΣI)/5，v*=12−(ΣI)/5，c*=10；与指定索引逐轮核对即可。t区间手算来源 Σ(x−10)²=10、分母4，非bootstrap估计。

对 F1–F6 的 m、d/c/u/v 与次要终点均须核对；best复制last时b/g必为精确零且CI[0,0]。F1各配置m为[110,100]、[120,100]、[130,100]（n1,n3），跨seed均值同此、sd=0；死亡率1、通关/截断率0、平均步数100。同理其他fixture的m由100+d逐seed手算。

### 8.3 必须抓住测试轴抽样和配对错误的 F7

令 i=s−100，h(e)=1 当 e≥150，否则0。每架构 n=3 score=100；n=1 score=100+B_a+i+h(e)，B_cnn2=10、B_res4=20、B_res8=30。此处 i=0..4，e=0..299。所有记录仍合法。

手算：

~~~text
d[a,s] = B_a+i+1/2
mean(d[a]) = B_a+5/2
sd(d[a]) = sqrt(5/2)
c=20，u=v=10，r=20（每seed完全相同）
bootstrap d_b*[a] = B_a + (Σ I)/5 + #{J_j≥150}/300
~~~

随机流第0轮 ΣI=13、测试后半区计数151，偏移为931/300；第1轮 ΣI=10、后半区计数142，偏移为742/300。因此 d.res4* 分别为6931/300和6742/300，c*逐轮必须精确20。若只重抽训练轴、丢了测试轴、配置分别抽样或不配对，至少一项不符。

完整10000轮的独立标量oracle：每轮仅计算整数 T_b=60ΣI+#{J≥150}，完全不加载Y、不调用分析器。排序后的0基T249=384、T250=385、T9749=T9750=1116；type7给偏移下界=(384+39×385)/(40×300)=5133/4000=1.28325，上界1116/300=93/25=3.72。故 d[a] 的bootstrap95% CI精确为 [B_a+1.28325,B_a+3.72]；c为[20,20]、u/v为[10,10]，b/g为[0,0]。这些排序位置由规定随机流的独立计数公式核验，**不是从被测脚本反推**；随机算法结果不能仅靠手算10000次，验证分为流哈希与闭式统计两层。

另独立验证分位数工具：输入固定向量 [1,…,10000]，type7的95%界应为[250.975,9750.025]。这只是quantile单元fixture，不是模拟训练的bootstrap结果。

闭式数值与 float64 运算结果按同一 `1e-12` 容差比较。例如 F7 的 Res4 bootstrap 下界 `21.28325` 与 `21.283250000000002`、分位数 fixture 下界 `250.975` 与 `250.97500000000002` 均视为一致；计算路径与分位数方法不变。

### 8.4 畸形输入用例（每次单独修改有效F1）

| 用例 | 唯一修改 | 必须结果 |
|---|---|---|
| E1 缺文件 | 删除一个best/standard.json | E_MISSING_FILE，报具体run/path；退出2，无统计报告 |
| E2 重复种子 | 将某文件最后seed30299改30298，仍300条 | E_DUPLICATE_SEED，注明30298 |
| E3 NaN | score写JSON常量NaN；分别另测Infinity和1e999 | E_NONFINITE；不得静默丢局或变0 |
| E4 坏集合 | 将30299改30300，300个唯一seed | E_TEST_SEED_SET，missing=[30299]，unexpected=[30300] |
| E5 少于300局 | 删除最后一条，剩299 | E_EPISODE_COUNT，expected=300,actual=299 |
| E6 val/test混用 | 将seed30000改21000，仍300个唯一seed | E_VAL_TEST_MIXED，注明21000及验证分区 |
| E7 缺字段 | 删除任一记录truncated | E_REQUIRED_FIELD；不得从steps推断补齐 |
| E8 不可能通关 | score=376但won=true、died=false | E_WON_SCORE；该行其他类型/区间合法 |
| E9 分数/步数范围 | 分别score=378、steps=0（两次独立测试） | E_SCORE_RANGE / E_STEPS_RANGE |
| E10 hard不完整 | 冻结hard_enabled=true，仅缺一个last/hard.json，其余齐全 | E_MISSING_FILE，不得只分析29个hard |
| E11 配置漂移 | 一个config的tau改0.02，合成文件哈希同步正确 | E_CONFIG_MISMATCH；不能因均值仍相同放过 |
| E12 验证重复 | 一个summary.validation_steps末尾再加300000 | E_VALIDATION_SCHEDULE，拒绝16次记录 |
| E13 未声明hard | hard_enabled=false却含last/hard.json | E_UNDECLARED_HARD |

重复种子用例与坏集合用例必须分开，否则重复检查优先遮住集合检查。val/test混用是文件seed语义检查，不要求分析器加载真实验证成绩。另外将文件300条随机重排后，所有统计/标签/bootstrap估计应与原文件完全一致（输入文件哈希允许不同）；这是按seed对齐验收。

### 8.5 人员与签核

云端是实现者，也是测试作者；其“测试通过”不是另一个人独立复核。本文给出与被测代码分离的数学oracle、随机流合同；这称独立预期值，不称人员独立审计。人工验收表保留：

~~~text
实现者：____
测试作者：____（如同实现者，明确填写相同）
人类复核人：____
人类复核日期：____
实际核对的fixture / 数值 / 代码提交 / 结果：____
冻结批准记录：____
~~~

这些人类字段由人填写；AI不得代签或标“已由人复核”。小MDP独立验证n步目标仍是单独冻结门槛；分析合成fixture通过不能替代训练目标oracle。

### 8.6 补充验收：顺序、非整数score、非零best与正式身份

以下不替代F1–F8/E1–E13，也不得用被测输出反推oracle。

formal 身份验收的临时 Git 仓库必须复制真实 `matrix.csv` 的原始字节，其 SHA-256 必须等于既定 `5cbd4e7b2cf79f65c96180acfc61b1914fe2e8521c036218bc7c9a4db59f0dfe`。不得重新序列化 CSV 或转换行尾。运行、机器和评估记录仍使用合成 fixture，不读取真实成绩；“合成”不豁免 formal 模式的固定矩阵哈希检查。synthetic 模式合同不因本条改变。

| 用例 | 合成修改/独立预期 |
|---|---|
| 有限非整数score | 唯一score=1.5且所有哈希更新，E_SCORE_RANGE；score=100.0允许；bool/字符串score为E_FIELD_TYPE；NaN/Infinity/1e999为E_NONFINITE，优先解析拒绝 |
| 跨文件错误顺序 | CSV第一run的last有300条、某score=378；同run best只有299条；哈希同步且其他输入合法。应先E_SCORE_RANGE(last)，不先E_EPISODE_COUNT(best)。把前者移至后一个run仍应先遇到CSV前run的best计数错误 |
| 全局解析优先 | CSV前run score=378，同时后run任意JSON含NaN且hash同步；先E_NONFINITE(后run)，因为全树解析第3阶段在任何记录语义前；后run配置tau漂移也先E_CONFIG_MISMATCH，属全局第4阶段 |
| 非零best−last | 基于F7的last，n1 best=last+7+h(e)，n3 best=last+2；best步数按seed为[60000,80000,100000,120000,140000]。b[n1]=7.5全5、b[n3]=2全5、g=5.5全5，sd=0；d_best=B_a+i+6。每轮K=#{J≥150}，b_n1*=7+K/300，b_n3*=2，g*=5+K/300，d_best*=B_a+ΣI/5+5+2K/300；c/u/v仍20/10/10。用同一独立索引公式核对每轮，不新选RNG |
| 正式C/F通过 | throwaway Git先提交全部代码/锁/假配置得C，只改许可冻结材料得F；完整合成结果/匿名机器/环境/协议seal一致。formal身份校验可通过，再计算F1原期望；全套fixture仍不读取真实seed结果 |
| 正式C/F拒绝 | 分别单独：非祖先C、F改python、F改matrix、F改非许可README、HEAD非封存F、dirty跟踪文件、缺Git。均E_MANIFEST（若更早实际哈希错则E_HASH_MISMATCH）；隔离fixture需同步所测检查之前的hash，不能被陈旧hash遮住 |
| 正式环境证据拒绝 | 单独缺独立文件→E_MISSING_FILE；hash错→E_HASH_MISMATCH；hash同步后machine_id/CPU/线程/C/F错→E_MANIFEST；缺protocol_evidence→E_MANIFEST |
| 正式溯源成功 | 输出provenance恰列C、F、当前HEAD=F及环境文件path/hash/machine_id；核心F1数字及标签等于原oracle，不因新溯源改变 |

#### 8.6.1 训练/最终评估绑定验收（R1）

全部使用临时Git仓库、模拟冻结材料和启动/评估调用spy，不访问真实成绩或封存种子；不需要为了验证正例真的启动300k训练。

| 单独修改有效fixture | 训练预检 / 最终评估预检的预期 |
|---|---|
| 将方案文本改变后提交，保持清单不变 | 均拒绝；报告方案实际hash与清单不符 |
| 某一配置主哈希设为全零；为避免被配置本身陈旧hash遮住，同时更新fixture的配置文件hash | 均拒绝；分别点名三个主哈希字段与对应清单项不符，三个字段各独立测试 |
| 删除freeze_manifest.json | 均拒绝，明确缺文件 |
| complete=false / synthetic=true / 错code_commit，分别测试 | 均拒绝对应正式清单/身份条件 |
| 删必需frozen_files项 / 改extra-frozen文件 / 删其实际文件，分别测试 | 均拒绝；不能只检查固定三个文件 |
| 合法C/F、配置三值、所有实际文件与清单一致 | 两个实际调用路径均通过绑定检查；启动/评估仍由各自其它门槛控制 |

反例断言训练入口/子进程启动/环境步进调用数为0；最终评估反例断言许可签发或读取测试分区的调用数为0。至少用真实CLI负例确认非零退出，再用实际preflight接线spy验证检查时点。生成清单的正例无需已有manifest；不能为消除循环而跳过正式绑定检查。

#### 8.6.2 字节检出与依赖快照验收（R2/R3）

- 使用临时 Git 仓库的 LF 文档/脚本/依赖与字面 CRLF 矩阵 fixture；-text 生效后在 core.autocrlf=true/false 的全新检出中，raw bytes、blob 和已知 hash 相同。期望值从原 fixture 字节独立 SHA-256 得出，不从被测检查器或规范化后的文件得出。
- 正例：完整运行快照已随 C 提交，F 只改许可文件，路径、三个主 hash 与实际文件一致。
- 反例：F 才新增/修改完整快照；dependency_lock_path 指错文件；以 >= 安装需求或仅 NumPy 文件冒充；快照格式非精确、缺原安装需求中任一顶层依赖。正式生成器/预检拒绝；正式分析保持其文件/身份合同，不允许依赖错位后继续统计。
- 对 C/F 关系和格式反例同步所测检查之前的 fixture hash，避免被陈旧 hash 提前遮住。实际 A1000 全新 Windows 克隆及安装环境逐包对应由本地执行者验收；临时 Git 测试通过不能代替它。
- R1/R2/R3 用例不替代 F1–F8/E1–E13，不修改其字面数值/容差；runner 的 Refused 非零退出和分析器的既定 E_* 分类是两个入口的合同，不互相杜撰错误码。

### 8.7 源码/运行证据记录

6023b1a新增test_prereg_analysis_expected.py静态可见F1–F6/F8完整m/效应/率/步数及非零best−last共享索引预期；不能因它另放一个测试文件就要求重复搬回test_prereg_analysis.py。合并验收按fixture内容与实际收集执行结果判断。本轮GPT未运行该测试文件；415 passed为本地报告，不能据此称新增§8.6（尚待实现）已通过。人类复核栏保持§8.5。

## 9. B1/B2独立描述分析合同

### 9.1 输入、定义与边界

本节为已采用次要指标，完全独立于§2–8核心数据/标签。输入仅为matrix.csv、冻结manifest、两份冻结诊断代码字节和30个runs/<run_name>/window_diagnostics.json；不读standard/hard测试、.pt、训练/验证分数或coreanalysis来挑指标。冻结身份/代码哈希属于非成绩证据，不违反该隔离。

schema=window-diagnostics-1，definition_version="1"（字符串），counting_source=emitted_once，indicator=action_mismatch_to_selected_greedy，descriptive_only=true；n_envs=8、n_step按CSV、gamma=.99、transition_budget=300000、bin_size=20000、15箱按0基编号0–14。meta含run_name/arch/n_step/run_seed、git_sha=F，不把F当C。正式30/30开--window-diagnostics通过F清单、外部冻结记录和实际命令固定；不新增frozen_config字段。续训无完整诊断，正式禁止resume。

对实际采集批次的更新前online网络复用已有g=greedy_actions返回（no_grad/eval后恢复train），实际执行A来自原ε-greedy；U=1[A≠g]，G=1−U。target、最终模型、更新时网络都不用于重算。并列另一等值动作也可U=1；不等于严格次优，不假定并列为零。随机分支恰好A=g仍U=0，不需要explore_mask；不新增前向、随机数、每step tensor同步。

一条实际入库窗口计一次，不按回放sample/updates重复计。W=[t,…,t+h−1]，h=1..n，同env同episode；L=any(U_j,j=1..h−1)，起点不入L，h1空集L=0。真正term与时间trunc按实际NStepReplay规则flush全部实际短h；term的bootstrap折扣0，trunc使用真实终态观测及γ^h，reset不拼旧窗口；预算停止不额外flush，最多16pending。每批global_id=batch_start_env_steps+i+1，归窗口**起点**15箱，跨箱发出回填起点箱；h>=2口径排除没有后续动作的尾项。

D=窗口中info.died事件，死亡不由reward/term/trunc推断。末步死亡偏移j_D=h−1；T=D∧G_start∧L；J=D∧G_start∧j_D≥1∧U_death；P=D∧G_start∧any(U_j,1≤j<j_D)。T=J OR P，J/P可重叠不能相加。Z=−10*.99^j_D（D1），否则0；只为已知死亡罚项分量，不为全部ret/TD误差/因果影响。环境罚项−10合同需独立测试；死亡吃豆总reward−9.01不是判D依据。

每箱/h cells保存n，C_g_l_d[g][l][d]的2×2×2非负整数表，J/P整数，death_component_sum_g_l_d同布局float64累计，end_kind_counts={nonterminal,death,win,truncated}，start_eps={sum,min,max,count}。起点eps直接复用采集批次实际值，零窗口eps min/max可null。原文件还保存pending_by_start_bin、pending_total、totals.collected_transitions/emitted_windows/death_events/death_events_by_transition_bin、rates.run.h1..hn/all及rates.by_bin.0..14.h1..hn/all、integrity.complete/checks/errors/verified_against_replay。

完整性：实际collected=300000，emitted+pending=collected，所有C格总和=emitted，各endkind和=n且death=endkind的D格和，death_events≤N_D≤n*death_events，pending≤8(n−1)，n1的L/T/J/P=0，verify_against_replay=true且真实emit数量/h/顺序/动作/ret/disc核验通过。发布原子最终文件，partial不能当完整文件；不在每transition写盘。数组浮点和值必须有限，计数非负，不生成NaN。

定义在方案§11完整展开，本节所有统计与预期足以独立实现。以下对任一run、箱/h组合或all组，N=ΣC，N_G=ΣC[1,l,d]，N_L=ΣC[g,1,d]，N_D=ΣC[g,l,1]，N_GL=ΣC[1,1,d]，N_GD=ΣC[1,l,1]，N_T=C[1,1,1]；按选定组求和。J/P使用同组记录。

| 输出键 | 分子/分母 |
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

死亡分量另外保存death_component_sum_greedy_start_death=ΣZ_GD、death_component_sum_T=ΣZ_T、death_component_mean_greedy_start_death=ΣZ_GD/N_GD、death_component_mean_T=ΣZ_T/N_T。Z始终非正，所以表格求和绝对值与窗口绝对值和相同；分母是全部死亡窗口的绝对分量，不能改为GD分母。

rate字段为{numerator,denominator,rate,status}，分母0时rate=null,status=no_eligible_windows；h1/n1的h≥2率0/0不是零比例。Z均值分母0时null。对于单独h1，“full_horizon”分子只有该h恰等于本run n才计，否则0；all的h≥2率仅选实际h≥2的格。真实死亡可重复进入多个重叠窗口，不能当多个独立死亡transition。

### 9.2 独立封存与身份核验（剩余最小代码补齐）

辅助seal文件为results_prereg/window_diagnostics_seal.json；schema=window-diagnostics-seal-1，matrix_sha256固定，runs恰CSV顺序30个，files恰30个<run_name>/window_diagnostics.json→实际hash，transition_budget=300000，descriptive_only=true，code_sha256恰列window_diag.py与window_diagnostics_summary.py。增加code_commit=C、freeze_commit=F、freeze_manifest_sha256；不增加核心evaluation_seal.files项目。

seal/summarize命令新增显式--freeze-manifest（同F冻结manifest）和--freeze-commit（外部冻结记录的完整F）作为**辅助工具**参数；不增加训练/核心分析参数或冻结配置字段。seal生成时：manifest含两份诊断代码哈希，实际代码/当前Git HEAD=F、C/F许可关系一致；30份meta.git_sha均F、矩阵身份/完整性/预算/真实emit核验满足§9.1；code_sha256从冻结哈希绑定且实际匹配，不仅记录当时未知版本哈希。summarize重新核验manifest哈希、外部F、当前代码哈希=封存哈希=冻结哈希、实际30文件哈希和meta/F及结构；不能只核验文件hash而忽略保存的code_sha256。两端解析应递归拒绝非有限数（包括1e999），复核固定header与完整性字段，不只拒绝NaN常量。缺文件/错误F/代码漂移/计数不完整应DiagError，stderr说明、退出2、不发布貌似成功汇总；错误类别不混入核心E_*。

诊断缺失或失败作为辅助协议偏离单独报，不使核心run_problems/final-eval/H1/H2依赖诊断存在，也不授权重训有效run以补日志。若无法满足全部30辅助输入，不能发布complete=true的30-run汇总；保留缺失清单，不把剩余样本装成完整5seed。工程修复须留时点/身份；记录器原计数不重新采集或篡改。

### 9.3 汇总、数值路径与输出

按arch=[cnn2,res4,res8]、n=[1,3]、训练seed100..104固定列。每配置JSON输出run_level的h1..hn/all全部16比例及2个Z均值，by_start_bin_all_h的15箱全部比例（包含各箱h≥2口径）、5个原值/分子/分母/身份、有效k/5、均值、ddof1 sd与pooled。原始diag JSON保留每箱/h详细统计；配置级不另求逐箱/逐h推断。另列pending_total/death_events的5值和汇总、窗口N和每个值源文件hash/JSON路径/公式键。Z原累计表及分量sum来自原文件，摘要输出均值与绝对占比，不丢原数据来源。

整数分子/分母比例用Fraction精确值求均值和方差，再float→math.sqrt；零分母保留null及身份，在该指标均值中排除并明确k。k=0均值null；k<2 sd=null及原因；pooled=Σnum/Σden不是run均值。Z分量记录器为float64按冻结emit/汇总遍历次序累计，已记录有限浮点均值以Fraction(float)转换其精确二进制值，求种子均值/样本方差后转float；不重建反事实，不对观察性重叠窗口生成CI。int比例及Z绝对占比分开，浮点分量的分母不是整数窗口数。

成功原子发布独立window_diagnostics_summary.json与window_diagnostics_summary.md，不覆盖；JSON完整保存全部上述字段并列明C/F、freeze_manifest/辅助seal/原始文件/代码hash和定义版本。Markdown固定摘要列：p_later_mismatch、p_later_mismatch_hge2、p_later_mismatch_given_greedy_start、full_horizon_fraction、death_window_fraction、cooccurrence_given_greedy_start_death、death_given_later_mismatch_greedy_start；同时固定给15箱h≥2曲线均值/pooled，并指向JSON中全部J/P/Z及其它比例。**接受现实现的固定摘要选择；不得按结果换列或把未显示列称未测。**因此无需把16率全部重复塞入Markdown，所有预定指标均必须在JSON及原数据中可追溯。

无新增p/确认性标签、bootstrap、相关、回归、诊断排序、风险比或逐箱显著性。不能把U/D共现称因果、将窗口比例当影响大小、或据前后箱差宣称作用只在前40%。核心报告可链接辅助报告但核心数值/标签不读它。

### 9.4 独立预期与剩余测试

方案§11.6的全部手算/接线用例仍保留：随机分支选到g、并列另一动作、G链、死亡J/P、两步截断/通关/死亡吃豆、起点非贪心、pending、环境隔离、跨箱、回放绕环、零分母、重叠死亡、无RNG/前向/同步副作用、核心sidecar隔离。独立例：比例1/2与9/10的run均值7/10、sd=√(2/25)=0.282842712474619，pooled=5/6；G=[1,1,0]第3步死亡，h3 T=J=1,P=0,Z=−9.801，h2 T=J=1,P=0,Z=−9.9，h1起点非贪心T=0,Z=−10，死亡transition1/死亡窗口3。G=[1,0,1]第3步死亡，h3 T=P=1,J=0；零分母null不是NaN。

新增测试：正式F正确可seal/summary；单份meta.git_sha错、seal中F错、实际/封存code_sha256与冻结不符分别拒绝；缺诊断不影响核心F1/H1/H2但辅助拒绝；未attach真实emit不能正式seal；错误definition_version/非有限溢出字段拒绝；独立Pacman死亡奖励分量−10合同（包含死亡＋豆的总reward−9.01）成立，改变常数会使该测试变红。所有输入/正式身份都用合成/throwaway材料，不读取真实测试。

**诊断结构缺陷或只改seal/summary不授权重写旧训练结果**。本轮对实际A1000开销/权重一致仅采纳执行者记录；人类oracle/分析/文献及冻结签核由人填。未经最终验收不得把本合并文档标已冻结。
