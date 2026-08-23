window.__ModuleLoader__.load({ id: "@dsh-custom/insar-genie-dsh", factory: (require) => {

		var module = { exports: {} };
		var exports = module.exports;
import { createElement } from "react";
import "@deepseek-ai/dsh-client-runtime/client";
//#region src/client/SettingsCard.d.ts
/** 设置表单字段（与 host settings.ts 的 SettingsSchema 对齐） */
interface SettingsShape {
  earthdataUser: string;
  earthdataPassword: string;
  gacosEmail: string;
  gacosImapAuthCode: string;
  enviIdl: string;
  sarscapeLib: string;
  workDir: string;
  poeorbDir: string;
}
//#endregion
//#region src/client/shared.d.ts
/** 进度快照（与 host shared/types.ts 的 ExperimentStatus 对齐；client 独立声明避免 host 依赖） */
interface ProgressSnapshot {
  stepIndex: number;
  totalSteps: number;
  donePairs: number;
  totalPairs: number;
  pairsPerMinute: number;
  etaMinutes: number;
  diskGb: number;
  progressLabel: string;
  isStalled: boolean;
  error?: {
    code: string;
    detail: string;
    evidence: string;
  };
}
//#endregion
//#region src/client/conversation.d.ts
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
interface InsarExperimentItem {
  id: string;
  name: string;
  terrain: string;
  status: string;
}
/** 发布到 turn 的 insar 业务数据（turnTail select 与组件读取） */
interface InsarTurnData {
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
//#endregion
//#region src/client/index.d.ts
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
declare const name = "insar-genie-dsh";
declare const inject: string[];
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
declare function InsarTurnTail(props: {
  matched: InsarTurnData;
  useSession: (selector: (s: unknown) => unknown) => unknown;
}): ReturnType<typeof createElement> | null;
/**
 * SettingsCardBound：绑定 settingsScope 的容器组件。
 * - 挂载时从 scope.getSnapshot().value 读 host 设置值（含启动探测 base 默认）
 * - 订阅 scope 变化 → 更新显示（host 值变更时字段跟随）
 * - onChange 通过 scope.set 逐字段写回 host
 */
declare function SettingsCardBound(props: {
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
declare function apply(ctx: any): void;
//#endregion
export { InsarTurnTail, SettingsCardBound, apply, inject, name };
return module.exports; } });
//# sourceMappingURL=client.d.ts.map