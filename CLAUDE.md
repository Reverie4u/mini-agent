# mini-agent 项目配置

## 语言偏好
- 所有对话使用中文

## 代码修改规则

修改项目代码前，必须先写 **spec 和 plan**，且只能新增文件，不能覆盖已有文件。

### Spec（设计规格）

- 放在 `docs/superpowers/specs/` 目录下
- 文件名格式：`YYYY-MM-DD-<topic>.md`
- 内容：概述、架构/组件设计、关键决策和理由
- **只能新增，不能覆盖已有 spec**

### Plan（实现计划）

- 放在 `docs/superpowers/plans/` 目录下
- 文件名格式：`YYYY-MM-DD-<topic>-plan.md`
- 内容：步骤分解、涉及文件、执行顺序
- **只能新增，不能覆盖已有 plan**

### 流程

1. 写 spec → 用户确认
2. 写 plan → 用户确认
3. 按 plan 实现代码
4. 更新 spec 状态为"已实现"

### 注意事项

- **spec 和 plan 必须写到项目 `docs/superpowers/` 目录下**，不能写到 `~/.claude/plans/` 等 Claude 内部路径
- `~/.claude/plans/` 下的 plan 文件仅在 plan 模式下用于审核流程，最终 plan 必须落到项目目录
