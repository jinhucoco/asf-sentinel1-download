import { jsxs as _jsxs, jsx as _jsx } from "react/jsx-runtime";
import { useState } from "react";
import { PanelCard, TERRAIN_LABELS, validateBaseline } from "./shared.js";
/**
 * 参数确认卡片：地形联动参数 + 2-4% 基线防呆。
 * 挂载于 conversation.chat.turnTail；AI 生成参数后渲染，用户确认后才执行。
 */
export function ParamConfirm(props) {
    const [params, setParams] = useState(props.params);
    const gate = validateBaseline(params.maxPercBaseline);
    const update = (patch) => {
        const next = { ...params, ...patch };
        setParams(next);
        props.onChange?.(next);
    };
    return (_jsxs(PanelCard, { title: "\u5B9E\u9A8C\u53C2\u6570\u786E\u8BA4", children: [_jsxs("div", { style: { marginBottom: 8 }, children: ["\u5730\u5F62\uFF1A", TERRAIN_LABELS[props.terrain]] }), _jsxs("label", { style: { display: "block", marginBottom: 6 }, children: ["\u7A7A\u95F4\u57FA\u7EBF\uFF08% of critical\uFF09\uFF1A", _jsx("input", { type: "number", value: params.maxPercBaseline, onChange: (e) => update({ maxPercBaseline: Number(e.target.value) }), style: {
                            marginLeft: 6,
                            width: 80,
                            border: gate.ok ? "1px solid #ccc" : "2px solid #d32f2f",
                        } })] }), !gate.ok && (_jsxs("div", { style: { color: "#d32f2f", marginBottom: 6 }, children: ["\u26A0\uFE0F ", gate.message] })), _jsxs("div", { style: { marginBottom: 6 }, children: ["\u591A\u89C6 ", params.rgLooks, ":", params.azLooks, " \u00B7 \u65F6\u95F4\u57FA\u7EBF ", params.maxTimeBaselineDays, " \u5929 \u00B7 \u6EE4\u6CE2 ", params.filtering, " ", params.goldsteinWinSize, " \u00B7 \u89E3\u7F20 ", params.unwrap, " \u9608\u503C ", params.unwrapCohThreshold, " \u00B7 GACOS ", params.useGacos ? "开" : "关"] }), _jsxs("div", { children: [_jsx("button", { onClick: props.onConfirm, disabled: !gate.ok, style: { marginRight: 8, padding: "4px 12px" }, children: "\u786E\u8BA4\u6267\u884C" }), _jsx("button", { onClick: props.onCancel, style: { padding: "4px 12px" }, children: "\u53D6\u6D88" })] })] }));
}
