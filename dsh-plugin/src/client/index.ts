import { createElement } from "react";
import { ProgressPanel } from "./ProgressPanel.js";
import { ParamConfirm } from "./ParamConfirm.js";
import { SettingsCard } from "./SettingsCard.js";
import type { ParamSnapshot, ProgressSnapshot, TerrainType } from "./shared.js";

/**
 * insar-genie-dsh client 入口。
 * 通过 DSH client 插槽注册：
 * - turnTail（conversation.chat.turnTail）：按注入 kind 渲染 ProgressPanel 或 ParamConfirm
 * - settings.section：SettingsCard（设置页插件区）
 *
 * 数据接线：DSH client 无同步 host 工具调用通道，host/agent 把数据作为 props 注入
 * （turnTail 的 inject 回调可从会话/消息上下文携带进度快照或参数快照）；
 * ProgressPanel 也支持 fetchStatus 轮询注入（window.insarGenieBridge）。
 */
export const name = "insar-genie-dsh";

export const inject = [
  "@deepseek-ai/dsh-client-runtime",
  "@deepseek-ai/dsh-client-locale",
  "@deepseek-ai/dsh-client-ui-settings-plugins",
];

/** host 侧注入的运行时桥（可选；无则走 props 注入） */
declare global {
  interface Window {
    insarGenieBridge?: {
      fetchStatus?: (experimentId: string) => Promise<ProgressSnapshot>;
      experiments?: { id: string; name: string; terrain: string; status: string }[];
    };
  }
}

/** turnTail 注入的 props（由 host/agent 决定渲染哪个组件） */
interface TurnTailProps {
  kind?: "progress" | "param-confirm";
  // ProgressPanel
  experimentId?: string;
  experimentLabel?: string;
  fetchStatus?: (experimentId: string) => Promise<ProgressSnapshot>;
  initialProgress?: ProgressSnapshot;
  // ParamConfirm
  terrain?: TerrainType;
  params?: ParamSnapshot;
  onConfirm?: () => void;
  onCancel?: () => void;
}

function renderTurnTail(props: TurnTailProps | undefined) {
  if (props?.kind === "param-confirm" && props.terrain && props.params) {
    return createElement(ParamConfirm, {
      terrain: props.terrain,
      params: props.params,
      onConfirm: props.onConfirm ?? (() => {}),
      onCancel: props.onCancel ?? (() => {}),
    });
  }
  // 默认：进度面板
  return createElement(ProgressPanel, {
    experimentId: props?.experimentId,
    experimentLabel: props?.experimentLabel,
    fetchStatus: props?.fetchStatus ?? window.insarGenieBridge?.fetchStatus,
    initial: props?.initialProgress,
  });
}

export function apply(ctx: any): void {
  // settings.section：设置卡片（设置页插件区）
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

  // conversation.chat.turnTail：进度面板 / 参数确认卡（按注入 kind 渲染）
  ctx.slots.inject("conversation.chat.turnTail", () => {
    const off = ctx.slots.register(
      {
        name: "conversation.chat.turnTail",
        priority: -1,
        registrant: "insar-genie-dsh",
        inject: () => ({}),
      },
      (props: TurnTailProps | undefined) => renderTurnTail(props),
    );
    return () => {
      if (typeof off === "function") off();
    };
  });
}
