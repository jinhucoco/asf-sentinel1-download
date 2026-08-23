import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { validateBaseline } from "../shared/baseline.js";
export { validateBaseline };
/** 五步进度标签（与 host status.ts 一致） */
export const STEP_LABELS = ["连接图", "干涉", "解缠", "反演1", "反演2", "地理编码"];
export const TERRAIN_LABELS = {
    mining: "矿区",
    landslide: "滑坡",
    urban: "城市",
    desert: "沙漠",
    loess: "黄土高原",
};
/** turnTail 插槽渲染的通用包装（简单卡片容器） */
export function PanelCard(props) {
    return (_jsxs("div", { style: { border: "1px solid #ccc", borderRadius: 8, padding: 12, margin: "8px 0", maxWidth: 640 }, children: [_jsx("div", { style: { fontWeight: 600, marginBottom: 8 }, children: props.title }), props.children] }));
}
