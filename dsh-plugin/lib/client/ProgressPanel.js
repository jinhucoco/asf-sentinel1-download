import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useState } from "react";
import { PanelCard, STEP_LABELS } from "./shared.js";
/**
 * 进度面板：五步进度条 + 剩余时间 + 异常区。
 * 挂载于 conversation.chat.turnTail。
 *
 * 数据源（按优先级）：
 * 1. snapshot —— 会话快照实时提取的 insar_status 结果（host→client 原生通道；
 *    快照每次更新面板随之刷新，无需轮询）
 * 2. fetchStatus —— 注入的轮询函数（30s，window.insarGenieBridge 或 props 注入）
 * 3. initial —— 一次性初始值（仅挂载时生效）
 */
export function ProgressPanel(props) {
    const [status, setStatus] = useState(props.initial ?? null);
    const [error, setError] = useState(null);
    useEffect(() => {
        if (!props.fetchStatus || !props.experimentId)
            return;
        let cancelled = false;
        const tick = async () => {
            try {
                const s = await props.fetchStatus(props.experimentId);
                if (!cancelled) {
                    setStatus(s);
                    setError(null);
                }
            }
            catch (e) {
                if (!cancelled)
                    setError(e instanceof Error ? e.message : String(e));
            }
        };
        tick();
        const timer = setInterval(tick, 30_000); // 30s 轮询
        return () => {
            cancelled = true;
            clearInterval(timer);
        };
    }, [props.experimentId, props.fetchStatus]);
    // 会话快照实时值优先（host 工具结果每次到达都重渲染）
    const display = props.snapshot ?? status;
    const title = `SBAS 实验进度${props.experimentLabel ? ` · ${props.experimentLabel}` : ""}`;
    // 无数据源且无 initial：显示占位提示（不误导）
    if (!display && !error) {
        return (_jsx(PanelCard, { title: title, children: _jsx("span", { style: { color: "#888" }, children: "\u7B49\u5F85\u8FDB\u5EA6\u6570\u636E\u2026\uFF08\u5B9E\u9A8C\u542F\u52A8\u540E\u663E\u793A\uFF09" }) }));
    }
    if (error) {
        return (_jsx(PanelCard, { title: title, children: _jsxs("span", { style: { color: "#c00" }, children: ["\u26A0\uFE0F \u65E0\u6CD5\u8BFB\u53D6\u8FDB\u5EA6\uFF1A", error] }) }));
    }
    // 数据缺失（host 返回 error 而非全零）
    if (display?.error) {
        return (_jsx(PanelCard, { title: title, children: _jsxs("span", { style: { color: "#c00" }, children: ["\u26A0\uFE0F ", display.error.detail || display.progressLabel] }) }));
    }
    const stepIndex = Math.min(display.stepIndex, STEP_LABELS.length - 1);
    const etaH = Math.round(display.etaMinutes / 60);
    return (_jsxs(PanelCard, { title: title, children: [_jsx("div", { style: { display: "flex", gap: 4, marginBottom: 8 }, children: STEP_LABELS.map((label, i) => (_jsx("div", { style: {
                        flex: 1,
                        padding: 4,
                        textAlign: "center",
                        fontSize: 12,
                        borderRadius: 4,
                        background: i < stepIndex ? "#4caf50" : i === stepIndex ? "#ff9800" : "#eee",
                        color: i <= stepIndex ? "#fff" : "#666",
                    }, children: label }, label))) }), _jsx("div", { style: { marginBottom: 4 }, children: _jsx("strong", { children: display.progressLabel }) }), display.totalPairs > 0 && (_jsxs("div", { style: { marginBottom: 4 }, children: ["\u5DF2\u5B8C\u6210 ", display.donePairs, "/", display.totalPairs, " \u5BF9", display.pairsPerMinute > 0 && (_jsxs("span", { children: [" \u00B7 \u901F\u7387 ", display.pairsPerMinute.toFixed(2), " \u5BF9/\u5206"] })), etaH > 0 && _jsxs("span", { children: [" \u00B7 \u9884\u8BA1\u5269\u4F59\u7EA6 ", etaH, " \u5C0F\u65F6"] })] })), display.diskGb > 0 && _jsxs("div", { style: { color: "#888" }, children: ["\u6570\u636E\u76D8\u5360\u7528\uFF1A", display.diskGb.toFixed(1), " GB"] }), display.isStalled && (_jsx("div", { style: { border: "1px solid #e91e63", color: "#c2185b", padding: 6, marginTop: 8, borderRadius: 4 }, children: "\u26A0\uFE0F \u68C0\u6D4B\u5230\u505C\u6EDE\uFF1A\u8FDB\u7A0B\u53EF\u80FD\u672A\u5728\u63A8\u8FDB" }))] }));
}
