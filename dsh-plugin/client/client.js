window.__ModuleLoader__.load({ id: "@dsh-custom/insar-genie-dsh", factory: (require) => {

		var module = { exports: {} };
		var exports = module.exports;
Object.defineProperty(exports, Symbol.toStringTag, { value: 'Module' });
let react = require("react");
let react_jsx_runtime = require("react/jsx-runtime");
let _deepseek_ai_dsh_client_runtime_client = require("@deepseek-ai/dsh-client-runtime/client");

//#region src/shared/baseline.ts
/**
* 防呆：空间基线必须 2-4%（设计铁律，杜绝 45% 事故）。
* 单一来源：host（templates.ts）与 client（ParamConfirm 确认卡）共用，避免双源漂移。
* 纯函数、无任何平台依赖，可同时被 host 与 client（tsdown browser bundle）引用。
*/
function validateBaseline(perc) {
	if (perc >= 2 && perc <= 4) return { ok: true };
	return {
		ok: false,
		message: `空间基线 ${perc}% 不在允许区间 2-4%（SARscape 默认 45% 是事故根源，已禁止）`
	};
}

//#endregion
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
* 挂载于 conversation.chat.turnTail。
*
* 数据源（按优先级）：
* 1. snapshot —— 会话快照实时提取的 insar_status 结果（host→client 原生通道；
*    快照每次更新面板随之刷新，无需轮询）
* 2. fetchStatus —— 注入的轮询函数（30s，window.insarGenieBridge 或 props 注入）
* 3. initial —— 一次性初始值（仅挂载时生效）
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
	const display = props.snapshot ?? status;
	const title = `SBAS 实验进度${props.experimentLabel ? ` · ${props.experimentLabel}` : ""}`;
	if (!display && !error) return /* @__PURE__ */ (0, react_jsx_runtime.jsx)(PanelCard, {
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
	if (display?.error) return /* @__PURE__ */ (0, react_jsx_runtime.jsx)(PanelCard, {
		title,
		children: /* @__PURE__ */ (0, react_jsx_runtime.jsxs)("span", {
			style: { color: "#c00" },
			children: ["⚠️ ", display.error.detail || display.progressLabel]
		})
	});
	const stepIndex = Math.min(display.stepIndex, STEP_LABELS.length - 1);
	const etaH = Math.round(display.etaMinutes / 60);
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
				children: /* @__PURE__ */ (0, react_jsx_runtime.jsx)("strong", { children: display.progressLabel })
			}),
			display.totalPairs > 0 && /* @__PURE__ */ (0, react_jsx_runtime.jsxs)("div", {
				style: { marginBottom: 4 },
				children: [
					"已完成 ",
					display.donePairs,
					"/",
					display.totalPairs,
					" 对",
					display.pairsPerMinute > 0 && /* @__PURE__ */ (0, react_jsx_runtime.jsxs)("span", { children: [
						" · 速率 ",
						display.pairsPerMinute.toFixed(2),
						" 对/分"
					] }),
					etaH > 0 && /* @__PURE__ */ (0, react_jsx_runtime.jsxs)("span", { children: [
						" · 预计剩余约 ",
						etaH,
						" 小时"
					] })
				]
			}),
			display.diskGb > 0 && /* @__PURE__ */ (0, react_jsx_runtime.jsxs)("div", {
				style: { color: "#888" },
				children: [
					"数据盘占用：",
					display.diskGb.toFixed(1),
					" GB"
				]
			}),
			display.isStalled && /* @__PURE__ */ (0, react_jsx_runtime.jsx)("div", {
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
const DEFAULT_SETTINGS = {
	earthdataUser: "",
	earthdataPassword: "",
	gacosEmail: "",
	gacosImapAuthCode: "",
	enviIdl: "",
	sarscapeLib: "",
	workDir: "G:\\",
	poeorbDir: ""
};
const FIELD_LABELS = {
	earthdataUser: "ASF 账号",
	earthdataPassword: "ASF 密码",
	gacosEmail: "GACOS 邮箱",
	gacosImapAuthCode: "GACOS 邮箱 IMAP 授权码",
	enviIdl: "ENVI IDL 路径",
	sarscapeLib: "SARscape 路径",
	workDir: "工作目录",
	poeorbDir: "POEORB 目录"
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
function SettingsCard(props) {
	const settings = {
		...DEFAULT_SETTINGS,
		...props.settings ?? {}
	};
	const [revealed, setRevealed] = (0, react.useState)({});
	const update = (key, value) => {
		props.onChange?.({
			...settings,
			[key]: value
		});
	};
	/** 敏感字段（存密码/授权码，默认隐藏，可切换显示） */
	const isSecret = (key) => key === "earthdataPassword" || key === "gacosImapAuthCode";
	const toggleReveal = (key) => setRevealed((prev) => ({
		...prev,
		[key]: !prev[key]
	}));
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
					children: [
						FIELD_LABELS[key],
						/* @__PURE__ */ (0, react_jsx_runtime.jsx)("span", {
							style: {
								fontSize: 11,
								color: "#2e7d32"
							},
							children: props.autoDetected?.[key] ? "▲ 启动时自动定位" : ""
						}),
						/* @__PURE__ */ (0, react_jsx_runtime.jsxs)("div", {
							style: {
								display: "flex",
								alignItems: "center",
								gap: 4
							},
							children: [/* @__PURE__ */ (0, react_jsx_runtime.jsx)("input", {
								type: isSecret(key) && !revealed[key] ? "password" : "text",
								value: settings[key],
								onChange: (e) => update(key, e.target.value),
								style: {
									marginTop: 2,
									padding: "2px 6px",
									flex: 1
								}
							}), isSecret(key) && /* @__PURE__ */ (0, react_jsx_runtime.jsx)("button", {
								type: "button",
								"aria-label": revealed[key] ? `隐藏${FIELD_LABELS[key]}` : `显示${FIELD_LABELS[key]}`,
								onClick: () => toggleReveal(key),
								title: revealed[key] ? "隐藏" : "显示",
								style: {
									marginTop: 2,
									border: "none",
									background: "transparent",
									cursor: "pointer",
									fontSize: 14,
									padding: "2px 4px"
								},
								children: revealed[key] ? "🙈" : "👁"
							})]
						})
					]
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
//#region src/client/conversation.ts
/** 本 Definition 关注的 insar 工具名 */
const INSAR_TOOLS = /* @__PURE__ */ new Set([
	"insar_status",
	"insar_list",
	"insar_register",
	"insar_templates"
]);
/**
* 从 tool/result 事件的 message.content 提取 render 输出的 JSON 文本。
* host JSON_OUTPUT.render 产出 [{type:"text", text: JSON.stringify(value)}]，
* message.content 是 [ToolResultBlock]，其 content 是 ContentBlock[]。
*/
function extractToolResultText(content) {
	const block = content?.[0];
	if (!block || block.type !== "tool-result") return null;
	const inner = block.content ?? [];
	for (const c of inner) if (c.type === "text" && typeof c.text === "string") return c.text;
	return null;
}
/** 解析 tool/result 中的结构化 JSON；失败返回 undefined（不中断状态机） */
function parseToolResultJson(content) {
	const text = extractToolResultText(content);
	if (!text) return void 0;
	try {
		return JSON.parse(text);
	} catch {
		return;
	}
}
/** 单 turn 内累积 insar 工具结果的 Conversation 业务 Definition */
const insarGenieDefinition = {
	kind: "insar-genie",
	match(event) {
		if (event.type === "turn/start") return {
			id: String(event.data.turn),
			role: "start"
		};
		if (event.type === "tool/call" && INSAR_TOOLS.has(event.data.name)) return {
			id: String(event.data.turn),
			role: "update"
		};
		if (event.type === "tool/result" && (0, _deepseek_ai_dsh_client_runtime_client.isAppendSurfaceEvent)(event)) return {
			id: String(event.data.turn),
			role: "update"
		};
		return null;
	},
	start(context, match) {
		if (match.event.type !== "turn/start") throw new Error("insar-genie start requires turn/start");
		return {
			turn: match.event.data.turn,
			calls: /* @__PURE__ */ new Map()
		};
	},
	update(context, match) {
		const state = context.state;
		if (match.event.type === "tool/call") {
			const calls = new Map(state.calls);
			calls.set(String(match.event.data.callId), {
				name: match.event.data.name,
				args: match.event.data.arguments
			});
			return {
				...state,
				calls
			};
		}
		if (match.event.type !== "tool/result") return state;
		const callId = String(match.event.data.message.source.callId);
		const call = state.calls.get(callId);
		if (!call || !INSAR_TOOLS.has(call.name)) return state;
		const json = parseToolResultJson(match.event.data.message.content);
		if (json === void 0) return state;
		if (call.name === "insar_status" && isProgressSnapshot(json)) return {
			...state,
			status: json
		};
		if (call.name === "insar_list" && isExperimentList(json)) return {
			...state,
			experiments: json.experiments
		};
		if (call.name === "insar_register" && isRegistered(json)) return {
			...state,
			registered: {
				ok: json.ok === true,
				experimentId: json.experimentId
			}
		};
		if (call.name === "insar_templates" && isParams(json)) {
			let terrain = "";
			try {
				const callArgs = JSON.parse(call.args);
				if (typeof callArgs.terrain === "string") terrain = callArgs.terrain;
			} catch {}
			return {
				...state,
				paramConfirm: {
					terrain,
					params: json
				}
			};
		}
		return state;
	},
	buildLocationData(context, scope) {
		if (scope !== "turn" || context.state === void 0) return null;
		const { status, experiments, registered, paramConfirm } = context.state;
		if (!status && !experiments && !registered && !paramConfirm) return null;
		return {
			kind: "turn",
			turn: context.state.turn,
			key: "insar-genie",
			value: {
				status,
				experiments,
				registered,
				paramConfirm
			}
		};
	}
};
/** turnTail chain select：仅当该 turn 有 insar 工具结果时认领，否则 null 放行其他贡献者 */
function selectInsarTurn(owner) {
	const data = owner.turn.data.get("insar-genie");
	if (!data) return null;
	if (!data.status && !data.experiments && !data.registered && !data.paramConfirm) return null;
	return data;
}
/**
* 从 ConversationSnapshot 提取最新一次 insar_status 的结构化结果。
* 这是 host→client 的真实数据通道：host 工具结果经会话事件流到达 client，
* 组件订阅快照即可实时显示，无需 window 桥、无需 30s 轮询。
* @param nodes - snapshot.nodes（legacy 兼容字段，所有已物化会话节点）
* @returns 最新 insar_status 结果 + 工具调用参数里的 experimentId（可作标签），无则 null
*/
function latestInsarStatus(nodes) {
	if (!nodes || nodes.length === 0) return null;
	let latest = null;
	for (const node of nodes) {
		if (node?.kind !== "tool-result") continue;
		if (node.call?.name !== "insar_status") continue;
		if (!latest || (node.seq ?? 0) >= (latest.seq ?? 0)) latest = node;
	}
	if (!latest) return null;
	const json = parseToolResultJson(latest.content);
	if (!isProgressSnapshot(json)) return null;
	let experimentId;
	try {
		const args = JSON.parse(latest.call?.argsRaw ?? "{}");
		if (typeof args.experimentId === "string") experimentId = args.experimentId;
	} catch {}
	return {
		status: json,
		experimentId
	};
}
function isProgressSnapshot(v) {
	return typeof v === "object" && v !== null && typeof v.stepIndex === "number" && typeof v.progressLabel === "string";
}
function isExperimentList(v) {
	return typeof v === "object" && v !== null && Array.isArray(v.experiments) && v.experiments.every((e) => typeof e === "object" && e !== null && typeof e.id === "string");
}
function isRegistered(v) {
	return typeof v === "object" && v !== null && typeof v.experimentId === "string";
}
/** insar_templates 返回的参数模板（ExperimentParams 形状的宽松校验） */
function isParams(v) {
	return typeof v === "object" && v !== null && typeof v.rgLooks === "number";
}

//#endregion
//#region src/client/index.ts
/**
* insar-genie-dsh client 入口。
* 通过 DSH client 插槽注册：
* - conversationEvents：insar 工具结果（insar_status/insar_list/insar_register）累积为
*   turn 级业务数据（conversation.ts 的 insarGenieDefinition）
* - turnTail（conversation.chat.turnTail，chain）：当一轮 turn 有 insar 工具活动时认领，
*   组件通过框架注入的 useSession 从会话快照提取最新 insar_status 结果并渲染进度面板
* - settings.section：SettingsCard（设置页插件区）
*
* 数据接线（host→client）：DSH 无同步 host 工具调用通道，但 host 工具结果作为
* tool/result 会话事件流入 client 的 ConversationSnapshot——组件订阅快照即拿到
* 真实数据，无需 window 桥、无需轮询。window.insarGenieBridge 仅保留为可选
* 注入位（未来 host 若提供 HTTP 桥可直接替换），默认数据源是会话快照。
*/
const name = "insar-genie-dsh";
const inject = [
	"slots",
	"conversationEvents",
	"settingsScope"
];
/** turnTail 组件（chain 注册，session 作用域）：
* - matched：selectInsarTurn 的返回（该 turn 有 insar 工具活动才认领）——**本 turn 数据优先**
* - useSession：框架注入的会话快照选择器——仅用于对"本 turn 已有 insar_status 活动"的
*   实验做实时刷新（AI 在同一实验上再次调用 insar_status 时面板自动更新）。
*   不做跨 turn 泄漏：其他 turn 的 insar 活动由它们自己的 turnTail 渲染。
*/
function InsarTurnTail(props) {
	const snapshot = props.useSession((s) => s);
	const latest = latestInsarStatus(snapshot?.nodes);
	if (props.matched?.paramConfirm) return (0, react.createElement)(ParamConfirm, {
		terrain: props.matched.paramConfirm.terrain,
		params: props.matched.paramConfirm.params,
		onConfirm: () => {},
		onCancel: () => {}
	});
	if (props.matched?.status) return (0, react.createElement)(ProgressPanel, {
		experimentId: latest?.experimentId,
		experimentLabel: void 0,
		fetchStatus: window.insarGenieBridge?.fetchStatus,
		initial: props.matched.status,
		snapshot: latest?.status
	});
	if (props.matched?.experiments && props.matched.experiments.length > 0) return (0, react.createElement)(SettingsCard, {
		experiments: props.matched.experiments,
		onSave: (s) => {
			console.info("[insar-genie] settings save requested", s);
		}
	});
	if (props.matched?.registered && props.matched.registered.ok) return (0, react.createElement)("div", { style: {
		border: "1px solid #ccc",
		borderRadius: 8,
		padding: 12,
		margin: "8px 0",
		maxWidth: 640,
		fontSize: 13
	} }, `✅ 实验已注册：${props.matched.registered.experimentId}`);
	return null;
}
/**
* SettingsCardBound：绑定 settingsScope 的容器组件。
* - 挂载时从 scope.getSnapshot().value 读 host 设置值（含启动探测 base 默认）
* - 订阅 scope 变化 → 更新显示（host 值变更时字段跟随）
* - onChange 通过 scope.set 逐字段写回 host
*/
function SettingsCardBound(props) {
	const scope = props.scope;
	const [draft, setDraft] = (0, react.useState)(() => ({
		...DEFAULT_SETTINGS,
		...scope?.getSnapshot().value ?? {}
	}));
	(0, react.useEffect)(() => {
		const update = () => setDraft({
			...DEFAULT_SETTINGS,
			...scope?.getSnapshot().value ?? {}
		});
		update();
		const unsub = scope?.subscribe(update);
		return () => {
			if (typeof unsub === "function") unsub();
		};
	}, [scope]);
	const env = scope?.getSnapshot().value;
	const autoDetected = {
		enviIdl: Boolean(env?.enviIdl),
		sarscapeLib: Boolean(env?.sarscapeLib)
	};
	return (0, react.createElement)(SettingsCard, {
		experiments: props.experiments,
		settings: draft,
		autoDetected,
		onChange: (next) => setDraft(next),
		onSave: (next) => {
			for (const [k, v] of Object.entries(next)) scope?.set(k, v);
		}
	});
}
function apply(ctx) {
	ctx.conversationEvents.register(insarGenieDefinition);
	const scope = ctx.settingsScope?.bind({ namespace: "insar-genie" });
	ctx.slots.inject("settings.section", () => {
		const off = ctx.slots.register({
			name: "settings.section",
			id: "insar-genie",
			order: 40,
			label: () => "insar-genie",
			inject: () => ({ experiments: window.insarGenieBridge?.experiments })
		}, (props) => (0, react.createElement)(SettingsCardBound, {
			scope,
			experiments: props?.experiments
		}));
		return () => {
			if (typeof off === "function") off();
		};
	});
	ctx.slots.inject("conversation.chat.turnTail", () => {
		const off = ctx.slots.register({
			name: "conversation.chat.turnTail",
			select: selectInsarTurn,
			registrant: "insar-genie-dsh"
		}, InsarTurnTail);
		return () => {
			if (typeof off === "function") off();
		};
	});
}

//#endregion
exports.InsarTurnTail = InsarTurnTail;
exports.SettingsCardBound = SettingsCardBound;
exports.apply = apply;
exports.inject = inject;
exports.name = name;
return module.exports; } });
//# sourceMappingURL=client.js.map