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

export const inject = [
  "@deepseek-ai/dsh-client-runtime",
  "@deepseek-ai/dsh-client-locale",
  "@deepseek-ai/dsh-client-ui-settings-plugins",
];

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
 * - matched：selectInsarTurn 的返回（该 turn 有 insar 工具活动才认领）
 * - useSession：框架注入的会话快照选择器——从快照提取最新 insar_status 结果，
 *   实时反映 host 读取的真实进度（AI 每次调用 insar_status 面板自动更新）
 */
export function InsarTurnTail(props: {
  matched: InsarTurnData;
  useSession?: (selector: (s: unknown) => unknown) => unknown;
}): ReturnType<typeof createElement> | null {
  const snapshot = (props.useSession?.((s: unknown) => s) ?? undefined) as
    | { nodes?: readonly { kind?: string; call?: { name?: string; argsRaw?: string } | null; content?: readonly unknown[] }[] }
    | undefined;
  const latest = latestInsarStatus(snapshot?.nodes);

  // 1) 参数确认卡：insar_templates 结果（agent 查模板后向用户确认参数）
  if (props.matched?.paramConfirm) {
    return createElement(ParamConfirm, {
      terrain: props.matched.paramConfirm.terrain as TerrainType,
      params: props.matched.paramConfirm.params as unknown as ParamSnapshot,
      onConfirm: () => {},
      onCancel: () => {},
    });
  }

  // 2) 进度面板：优先最新会话快照的 insar_status 结果，其次 matched/注入
  const status = latest?.status ?? props.matched?.status;
  const experimentId = latest?.experimentId ?? props.matched?.registered?.experimentId;

  if (status) {
    return createElement(ProgressPanel, {
      experimentId,
      experimentLabel: undefined,
      fetchStatus: window.insarGenieBridge?.fetchStatus,
      initial: status,
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
  if (props.matched?.registered) {
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
      InsarTurnTail as never,
    );
    return () => {
      if (typeof off === "function") off();
    };
  });
}
