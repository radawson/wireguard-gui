module.exports = {
  content: [
    "./src/gui/templates/**/*.html",
    "./src/gui/static/js/**/*.js",
    "./src/gui/static/src/**/*.js"
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Roboto", "ui-sans-serif", "system-ui", "sans-serif"]
      }
    }
  },
  plugins: []
};
