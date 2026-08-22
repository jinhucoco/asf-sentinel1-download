window.__ModuleLoader__.load({ id: "insar-genie-dsh", factory: (require) => {
import "react";
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
//#region src/client/index.d.ts
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
declare const name = "insar-genie-dsh";
declare const inject: string[];
/** host 侧注入的运行时桥（可选；无则走 props 注入） */
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
declare function apply(ctx: any): void;
//#endregion
export { apply, inject, name };
return module.exports; } });
//# sourceMappingURL=client.d.ts.map