/** @type {import('tailwindcss').Config} */
// All colors are CSS variables (RGB channels) defined in src/index.css, so every utility —
// including opacity ones like bg-brand/10 — switches automatically between dark and light.
const v = (name) => `rgb(var(--c-${name}) / <alpha-value>)`;

export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontSize: { meta: ["12px", { lineHeight: "16px" }] },      
      colors: {
        void: v("void"),
        deep: v("deep"),
        panel: v("panel"),
        panel2: v("panel2"),
        line: v("line"),
        line2: v("line2"),
        edge: v("edge"),
        idle: v("idle"),
        dash: v("dash"),
        ink: v("ink"),
        muted: v("muted"),
        dim: v("dim"),
        brand: { DEFAULT: v("brand"), hover: v("brand-hover") },
        "on-brand": v("on-brand"),
        data: v("data"),
        strategy: v("strategy"),
        training: v("training"),
        danger: v("danger"),
      },
      fontFamily: {
        display: ['"Fraunces Variable"', "Georgia", "serif"],
        sans: ['"Instrument Sans Variable"', "system-ui", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "monospace"],
      },
      // squarer corners everywhere = more "printed", less "app template"
      borderRadius: { sm: "3px", DEFAULT: "4px", md: "5px", lg: "7px", xl: "9px", "2xl": "12px" },
      keyframes: {
        travel: {
          "0%": { left: "0%", opacity: "0" }, "6%": { opacity: "1" },
          "94%": { opacity: "1" }, "100%": { left: "100%", opacity: "0" },
        },
        travelV: {
          "0%": { top: "0%", opacity: "0" }, "6%": { opacity: "1" },
          "94%": { opacity: "1" }, "100%": { top: "100%", opacity: "0" },
        },
        pulseRing: {
          "0%": { boxShadow: "0 0 0 0 currentColor" },
          "100%": { boxShadow: "0 0 0 10px transparent" },
        },
        pageIn: {
          from: { opacity: "0", transform: "translateY(14px) scale(0.995)" },
          to: { opacity: "1", transform: "translateY(0) scale(1)" },
        },
        pop: {
          "0%": { transform: "scale(0.6)" },
          "60%": { transform: "scale(1.18)" },
          "100%": { transform: "scale(1)" },
        },
        float: {
          "0%,100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-6px)" },
        },
        driftA: {
          "0%,100%": { transform: "translate3d(0,0,0) scale(1)" },
          "50%": { transform: "translate3d(60px,40px,0) scale(1.15)" },
        },
        driftB: {
          "0%,100%": { transform: "translate3d(0,0,0) scale(1)" },
          "50%": { transform: "translate3d(-70px,50px,0) scale(0.9)" },
        },
        driftC: {
          "0%,100%": { transform: "translate3d(0,0,0) scale(1)" },
          "50%": { transform: "translate3d(40px,-50px,0) scale(1.1)" },
        },
        sweep: { "0%": { transform: "translateX(-100%)" }, "100%": { transform: "translateX(350%)" } },
        ringBurst: {
          "0%": { transform: "scale(0.6)", opacity: "0.7" },
          "100%": { transform: "scale(2.2)", opacity: "0" },
        },
        drawCheck: { to: { strokeDashoffset: "0" } },
        slideIn: { from: { transform: "translateX(-100%)" }, to: { transform: "translateX(0)" } },
        overlayIn: { from: { opacity: "0" }, to: { opacity: "1" } },
      },
      animation: {
        travel: "travel 5.5s linear infinite",
        "travel-v": "travelV 5.5s linear infinite",
        "pulse-ring": "pulseRing 2.2s ease-out infinite",
        "fade-in": "fadeIn .4s cubic-bezier(.2,.7,.2,1) both",
        "page-in": "pageIn .5s cubic-bezier(.2,.7,.2,1) both",
        pop: "pop .45s cubic-bezier(.3,1.4,.5,1) both",
        float: "float 3.4s ease-in-out infinite",
        "drift-a": "driftA 18s ease-in-out infinite",
        "drift-b": "driftB 22s ease-in-out infinite",
        "drift-c": "driftC 20s ease-in-out infinite",
        sweep: "sweep 1.5s ease-in-out infinite",
        "ring-burst": "ringBurst 1.2s ease-out both",
        "draw-check": "drawCheck .5s .25s ease-out forwards",
        "slide-in": "slideIn .32s cubic-bezier(.2,.7,.2,1) both",
        "overlay-in": "overlayIn .25s ease both",
      },
    },
  },
  plugins: [],
};
