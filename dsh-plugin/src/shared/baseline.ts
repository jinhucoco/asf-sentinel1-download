/**
 * 防呆：空间基线必须 2-4%（设计铁律，杜绝 45% 事故）。
 * 单一来源：host（templates.ts）与 client（ParamConfirm 确认卡）共用，避免双源漂移。
 * 纯函数、无任何平台依赖，可同时被 host 与 client（tsdown browser bundle）引用。
 */
export function validateBaseline(
  perc: number,
): { ok: boolean; message?: string } {
  if (perc >= 2 && perc <= 4) return { ok: true };
  return {
    ok: false,
    message: `空间基线 ${perc}% 不在允许区间 2-4%（SARscape 默认 45% 是事故根源，已禁止）`,
  };
}
