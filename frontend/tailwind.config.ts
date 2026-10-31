import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx,js,jsx}"],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#2563EB",
          hover: "#1D4ED8",
          light: "#EFF6FF",
          foreground: "#FFFFFF",
        },
        "bg-app": "#F8FAFC",
        "bg-surface": "#FFFFFF",
        "bg-sidebar": "#F1F5F9",
        "text-primary": "#0F172A",
        "text-secondary": "#475569",
        "text-muted": "#64748B",
        "border-default": "#E2E8F0",
        status: {
          success: "#16A34A",
          warning: "#D97706",
          danger: "#DC2626",
        },
        background: "#F8FAFC",
        surface: "#FFFFFF",
        sidebar: "#F1F5F9",
        foreground: "#0F172A",
        border: "#E2E8F0",
      },
      fontFamily: {
        sans: [
          "Inter",
          "Be Vietnam Pro",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;

