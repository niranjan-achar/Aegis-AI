/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        aegis: {
          bg: "#0a0a0f",
          surface: "#0d1117",
          primary: "#6C63FF",
          danger: "#f76471",
          warning: "#f6bb4f",
          success: "#2ED573",
          info: "#3896f5",
          muted: "rgba(255,255,255,0.45)"
        }
      },
      boxShadow: {
        glass: "0 8px 32px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255,255,255,0.1)"
      },
      borderRadius: {
        glass: "16px"
      }
    },
  },
  plugins: [],
};
