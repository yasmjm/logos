import '@fontsource/inter/400.css'
import '@fontsource/inter/500.css'
import '@fontsource/inter/600.css'
import '@fontsource/inter/700.css'
import '@fontsource/jetbrains-mono/400.css'
import '@fontsource/jetbrains-mono/500.css'
import './index.css'

import { QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { createQueryClient } from '@/api/queryClient'
import App from '@/App'
import { AppToaster } from '@/components/AppToaster'
import { TooltipProvider } from '@/components/ui/tooltip'
import { initTheme } from '@/lib/theme'

initTheme()
const queryClient = createQueryClient()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <TooltipProvider delayDuration={300}>
        <App />
        <AppToaster />
      </TooltipProvider>
    </QueryClientProvider>
  </StrictMode>,
)
