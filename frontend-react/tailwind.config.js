/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#FAF5EE",
        surface: {
          DEFAULT: "#FAF5EE",
          dim: "#DCD6CC",
          bright: "#FAF5EE",
          lowest: "#FFFFFF",
          low: "#F6F0E8",
          container: "#F2ECE4",
          high: "#ECE6DC",
          highest: "#E6E0D6",
        },
        primary: {
          DEFAULT: "#C2652A",
          hover: "#A85320",
          container: "#E08850",
          fixed: "#FBE8D8",
          dim: "#F0A878",
        },
        secondary: {
          DEFAULT: "#78706A",
          container: "#EAE2DA",
          fixed: "#EAE2DA",
          dim: "#CEC6BE",
        },
        grounding: {
          DEFAULT: "#006E4B",
          emerald: "#10B981",
          container: "#D1FAE5",
          badge: "#ECFDF5",
        },
        neutral: {
          dark: "#3A302A",
          muted: "#605850",
          light: "#78706A",
          border: "#D8D0C8",
          subtle: "#EAE2DA",
        },
        error: {
          DEFAULT: "#C0392B",
          container: "#FCE4E0",
        },
      },
      fontFamily: {
        headline: ["'EB Garamond'", "Georgia", "serif"],
        display: ["'EB Garamond'", "Georgia", "serif"],
        body: ["'Manrope'", "'Inter'", "-apple-system", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
      boxShadow: {
        soft: "0 2px 16px rgba(58, 48, 42, 0.05)",
        card: "0 1px 3px rgba(58, 48, 42, 0.06), 0 1px 2px rgba(58, 48, 42, 0.04)",
        dropdown: "0 10px 25px -5px rgba(58, 48, 42, 0.1), 0 8px 10px -6px rgba(58, 48, 42, 0.05)",
      },
      borderRadius: {
        DEFAULT: "0.375rem",
        md: "0.5rem",
        lg: "0.75rem",
        xl: "1rem",
        "2xl": "1.25rem",
      },
    },
  },
  plugins: [
    require("@tailwindcss/typography"),
  ],
};
