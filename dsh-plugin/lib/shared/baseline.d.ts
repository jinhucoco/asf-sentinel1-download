/**
 * 防呆：空间基线必须 2-4%（设计铁律，杜绝 45% 事故）。
 * 单一来源：host（templates.ts）与 client（ParamConfirm 确认卡）共用，避免双源漂移。
 * 纯函数、无任何平台依赖，可同时被 host 与 client（tsdown browser bundle）引用。
 */
export declare function validateBaseline(perc: number): {
    ok: boolean;
    message?: string;
};
