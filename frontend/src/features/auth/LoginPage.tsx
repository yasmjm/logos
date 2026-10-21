import { useMutation } from '@tanstack/react-query'
import { ArrowUpRight, CircleAlert, Clock, KeyRound, LoaderCircle, Users } from 'lucide-react'
import { type FormEvent, useState } from 'react'

import { login } from '@/api/auth'
import { API_URL } from '@/api/config'
import { ApiError, NetworkError } from '@/api/errors'
import { startSession, takeEndReason } from '@/api/session'
import type { TokenResponse } from '@/api/types'
import { LogoMark } from '@/components/LogoMark'
import { ThemeToggle } from '@/components/ThemeToggle'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { DEMO_ACCOUNTS, DEMO_PASSWORD } from '@/features/auth/demoAccounts'
import { type ApiStatus, useApiStatus } from '@/features/auth/useApiStatus'
import { useCountdown } from '@/lib/useCountdown'

type Attempt = { source: 'form' | (typeof DEMO_ACCOUNTS)[number]['username'] }

const STATUS_NOTICE: Partial<Record<ApiStatus, { title: string; text: string }>> = {
  waking: {
    title: 'A API está acordando…',
    text: 'O primeiro acesso depois de um tempo parado pode levar alguns segundos.',
  },
  'database-waking': {
    title: 'O banco de dados está acordando…',
    text: 'A API respondeu, mas o banco ainda não. Tentamos de novo sozinhos.',
  },
  offline: {
    title: 'Não conseguimos falar com a API agora',
    text: 'Ela pode estar fora do ar. Tentamos de novo a cada poucos segundos.',
  },
}

function errorMessage(error: unknown, secondsLeft: number): string {
  if (error instanceof ApiError) {
    if (error.status === 401) return 'Usuário ou senha inválidos.'
    if (error.status === 429) {
      return secondsLeft > 0
        ? `Muitas tentativas de login. Tente de novo em ${secondsLeft} s.`
        : 'Você já pode tentar de novo.'
    }
    if (error.status === 422) return 'Preencha usuário e senha.'
    if (error.status >= 500) return 'A API está indisponível no momento. Tente em instantes.'
    return error.detail
  }
  if (error instanceof NetworkError) {
    return error.timedOut
      ? 'A API demorou demais para responder. Ela pode estar acordando; tente de novo.'
      : 'Não conseguimos falar com a API. Verifique a conexão ou tente em instantes.'
  }
  return 'Algo deu errado ao entrar. Tente de novo.'
}

export function LoginPage() {
  const [expired] = useState(() => takeEndReason() === 'expired')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const apiStatus = useApiStatus()

  const signIn = useMutation<TokenResponse, unknown, { username: string; password: string } & Attempt>(
    {
      mutationFn: ({ username: user, password: pass }) => login(user, pass),
      onSuccess: (token) => startSession({ token: token.access_token, analyst: token.analyst }),
    },
  )

  const rateLimit =
    signIn.error instanceof ApiError && signIn.error.status === 429
      ? signIn.error.retryAfterSeconds
      : null
  const secondsLeft = useCountdown(rateLimit, signIn.submittedAt)
  const blocked = secondsLeft > 0
  const busy = signIn.isPending

  function submit(event: FormEvent) {
    event.preventDefault()
    signIn.mutate({ username: username.trim(), password, source: 'form' })
  }

  function signInAs(account: (typeof DEMO_ACCOUNTS)[number]) {
    signIn.mutate({ username: account.username, password: DEMO_PASSWORD, source: account.username })
  }

  const pendingSource = busy ? signIn.variables?.source : null
  const notice = STATUS_NOTICE[apiStatus]

  return (
    <div className="flex min-h-svh flex-col">
      <header className="flex h-12 items-center justify-between border-b px-4">
        <LogoMark />
        <ThemeToggle />
      </header>

      <main className="flex flex-1 items-start justify-center px-4 py-10 sm:items-center">
        <div className="grid w-full max-w-md gap-4">
          <section aria-labelledby="about-title" className="grid gap-1">
            <h1 id="about-title" className="text-xl font-semibold tracking-tight">
              Central de Resposta a Incidentes
            </h1>
            <p className="text-text-muted">
              O Logos reúne os incidentes da frota numa fila única, ordenada por prioridade, e deixa
              claro quem está cuidando de cada um.
            </p>
            <a
              className="inline-flex w-fit items-center gap-1 text-sm text-text"
              href={`${API_URL}/docs`}
              target="_blank"
              rel="noreferrer"
            >
              Documentação da API
              <ArrowUpRight aria-hidden className="size-3.5" />
            </a>
          </section>

          {expired && (
            <Alert>
              <Clock aria-hidden />
              <AlertTitle>Sua sessão expirou</AlertTitle>
              <AlertDescription>Entre novamente para continuar.</AlertDescription>
            </Alert>
          )}

          {notice && (
            <Alert role="status">
              <LoaderCircle aria-hidden className="animate-spin" />
              <AlertTitle>{notice.title}</AlertTitle>
              <AlertDescription>{notice.text}</AlertDescription>
            </Alert>
          )}

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Users aria-hidden className="size-4" />
                Acesso de demonstração
              </CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3">
              <div className="grid grid-cols-2 gap-2">
                {DEMO_ACCOUNTS.map((account) => (
                  <Button
                    key={account.username}
                    type="button"
                    className="h-12 text-sm"
                    disabled={busy || blocked}
                    onClick={() => signInAs(account)}
                  >
                    {pendingSource === account.username ? (
                      <>
                        <LoaderCircle aria-hidden className="animate-spin" />
                        Entrando…
                      </>
                    ) : (
                      `Entrar como ${account.name}`
                    )}
                  </Button>
                ))}
              </div>
              <p className="text-xs text-text-muted">
                Contas de teste. Entre como Ana numa aba e como Bruno em outra para ver o conflito
                quando os dois tentam assumir o mesmo incidente.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <KeyRound aria-hidden className="size-4" />
                Entrar com usuário e senha
              </CardTitle>
            </CardHeader>
            <CardContent>
              <form className="grid gap-3" onSubmit={submit} noValidate>
                <div className="grid gap-1.5">
                  <Label htmlFor="username">Usuário</Label>
                  <Input
                    id="username"
                    autoComplete="username"
                    autoCapitalize="none"
                    spellCheck={false}
                    value={username}
                    onChange={(event) => setUsername(event.target.value)}
                    required
                  />
                </div>
                <div className="grid gap-1.5">
                  <Label htmlFor="password">Senha</Label>
                  <Input
                    id="password"
                    type="password"
                    autoComplete="current-password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    required
                  />
                </div>
                <Button
                  type="submit"
                  className="h-10"
                  disabled={busy || blocked || !username.trim() || !password}
                >
                  {pendingSource === 'form' ? (
                    <>
                      <LoaderCircle aria-hidden className="animate-spin" />
                      Entrando…
                    </>
                  ) : (
                    'Entrar'
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>

          <div aria-live="polite">
            {signIn.isError && (
              <Alert variant="destructive">
                <CircleAlert aria-hidden />
                <AlertTitle>Não foi possível entrar</AlertTitle>
                <AlertDescription>{errorMessage(signIn.error, secondsLeft)}</AlertDescription>
              </Alert>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
