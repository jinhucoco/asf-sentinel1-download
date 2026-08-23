import type { Experiment } from "../shared/types.js";
export interface Registry {
    list(): Experiment[];
    get(id: string): Experiment | undefined;
    create(data: Omit<Experiment, "id">): string;
    update(id: string, patch: Partial<Experiment>): void;
}
export declare function createRegistry(dir: string): Registry;
