/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1C1917",
        sand: "#F3EEE4",
        paper: "#FFFbf5",
        forest: {
          DEFAULT: "#1F4D3A",
          deep: "#16382B",
          mist: "#DCE8E1",
        },
        clay: "#B85C38",
      },
      fontFamily: {
        sans: ["DM Sans", "system-ui", "sans-serif"],
        display: ["Fraunces", "Georgia", "serif"],
      },
      boxShadow: {
        card: "0 10px 30px -18px rgba(28, 25, 23, 0.35)",
      },
    },
  },
  plugins: [],
};
