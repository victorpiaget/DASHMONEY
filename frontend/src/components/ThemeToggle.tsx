import { useTheme } from '../context/ThemeContext'

export default function ThemeToggle({ className = '' }: { className?: string }) {
  const { theme, toggleTheme } = useTheme()
  return (
    <button
      onClick={toggleTheme}
      title={theme === 'dark' ? 'Passer en mode clair' : 'Passer en mode sombre'}
      className={`w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors text-sm ${className}`}
    >
      {theme === 'dark' ? '☀' : '◑'}
    </button>
  )
}
