/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      colors: {
        surface: {
          canvas: '#E6EAF2',
          app: '#F5F7FB',
          sidebar: '#FFFFFF',
          panel: '#E3E7F7',
          banner: '#E5E9F8',
          chart: '#EBF0FA',
          tooltip: '#D3D9F2',
          muted: '#F3F5FA',
          card: '#FFFFFF',
        },
        brand: {
          50: '#F2F4FC',
          100: '#E6E8F8',
          200: '#CFD5EE',
          300: '#AAB2E0',
          400: '#8891D4',
          500: '#6C72C9',
          600: '#575DB5',
          700: '#474B9E',
          800: '#353A85',
          900: '#2D317A',
        },
        ink: {
          primary: '#2D317A',
          secondary: '#5A607F',
          muted: '#8C93B0',
        },
        status: {
          infoBg: '#E1F3F7',
          infoText: '#1E6B7B',
          warningBg: '#FDF0E1',
          warningText: '#B45309',
          dangerBg: '#FCE8E9',
          dangerText: '#BE123C',
          successBg: '#E3F6EC',
          successText: '#15803D',
        },
      },
      borderRadius: {
        shell: '28px',
        card: '20px',
        badge: '12px',
        pill: '10px',
      },
      boxShadow: {
        shell: '0 24px 60px -15px rgba(45, 49, 122, 0.12)',
        card: '0 6px 20px -4px rgba(45, 49, 122, 0.05)',
        pill: '0 2px 8px rgba(45, 49, 122, 0.08)',
      },
    },
  },
  plugins: [],
};
