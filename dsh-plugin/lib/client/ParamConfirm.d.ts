import { type ReactNode } from "react";
import { type ParamSnapshot, type TerrainType } from "./shared.js";
/**
 * 参数确认卡片：地形联动参数 + 2-4% 基线防呆。
 * 挂载于 conversation.chat.turnTail；AI 生成参数后渲染，用户确认后才执行。
 */
export declare function ParamConfirm(props: {
    terrain: TerrainType;
    params: ParamSnapshot;
    onChange?: (p: ParamSnapshot) => void;
    onConfirm: () => void;
    onCancel: () => void;
}): ReactNode;
