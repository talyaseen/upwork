import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/app/**/*.{ts,tsx}",
    "./src/components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          900: "#0a0a0f",
          800: "#111118",
          700: "#16161f",
          600: "#1d1d28",
          500: "#262633",
        },
        gilt: {
          DEFAULT: "#c8a25a",
          soft: "#d9bd86",
          deep: "#a37e3c",
        },
      },
      fontFamily: {
        display: ['"Playfair Display"', "Georgia", "Cambria", "serif"],
        sans: [
          "Inter",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
      },
      letterSpacing: {
        luxe: "0.18em",
      },
      boxShadow: {
        card: "0 1px 0 0 rgba(255,255,255,0.04) inset, 0 24px 48px -24px rgba(0,0,0,0.85)",
        glow: "0 0 0 1px rgba(200,162,90,0.25), 0 16px 40px -16px rgba(200,162,90,0.18)",
      },
      backgroundImage: {
        "grain":
          "radial-gradient(circle at 1px 1px, rgba(255,255,255,0.04) 1px, transparent 0)",
      },
    },
  },
  plugins: [],
};

export default config;
