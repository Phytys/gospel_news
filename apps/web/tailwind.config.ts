import type { Config } from "tailwindcss";

export default {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      fontFamily: {
        serif: ["Georgia", "Cambria", "Times New Roman", "serif"],
        sans: ["system-ui", "Segoe UI", "sans-serif"],
      },
      colors: {
        ink: "#1a1a1a",
        paper: "#faf8f5",
        muted: "#5c5c5c",
        accent: "#3d4f3f",
      },
    },
  },
  plugins: [],
} satisfies Config;
