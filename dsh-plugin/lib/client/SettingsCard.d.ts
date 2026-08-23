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
/**
 * 设置卡片：凭证/路径/POEORB 表单 + 实验列表。
 * 挂载于 settings.section（设置页插件区）。
 * 数据通过注入的 settings + experiments 传入（host/agent 接线），本组件只做展示与编辑回调。
 */
export declare function SettingsCard(props: {
    settings?: Partial<SettingsShape>;
    experiments?: {
        id: string;
        name: string;
        terrain: string;
        status: string;
    }[];
    onSave?: (s: SettingsShape) => void;
}): ReactNode;
