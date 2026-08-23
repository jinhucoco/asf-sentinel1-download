import { createElement } from "react";
import { ProgressPanel } from "./ProgressPanel.js";
import { ParamConfirm } from "./ParamConfirm.js";
import { SettingsCard } from "./SettingsCard.js";
import {
  insarGenieDefinition,
  latestInsarStatus,
  selectInsarTurn,
  type InsarTurnData,
} from "./conversation.js";
import type { ParamSnapshot, ProgressSnapshot, TerrainType } from "./shared.js";

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
export const name = "insar-genie-dsh";

export const inject = ["slots", "conversationEvents"];

/** host 侧注入的运行时桥（可选；无则走会话快照提取） */
declare global {
  interface Window {
    insarGenieBridge?: {
      fetchStatus?: (experimentId: string) => Promise<ProgressSnapshot>;
      experiments?: { id: string; name: string; terrain: string; status: string }[];
    };
  }
}

/** turnTail 组件（chain 注册，session 作用域）：
 * - matched：selectInsarTurn 的返回（该 turn 有 insar 工具活动才认领）——**本 turn 数据优先**
 * - useSession：框架注入的会话快照选择器——仅用于对"本 turn 已有 insar_status 活动"的
 *   实验做实时刷新（AI 在同一实验上再次调用 insar_status 时面板自动更新）。
 *   不做跨 turn 泄漏：其他 turn 的 insar 活动由它们自己的 turnTail 渲染。
 */
export function InsarTurnTail(props: {
  matched: InsarTurnData;
  useSession: (selector: (s: unknown) => unknown) => unknown;
}): ReturnType<typeof createElement> | null {
  // session 作用域插槽恒注入 useSession（SessionStandardProps），直接调用（规则-of-hooks）
  const snapshot = props.useSession((s: unknown) => s) as
    | { nodes?: readonly { kind?: string; seq?: number; call?: { name?: string; argsRaw?: string } | null; content?: readonly unknown[] }[] }
    | undefined;
  const latest = latestInsarStatus(snapshot?.nodes);

  // 1) 参数确认卡：insar_templates 结果（agent 查模板后向用户确认参数）。
  //    优先于进度面板：同一 turn 既查模板又查状态时，先确认参数再展示进度。
  if (props.matched?.paramConfirm) {
    return createElement(ParamConfirm, {
      terrain: props.matched.paramConfirm.terrain as TerrainType,
      params: props.matched.paramConfirm.params as unknown as ParamSnapshot,
      onConfirm: () => {},
      onCancel: () => {},
    });
  }

  // 2) 进度面板：仅当**本 turn** 有 insar_status 活动时渲染（matched.status 是本 turn 的
  //    最后结果）。快照 latest 只作为同一实验的实时刷新值——通过 snapshot prop 传入，
  //    快照更新会重渲染并更新面板（initial 只挂载生效，不能承担实时刷新）。
  //    无 matched.status 时不渲染进度面板，避免历史 turn 的 insar_status 泄漏压制
  //    本 turn 的 experiments/registered 分支。
  if (props.matched?.status) {
    return createElement(ProgressPanel, {
      experimentId: latest?.experimentId,
      experimentLabel: undefined,
      fetchStatus: window.insarGenieBridge?.fetchStatus,
      initial: props.matched.status,
      snapshot: latest?.status,
    });
  }
  if (props.matched?.experiments && props.matched.experiments.length > 0) {
    return createElement(SettingsCard, {
      experiments: props.matched.experiments,
      onSave: (s: unknown) => {
        console.info("[insar-genie] settings save requested", s);
      },
    });
  }
  if (props.matched?.registered && props.matched.registered.ok) {
    return createElement(
      "div",
      {
        style: {
          border: "1px solid #ccc",
          borderRadius: 8,
          padding: 12,
          margin: "8px 0",
          maxWidth: 640,
          fontSize: 13,
        },
      },
      `✅ 实验已注册：${props.matched.registered.experimentId}`,
    );
  }
  return null;
}

export function apply(ctx: any): void {
  // 1) conversationEvents：累积 insar 工具结果到 turn 业务数据
  ctx.conversationEvents.register(insarGenieDefinition);

  // 2) settings.section：设置卡片（设置页插件区，list + root scope）
  ctx.slots.inject("settings.section", () => {
    const off = ctx.slots.register(
      {
        name: "settings.section",
        id: "insar-genie",
        order: 40,
        label: () => "insar-genie",
        inject: () => ({ experiments: window.insarGenieBridge?.experiments }),
      },
      (props: any) =>
        createElement(SettingsCard, {
          experiments: props?.experiments,
          onSave: (s: unknown) => {
            console.info("[insar-genie] settings save requested", s);
          },
        }),
    );
    return () => {
      if (typeof off === "function") off();
    };
  });

  // 3) conversation.chat.turnTail：进度面板（chain，session 作用域）
  //    chain 注册必须有 select：仅当该 turn 有 insar 工具活动时认领，否则 null 放行
  //    （deliverables 同款；缺 select 在真实 shell 注册时会 throw）
  ctx.slots.inject("conversation.chat.turnTail", () => {
    const off = ctx.slots.register(
      {
        name: "conversation.chat.turnTail",
        select: selectInsarTurn,
        registrant: "insar-genie-dsh",
      },
      InsarTurnTail,
    );
    return () => {
      if (typeof off === "function") off();
    };
  });
}
