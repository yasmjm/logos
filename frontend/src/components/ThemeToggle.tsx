import { Moon, Sun } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { useTheme } from '@/lib/theme'

export function ThemeToggle() {
  const { theme, toggle } = useTheme()
  const next = theme === 'dark' ? 'claro' : 'escuro'
  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={toggle}
      aria-label={`Mudar para o tema ${next}`}
      title={`Tema ${next}`}
    >
      {theme === 'dark' ? <Sun aria-hidden /> : <Moon aria-hidden />}
    </Button>
  )
}
