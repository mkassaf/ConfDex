/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          DEFAULT: "#25408F",
          dark:    "#1A2E65",
          deeper:  "#0f1629",
        },
        gold: {
          DEFAULT: "#f1c350",
          hover:   "#fad762",
          muted:   "#c49a28",
        },
      },
    },
  },
  plugins: [],
};
