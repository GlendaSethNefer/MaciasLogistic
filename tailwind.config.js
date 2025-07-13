/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./templates/**/*.jinja2",
    "./templates/**/*.j2",
    "./app.py"
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}