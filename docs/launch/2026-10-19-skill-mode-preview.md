# Skills mode early-access announcement (2026-10-19)

## English — short community post

**Manage Skills. Propose improvements. Prove what changed.**

We are experimenting with an opt-in Skill mode in CounterProof that connects the complete, pinned, MIT-licensed Skills Manager upstream source with CounterProof's existing evidence-first verification approach.

Skill mode currently supports local SKILL.md inspection (no script execution), trace-to-candidate proposals, and explicit delegation to the separately installed Skills Manager CLI. We explicitly distinguish installed Skills, hypotheses, static inspection, independently evaluated effects, and verified deployment.

**This is an early integration branch, not a production integrated desktop release.** The upstream GUI remains separately launched; cross-OS E2E and independent Skill behavior verification are pending.

- Feature preview: https://github.com/hippoley/CounterProof/tree/feat/skills-manager-skill-mode-20261019
- Setup and exact limitations: https://github.com/hippoley/CounterProof/blob/feat/skills-manager-skill-mode-20261019/docs/SKILLS_MANAGER_INTEGRATION.md
- Skills Manager upstream (MIT, credit): https://github.com/xingkongliang/skills-manager

We are looking for reproducible issues with agent/OS combinations and independent before/after Skill evaluations. Which Skill did you install that you cannot yet prove helped?

## 中文 — 社区贴

**从统一管理 Skills，到证明 Skills 是否真正改善了 Agent 的行为。**

我们在 CounterProof 的独立实验分支里，以 Git 子模块固定引入 Skills Manager 完整上游源码，并新增可选的 Skill 模式：静态检查、从执行轨迹提出技能改进候选，以及显式调用上游 Skills Manager CLI。

目前这是**实验预览，不是已经完成的桌面融合版本**。Skills Manager 的原生 GUI 仍需要独立运行，跨系统端到端部署和独立语义评测仍待验证。静态检查通过不等于 Skill 有效，更不等于已经部署成功。

欢迎提供明确的 Agent + 操作系统组合、复现步骤、失败案例，以及真实的前后对照评测数据。

预览地址：https://github.com/hippoley/CounterProof/tree/feat/skills-manager-skill-mode-20261019

上游项目与版权归属：https://github.com/xingkongliang/skills-manager
