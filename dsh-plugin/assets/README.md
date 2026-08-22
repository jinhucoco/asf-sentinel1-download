# assets

本插件的技能资产（SKILL.md / scripts/ / experiment/）由 agent preset
`dsh/insar-genie/` 携带（安装在 `~/.dsh/.agent-presets/insar-genie/skills/`）。

配套数据路径（settings → insar-genie）：
- `poeorbDir`：精密轨道目录（默认 `<实验目录>/poeorb`，可覆盖为公共轨道库）

gacos / dem / slc 目录当前由实验目录（exp.dir）管理，未单独暴露为设置项。
