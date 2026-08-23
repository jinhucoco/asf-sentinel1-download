import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { randomUUID } from "node:crypto";
export function createRegistry(dir) {
    const file = join(dir, "experiments.json");
    let items = [];
    if (existsSync(file)) {
        try {
            items = JSON.parse(readFileSync(file, "utf8"));
        }
        catch {
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
