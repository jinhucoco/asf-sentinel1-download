import { useState, type ReactNode } from "react";
import { PanelCard, TERRAIN_LABELS, validateBaseline, type ParamSnapshot, type TerrainType } from "./shared.js";

/**
 * 参数确认卡片：地形联动参数 + 2-4% 基线防呆。
 * 挂载于 conversation.chat.turnTail；AI 生成参数后渲染，用户确认后才执行。
 */
export function ParamConfirm(props: {
  terrain: TerrainType;
  params: ParamSnapshot;
  onChange?: (p: ParamSnapshot) => void;
  onConfirm: () => void;
  onCancel: () => void;
}): ReactNode {
  const [params, setParams] = useState<ParamSnapshot>(props.params);
  const gate = validateBaseline(params.maxPercBaseline);

  const update = (patch: Partial<ParamSnapshot>) => {
    const next = { ...params, ...patch };
    setParams(next);
    props.onChange?.(next);
  };

  return (
    <PanelCard title="实验参数确认">
      <div style={{ marginBottom: 8 }}>地形：{TERRAIN_LABELS[props.terrain]}</div>

      <label style={{ display: "block", marginBottom: 6 }}>
        空间基线（% of critical）：
        <input
          type="number"
          value={params.maxPercBaseline}
          onChange={(e) => update({ maxPercBaseline: Number(e.target.value) })}
          style={{
            marginLeft: 6,
            width: 80,
            border: gate.ok ? "1px solid #ccc" : "2px solid #d32f2f",
          }}
        />
      </label>
      {!gate.ok && (
        <div style={{ color: "#d32f2f", marginBottom: 6 }}>⚠️ {gate.message}</div>
      )}

      <div style={{ marginBottom: 6 }}>
        多视 {params.rgLooks}:{params.azLooks} · 时间基线 {params.maxTimeBaselineDays} 天 · 滤波 {params.filtering} {params.goldsteinWinSize} · 解缠 {params.unwrap} 阈值 {params.unwrapCohThreshold} · GACOS {params.useGacos ? "开" : "关"}
      </div>

      <div>
        <button
          onClick={props.onConfirm}
          disabled={!gate.ok}
          style={{ marginRight: 8, padding: "4px 12px" }}
        >
          确认执行
        </button>
        <button onClick={props.onCancel} style={{ padding: "4px 12px" }}>
          取消
        </button>
      </div>
    </PanelCard>
  );
}
