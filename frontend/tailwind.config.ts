import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        bg: {
          base: "#07090b",
          surface: "#0d1117",
          elevated: "#141c24",
          border: "#1d2b38",
        },
        accent: {
          DEFAULT: "#00d4a0",
          dim: "#00a07a",
          glow: "rgba(0,212,160,0.12)",
        },
        text: {
          primary: "#dce8f0",
          secondary: "#7a9aad",
          muted: "#3d5566",
        },
        status: {
          success: "#00d4a0",
          pending: "#e8a020",
          failure: "#d04040",
        },
      },
      fontFamily: {
        display: ["var(--font-syne)", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
        body: ["var(--font-body)", "sans-serif"],
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "fade-in": "fadeIn 0.4s ease forwards",
        "slide-up": "slideUp 0.4s ease forwards",
      },
      keyframes: {
        fadeIn: {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        slideUp: {
          from: { opacity: "0", transform: "translateY(12px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
