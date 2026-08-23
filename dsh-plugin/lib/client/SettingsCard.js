import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { PanelCard } from "./shared.js";
export const DEFAULT_SETTINGS = {
    earthdataUser: "",
    earthdataPassword: "",
    gacosEmail: "",
    gacosImapAuthCode: "",
    enviIdl: "",
    sarscapeLib: "",
    workDir: "G:\\",
    poeorbDir: "",
};
const FIELD_LABELS = {
    earthdataUser: "ASF 账号",
    earthdataPassword: "ASF 密码",
    gacosEmail: "GACOS 邮箱",
    gacosImapAuthCode: "GACOS 邮箱 IMAP 授权码",
    enviIdl: "ENVI IDL 路径",
    sarscapeLib: "SARscape 路径",
    workDir: "工作目录",
    poeorbDir: "POEORB 目录",
};
/**
 * 设置卡片：凭证/路径/POEORB 表单 + 实验列表。
 * 挂载于 settings.section（设置页插件区）。
 *
 * **受控组件**：value 全部来自 props.settings（父级经 settingsScope 从 host 读，含启动
 * 探测的 base 默认值），用户改动通过 onChange 通知父级写回 host。组件自己不持有状态，
 * 保证 host 值更新（scope 变化）能反映到字段。
 *
 * autoDetected 标记（若有）则额外显示"▲ 启动时自动定位"。
 */
export function SettingsCard(props) {
    const settings = { ...DEFAULT_SETTINGS, ...(props.settings ?? {}) };
    // 敏感字段"显示/隐藏"状态（仅本地 UI，不影响持久化；key = 敏感字段名）
    const [revealed, setRevealed] = useState({});
    const update = (key, value) => {
        props.onChange?.({ ...settings, [key]: value });
    };
    /** 敏感字段（存密码/授权码，默认隐藏，可切换显示） */
    const isSecret = (key) => key === "earthdataPassword" || key === "gacosImapAuthCode";
    const toggleReveal = (key) => setRevealed((prev) => ({ ...prev, [key]: !prev[key] }));
    return (_jsxs(PanelCard, { title: "insar-genie \u8BBE\u7F6E", children: [_jsx("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 12 }, children: Object.keys(FIELD_LABELS).map((key) => (_jsxs("label", { style: { display: "flex", flexDirection: "column", fontSize: 12 }, children: [FIELD_LABELS[key], _jsx("span", { style: { fontSize: 11, color: "#2e7d32" }, children: props.autoDetected?.[key] ? "▲ 启动时自动定位" : "" }), _jsxs("div", { style: { display: "flex", alignItems: "center", gap: 4 }, children: [_jsx("input", { type: isSecret(key) && !revealed[key] ? "password" : "text", value: settings[key], onChange: (e) => update(key, e.target.value), style: { marginTop: 2, padding: "2px 6px", flex: 1 } }), isSecret(key) && (_jsx("button", { type: "button", "aria-label": revealed[key] ? `隐藏${FIELD_LABELS[key]}` : `显示${FIELD_LABELS[key]}`, onClick: () => toggleReveal(key), title: revealed[key] ? "隐藏" : "显示", style: {
                                        marginTop: 2,
                                        border: "none",
                                        background: "transparent",
                                        cursor: "pointer",
                                        fontSize: 14,
                                        padding: "2px 4px",
                                    }, children: revealed[key] ? "🙈" : "👁" }))] })] }, key))) }), _jsx("button", { onClick: () => props.onSave?.(settings), style: { padding: "4px 12px" }, children: "\u4FDD\u5B58\u8BBE\u7F6E" }), props.experiments && props.experiments.length > 0 && (_jsxs("div", { style: { marginTop: 16 }, children: [_jsx("div", { style: { fontWeight: 600, marginBottom: 4 }, children: "\u5B9E\u9A8C\u5217\u8868" }), _jsx("ul", { style: { margin: 0, paddingLeft: 16 }, children: props.experiments.map((e) => (_jsxs("li", { style: { fontSize: 13 }, children: [e.name, " \u00B7 ", e.terrain, " \u00B7 ", e.status] }, e.id))) })] }))] }));
}
