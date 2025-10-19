import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f4f8ff",
          100: "#e6efff",
          200: "#c7dafe",
          300: "#9ebcfd",
          400: "#6d93fb",
          500: "#426af6",
          600: "#2e4fe3",
          700: "#2540be",
          800: "#233697",
          900: "#222f76"
        }
      }
    },
  },
  plugins: [],
};

export default config;

