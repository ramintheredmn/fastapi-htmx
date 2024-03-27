/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/templates/**/*.html", "./app/templates/**/**/*.html"],
  theme: {
    fontFamily: {
      "iransans-light": ["iransans-light", "sans-serif"],
      "iransans-medium": ["iransans-medium", "sans-serif"],
      "iransans-bold": ["iransans-bold", "sans-serif"],
      "iransans-ultra-light": ["iransans-ultra-light", "sans-serif"],
    },
    extend: {},
  },
  plugins: [],
};
