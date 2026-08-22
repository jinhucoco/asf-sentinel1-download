import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["test/**/*.test.ts", "test/**/*.test.tsx"],
    environment: "node",
    // client 组件测试用 jsdom + development React（act() 支持需要 dev 构建）
    environmentMatchGlobs: [
      ["test/client.test.tsx", "jsdom"],
    ],
    env: {
      NODE_ENV: "development",
    },
  },
});
