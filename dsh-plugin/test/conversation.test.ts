import { describe, it, expect, vi } from "vitest";
// dsh-client-runtime/client 顶层访问 window（浏览器 bundle），node 测试环境 mock 掉运行时函数
vi.mock("@deepseek-ai/dsh-client-runtime/client", () => ({
  isAppendSurfaceEvent: (event: { surfaceOp?: string }) => event.surfaceOp === "append",
}));
import {
  insarGenieDefinition,
  latestInsarStatus,
  selectInsarTurn,
  type InsarTurnData,
} from "../src/client/conversation.js";
import type { ProgressSnapshot } from "../src/client/shared.js";

/* eslint-disable @typescript-eslint/no-explicit-any */

/** 构造 tool/call 事件 */
function toolCallEvent(turn: number, callId: string, name: string) {
  return {
    type: "tool/call",
    seq: 100 + callId.length,
    time: 0,
    data: { turn, step: 1, callId, name, arguments: "{}" },
  };
}

/** 构造 tool/result 事件（append surface；content 结构同 host JSON_OUTPUT.render 产物） */
function toolResultEvent(turn: number, callId: string, json: unknown) {
  return {
    type: "tool/result",
    surfaceOp: "append",
    seq: 200,
    time: 0,
    data: {
      turn,
      step: 1,
      message: {
        source: { kind: "tool", callId },
        content: [{ type: "tool-result", content: [{ type: "text", text: JSON.stringify(json) }] }],
      },
    },
  };
}

function turnStartEvent(turn: number) {
  return { type: "turn/start", seq: 50, time: 0, data: { turn } };
}

const STATUS: ProgressSnapshot = {
  stepIndex: 1,
  totalSteps: 6,
  donePairs: 190,
  totalPairs: 376,
  pairsPerMinute: 0.22,
  etaMinutes: 846,
  diskGb: 21.7,
  progressLabel: "干涉图生成 51%",
  isStalled: false,
};

describe("insarGenieDefinition.match", () => {
  it("turn/start 返回 start role", () => {
    const r = insarGenieDefinition.match(turnStartEvent(3) as any);
    expect(r).toEqual({ id: "3", role: "start" });
  });

  it("insar 工具 tool/call 返回 update", () => {
    expect(insarGenieDefinition.match(toolCallEvent(3, "c1", "insar_status") as any)).toEqual({
      id: "3",
      role: "update",
    });
    expect(insarGenieDefinition.match(toolCallEvent(3, "c2", "insar_list") as any)).toEqual({
      id: "3",
      role: "update",
    });
  });

  it("非 insar 工具 tool/call 不匹配", () => {
    expect(insarGenieDefinition.match(toolCallEvent(3, "c3", "bash") as any)).toBeNull();
  });

  it("tool/result（append surface）匹配 update", () => {
    expect(insarGenieDefinition.match(toolResultEvent(3, "c1", {}) as any)).toEqual({
      id: "3",
      role: "update",
    });
  });
});

describe("insarGenieDefinition.start/update/buildLocationData", () => {
  it("start 初始化 turn 与 calls", () => {
    const state = insarGenieDefinition.start({} as any, { event: turnStartEvent(3) } as any);
    expect(state.turn).toBe(3);
    expect(state.calls.size).toBe(0);
  });

  it("insar_status 的 tool/result 累积为 status", () => {
    let state = insarGenieDefinition.start({} as any, { event: turnStartEvent(3) } as any);
    state = insarGenieDefinition.update(
      { state } as any,
      { event: toolCallEvent(3, "c1", "insar_status") } as any,
    );
    state = insarGenieDefinition.update(
      { state } as any,
      { event: toolResultEvent(3, "c1", STATUS) } as any,
    );
    expect(state.status).toEqual(STATUS);
  });

  it("insar_list 的 tool/result 累积为 experiments", () => {
    let state = insarGenieDefinition.start({} as any, { event: turnStartEvent(3) } as any);
    state = insarGenieDefinition.update(
      { state } as any,
      { event: toolCallEvent(3, "c2", "insar_list") } as any,
    );
    state = insarGenieDefinition.update(
      { state } as any,
      {
        event: toolResultEvent(3, "c2", {
          experiments: [{ id: "e1", name: "minqin", terrain: "desert", status: "running" }],
        }),
      } as any,
    );
    expect(state.experiments).toEqual([{ id: "e1", name: "minqin", terrain: "desert", status: "running" }]);
  });

  it("insar_register 的 tool/result 累积为 registered", () => {
    let state = insarGenieDefinition.start({} as any, { event: turnStartEvent(3) } as any);
    state = insarGenieDefinition.update(
      { state } as any,
      { event: toolCallEvent(3, "c3", "insar_register") } as any,
    );
    state = insarGenieDefinition.update(
      { state } as any,
      { event: toolResultEvent(3, "c3", { ok: true, experimentId: "e9" }) } as any,
    );
    expect(state.registered).toEqual({ ok: true, experimentId: "e9" });
  });

  it("insar_templates 的 tool/result 累积为 paramConfirm（terrain 取自工具参数）", () => {
    const callArgs = JSON.stringify({ terrain: "desert" });
    let state = insarGenieDefinition.start({} as any, { event: turnStartEvent(3) } as any);
    state = insarGenieDefinition.update(
      { state } as any,
      {
        event: {
          type: "tool/call",
          seq: 101,
          time: 0,
          data: { turn: 3, step: 1, callId: "c6", name: "insar_templates", arguments: callArgs },
        },
      } as any,
    );
    state = insarGenieDefinition.update(
      { state } as any,
      {
        event: toolResultEvent(3, "c6", {
          rgLooks: 8,
          azLooks: 2,
          maxTimeBaselineDays: 180,
          maxPercBaseline: 2,
        }),
      } as any,
    );
    expect(state.paramConfirm?.terrain).toBe("desert");
    expect(state.paramConfirm?.params.rgLooks).toBe(8);
  });

  it("非 insar 工具结果不影响状态", () => {
    let state = insarGenieDefinition.start({} as any, { event: turnStartEvent(3) } as any);
    state = insarGenieDefinition.update(
      { state } as any,
      { event: toolCallEvent(3, "c4", "bash") } as any,
    );
    state = insarGenieDefinition.update(
      { state } as any,
      { event: toolResultEvent(3, "c4", { stdout: "hi" }) } as any,
    );
    expect(state.status).toBeUndefined();
    expect(state.experiments).toBeUndefined();
  });

  it("无法解析的 JSON 不中断状态机", () => {
    let state = insarGenieDefinition.start({} as any, { event: turnStartEvent(3) } as any);
    state = insarGenieDefinition.update(
      { state } as any,
      { event: toolCallEvent(3, "c5", "insar_status") } as any,
    );
    state = insarGenieDefinition.update(
      { state } as any,
      {
        event: {
          ...toolResultEvent(3, "c5", STATUS),
          data: {
            turn: 3,
            step: 1,
            message: {
              source: { kind: "tool", callId: "c5" },
              content: [{ type: "tool-result", content: [{ type: "text", text: "not-json{{{" }] }],
            },
          },
        },
      } as any,
    );
    expect(state.status).toBeUndefined();
  });

  it("buildLocationData 仅 turn scope 且有数据时发布", () => {
    let state = insarGenieDefinition.start({} as any, { event: turnStartEvent(3) } as any);
    state = insarGenieDefinition.update(
      { state } as any,
      { event: toolCallEvent(3, "c1", "insar_status") } as any,
    );
    state = insarGenieDefinition.update(
      { state } as any,
      { event: toolResultEvent(3, "c1", STATUS) } as any,
    );
    const data = insarGenieDefinition.buildLocationData?.({ state } as any, "turn");
    expect(data).toEqual({ kind: "turn", turn: 3, key: "insar-genie", value: { status: STATUS } });
    // 无数据时不发布
    const empty = insarGenieDefinition.buildLocationData?.(
      { state: { ...state, status: undefined, experiments: undefined, registered: undefined } } as any,
      "turn",
    );
    expect(empty).toBeNull();
    // step scope 不发布
    expect(insarGenieDefinition.buildLocationData?.({ state } as any, "step")).toBeNull();
  });
});

describe("selectInsarTurn", () => {
  it("有 insar 数据时返回", () => {
    const owner = { turn: { data: { get: (k: string) => (k === "insar-genie" ? { status: STATUS } : undefined) } } };
    expect(selectInsarTurn(owner as any)).toEqual({ status: STATUS });
  });

  it("无数据或数据为空时返回 null（放行其他 turnTail 贡献者）", () => {
    expect(selectInsarTurn({ turn: { data: { get: () => undefined } } } as any)).toBeNull();
    expect(
      selectInsarTurn({ turn: { data: { get: () => ({}) } } } as any),
    ).toBeNull();
  });
});

describe("latestInsarStatus", () => {
  it("从会话快照提取最新 insar_status 结果与 experimentId", () => {
    const nodes = [
      {
        kind: "tool-result",
        call: { name: "insar_list", argsRaw: "{}" },
        content: [{ type: "tool-result", content: [{ type: "text", text: JSON.stringify({ experiments: [] }) }] }],
      },
      {
        kind: "tool-result",
        call: { name: "insar_status", argsRaw: JSON.stringify({ experimentId: "e1" }) },
        content: [{ type: "tool-result", content: [{ type: "text", text: JSON.stringify(STATUS) }] }],
      },
    ];
    const r = latestInsarStatus(nodes as any);
    expect(r).toEqual({ status: STATUS, experimentId: "e1" });
  });

  it("多个 insar_status 时取最新（seq 升序，取最后一个）", () => {
    const older = { ...STATUS, donePairs: 10, progressLabel: "连接图 5%" };
    const newer = { ...STATUS, donePairs: 190, progressLabel: "干涉图生成 51%" };
    const nodes = [
      {
        kind: "tool-result",
        seq: 100,
        call: { name: "insar_status", argsRaw: JSON.stringify({ experimentId: "e1" }) },
        content: [{ type: "tool-result", content: [{ type: "text", text: JSON.stringify(older) }] }],
      },
      {
        kind: "tool-result",
        seq: 200,
        call: { name: "insar_status", argsRaw: JSON.stringify({ experimentId: "e1" }) },
        content: [{ type: "tool-result", content: [{ type: "text", text: JSON.stringify(newer) }] }],
      },
    ];
    const r = latestInsarStatus(nodes as any);
    expect(r?.status).toEqual(newer);
  });

  it("多个 insar_status 时取最新（seq 无序也能取到 seq 最大的）", () => {
    const older = { ...STATUS, donePairs: 10, progressLabel: "连接图 5%" };
    const newer = { ...STATUS, donePairs: 190, progressLabel: "干涉图生成 51%" };
    const nodes = [
      {
        kind: "tool-result",
        seq: 200,
        call: { name: "insar_status", argsRaw: "{}" },
        content: [{ type: "tool-result", content: [{ type: "text", text: JSON.stringify(newer) }] }],
      },
      {
        kind: "tool-result",
        seq: 100,
        call: { name: "insar_status", argsRaw: "{}" },
        content: [{ type: "tool-result", content: [{ type: "text", text: JSON.stringify(older) }] }],
      },
    ];
    const r = latestInsarStatus(nodes as any);
    expect(r?.status).toEqual(newer);
  });

  it("无 insar_status 结果时返回 null", () => {
    expect(latestInsarStatus([])).toBeNull();
    expect(latestInsarStatus(undefined)).toBeNull();
    const nodes = [
      { kind: "tool-result", call: { name: "insar_list", argsRaw: "{}" }, content: [] },
    ];
    expect(latestInsarStatus(nodes as any)).toBeNull();
  });

  it("非法结果内容返回 null 而非抛错", () => {
    const nodes = [
      {
        kind: "tool-result",
        call: { name: "insar_status", argsRaw: "{}" },
        content: [{ type: "tool-result", content: [{ type: "text", text: "oops" }] }],
      },
    ];
    expect(latestInsarStatus(nodes as any)).toBeNull();
  });
});
