/**
 * insar-genie-dsh client 入口。
 * 通过 DSH client 插槽注册 UI 组件：
 * - ProgressPanel → conversation.chat.turnTail（对话消息尾部，自带轮询）
 * - ParamConfirm → conversation.chat.turnTail
 * - SettingsCard → settings.section（设置页插件区）
 *
 * 打包：tsdown 生成 client/client.js（ModuleLoader 格式，见 tsdown.config.ts）。
 * 运行时由 dsh.client.inject 依赖（dsh-client-runtime 等）提供 ctx.slots。
 */
export const name = "insar-genie-dsh";

// 占位导出：完整组件在任务 8c 实现（ProgressPanel/ParamConfirm/SettingsCard）
export {};
