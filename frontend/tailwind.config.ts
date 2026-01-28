import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        // Deep Space Base
        void: "#030014",
        nebula: "#0f172a",

        // Brand Gradients
        brand: {
          50: "#f4f8ff",
          400: "#818cf8",
          500: "#6366f1",
          600: "#4f46e5",
          cyan: "#06b6d4",
          purple: "#a855f7",
        },

        // Semantic
        danger: "#f43f5e",
        success: "#10b981",
        warning: "#f59e0b",
      },
      backgroundImage: {
        'cosmic-gradient': 'radial-gradient(circle at 50% 0%, #1e1b4b 0%, #030014 60%)',
        'glass-gradient': 'linear-gradient(145deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.01) 100%)',
      },
      animation: {
        'float': 'float 6s ease-in-out infinite',
        'pulse-glow': 'pulse-glow 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 3s linear infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        'pulse-glow': {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(99, 102, 241, 0)' },
          '50%': { boxShadow: '0 0 20px 0 rgba(99, 102, 241, 0.3)' },
        }
      }
    },
  },
  plugins: [],
};

export default config;
