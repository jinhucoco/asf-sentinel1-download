window.__ModuleLoader__.load({ id: "insar-genie-dsh", factory: (require) => {
Object.defineProperty(exports, Symbol.toStringTag, { value: 'Module' });
//#region src/client/index.ts
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
const name = "insar-genie-dsh";

//#endregion
exports.name = name;
return module.exports; } });
//# sourceMappingURL=client.js.map