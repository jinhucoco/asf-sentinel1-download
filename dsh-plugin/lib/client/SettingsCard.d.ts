import { type ReactNode } from "react";
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
export declare const DEFAULT_SETTINGS: SettingsShape;
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
export declare function SettingsCard(props: {
    settings?: Partial<SettingsShape>;
    experiments?: {
        id: string;
        name: string;
        terrain: string;
        status: string;
    }[];
    autoDetected?: {
        enviIdl?: boolean;
        sarscapeLib?: boolean;
    };
    onChange?: (next: SettingsShape) => void;
    onSave?: (s: SettingsShape) => void;
}): ReactNode;
