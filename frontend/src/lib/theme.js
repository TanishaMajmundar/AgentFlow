// Builds a theme-aware color string from a design token, e.g. rgb("data") or rgb("data", 0.3).
// Works in inline styles because the tokens are CSS variables that change with the theme.
export const rgb = (token, alpha) =>
  alpha == null ? `rgb(var(--c-${token}))` : `rgb(var(--c-${token}) / ${alpha})`;
