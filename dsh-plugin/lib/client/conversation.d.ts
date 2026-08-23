import type { ConversationNodeDefinition, TurnLocation } from "@deepseek-ai/dsh-client-runtime/client";
import type { ProgressSnapshot } from "./shared.js";
/** 把 insar turn 数据合并进引擎的 turn 级业务数据表（deliverables/turn-tail 同款模式） */
declare module "@deepseek-ai/dsh-client-runtime/client" {
    interface ConversationTurnDataMap {
        "insar-genie": InsarTurnData;
    }
}
/**
 * host→client 数据接线（第 3 点）：
 * DSH 无同步 host 工具调用通道，但 host 工具结果（insar_status / insar_list /
 * insar_register）作为 tool/result 会话事件已经流入 client 的 ConversationSnapshot。
 * 本模块注册一个 ConversationNodeDefinition，把这些 insar 工具结果累积到
 * turn 级业务数据（ConversationTurnDataMap['insar-genie']），turnTail 的
 * chain select 读取该数据决定是否认领渲染——与官方 ui-deliverables 完全同构。
 */
/** insar_list 返回的实验条目 */
export interface InsarExperimentItem {
    id: string;
    name: string;
    terrain: string;
    status: string;
}
/** 发布到 turn 的 insar 业务数据（turnTail select 与组件读取） */
export interface InsarTurnData {
    /** 最近一次 insar_status 的结构化结果（host computeStatus 的 JSON） */
    status?: ProgressSnapshot;
    /** 最近一次 insar_list 的实验列表 */
    experiments?: InsarExperimentItem[];
    /** 最近一次 insar_register 的注册结果 */
    registered?: {
        ok: boolean;
        experimentId: string;
    };
    /** 最近一次 insar_templates 的参数模板（terrain 取工具参数） */
    paramConfirm?: {
        terrain: string;
        params: Record<string, unknown>;
    };
}
/** 单 turn 累积状态 */
interface InsarGenieState {
    turn: number;
    /** callId -> { name, args }（tool/result 需要配对 tool/call 才知道是哪个工具、参数是什么） */
    calls: Map<string, {
        name: string;
        args: string;
    }>;
    status?: ProgressSnapshot;
    experiments?: InsarExperimentItem[];
    registered?: {
        ok: boolean;
        experimentId: string;
    };
    paramConfirm?: {
        terrain: string;
        params: Record<string, unknown>;
    };
}
/** 单 turn 内累积 insar 工具结果的 Conversation 业务 Definition */
export declare const insarGenieDefinition: ConversationNodeDefinition<InsarGenieState>;
/** turnTail chain select：仅当该 turn 有 insar 工具结果时认领，否则 null 放行其他贡献者 */
export declare function selectInsarTurn(owner: {
    turn: TurnLocation;
}): InsarTurnData | null;
/** 会话快照里的 tool-result 节点（宽松形状，避免 client 依赖 host 类型） */
interface ToolResultLike {
    kind?: string;
    seq?: number;
    call?: {
        name?: string;
        argsRaw?: string;
    } | null;
    content?: readonly unknown[];
}
/**
 * 从 ConversationSnapshot 提取最新一次 insar_status 的结构化结果。
 * 这是 host→client 的真实数据通道：host 工具结果经会话事件流到达 client，
 * 组件订阅快照即可实时显示，无需 window 桥、无需 30s 轮询。
 * @param nodes - snapshot.nodes（legacy 兼容字段，所有已物化会话节点）
 * @returns 最新 insar_status 结果 + 工具调用参数里的 experimentId（可作标签），无则 null
 */
export declare function latestInsarStatus(nodes: readonly ToolResultLike[] | undefined): {
    status: ProgressSnapshot;
    experimentId?: string;
} | null;
export {};
