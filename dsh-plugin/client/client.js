window.__ModuleLoader__.load({ id: "insar-genie-dsh", factory: (require) => {
Object.defineProperty(exports, Symbol.toStringTag, { value: 'Module' });
let react = require("react");
let react_jsx_runtime = require("react/jsx-runtime");

//#region src/client/shared.tsx
/** 五步进度标签（与 host status.ts 一致） */
const STEP_LABELS = [
	"连接图",
	"干涉",
	"解缠",
	"反演1",
	"反演2",
	"地理编码"
];
const TERRAIN_LABELS = {
	mining: "矿区",
	landslide: "滑坡",
	urban: "城市",
	desert: "沙漠",
	loess: "黄土高原"
};
/**
* 防呆：空间基线必须在 2-4%（杜绝 45% 事故）。
* 与 host templates.ts 的 validateBaseline 语义一致。
*/
function validateBaseline(perc) {
	if (perc >= 2 && perc <= 4) return { ok: true };
	return {
		ok: false,
		message: `空间基线 ${perc}% 不在允许区间 2-4%（SARscape 默认 45% 是事故根源，已禁止）`
	};
}
/** turnTail 插槽渲染的通用包装（简单卡片容器） */
function PanelCard(props) {
	return /* @__PURE__ */ (0, react_jsx_runtime.jsxs)("div", {
		style: {
			border: "1px solid #ccc",
			borderRadius: 8,
			padding: 12,
			margin: "8px 0",
			maxWidth: 640
		},
		children: [/* @__PURE__ */ (0, react_jsx_runtime.jsx)("div", {
			style: {
				fontWeight: 600,
				marginBottom: 8
			},
			children: props.title
		}), props.children]
	});
}

//#endregion
//#region src/client/ProgressPanel.tsx
/**
* 进度面板：五步进度条 + 剩余时间 + 异常区。
* 挂载于 conversation.chat.turnTail；自带 30s 轮询（不依赖 AI 主动汇报）。
*
* 数据获取通过注入的 fetchStatus（client 侧由 host/agent 通过 props 注入，
* 或由调用方传入从 insar_status 工具获得的数据源）——见 client/index.ts 的接线说明。
*/
function ProgressPanel(props) {
	const [status, setStatus] = (0, react.useState)(props.initial ?? null);
	const [error, setError] = (0, react.useState)(null);
	(0, react.useEffect)(() => {
		if (!props.fetchStatus || !props.experimentId) return;
		let cancelled = false;
		const tick = async () => {
			try {
				const s = await props.fetchStatus(props.experimentId);
				if (!cancelled) {
					setStatus(s);
					setError(null);
				}
			} catch (e) {
				if (!cancelled) setError(e instanceof Error ? e.message : String(e));
			}
		};
		tick();
		const timer = setInterval(tick, 3e4);
		return () => {
			cancelled = true;
			clearInterval(timer);
		};
	}, [props.experimentId, props.fetchStatus]);
	const title = `SBAS 实验进度${props.experimentLabel ? ` · ${props.experimentLabel}` : ""}`;
	if (!status && !error) return /* @__PURE__ */ (0, react_jsx_runtime.jsx)(PanelCard, {
		title,
		children: /* @__PURE__ */ (0, react_jsx_runtime.jsx)("span", {
			style: { color: "#888" },
			children: "等待进度数据…（实验启动后显示）"
		})
	});
	if (error) return /* @__PURE__ */ (0, react_jsx_runtime.jsx)(PanelCard, {
		title,
		children: /* @__PURE__ */ (0, react_jsx_runtime.jsxs)("span", {
			style: { color: "#c00" },
			children: ["⚠️ 无法读取进度：", error]
		})
	});
	if (status?.error) return /* @__PURE__ */ (0, react_jsx_runtime.jsx)(PanelCard, {
		title,
		children: /* @__PURE__ */ (0, react_jsx_runtime.jsxs)("span", {
			style: { color: "#c00" },
			children: ["⚠️ ", status.error.detail || status.progressLabel]
		})
	});
	const stepIndex = Math.min(status.stepIndex, STEP_LABELS.length - 1);
	const etaH = Math.round(status.etaMinutes / 60);
	return /* @__PURE__ */ (0, react_jsx_runtime.jsxs)(PanelCard, {
		title,
		children: [
			/* @__PURE__ */ (0, react_jsx_runtime.jsx)("div", {
				style: {
					display: "flex",
					gap: 4,
					marginBottom: 8
				},
				children: STEP_LABELS.map((label, i) => /* @__PURE__ */ (0, react_jsx_runtime.jsx)("div", {
					style: {
						flex: 1,
						padding: 4,
						textAlign: "center",
						fontSize: 12,
						borderRadius: 4,
						background: i < stepIndex ? "#4caf50" : i === stepIndex ? "#ff9800" : "#eee",
						color: i <= stepIndex ? "#fff" : "#666"
					},
					children: label
				}, label))
			}),
			/* @__PURE__ */ (0, react_jsx_runtime.jsx)("div", {
				style: { marginBottom: 4 },
				children: /* @__PURE__ */ (0, react_jsx_runtime.jsx)("strong", { children: status.progressLabel })
			}),
			status.totalPairs > 0 && /* @__PURE__ */ (0, react_jsx_runtime.jsxs)("div", {
				style: { marginBottom: 4 },
				children: [
					"已完成 ",
					status.donePairs,
					"/",
					status.totalPairs,
					" 对",
					status.pairsPerMinute > 0 && /* @__PURE__ */ (0, react_jsx_runtime.jsxs)("span", { children: [
						" · 速率 ",
						status.pairsPerMinute.toFixed(2),
						" 对/分"
					] }),
					etaH > 0 && /* @__PURE__ */ (0, react_jsx_runtime.jsxs)("span", { children: [
						" · 预计剩余约 ",
						etaH,
						" 小时"
					] })
				]
			}),
			status.diskGb > 0 && /* @__PURE__ */ (0, react_jsx_runtime.jsxs)("div", {
				style: { color: "#888" },
				children: [
					"数据盘占用：",
					status.diskGb.toFixed(1),
					" GB"
				]
			}),
			status.isStalled && /* @__PURE__ */ (0, react_jsx_runtime.jsx)("div", {
				style: {
					border: "1px solid #e91e63",
					color: "#c2185b",
					padding: 6,
					marginTop: 8,
					borderRadius: 4
				},
				children: "⚠️ 检测到停滞：进程可能未在推进"
			})
		]
	});
}

//#endregion
//#region src/client/ParamConfirm.tsx
/**
* 参数确认卡片：地形联动参数 + 2-4% 基线防呆。
* 挂载于 conversation.chat.turnTail；AI 生成参数后渲染，用户确认后才执行。
*/
function ParamConfirm(props) {
	const [params, setParams] = (0, react.useState)(props.params);
	const gate = validateBaseline(params.maxPercBaseline);
	const update = (patch) => {
		const next = {
			...params,
			...patch
		};
		setParams(next);
		props.onChange?.(next);
	};
	return /* @__PURE__ */ (0, react_jsx_runtime.jsxs)(PanelCard, {
		title: "实验参数确认",
		children: [
			/* @__PURE__ */ (0, react_jsx_runtime.jsxs)("div", {
				style: { marginBottom: 8 },
				children: ["地形：", TERRAIN_LABELS[props.terrain]]
			}),
			/* @__PURE__ */ (0, react_jsx_runtime.jsxs)("label", {
				style: {
					display: "block",
					marginBottom: 6
				},
				children: ["空间基线（% of critical）：", /* @__PURE__ */ (0, react_jsx_runtime.jsx)("input", {
					type: "number",
					value: params.maxPercBaseline,
					onChange: (e) => update({ maxPercBaseline: Number(e.target.value) }),
					style: {
						marginLeft: 6,
						width: 80,
						border: gate.ok ? "1px solid #ccc" : "2px solid #d32f2f"
					}
				})]
			}),
			!gate.ok && /* @__PURE__ */ (0, react_jsx_runtime.jsxs)("div", {
				style: {
					color: "#d32f2f",
					marginBottom: 6
				},
				children: ["⚠️ ", gate.message]
			}),
			/* @__PURE__ */ (0, react_jsx_runtime.jsxs)("div", {
				style: { marginBottom: 6 },
				children: [
					"多视 ",
					params.rgLooks,
					":",
					params.azLooks,
					" · 时间基线 ",
					params.maxTimeBaselineDays,
					" 天 · 滤波 ",
					params.filtering,
					" ",
					params.goldsteinWinSize,
					" · 解缠 ",
					params.unwrap,
					" 阈值 ",
					params.unwrapCohThreshold,
					" · GACOS ",
					params.useGacos ? "开" : "关"
				]
			}),
			/* @__PURE__ */ (0, react_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, react_jsx_runtime.jsx)("button", {
				onClick: props.onConfirm,
				disabled: !gate.ok,
				style: {
					marginRight: 8,
					padding: "4px 12px"
				},
				children: "确认执行"
			}), /* @__PURE__ */ (0, react_jsx_runtime.jsx)("button", {
				onClick: props.onCancel,
				style: { padding: "4px 12px" },
				children: "取消"
			})] })
		]
	});
}

//#endregion
//#region src/client/SettingsCard.tsx
const FIELD_LABELS = {
	earthdataUser: "ASF 账号",
	earthdataPassword: "ASF 密码",
	gacosEmail: "GACOS 邮箱",
	gacosImapAuthCode: "GACOS IMAP 授权码",
	enviIdl: "ENVI IDL 路径",
	sarscapeLib: "SARscape 路径",
	workDir: "工作目录",
	poeorbDir: "POEORB 目录",
	registryDir: "注册表目录"
};
/**
* 设置卡片：凭证/路径/POEORB 表单 + 实验列表。
* 挂载于 settings.section（设置页插件区）。
* 数据通过注入的 settings + experiments 传入（host/agent 接线），本组件只做展示与编辑回调。
*/
function SettingsCard(props) {
	const [settings, setSettings] = (0, react.useState)({
		earthdataUser: "",
		earthdataPassword: "",
		gacosEmail: "",
		gacosImapAuthCode: "",
		enviIdl: "",
		sarscapeLib: "",
		workDir: "G:\\",
		poeorbDir: "",
		registryDir: "",
		...props.settings ?? {}
	});
	const update = (key, value) => {
		setSettings((prev) => ({
			...prev,
			[key]: value
		}));
	};
	return /* @__PURE__ */ (0, react_jsx_runtime.jsxs)(PanelCard, {
		title: "insar-genie 设置",
		children: [
			/* @__PURE__ */ (0, react_jsx_runtime.jsx)("div", {
				style: {
					display: "grid",
					gridTemplateColumns: "1fr 1fr",
					gap: 8,
					marginBottom: 12
				},
				children: Object.keys(FIELD_LABELS).map((key) => /* @__PURE__ */ (0, react_jsx_runtime.jsxs)("label", {
					style: {
						display: "flex",
						flexDirection: "column",
						fontSize: 12
					},
					children: [FIELD_LABELS[key], /* @__PURE__ */ (0, react_jsx_runtime.jsx)("input", {
						type: key === "earthdataPassword" || key === "gacosImapAuthCode" ? "password" : "text",
						value: settings[key],
						onChange: (e) => update(key, e.target.value),
						style: {
							marginTop: 2,
							padding: "2px 6px"
						}
					})]
				}, key))
			}),
			/* @__PURE__ */ (0, react_jsx_runtime.jsx)("button", {
				onClick: () => props.onSave?.(settings),
				style: { padding: "4px 12px" },
				children: "保存设置"
			}),
			props.experiments && props.experiments.length > 0 && /* @__PURE__ */ (0, react_jsx_runtime.jsxs)("div", {
				style: { marginTop: 16 },
				children: [/* @__PURE__ */ (0, react_jsx_runtime.jsx)("div", {
					style: {
						fontWeight: 600,
						marginBottom: 4
					},
					children: "实验列表"
				}), /* @__PURE__ */ (0, react_jsx_runtime.jsx)("ul", {
					style: {
						margin: 0,
						paddingLeft: 16
					},
					children: props.experiments.map((e) => /* @__PURE__ */ (0, react_jsx_runtime.jsxs)("li", {
						style: { fontSize: 13 },
						children: [
							e.name,
							" · ",
							e.terrain,
							" · ",
							e.status
						]
					}, e.id))
				})]
			})
		]
	});
}

//#endregion
//#region src/client/index.ts
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
const name = "insar-genie-dsh";
const inject = [
	"@deepseek-ai/dsh-client-runtime",
	"@deepseek-ai/dsh-client-locale",
	"@deepseek-ai/dsh-client-ui-settings-plugins"
];
function renderTurnTail(props) {
	if (props?.kind === "param-confirm" && props.terrain && props.params) return (0, react.createElement)(ParamConfirm, {
		terrain: props.terrain,
		params: props.params,
		onConfirm: props.onConfirm ?? (() => {}),
		onCancel: props.onCancel ?? (() => {})
	});
	return (0, react.createElement)(ProgressPanel, {
		experimentId: props?.experimentId,
		experimentLabel: props?.experimentLabel,
		fetchStatus: props?.fetchStatus ?? window.insarGenieBridge?.fetchStatus,
		initial: props?.initialProgress
	});
}
function apply(ctx) {
	ctx.slots.inject("settings.section", () => {
		const off = ctx.slots.register({
			name: "settings.section",
			id: "insar-genie",
			order: 40,
			label: () => "insar-genie",
			inject: () => ({ experiments: window.insarGenieBridge?.experiments })
		}, (props) => (0, react.createElement)(SettingsCard, {
			experiments: props?.experiments,
			onSave: (s) => {
				console.info("[insar-genie] settings save requested", s);
			}
		}));
		return () => {
			if (typeof off === "function") off();
		};
	});
	ctx.slots.inject("conversation.chat.turnTail", () => {
		const off = ctx.slots.register({
			name: "conversation.chat.turnTail",
			priority: -1,
			registrant: "insar-genie-dsh",
			inject: () => ({})
		}, (props) => renderTurnTail(props));
		return () => {
			if (typeof off === "function") off();
		};
	});
}

//#endregion
exports.apply = apply;
exports.inject = inject;
exports.name = name;
return module.exports; } });
//# sourceMappingURL=client.js.map