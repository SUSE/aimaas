/* eslint-env node */
require("@rushstack/eslint-patch/modern-module-resolution");

module.exports = {
  // Stop looking for configuration files in parent directories
  root: true,
  extends: [
    // Base rules for Vue 3
    "plugin:vue/vue3-essential",
    // ESLint recommended rules
    "eslint:recommended",
    // don't force prettier formatting, we don't follow it consistently
    "@vue/eslint-config-prettier/skip-formatting",
  ],
  rules: {
    // Disable the requirement for multi-word component names
    // We have components like breadcrumbs or Tabbing that conflict with this
    "vue/multi-word-component-names": "off",
  },
  parserOptions: {
    ecmaVersion: "latest",
  },
};
