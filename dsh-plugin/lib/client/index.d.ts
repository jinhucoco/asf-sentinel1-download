import { createElement } from "react";
import { type SettingsShape } from "./SettingsCard.js";
import { type InsarTurnData } from "./conversation.js";
import type { ProgressSnapshot } from "./shared.js";
/**
 * insar-genie-dsh client 入口。
 * 通过 DSH client 插槽注册：
 * - conversationEvents：insar 工具结果（insar_status/insar_list/insar_register）累积为
 *   turn 级业务数据（conversation.ts 的 insarGenieDefinition）
 * - turnTail（conversation.chat.turnTail，chain）：当一轮 turn 有 insar 工具活动时认领，
 *   组件通过框架注入的 useSession 从会话快照提取最新 insar_status 结果并渲染进度面板
 * - settings.section：SettingsCard（设置页插件区）
 *
 * 数据接线（host→client）：DSH 无同步 host 工具调用通道，但 host 工具结果作为
 * tool/result 会话事件流入 client 的 ConversationSnapshot——组件订阅快照即拿到
 * 真实数据，无需 window 桥、无需轮询。window.insarGenieBridge 仅保留为可选
 * 注入位（未来 host 若提供 HTTP 桥可直接替换），默认数据源是会话快照。
 */
export declare const name = "insar-genie-dsh";
export declare const inject: string[];
/** host 侧注入的运行时桥（可选；无则走会话快照提取） */
declare global {
    interface Window {
        insarGenieBridge?: {
            fetchStatus?: (experimentId: string) => Promise<ProgressSnapshot>;
            experiments?: {
                id: string;
                name: string;
                terrain: string;
                status: string;
            }[];
        };
    }
}
/** turnTail 组件（chain 注册，session 作用域）：
 * - matched：selectInsarTurn 的返回（该 turn 有 insar 工具活动才认领）——**本 turn 数据优先**
 * - useSession：框架注入的会话快照选择器——仅用于对"本 turn 已有 insar_status 活动"的
 *   实验做实时刷新（AI 在同一实验上再次调用 insar_status 时面板自动更新）。
 *   不做跨 turn 泄漏：其他 turn 的 insar 活动由它们自己的 turnTail 渲染。
 */
export declare function InsarTurnTail(props: {
    matched: InsarTurnData;
    useSession: (selector: (s: unknown) => unknown) => unknown;
}): ReturnType<typeof createElement> | null;
/**
 * SettingsCardBound：绑定 settingsScope 的容器组件。
 * - 挂载时从 scope.getSnapshot().value 读 host 设置值（含启动探测 base 默认）
 * - 订阅 scope 变化 → 更新显示（host 值变更时字段跟随）
 * - onChange 通过 scope.set 逐字段写回 host
 */
export declare function SettingsCardBound(props: {
    scope?: {
        getSnapshot(): {
            value?: SettingsShape;
        };
        subscribe(fn: () => void): () => void;
        set(field: string, value: unknown): void;
    };
    experiments?: {
        id: string;
        name: string;
        terrain: string;
        status: string;
    }[];
}): ReturnType<typeof createElement>;
export declare function apply(ctx: any): void;
