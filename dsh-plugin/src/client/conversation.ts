import type {
  ConversationMatch,
  ConversationMatchResult,
  ConversationNodeContext,
  ConversationNodeDefinition,
  TurnLocation,
} from "@deepseek-ai/dsh-client-runtime/client";
import { isAppendSurfaceEvent } from "@deepseek-ai/dsh-client-runtime/client";
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
  registered?: { ok: boolean; experimentId: string };
  /** 最近一次 insar_templates 的参数模板（terrain 取工具参数） */
  paramConfirm?: { terrain: string; params: Record<string, unknown> };
}

/** 本 Definition 关注的 insar 工具名 */
const INSAR_TOOLS = new Set(["insar_status", "insar_list", "insar_register", "insar_templates"]);

/** 单 turn 累积状态 */
interface InsarGenieState {
  turn: number;
  /** callId -> { name, args }（tool/result 需要配对 tool/call 才知道是哪个工具、参数是什么） */
  calls: Map<string, { name: string; args: string }>;
  status?: ProgressSnapshot;
  experiments?: InsarExperimentItem[];
  registered?: { ok: boolean; experimentId: string };
  paramConfirm?: { terrain: string; params: Record<string, unknown> };
}

/**
 * 从 tool/result 事件的 message.content 提取 render 输出的 JSON 文本。
 * host JSON_OUTPUT.render 产出 [{type:"text", text: JSON.stringify(value)}]，
 * message.content 是 [ToolResultBlock]，其 content 是 ContentBlock[]。
 */
function extractToolResultText(content: readonly unknown[] | undefined): string | null {
  const block = content?.[0] as { type?: string; content?: readonly unknown[] } | undefined;
  if (!block || block.type !== "tool-result") return null;
  const inner = (block.content ?? []) as readonly { type?: string; text?: string }[];
  for (const c of inner) {
    if (c.type === "text" && typeof c.text === "string") return c.text;
  }
  return null;
}

/** 解析 tool/result 中的结构化 JSON；失败返回 undefined（不中断状态机） */
function parseToolResultJson(content: readonly unknown[] | undefined): unknown {
  const text = extractToolResultText(content);
  if (!text) return undefined;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return undefined;
  }
}

/** 单 turn 内累积 insar 工具结果的 Conversation 业务 Definition */
export const insarGenieDefinition: ConversationNodeDefinition<InsarGenieState> = {
  kind: "insar-genie",
  match(event): ConversationMatchResult | null {
    if (event.type === "turn/start") {
      return { id: String(event.data.turn), role: "start" };
    }
    // 只累积 insar 工具的活动；其他工具事件不匹配，Definition 保持休眠
    if (event.type === "tool/call" && INSAR_TOOLS.has(event.data.name)) {
      return { id: String(event.data.turn), role: "update" };
    }
    if (event.type === "tool/result" && isAppendSurfaceEvent(event)) {
      return { id: String(event.data.turn), role: "update" };
    }
    return null;
  },
  start(context: ConversationNodeContext<InsarGenieState>, match: ConversationMatch): InsarGenieState {
    if (match.event.type !== "turn/start") {
      throw new Error("insar-genie start requires turn/start");
    }
    return { turn: match.event.data.turn, calls: new Map() };
  },
  update(
    context: ConversationNodeContext<InsarGenieState> & { state: InsarGenieState },
    match: ConversationMatch,
  ): InsarGenieState {
    const state = context.state;
    if (match.event.type === "tool/call") {
      const calls = new Map(state.calls);
      calls.set(String(match.event.data.callId), {
        name: match.event.data.name,
        args: match.event.data.arguments,
      });
      return { ...state, calls };
    }
    if (match.event.type !== "tool/result") return state;

    const callId = String(match.event.data.message.source.callId);
    const call = state.calls.get(callId);
    if (!call || !INSAR_TOOLS.has(call.name)) return state;

    const json = parseToolResultJson(match.event.data.message.content);
    if (json === undefined) return state;

    if (call.name === "insar_status" && isProgressSnapshot(json)) {
      return { ...state, status: json };
    }
    if (call.name === "insar_list" && isExperimentList(json)) {
      return { ...state, experiments: json.experiments };
    }
    if (call.name === "insar_register" && isRegistered(json)) {
      return { ...state, registered: { ok: json.ok === true, experimentId: json.experimentId } };
    }
    if (call.name === "insar_templates" && isParams(json)) {
      // terrain 从 tool/call 参数取（insar_templates 入参是 terrain）
      let terrain = "";
      try {
        const callArgs = JSON.parse(call.args) as { terrain?: unknown };
        if (typeof callArgs.terrain === "string") terrain = callArgs.terrain;
      } catch {
        // 参数缺失/不可解析时 terrain 留空
      }
      return { ...state, paramConfirm: { terrain, params: json as Record<string, unknown> } };
    }
    return state;
  },
  buildLocationData(
    context: ConversationNodeContext<InsarGenieState>,
    scope: "step" | "turn",
  ): { kind: "turn"; turn: number; key: "insar-genie"; value: InsarTurnData } | null {
    if (scope !== "turn" || context.state === undefined) return null;
    const { status, experiments, registered, paramConfirm } = context.state;
    if (!status && !experiments && !registered && !paramConfirm) return null;
    return {
      kind: "turn",
      turn: context.state.turn,
      key: "insar-genie",
      value: { status, experiments, registered, paramConfirm },
    };
  },
};

/** turnTail chain select：仅当该 turn 有 insar 工具结果时认领，否则 null 放行其他贡献者 */
export function selectInsarTurn(owner: { turn: TurnLocation }): InsarTurnData | null {
  const data = owner.turn.data.get("insar-genie");
  if (!data) return null;
  if (!data.status && !data.experiments && !data.registered && !data.paramConfirm) return null;
  return data;
}

/** 会话快照里的 tool-result 节点（宽松形状，避免 client 依赖 host 类型） */
interface ToolResultLike {
  kind?: string;
  seq?: number;
  call?: { name?: string; argsRaw?: string } | null;
  content?: readonly unknown[];
}

/**
 * 从 ConversationSnapshot 提取最新一次 insar_status 的结构化结果。
 * 这是 host→client 的真实数据通道：host 工具结果经会话事件流到达 client，
 * 组件订阅快照即可实时显示，无需 window 桥、无需 30s 轮询。
 * @param nodes - snapshot.nodes（legacy 兼容字段，所有已物化会话节点）
 * @returns 最新 insar_status 结果 + 工具调用参数里的 experimentId（可作标签），无则 null
 */
export function latestInsarStatus(
  nodes: readonly ToolResultLike[] | undefined,
): { status: ProgressSnapshot; experimentId?: string } | null {
  if (!nodes || nodes.length === 0) return null;
  // nodes 按 seq 升序（legacy 快照排序保证），取最后一个命中的 insar_status；
  // 同时用 seq 显式比较兜底，防止调用方传无序数组时仍取到最新。
  let latest: ToolResultLike | null = null;
  for (const node of nodes) {
    if (node?.kind !== "tool-result") continue;
    if (node.call?.name !== "insar_status") continue;
    if (!latest || (node.seq ?? 0) >= (latest.seq ?? 0)) latest = node;
  }
  if (!latest) return null;
  const json = parseToolResultJson(latest.content);
  if (!isProgressSnapshot(json)) return null;
  let experimentId: string | undefined;
  try {
    const args = JSON.parse(latest.call?.argsRaw ?? "{}") as { experimentId?: unknown };
    if (typeof args.experimentId === "string") experimentId = args.experimentId;
  } catch {
    // 参数缺失/不可解析时忽略
  }
  return { status: json, experimentId };
}

function isProgressSnapshot(v: unknown): v is ProgressSnapshot {
  return (
    typeof v === "object" &&
    v !== null &&
    typeof (v as ProgressSnapshot).stepIndex === "number" &&
    typeof (v as ProgressSnapshot).progressLabel === "string"
  );
}

function isExperimentList(v: unknown): v is { experiments: InsarExperimentItem[] } {
  return (
    typeof v === "object" &&
    v !== null &&
    Array.isArray((v as { experiments?: unknown }).experiments) &&
    ((v as { experiments: unknown[] }).experiments as unknown[]).every(
      (e) => typeof e === "object" && e !== null && typeof (e as InsarExperimentItem).id === "string",
    )
  );
}

function isRegistered(v: unknown): v is { ok: boolean; experimentId: string } {
  return (
    typeof v === "object" &&
    v !== null &&
    typeof (v as { experimentId?: unknown }).experimentId === "string"
  );
}

/** insar_templates 返回的参数模板（ExperimentParams 形状的宽松校验） */
function isParams(v: unknown): v is Record<string, unknown> {
  return (
    typeof v === "object" &&
    v !== null &&
    typeof (v as { rgLooks?: unknown }).rgLooks === "number"
  );
}
