import { type ReactNode } from "react";
import { type ProgressSnapshot } from "./shared.js";
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
export declare function ProgressPanel(props: {
    experimentId?: string;
    experimentLabel?: string;
    fetchStatus?: (experimentId: string) => Promise<ProgressSnapshot>;
    initial?: ProgressSnapshot;
    snapshot?: ProgressSnapshot;
}): ReactNode;
