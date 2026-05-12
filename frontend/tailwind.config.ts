import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {},
  },
  plugins: [],
  // 避免与 Ant Design 样式冲突
  corePlugins: {
    preflight: false,
  },
};

export default config;
