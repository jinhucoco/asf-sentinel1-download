window.__ModuleLoader__.load({ id: "insar-genie-dsh", factory: (require) => {
//#region src/client/index.d.ts
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
declare const name = "insar-genie-dsh";
//#endregion
export { name };
return module.exports; } });
//# sourceMappingURL=client.d.ts.map