# assets

本插件的技能资产（SKILL.md / scripts/ / experiment/）由 agent preset
`dsh/insar-genie/` 携带（安装在 `~/.dsh/.agent-presets/insar-genie/skills/`）。

插件运行时通过设置命名空间的 `skillDir` 解析脚本路径，不重复打包 Python 资产。

配套数据路径（settings → insarGenie）：
- `poeorbDir`：精密轨道目录（默认 `<实验目录>/poeorb`，可覆盖为公共轨道库）
- `gacosDir` / `demDir` / `slcDir`：其余配套数据目录
