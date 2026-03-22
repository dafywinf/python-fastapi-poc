/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#4f46e5',
          hover: '#4338ca',
          light: '#ede9fe',
          text: '#5b21b6',
        },
      },
    },
  },
  plugins: [],
}
