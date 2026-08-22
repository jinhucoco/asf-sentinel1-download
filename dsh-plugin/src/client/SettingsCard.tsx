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
  registryDir: string;
}

const FIELD_LABELS: Record<keyof SettingsShape, string> = {
  earthdataUser: "ASF 账号",
  earthdataPassword: "ASF 密码",
  gacosEmail: "GACOS 邮箱",
  gacosImapAuthCode: "GACOS IMAP 授权码",
  enviIdl: "ENVI IDL 路径",
  sarscapeLib: "SARscape 路径",
  workDir: "工作目录",
  poeorbDir: "POEORB 目录",
  registryDir: "注册表目录",
};

/**
 * 设置卡片：凭证/路径/POEORB 表单 + 实验列表。
 * 挂载于 settings.section（设置页插件区）。
 * 数据通过注入的 settings + experiments 传入（host/agent 接线），本组件只做展示与编辑回调。
 */
export function SettingsCard(props: {
  settings?: Partial<SettingsShape>;
  experiments?: { id: string; name: string; terrain: string; status: string }[];
  onSave?: (s: SettingsShape) => void;
}): ReactNode {
  const [settings, setSettings] = useState<SettingsShape>({
    earthdataUser: "",
    earthdataPassword: "",
    gacosEmail: "",
    gacosImapAuthCode: "",
    enviIdl: "",
    sarscapeLib: "",
    workDir: "G:\\",
    poeorbDir: "",
    registryDir: "",
    ...(props.settings ?? {}),
  });

  const update = (key: keyof SettingsShape, value: string) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <PanelCard title="insar-genie 设置">
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 12 }}>
        {(Object.keys(FIELD_LABELS) as (keyof SettingsShape)[]).map((key) => (
          <label key={key} style={{ display: "flex", flexDirection: "column", fontSize: 12 }}>
            {FIELD_LABELS[key]}
            <input
              type={key === "earthdataPassword" || key === "gacosImapAuthCode" ? "password" : "text"}
              value={settings[key]}
              onChange={(e) => update(key, e.target.value)}
              style={{ marginTop: 2, padding: "2px 6px" }}
            />
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
