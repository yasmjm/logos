# ADR 0005: Chatbot de triagem guiado no WhatsApp (simulado no MVP)

- **Status:** aceito
- **Data:** 2026-10-21

## Contexto

O motorista já usa o WhatsApp e não vai instalar outro app (o app do motorista está fora do escopo). Hoje o relato chega como texto livre ("aqui é o 1042, bati na BR"), e a central gasta tempo perguntando de novo o caminhão, o local e se há feridos. O MVP não integra com a Meta: a conversa é simulada na interface, mas pelo mesmo caminho que a integração real usaria.

## Decisão

**Chatbot guiado**, com seis perguntas fixas (`app/domain/triage.py`): código do caminhão (TRK-0000), o que aconteceu (1 a 4), se há feridos, onde está (texto livre, aceita "não sei"), se o caminhão segue viagem e uma descrição curta (aceita "pular"). "cancelar" encerra a qualquer momento, e uma conversa parada há 30 min recomeça do início.

- **Guiado, e não interpretação de texto livre:** cada resposta é validada na hora. Se algo não fica claro, o bot repete a pergunta com as opções, e o incidente sempre chega completo e com categoria e criticidade corretas. Interpretar texto livre (regex ou LLM) erra calado justamente nos casos graves, custa mais e é difícil de testar. As perguntas cabem em menos de um minuto, e os botões de resposta rápida reduzem a digitação.
- **Criticidade por regras simples** (tabela no início de `triage.py`): feridos → `accident_with_victims` com criticidade alta; acidente → alta se o caminhão não segue, média se segue; problema mecânico, clima e bloqueio → média se não segue, baixa se segue. **A criticidade do bot mede o problema; carga e cliente entram na pontuação pela frota (ADR 0004), por isso o bot não pergunta sobre eles.**
- **Mesmo caminho da ingestão:** ao final, o incidente é criado pelo `create_incident` (`source=whatsapp`, transcrição em `raw_message`, localização pelo mesmo salvage e carga e cliente copiados da frota pelo `truck_code`). O telefone fica só na conversa; na fila aparece "Motorista do TRK-XXXX (via WhatsApp)".
- **Formato do webhook da WhatsApp Cloud API:** `POST /channels/whatsapp/webhook` recebe o objeto de mensagem da Cloud API (`from`, `id`, `type`, `text.body`) sem o envelope `entry[].changes[]`, e é protegido pela mesma `X-API-Key` da ingestão. Plugar a API real fica restrito a desembrulhar o envelope e validar a assinatura, sem mudar a máquina de estados. O simulador da interface usa uma rota equivalente, autenticada pelo analista e disponível só com `DEMO_MODE`.
- **Retorno ao motorista:** quando um incidente do WhatsApp é assumido ou encerrado, a mesma transação da mudança de status grava a mensagem de saída ("Ana Souza está cuidando do seu chamado…").

## Caminho para produção

1. **Somente a API oficial da Meta (WhatsApp Business Platform / Cloud API)**, com número verificado e templates aprovados para mensagens fora da janela de 24 h. **Nunca bibliotecas não oficiais** que automatizam o WhatsApp Web: elas violam os termos de uso, levam ao banimento do número e não oferecem garantia de entrega.
2. Validar a assinatura `X-Hub-Signature-256` do webhook e responder ao desafio de verificação (`hub.challenge`).
3. **Deduplicar pelo id da mensagem da Meta (`wamid`)**: o webhook pode reenviar a mesma mensagem, e sem deduplicação ela avançaria a conversa duas vezes.
4. Enviar as respostas pela Graph API (`/messages`), de forma assíncrona: hoje elas só ficam gravadas e voltam na resposta do webhook.
