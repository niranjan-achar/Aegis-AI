/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        aegis: {
          bg: "#071018",
          surface: "#0c1724",
          primary: "#22e1c3",
          danger: "#ff6b6b",
          warning: "#ffb84d",
          success: "#57e389",
          info: "#47c0ff",
          muted: "rgba(214,226,239,0.55)"
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
