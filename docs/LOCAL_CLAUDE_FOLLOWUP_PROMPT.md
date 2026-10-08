# 给本地 Claude Code 的补充提示词:清理 GitHub 上的两个分支 + 正确交付训练结果

> 用法:把下面"提示词正文"整段粘贴给本机的 Claude Code。它自带背景,不依赖你之前给过它什么。
> 训练的部署与运行细节仍以 `docs/LOCAL_GPU_RUN_PROMPT.md` 为准;本文件补充两件事:**任务 A(删两个多余分支)**和**任务 B(训练结束后怎么把结果交回来)**。

---

## 提示词正文

你是我笔记本上的 Claude Code。我有一个 GitHub 私有仓库 `Firefade0329/Reinforcement-Learning-Pacman`。云端的另一个 Claude 刚刚**改写了这个仓库的 git 历史**(为了清理个人信息),所有提交哈希都变了。我需要你做两件事:任务 A 现在就做,任务 B 等我这台电脑上的训练全部结束后再做。**请严格按步骤和规则执行;每个"停下来问我"的地方一定要停。**

### 总规则(两项任务都适用)
- 提交和推送必须使用这个身份(只设**仓库本地**配置,不要改全局):
  `git config user.name "Firefade0329"` 和 `git config user.email "114788148+Firefade0329@users.noreply.github.com"`。提交信息末尾加一行 `Co-Authored-By: Claude <noreply@anthropic.com>`。
- 提交信息、代码、文档、对我的回复里,**都不要出现我的真实姓名、旧用户名或任何个人邮箱**。
- **绝对不要**:强制推送(`--force`、`--force-with-lease`)、改写历史、碰 `main` 和 `claude/sleepy-knuth-9pl6y5` 这两个分支、把仓库改成公开、改动账号或仓库的设置。
- **不要从这台电脑上已有的旧克隆里 `git push` / `git pull` / `git merge`**(它含有改写前的历史,推送会把旧提交重新传上去)。所有 git 操作都在下面新建的"新克隆"里做。**不要打断正在跑的训练**,也不要删除或移动旧克隆里的 `results_gpu/`。

### 任务 A:删除 GitHub 上两个多余的分支(现在做)
背景:线上现在有 4 个分支:`main`、`claude/sleepy-knuth-9pl6y5`(都要保留),以及两个要删的:
1. `zz-capability-probe`:云端 Claude 为测试权限建的一次性分支,里面只有一个空树提交。
2. `claude/privacy-cleanup`:现在与 `main` 完全相同,已经没用。

步骤:
1. 在一个**全新的空目录**里克隆仓库(需要 GitHub 授权时告诉我怎么授权,不要自己绕):
   `git clone https://github.com/Firefade0329/Reinforcement-Learning-Pacman new-clone && cd new-clone`,然后按"总规则"设置本地 git 身份。
2. 先**验证**再删除,三项都满足才能继续,任何一项不满足就停下来把输出给我看:
   - `git ls-remote --heads origin` 应该列出这四个分支(可能还有我之后推的 `local/...` 分支,忽略它们)。
   - `git rev-parse origin/main origin/claude/privacy-cleanup`:两行**必须完全相同**。
   - `git log -1 --format='%h | %an <%ae> | parents=%P | %s' origin/zz-capability-probe` 应显示作者是 `Firefade0329 <114788148+Firefade0329@users.noreply.github.com>`、`parents=` 为空、主题包含 "capability probe";并且 `git ls-tree -r origin/zz-capability-probe` 的输出为空(空树)。
   - 顺便检查改写是否生效:`git log --all --format='%an <%ae>' | sort | uniq -c` 应该**只有一行**,即 Firefade0329 的 noreply 身份。出现任何别的作者就停下来告诉我。
3. 删除(只删这两个,命令里不要有别的分支名,不要加 `--force`):
   `git push origin --delete zz-capability-probe`
   `git push origin --delete claude/privacy-cleanup`
   如果被拒绝(分支保护、权限不足等),**不要想办法绕过**,把完整报错发给我,我会在 GitHub 网页上手动删。你也可以改用 `gh api -X DELETE repos/Firefade0329/Reinforcement-Learning-Pacman/git/refs/heads/<分支名>`,仍然只限这两个分支。
4. 删完再次运行 `git ls-remote --heads origin`,确认只剩 `main`、`claude/sleepy-knuth-9pl6y5`(及可能的 `local/...` 分支)。把前后两次的输出贴给我。

### 任务 B:训练全部结束后,把结果交回云端(训练没结束就不要做)
1. 确认训练全部结束(没有残留的训练进程;`results_gpu/`(以及第二遍的 `results_gpu_nstep1/`,如果有)里每个运行都有 `test_standard.json`)。
2. 照 `docs/LOCAL_GPU_RUN_PROMPT.md` 第 4 节收尾:在 `python/` 下用 `PACMAN_RESULTS_DIR` 指向对应结果目录,运行 `python scripts/make_report.py` 和 `python scripts/check_acceptance.py`,写 `results_gpu/LOCAL_RUN_REPORT.md`(机器信息、bench 对比表、步数和并行数、各运行是否完成、测试成绩表、问题和处理、哪些运行是中断后续训的,**如实写,有失败就写失败**)。
3. 把结果目录拷到仓库目录之外的安全位置,再用任务 A 里的**新克隆**(或再重新克隆一份):
   `git checkout -b local/gpu-longrun origin/claude/sleepy-knuth-9pl6y5`(第二遍用 `local/gpu-longrun-nstep1`),把拷出来的结果目录放进去。
4. 提交前运行 `git status`,确认**只有** `results_gpu/`(或 `results_gpu_nstep1/`)下的 JSON、日志、最终 `best.pt` / `last.pt`、报告和图;**不得包含** `resume.pt`、`resume_replay.npz`、`.lock` 等大文件或临时文件。然后提交并推送该新分支(普通推送,不要强制)。
5. 用 `git log -1 --format='%h %an <%ae>'` 确认作者身份正确,把分支名和提交号告诉我。云端的 Claude 之后会直接从这个分支读取结果并并入最终报告。
6. 另外把结果目录打成 `results_gpu.zip` 放在仓库目录之外,作为备份。

### 完成后向我汇报(简洁)
- 任务 A:两个分支是否已删除,前后 `ls-remote` 输出,有无异常。
- 任务 B(如果已做):推送的分支名和提交号;训练成绩的简要对比(各架构在测试集上的得分,对比 MLP 约 236、强手写启发式 268);验收脚本的 MUST / SHOULD 结果;任何异常。一切正常也请明说"没有异常"。

---

## 你自己要做的两个设置(不让 Claude 代劳)
在 GitHub 网页:**Settings → Emails**,勾选:
1. **Keep my email addresses private**
2. **Block command line pushes that expose my email**

这样以后即使本机的全局 git 邮箱设错了,也不会再把个人邮箱暴露到提交里。这两项属于账号安全设置,建议你自己点,不交给 Claude 操作。
