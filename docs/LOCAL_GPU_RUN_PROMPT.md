# 给本地 Claude Code 的提示词:在带 NVIDIA GPU 的笔记本上部署并跑完实验

> 用法:克隆仓库后,把下面"提示词正文"整段粘贴给本机的 Claude Code。

---

## 提示词正文

你是我笔记本上的 Claude Code。请帮我把一个强化学习项目部署到这台带 NVIDIA 显卡(RTX A1000 笔记本版)的机器上,用 GPU 跑完一批更长的训练实验,并把结果整理好。**请严格按下面的顺序和规则做;遇到"停下来问我"的地方一定要停。**

### 0. 项目背景(先读完再动手)
- 仓库:GitHub 上我名下的私有仓库 `Firefade0329/Reinforcement-Learning-Pacman`。工作分支:`claude/sleepy-knuth-9pl6y5`(不是 main)。
- 项目是一个 Pacman 强化学习升级:Python 复刻了原 Java 游戏,并比较从随机、手写规则、表格 Q-learning 到 MLP/CNN/ResNet-DQN 的一系列智能体。
- 开工前请完整阅读:`docs/PLAN.md`(方案、验收门槛、偏差记录)、`docs/ACCEPTANCE.md`、`python/README.md`(尤其 "Training on a GPU" 一节)。
- 云端那边已经跑出来的 12 万步 CPU 结果在 `results/`,**不要改动、不要覆盖**。你这次跑的是 **GPU、更长步数(默认 30 万步)的补充实验**,结果写到独立目录 `results_gpu/`,两者不要混在一起。
- 已知参考数字(测试集 300 局,标准场景,平均得分,满分 377):random 7.5;legacy(原 Java 复刻)153;强手写启发式 268;MLP-DQN 三个种子约 246/241/220。卷积网络在 12 万步时仍在上升,你这次的目标就是看它们在更长训练下能走到哪。你的数字不必和这些一样,但如果出现明显异常(例如全部接近随机的 8 分),请停下来排查。

### 1. 环境部署
1. 克隆仓库并切到 `claude/sleepy-knuth-9pl6y5`。需要我的 GitHub 授权时,告诉我怎么授权,不要自己想办法绕。
2. **先设置仓库本地的 git 身份,再做任何提交**(这一步非常重要,否则会把这台电脑上的全局邮箱写进提交):
   ```
   git config user.name "Firefade0329"
   git config user.email "114788148+Firefade0329@users.noreply.github.com"
   ```
   提交信息末尾统一加一行:`Co-Authored-By: Claude <noreply@anthropic.com>`。提交信息、代码、文档、回复里都**不要出现我的真实姓名、旧用户名或任何个人邮箱**。
3. 创建 Python 虚拟环境(3.10 及以上)。先运行 `nvidia-smi` 确认驱动和 CUDA 版本,然后按 pytorch.org 官方指引安装**与之匹配的 CUDA 版 PyTorch**(Windows 上默认的 pip 版是 CPU 版,会没有 GPU 支持),再 `pip install numpy matplotlib pytest`。
4. 验证 GPU 可用:
   `python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"`。若 `False`,先排查驱动/CUDA/安装版本,排查不了就停下来告诉我。
5. 进入 `python/` 目录跑测试:`python -m pytest tests -q`。预期全部通过(此前是 45 项通过、1 项因无 GPU 跳过;现在有 GPU 时那 1 项会实际运行并应通过)。有失败就停下来报告,**不要为了通过而改测试**。
6. 跑速度基准并保存输出:
   `python -m pacman_rl.cli bench --device cuda` 和 `python -m pacman_rl.cli bench --device cpu`,把两份结果和比值记下来。如果 GPU 对 res4 / res8 的加速不到 2 倍,请停下来告诉我,不要硬跑。

### 2. 跑实验
- 推荐命令(bash;Windows 请用 WSL 或 Git Bash,否则按 `python/scripts/run_gpu_longrun.sh` 里的步骤在 PowerShell 里手动设置同名环境变量后依次执行):
  `bash python/scripts/run_gpu_longrun.sh`
  可选环境变量:`PACMAN_STEPS`(默认 300000)、`PACMAN_WORKERS`(默认 3,按 CPU 核数和内存调;每个卷积训练进程约需 1.1 GB 内存回放缓冲区加 1~2 GB 进程开销)、`PACMAN_DEVICE`(默认 cuda)。
- 这是几小时级的任务:请**在后台运行并把日志写到文件**(Linux/WSL 用 nohup 或 tmux;Windows 用 Start-Process 或 WSL),不要占着交互式终端。同时请**阻止电脑睡眠**(插电、关闭睡眠/合盖休眠),否则训练会中断。
- 训练支持**断点续训**:每 2 万步存一次状态。被中断后,重新运行同一条命令即可自动接着跑,已完成的运行会被跳过。如果提示某个 `.lock` 被占用但其实没有在跑,先用 `ps` 确认没有残留进程,再删除那个 `.lock` 目录。
- 监控进度:`results_gpu/runs/<运行名>/stdout.log`(每次评估会打印 `[val] steps=... val_score=...`)。
- 内存不足时进程会被系统静默杀掉(日志里没有报错就消失)。如果发现有运行无故消失,先查内存和系统日志,降低 `PACMAN_WORKERS` 后重新运行同一条命令。

### 3. 规则(必须遵守)
- **不要修改项目代码和测试**,除非为了在这台机器上跑通(例如 Windows 路径问题),且改动要最小、单独提交、在回复里明确说明。
- **不要改动 `results/`**(云端的 CPU 结果)。你的输出只在 `results_gpu/`。
- **不要把 `resume.pt`、`resume_replay.npz`、`.lock` 提交进仓库**(已在 .gitignore 中,提交前用 `git status` 确认没有大文件)。
- **不要对任何分支强制推送;不要碰 `main`;不要做任何改写 git 历史的操作**;不要把仓库改成公开。历史改写是另一项单独的任务,由云端那边的 Claude 在我确认后做,你不要参与。
- 提交前确认 `git log -1 --format='%an <%ae>'` 显示的是 `Firefade0329 <114788148+Firefade0329@users.noreply.github.com>`。

### 4. 收尾:汇总并提交
全部跑完(或你判断无法继续)后:
1. 运行 `python scripts/make_report.py`(在 `python/` 目录下,`PACMAN_RESULTS_DIR` 指向 `results_gpu`,报告会写到 `results_gpu/RESULTS.md`),再运行 `python scripts/check_acceptance.py`,保存输出。
2. 写一份 `results_gpu/LOCAL_RUN_REPORT.md`,包含:机器信息(GPU、驱动、CUDA、PyTorch 版本、CPU 核数、内存)、bench 对比表、实际用的步数和并行数、每个运行是否完成、测试集成绩表(对比上面的参考数字)、遇到的问题和处理、哪些运行是被中断后续训完成的。**如实写,有失败就写失败,不要美化。**
3. 新建分支 `local/gpu-longrun`,只提交 `results_gpu/`(JSON、日志、最终 `best.pt`/`last.pt`、报告、图),推送该分支。**不要推到 `claude/sleepy-knuth-9pl6y5`。** 把推送后的分支名和提交号告诉我。
4. 另外把 `results_gpu/` 打成 `results_gpu.zip` 放在仓库目录之外,方便我直接上传给云端那边的 Claude。

### 5. 完成后向我汇报(简洁)
给我:bench 的加速比、哪些运行完成了、卷积网络(cnn2 / res2 / res4 / res8)在 30 万步的测试得分对比 MLP 和强手写启发式(268)、验收脚本的 MUST / SHOULD 结果、遇到的任何异常。**如果一切正常也请明说"没有异常"。**

---

## 后续还要做的事(给我自己的备忘,不属于提示词)

1. **云端实验**:云端的 12 万步 CPU 矩阵仍在跑(有断点续训,被挂起后需要唤醒会话让它接着跑)。跑完后云端会生成 `docs/RESULTS.md`,运行验收脚本,并给出结论。
2. **合并两套结果**:GPU 长训练是补充实验。把 `local/gpu-longrun` 的结果(或 `results_gpu.zip`)交给云端的 Claude,写入最终报告,对照"12 万步 vs 30 万步"下卷积网络深度的结论。
3. **历史改写(隐私)**:实验结束后,先重新备份,再把所有提交(含本地分支那一个)的作者统一成 noreply 身份、替换历史文件内容里的真实姓名和旧用户名、清理提交信息;**云端会先把方案和新旧哈希对照表给我确认,再强制推送**。本地分支 `local/gpu-longrun` 的那个结果提交会在改写后用 cherry-pick 重新挂到新历史上。
4. **收尾**:把清理分支和工作分支合并进 `main`、删除多余分支;更新根 README(中英文)说明新旧两套代码与运行方法;为最终智能体生成回放 GIF(`python -m pacman_rl.cli replay`),人工看一眼行为是否合理;跑 `bash python/scripts/acceptance.sh --quick` 做最终冒烟。
5. **隐私收尾**:历史改写完成后再决定是否把仓库改回公开;在 GitHub 邮箱设置里开启 "Keep my email addresses private" 和 "Block command line pushes that expose my email"。
