# Discovery: entendendo o problema antes de construir

Este documento registra como cheguei às decisões do Logos. Não houve pesquisa com usuários reais, então **tudo aqui é hipótese**, a ser validada com a operação do cliente.

## 1. O problema central

> A central de incidentes reage devagar demais porque a informação chega espalhada, sem prioridade e sem dono definido, e cada hora de atraso vira prejuízo.

No começo, pensei no problema como um gap de comunicação. Mas, mesmo com a comunicação perfeita, sobrariam dois problemas: **priorizar** (com 100 incidentes no mesmo lugar, qual atacar primeiro?) e **responsabilizar** (saber que o incidente existe não garante que alguém o assumiu). Por isso, prefiro chamar de **gap de coordenação operacional**: a informação não chega organizada, não é priorizada e não tem dono.

**Métrica de sucesso:** o tempo médio de reação (MTTA), ou seja, quanto tempo um incidente espera até alguém assumir. É o número que mostra se o Logos reduz as "horas para reagir" do enunciado. Ele aparece no topo da tela.

## 2. Cenário ilustrativo

*(Os valores são fictícios, só para tornar a dor concreta.)*

Um caminhão com carga perecível fura o pneu na BR-163. O motorista manda um áudio no grupo da frota, que se perde entre centenas de mensagens. Duas horas depois, dois analistas veem o recado ao mesmo tempo, sem saber um do outro, e cada um chama um guincho. A carga perde a janela de embarque, e a empresa paga a multa contratual, o risco da carga e um guincho a mais.

O Logos ataca as três falhas desse cenário: o relato chega estruturado, a fila mostra que esse pneu furado é urgente por causa da carga, e só um analista consegue assumir o incidente.

## 3. Quem usa

### Analista da central

Trabalha numa sala de controle, com vários monitores, sob pressão e com interrupções o tempo todo, inclusive de madrugada. Hoje alterna entre grupos de WhatsApp e planilhas.

> **Conclusão:** sob pressão e com dezenas de alertas ao mesmo tempo, ele precisa saber em segundos o que é mais urgente, quem já está cuidando de cada incidente e o que está sendo esquecido.

Implicações de design:

- Uma fila única, já ordenada pela prioridade, sem precisar ordenar nada na mão.
- Criticidade sempre com cor, ícone e rótulo; o vermelho reservado para o que realmente estourou o prazo.
- Incidentes com dono ficam em segundo plano; os esquecidos ganham o marcador "Sem dono há X min".
- Tela densa de propósito, no tema escuro por padrão, com navegação por teclado.

### Motorista

Está parado no acostamento, possivelmente sob estresse, com sinal instável e pouco tempo. Muitos são agregados ou terceirizados, com celular próprio.

> **Conclusão:** parado na estrada, com sinal instável e sem paciência para formulário, ele precisa avisar do problema pelo canal que já usa e ter a confirmação de que alguém da central recebeu.

Implicações de design:

- Ele continua no WhatsApp: nenhum app novo para instalar, nenhum login para lembrar.
- Perguntas curtas e fechadas, com respostas por número.
- Confirmação imediata com protocolo, e um aviso quando um analista assume o chamado.

## 4. As minhas ideias

### Prioridade pelo impacto no negócio

Ordenar só pela gravidade do problema não basta. Um pneu furado num caminhão com carga perecível de um cliente com multa contratual custa muito mais do que um raspão num caminhão com carga comum. Por isso, a pontuação considera três dimensões, com pesos:

- **carga** (peso 2): o que está sendo transportado;
- **problema** (peso 1,5): o tipo e a criticidade do incidente;
- **cliente** (peso 1): para quem é a entrega.

Com uma regra fora da conta: **acidente com vítimas vai sempre para o topo.** Vida humana não entra em média ponderada.

A carga e o cliente vêm da frota, pelo código do caminhão, então o motorista não precisa informar. Os pesos são uma hipótese a validar com a operação do cliente (ADR 0004).

### Chatbot de triagem no WhatsApp

Em vez de tentar interpretar mensagens soltas, um chatbot conduz a conversa com o motorista: código do caminhão, o que aconteceu, se há feridos, onde ele está, se consegue seguir viagem e uma descrição curta. A central recebe o incidente já organizado, e a criticidade sai por regra, e não por adivinhação. Quando um analista assume, o motorista recebe "Fulana está cuidando do seu chamado" (ADR 0005).

## 5. Hipóteses a validar

- Os pesos da pontuação (carga 2, problema 1,5, cliente 1) e as notas de cada tipo de carga e de cliente.
- Os prazos de SLA por criticidade (5, 15 e 30 minutos).
- Que os motoristas responderiam a uma triagem de seis perguntas em menos de um minuto.
- Que a empresa tem a carga e o cliente de cada viagem num sistema consultável (TMS).

## 6. O que ficou fora do MVP, e por quê

| Fora do MVP | Motivo |
|---|---|
| Integração real com a Meta | Exige verificação da empresa e número oficial; o avaliador não conseguiria testar. O formato do webhook já é o da Cloud API. |
| Áudio do motorista | Exige transcrição; é o próximo passo natural do chatbot. |
| App do motorista | O WhatsApp gera adoção desde o primeiro dia; um app exigiria treinamento e meses de adoção. |
| Tempo real com WebSocket/SSE | Polling de 5 s basta nessa escala e é mais robusto a quedas de conexão (ADR 0003). |
| Mapa | Útil, mas a fila priorizada responde primeiro à pergunta "o que atacar agora". |
| Perfis de acesso | No MVP, todos os analistas têm as mesmas permissões. |
