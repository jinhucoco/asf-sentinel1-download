import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { randomUUID } from "node:crypto";
import type { Experiment } from "../shared/types.js";

export interface Registry {
  list(): Experiment[];
  get(id: string): Experiment | undefined;
  create(data: Omit<Experiment, "id">): string;
  update(id: string, patch: Partial<Experiment>): void;
}

export function createRegistry(dir: string): Registry {
  const file = join(dir, "experiments.json");
  let items: Experiment[] = [];
  if (existsSync(file)) {
    try {
      items = JSON.parse(readFileSync(file, "utf8")) as Experiment[];
    } catch {
      items = [];
    }
  }
  const persist = () => {
    mkdirSync(dir, { recursive: true });
    writeFileSync(file, JSON.stringify(items, null, 2), "utf8");
  };
  return {
    list: () => items,
    get: (id) => items.find((e) => e.id === id),
    create(data) {
      const id = randomUUID().slice(0, 8);
      items.push({ ...data, id });
      persist();
      return id;
    },
    update(id, patch) {
      const i = items.findIndex((e) => e.id === id);
      if (i >= 0) {
        items[i] = { ...items[i], ...patch, id };
        persist();
      }
    },
  };
}
