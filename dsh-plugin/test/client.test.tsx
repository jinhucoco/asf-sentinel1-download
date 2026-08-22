// @vitest-environment jsdom
import { describe, it, expect, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { createElement } from "react";
import { ProgressPanel } from "../src/client/ProgressPanel.js";
import { ParamConfirm } from "../src/client/ParamConfirm.js";
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
