import { useEffect, useState, type ReactNode } from "react";
import { PanelCard, STEP_LABELS, type ProgressSnapshot } from "./shared.js";

/**
 * 进度面板：五步进度条 + 剩余时间 + 异常区。
 * 挂载于 conversation.chat.turnTail；自带 30s 轮询（不依赖 AI 主动汇报）。
 *
 * 数据获取通过注入的 fetchStatus（client 侧由 host/agent 通过 props 注入，
 * 或由调用方传入从 insar_status 工具获得的数据源）——见 client/index.ts 的接线说明。
 */
export function ProgressPanel(props: {
  experimentId?: string;
  experimentLabel?: string;
  fetchStatus?: (experimentId: string) => Promise<ProgressSnapshot>;
  initial?: ProgressSnapshot;
}): ReactNode {
  const [status, setStatus] = useState<ProgressSnapshot | null>(props.initial ?? null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!props.fetchStatus || !props.experimentId) return;
    let cancelled = false;
    const tick = async () => {
      try {
        const s = await props.fetchStatus!(props.experimentId!);
        if (!cancelled) {
          setStatus(s);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      }
    };
    tick();
    const timer = setInterval(tick, 30_000); // 30s 轮询
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [props.experimentId, props.fetchStatus]);

  const title = `SBAS 实验进度${props.experimentLabel ? ` · ${props.experimentLabel}` : ""}`;

  // 无数据源且无 initial：显示占位提示（不误导）
  if (!status && !error) {
    return (
      <PanelCard title={title}>
        <span style={{ color: "#888" }}>等待进度数据…（实验启动后显示）</span>
      </PanelCard>
    );
  }

  if (error) {
    return (
      <PanelCard title={title}>
        <span style={{ color: "#c00" }}>⚠️ 无法读取进度：{error}</span>
      </PanelCard>
    );
  }

  // 数据缺失（host 返回 error 而非全零）
  if (status?.error) {
    return (
      <PanelCard title={title}>
        <span style={{ color: "#c00" }}>⚠️ {status.error.detail || status.progressLabel}</span>
      </PanelCard>
    );
  }

  const stepIndex = Math.min(status!.stepIndex, STEP_LABELS.length - 1);
  const etaH = Math.round(status!.etaMinutes / 60);

  return (
    <PanelCard title={title}>
      {/* 五步进度条 */}
      <div style={{ display: "flex", gap: 4, marginBottom: 8 }}>
        {STEP_LABELS.map((label, i) => (
          <div
            key={label}
            style={{
              flex: 1,
              padding: 4,
              textAlign: "center",
              fontSize: 12,
              borderRadius: 4,
              background: i < stepIndex ? "#4caf50" : i === stepIndex ? "#ff9800" : "#eee",
              color: i <= stepIndex ? "#fff" : "#666",
            }}
          >
            {label}
          </div>
        ))}
      </div>

      <div style={{ marginBottom: 4 }}>
        <strong>{status!.progressLabel}</strong>
      </div>
      {status!.totalPairs > 0 && (
        <div style={{ marginBottom: 4 }}>
          已完成 {status!.donePairs}/{status!.totalPairs} 对
          {status!.pairsPerMinute > 0 && (
            <span> · 速率 {status!.pairsPerMinute.toFixed(2)} 对/分</span>
          )}
          {etaH > 0 && <span> · 预计剩余约 {etaH} 小时</span>}
        </div>
      )}
      {status!.diskGb > 0 && <div style={{ color: "#888" }}>数据盘占用：{status!.diskGb.toFixed(1)} GB</div>}

      {status!.isStalled && (
        <div style={{ border: "1px solid #e91e63", color: "#c2185b", padding: 6, marginTop: 8, borderRadius: 4 }}>
          ⚠️ 检测到停滞：进程可能未在推进
        </div>
      )}
    </PanelCard>
  );
}
