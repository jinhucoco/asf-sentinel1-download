import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { PanelCard } from "./shared.js";
const FIELD_LABELS = {
    earthdataUser: "ASF 账号",
    earthdataPassword: "ASF 密码",
    gacosEmail: "GACOS 邮箱",
    gacosImapAuthCode: "GACOS 邮箱授权码",
    enviIdl: "ENVI IDL 路径",
    sarscapeLib: "SARscape 路径",
    workDir: "工作目录",
    poeorbDir: "POEORB 目录",
};
/**
 * 设置卡片：凭证/路径/POEORB 表单 + 实验列表。
 * 挂载于 settings.section（设置页插件区）。
 * 数据通过注入的 settings + experiments 传入（host/agent 接线），本组件只做展示与编辑回调。
 *
 * 启动时路径探测：host 侧在 base 层填好 enviIdl/sarscapeLib 默认值，
 * 字段里已显示探测路径 —— 无需手动填专业软件路径（普通用户友好）。
 * autoDetected 标记（若有）则额外显示"▲ 启动时自动定位"。
 */
export function SettingsCard(props) {
    const [settings, setSettings] = useState({
        earthdataUser: "",
        earthdataPassword: "",
        gacosEmail: "",
        gacosImapAuthCode: "",
        enviIdl: "",
        sarscapeLib: "",
        workDir: "G:\\",
        poeorbDir: "",
        ...(props.settings ?? {}),
    });
    const update = (key, value) => {
        setSettings((prev) => ({ ...prev, [key]: value }));
    };
    return (_jsxs(PanelCard, { title: "insar-genie \u8BBE\u7F6E", children: [_jsx("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 12 }, children: Object.keys(FIELD_LABELS).map((key) => (_jsxs("label", { style: { display: "flex", flexDirection: "column", fontSize: 12 }, children: [FIELD_LABELS[key], _jsx("span", { style: { fontSize: 11, color: "#2e7d32" }, children: props.autoDetected?.[key] ? "▲ 启动时自动定位" : "" }), _jsx("input", { type: key === "earthdataPassword" || key === "gacosImapAuthCode" ? "password" : "text", value: settings[key], onChange: (e) => update(key, e.target.value), style: { marginTop: 2, padding: "2px 6px" } })] }, key))) }), _jsx("button", { onClick: () => props.onSave?.(settings), style: { padding: "4px 12px" }, children: "\u4FDD\u5B58\u8BBE\u7F6E" }), props.experiments && props.experiments.length > 0 && (_jsxs("div", { style: { marginTop: 16 }, children: [_jsx("div", { style: { fontWeight: 600, marginBottom: 4 }, children: "\u5B9E\u9A8C\u5217\u8868" }), _jsx("ul", { style: { margin: 0, paddingLeft: 16 }, children: props.experiments.map((e) => (_jsxs("li", { style: { fontSize: 13 }, children: [e.name, " \u00B7 ", e.terrain, " \u00B7 ", e.status] }, e.id))) })] }))] }));
}
