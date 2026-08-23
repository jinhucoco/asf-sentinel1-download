import { useState, type ReactNode } from "react";
import { PanelCard } from "./shared.js";

/** 设置表单字段（与 host settings.ts 的 SettingsSchema 对齐） */
export interface SettingsShape {
  earthdataUser: string;
  earthdataPassword: string;
  gacosEmail: string;
  gacosImapAuthCode: string;
  enviIdl: string;
  sarscapeLib: string;
  workDir: string;
  poeorbDir: string;
}

export const DEFAULT_SETTINGS: SettingsShape = {
  earthdataUser: "",
  earthdataPassword: "",
  gacosEmail: "",
  gacosImapAuthCode: "",
  enviIdl: "",
  sarscapeLib: "",
  workDir: "G:\\",
  poeorbDir: "",
};

const FIELD_LABELS: Record<keyof SettingsShape, string> = {
  earthdataUser: "ASF 账号",
  earthdataPassword: "ASF 密码",
  gacosEmail: "GACOS 邮箱",
  gacosImapAuthCode: "GACOS 邮箱 IMAP 授权码",
  enviIdl: "ENVI IDL 路径",
  sarscapeLib: "SARscape 路径",
  workDir: "工作目录",
  poeorbDir: "POEORB 目录",
};

/**
 * 设置卡片：凭证/路径/POEORB 表单 + 实验列表。
 * 挂载于 settings.section（设置页插件区）。
 *
 * **受控组件**：value 全部来自 props.settings（父级经 settingsScope 从 host 读，含启动
 * 探测的 base 默认值），用户改动通过 onChange 通知父级写回 host。组件自己不持有状态，
 * 保证 host 值更新（scope 变化）能反映到字段。
 *
 * autoDetected 标记（若有）则额外显示"▲ 启动时自动定位"。
 */
export function SettingsCard(props: {
  settings?: Partial<SettingsShape>;
  experiments?: { id: string; name: string; terrain: string; status: string }[];
  autoDetected?: { enviIdl?: boolean; sarscapeLib?: boolean };
  onChange?: (next: SettingsShape) => void;
  onSave?: (s: SettingsShape) => void;
}): ReactNode {
  const settings: SettingsShape = { ...DEFAULT_SETTINGS, ...(props.settings ?? {}) };
  // 敏感字段"显示/隐藏"状态（仅本地 UI，不影响持久化；key = 敏感字段名）
  const [revealed, setRevealed] = useState<Record<string, boolean>>({});

  const update = (key: keyof SettingsShape, value: string) => {
    props.onChange?.({ ...settings, [key]: value });
  };

  /** 敏感字段（存密码/授权码，默认隐藏，可切换显示） */
  const isSecret = (key: keyof SettingsShape) =>
    key === "earthdataPassword" || key === "gacosImapAuthCode";

  const toggleReveal = (key: string) =>
    setRevealed((prev) => ({ ...prev, [key]: !prev[key] }));

  return (
    <PanelCard title="insar-genie 设置">
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 12 }}>
        {(Object.keys(FIELD_LABELS) as (keyof SettingsShape)[]).map((key) => (
          <label key={key} style={{ display: "flex", flexDirection: "column", fontSize: 12 }}>
            {FIELD_LABELS[key]}
            <span style={{ fontSize: 11, color: "#2e7d32" }}>
              {props.autoDetected?.[key as "enviIdl" | "sarscapeLib"] ? "▲ 启动时自动定位" : ""}
            </span>
            <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <input
                type={isSecret(key) && !revealed[key] ? "password" : "text"}
                value={settings[key]}
                onChange={(e) => update(key, e.target.value)}
                style={{ marginTop: 2, padding: "2px 6px", flex: 1 }}
              />
              {isSecret(key) && (
                <button
                  type="button"
                  aria-label={revealed[key] ? `隐藏${FIELD_LABELS[key]}` : `显示${FIELD_LABELS[key]}`}
                  onClick={() => toggleReveal(key)}
                  title={revealed[key] ? "隐藏" : "显示"}
                  style={{
                    marginTop: 2,
                    border: "none",
                    background: "transparent",
                    cursor: "pointer",
                    fontSize: 14,
                    padding: "2px 4px",
                  }}
                >
                  {/* 眼睛图标：⊕ 显示 / ⊖ 隐藏（无第三方图标依赖） */}
                  {revealed[key] ? "🙈" : "👁"}
                </button>
              )}
            </div>
          </label>
        ))}
      </div>
      <button onClick={() => props.onSave?.(settings)} style={{ padding: "4px 12px" }}>
        保存设置
      </button>

      {props.experiments && props.experiments.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>实验列表</div>
          <ul style={{ margin: 0, paddingLeft: 16 }}>
            {props.experiments.map((e) => (
              <li key={e.id} style={{ fontSize: 13 }}>
                {e.name} · {e.terrain} · {e.status}
              </li>
            ))}
          </ul>
        </div>
      )}
    </PanelCard>
  );
}
