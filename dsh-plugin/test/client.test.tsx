// @vitest-environment jsdom
import { describe, it, expect, afterEach, vi } from "vitest";
// dsh-client-runtime 是 ModuleLoader 格式浏览器 bundle，vitest 环境 mock 掉运行时函数
vi.mock("@deepseek-ai/dsh-client-runtime/client", () => ({
  isAppendSurfaceEvent: (event: { surfaceOp?: string }) => event.surfaceOp === "append",
}));
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { createElement } from "react";
import { ProgressPanel } from "../src/client/ProgressPanel.js";
import { ParamConfirm } from "../src/client/ParamConfirm.js";
import { InsarTurnTail } from "../src/client/index.js";
import { SettingsCard } from "../src/client/SettingsCard.js";
import { validateBaseline, type ParamSnapshot, type ProgressSnapshot } from "../src/client/shared.js";

// vitest 无自动 cleanup，每个测试后卸载 DOM，避免多元素查询歧义
afterEach(cleanup);

const PROGRESS: ProgressSnapshot = {
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

describe("validateBaseline（防呆铁律）", () => {
  it("2% 通过", () => expect(validateBaseline(2).ok).toBe(true));
  it("4% 通过", () => expect(validateBaseline(4).ok).toBe(true));
  it("45% 被拦截", () => {
    const r = validateBaseline(45);
    expect(r.ok).toBe(false);
    expect(r.message).toContain("2-4");
  });
});

describe("ProgressPanel", () => {
  it("渲染五步进度与剩余时间", () => {
    render(createElement(ProgressPanel, { experimentLabel: "民勤", initial: PROGRESS }));
    expect(screen.getByText("SBAS 实验进度 · 民勤")).toBeTruthy();
    expect(screen.getByText("干涉图生成 51%")).toBeTruthy();
    expect(screen.getByText(/190\/376/)).toBeTruthy();
    expect(screen.getByText(/预计剩余约 14 小时/)).toBeTruthy();
    // 五步标签
    for (const label of ["连接图", "干涉", "解缠", "反演1", "反演2", "地理编码"]) {
      expect(screen.getByText(label)).toBeTruthy();
    }
  });

  it("数据缺失（error）时显示无法读取而非 0%", () => {
    render(createElement(ProgressPanel, {
      experimentLabel: "x",
      initial: {
        ...PROGRESS,
        error: { code: "no-auxiliary", detail: "auxiliary.sml 缺失或不可读", evidence: "" },
      },
    }));
    expect(screen.getByText(/auxiliary.sml 缺失/)).toBeTruthy();
  });

  it("无数据源时显示等待提示（不误导）", () => {
    render(createElement(ProgressPanel, {}));
    expect(screen.getByText(/等待进度数据/)).toBeTruthy();
  });

  it("fetchStatus 轮询更新进度", async () => {
    let calls = 0;
    const fetchStatus = async () => {
      calls += 1;
      return { ...PROGRESS, donePairs: 191 + calls };
    };
    render(createElement(ProgressPanel, { experimentId: "e1", fetchStatus }));
    await waitFor(() => expect(screen.getByText(/192\/376/)).toBeTruthy(), { timeout: 2000 });
  });
});

describe("InsarTurnTail（host→client 接线）", () => {
  /** 无会话快照的 useSession stub */
  const noSnapshot = () => undefined;

  it("matched.status 渲染进度面板", () => {
    render(createElement(InsarTurnTail, { matched: { status: PROGRESS }, useSession: noSnapshot }));
    expect(screen.getByText("干涉图生成 51%")).toBeTruthy();
  });

  it("会话快照的最新 insar_status 优先于 matched（AI 每次调用自动更新）", () => {
    const snapshot = {
      nodes: [
        {
          kind: "tool-result",
          seq: 200,
          call: { name: "insar_status", argsRaw: JSON.stringify({ experimentId: "e1" }) },
          content: [
            {
              type: "tool-result",
              content: [{ type: "text", text: JSON.stringify({ ...PROGRESS, progressLabel: "解缠 88%" }) }],
            },
          ],
        },
      ],
    };
    const useSession = (sel: (s: unknown) => unknown) => sel(snapshot);
    render(createElement(InsarTurnTail, { matched: { status: PROGRESS }, useSession }));
    expect(screen.getByText("解缠 88%")).toBeTruthy();
  });

  it("快照更新后面板内容跟随（snapshot prop 实时通道，非 initial 一次性）", () => {
    let snapshot: unknown = {
      nodes: [
        {
          kind: "tool-result",
          seq: 100,
          call: { name: "insar_status", argsRaw: "{}" },
          content: [
            { type: "tool-result", content: [{ type: "text", text: JSON.stringify({ ...PROGRESS, progressLabel: "连接图 5%" }) }] },
          ],
        },
      ],
    };
    const useSession = (sel: (s: unknown) => unknown) => sel(snapshot);
    const { rerender } = render(
      createElement(InsarTurnTail, { matched: { status: PROGRESS }, useSession }),
    );
    expect(screen.getByText("连接图 5%")).toBeTruthy();
    // 模拟 AI 再次调用 insar_status：快照更新 → 组件重渲染 → 面板显示新进度
    snapshot = {
      nodes: [
        {
          kind: "tool-result",
          seq: 100,
          call: { name: "insar_status", argsRaw: "{}" },
          content: [
            { type: "tool-result", content: [{ type: "text", text: JSON.stringify({ ...PROGRESS, progressLabel: "连接图 5%" }) }] },
          ],
        },
        {
          kind: "tool-result",
          seq: 200,
          call: { name: "insar_status", argsRaw: "{}" },
          content: [
            { type: "tool-result", content: [{ type: "text", text: JSON.stringify({ ...PROGRESS, progressLabel: "干涉图生成 51%" }) }] },
          ],
        },
      ],
    };
    rerender(createElement(InsarTurnTail, { matched: { status: PROGRESS }, useSession }));
    expect(screen.getByText("干涉图生成 51%")).toBeTruthy();
    expect(screen.queryByText("连接图 5%")).toBeNull();
  });

  it("本 turn 无 insar_status 时不被历史快照泄漏压制（experiments 分支可达）", () => {
    // 会话历史里曾有 insar_status，但本 turn 的 matched 只有 insar_list 结果
    const snapshot = {
      nodes: [
        {
          kind: "tool-result",
          seq: 50,
          call: { name: "insar_status", argsRaw: "{}" },
          content: [
            { type: "tool-result", content: [{ type: "text", text: JSON.stringify(PROGRESS) }] },
          ],
        },
      ],
    };
    const useSession = (sel: (s: unknown) => unknown) => sel(snapshot);
    render(createElement(InsarTurnTail, {
      matched: { experiments: [{ id: "e1", name: "minqin", terrain: "desert", status: "running" }] },
      useSession,
    }));
    // 渲染实验列表而非被历史进度压制
    expect(screen.getByText("insar-genie 设置")).toBeTruthy();
    expect(screen.getByText(/minqin/)).toBeTruthy();
    expect(screen.queryByText(/干涉图生成/)).toBeNull();
  });

  it("matched.experiments 渲染实验列表", () => {
    render(createElement(InsarTurnTail, {
      matched: { experiments: [{ id: "e1", name: "minqin", terrain: "desert", status: "running" }] },
      useSession: noSnapshot,
    }));
    expect(screen.getByText("insar-genie 设置")).toBeTruthy();
    expect(screen.getByText(/minqin/)).toBeTruthy();
  });

  it("matched.registered 渲染注册成功提示", () => {
    render(createElement(InsarTurnTail, {
      matched: { registered: { ok: true, experimentId: "e9" } },
      useSession: noSnapshot,
    }));
    expect(screen.getByText(/实验已注册：e9/)).toBeTruthy();
  });

  it("registered.ok=false 不渲染成功提示", () => {
    const { container } = render(createElement(InsarTurnTail, {
      matched: { registered: { ok: false, experimentId: "e9" } },
      useSession: noSnapshot,
    }));
    expect(container.firstChild).toBeNull();
  });

  it("matched.paramConfirm 渲染参数确认卡", () => {
    render(createElement(InsarTurnTail, {
      matched: {
        paramConfirm: {
          terrain: "desert",
          params: {
            rgLooks: 8, azLooks: 2, maxTimeBaselineDays: 180, maxPercBaseline: 2,
            filtering: "GOLDSTEIN", goldsteinWinSize: 64, unwrap: "MCF", unwrapCohThreshold: 0.2,
            useGacos: true, demFile: "",
          },
        },
      },
      useSession: noSnapshot,
    }));
    expect(screen.getByText("确认执行")).toBeTruthy();
  });

  it("无数据时渲染 null", () => {
    const { container } = render(createElement(InsarTurnTail, { matched: {}, useSession: noSnapshot }));
    expect(container.firstChild).toBeNull();
  });
});

describe("SettingsCard（设置表单字段）", () => {
  it("GACOS 授权码显示为'邮箱授权码'而非'IMAP 授权码'（普通用户可读）", () => {
    render(createElement(SettingsCard, {}));
    expect(screen.getByText("GACOS 邮箱授权码")).toBeTruthy();
    expect(screen.queryByText(/IMAP 授权码/)).toBeNull();
  });

  it("不显示死字段'注册表目录'（registry 目录由 host 硬编码，用户无需配置）", () => {
    render(createElement(SettingsCard, {}));
    expect(screen.queryByText("注册表目录")).toBeNull();
  });

  it("autoDetected 标记显示'启动时自动定位'（ENVI/SARscape 探测命中提示）", () => {
    render(createElement(SettingsCard, {
      settings: { enviIdl: "C:\\Program Files\\Harris\\ENVI56\\IDL88\\bin\\bin.x86_64\\envi_idl.exe" },
      autoDetected: { enviIdl: true, sarscapeLib: true },
    }));
    expect(screen.getAllByText("▲ 启动时自动定位").length).toBe(2);
  });
});

describe("ParamConfirm", () => {
  const params: ParamSnapshot = {
    rgLooks: 8, azLooks: 2, maxTimeBaselineDays: 180, maxPercBaseline: 2,
    filtering: "GOLDSTEIN", goldsteinWinSize: 64, unwrap: "MCF", unwrapCohThreshold: 0.2,
    useGacos: true, demFile: "",
  };

  it("基线 2% 时确认按钮可用", () => {
    render(createElement(ParamConfirm, {
      terrain: "desert", params,
      onConfirm: () => {}, onCancel: () => {},
    }));
    const btn = screen.getByText("确认执行") as HTMLButtonElement;
    expect(btn.disabled).toBe(false);
  });

  it("基线 45% 时确认按钮禁用 + 红色警告", () => {
    render(createElement(ParamConfirm, {
      terrain: "desert",
      params: { ...params, maxPercBaseline: 45 },
      onConfirm: () => {}, onCancel: () => {},
    }));
    const btn = screen.getByText("确认执行") as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
    expect(screen.getByText(/空间基线 45%/)).toBeTruthy();
  });

  it("修改基线到 2% 后按钮启用", () => {
    render(createElement(ParamConfirm, {
      terrain: "desert",
      params: { ...params, maxPercBaseline: 45 },
      onConfirm: () => {}, onCancel: () => {},
    }));
    // 通过 label 文本定位输入框（避免 displayValue 多匹配歧义）
    const input = screen.getByLabelText(/空间基线/) as HTMLInputElement;
    fireEvent.change(input, { target: { value: "2" } });
    const btn = screen.getByText("确认执行") as HTMLButtonElement;
    expect(btn.disabled).toBe(false);
  });
});
