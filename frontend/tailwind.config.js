/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        neon: {
          50: '#e8ffe8',
          100: '#c5ffc5',
          200: '#8fff8f',
          300: '#5cff5c',
          400: '#2cff05',
          500: '#24d904',
          600: '#1cb303',
          700: '#158c02',
          800: '#0e6602',
          900: '#074001',
        },
        dark: {
          50: '#f8fafc',
          100: '#e2e8f0',
          200: '#cbd5e1',
          300: '#94a3b8',
          400: '#64748b',
          500: '#475569',
          600: '#334155',
          700: '#1e293b',
          800: '#0f172a',
          900: '#0a0f1a',
          950: '#050709',
        }
      },
      animation: {
        'float': 'float 20s ease-in-out infinite',
        'float-delayed': 'float 25s ease-in-out infinite reverse',
        'float-slow': 'float 30s ease-in-out infinite',
        'pulse-glow': 'pulse-glow 4s ease-in-out infinite',
        'shimmer': 'shimmer 3s ease-in-out infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translate(0, 0) scale(1)' },
          '25%': { transform: 'translate(100px, -50px) scale(1.1)' },
          '50%': { transform: 'translate(50px, 100px) scale(0.9)' },
          '75%': { transform: 'translate(-50px, 50px) scale(1.05)' },
        },
        'pulse-glow': {
          '0%, 100%': { opacity: '0.4', filter: 'blur(80px)' },
          '50%': { opacity: '0.7', filter: 'blur(120px)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
      backdropBlur: {
        xs: '2px',
      },
      boxShadow: {
        'glass': '0 8px 32px 0 rgba(44, 255, 5, 0.1)',
        'glass-lg': '0 16px 48px 0 rgba(44, 255, 5, 0.15)',
        'neon': '0 0 20px rgba(44, 255, 5, 0.3), 0 0 40px rgba(44, 255, 5, 0.1)',
        'neon-lg': '0 0 30px rgba(44, 255, 5, 0.4), 0 0 60px rgba(44, 255, 5, 0.2)',
      },
    },
  },
  plugins: [],
}
