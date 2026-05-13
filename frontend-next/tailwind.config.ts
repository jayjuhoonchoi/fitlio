import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0B0E14",
        panel: "#111622",
        panelElevated: "#151B2A",
        border: "#232C43",
        text: "#E8EEF8",
        muted: "#9AA6C1",
        accent: "#5EE6A8",
        silver: "#B9C4D9",
        danger: "#F87171"
      },
      borderRadius: {
        xl2: "1rem"
      },
      boxShadow: {
        soft: "0 10px 30px rgba(0,0,0,0.24)"
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"]
      }
    }
  },
  plugins: []
};

export default config;
