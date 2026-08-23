/** 探测 ENVI IDL 可执行文件路径 */
export declare function probeEnviIdl(fallback: string, roots?: string[]): string;
/** 探测 SARscape 根目录 */
export declare function probeSarscape(fallback: string, roots?: string[]): string;
/** 启动时组合探测，返回 base 层默认值（给 SettingsSchema 注入） */
export declare function probeDefaults(current: {
    enviIdl: string;
    sarscapeLib: string;
}): {
    enviIdl: string;
    sarscapeLib: string;
};
