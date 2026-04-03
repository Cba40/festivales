/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'media',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: '#1e3a8a',
        success: '#22c55e',
        warning: '#f59e0b',
        danger: '#dc2626',
      },
    },
  },
  plugins: [],
};
