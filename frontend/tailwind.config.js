/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        lime: {
          50: '#f7fee7',
          100: '#ecfccb',
          200: '#d9f99d',
          300: '#bef264',
          400: '#a3e635',
          500: '#84cc16',
          600: '#65a30d',
          accent: '#9ee82a',
        },
        lavender: {
          50: '#faf5ff',
          100: '#f3e8ff',
          200: '#e9d5ff',
          300: '#d8b4fe',
          400: '#c084fc',
          500: '#a855f7',
          600: '#9333ea',
          accent: '#c4b5fd',
        },
        charcoal: {
          950: '#0f1316',
          900: '#14181c',
          850: '#191f24',
          800: '#1f262c',
          700: '#2c353d',
          600: '#3e4a55',
          500: '#52606d',
        },
        paleLime: {
          canvas: '#edf6e8',
          subtle: '#f4f9f0',
        },
        sage: {
          50: '#f4f7f5',
          100: '#e5ece7',
          200: '#ccdbc0',
          500: '#4a7c59',
          600: '#3d6749',
          700: '#32533b',
          900: '#1b2d20',
        }
      }
    },
  },
  plugins: [],
}
