# ADR 0004: Priorização por impacto no negócio

- **Status:** aceito (pesos em validação)
- **Data:** 2026-10-21

## Contexto

A primeira regra de prioridade somava criticidade, categoria e tempo de espera. Ela trata igual um pneu furado de um caminhão vazio e um pneu furado de uma carga refrigerada de um cliente estratégico, mas para a transportadora o custo desses dois incidentes é muito diferente: perda de carga, multa contratual, risco ambiental. A ideia, proposta pela Yasmim, é ordenar a fila pelo **impacto no negócio**.

## Decisão

- **Três notas de 0 a 100, numa média ponderada:**
  - **carga:** perigosa 100, perecível 90, alto valor 75, geral 40, vazio 10;
  - **problema:** tabela categoria × criticidade, de 20 a 85;
  - **companhia:** estratégico 100, prioritário 70, padrão 40.

  `base = (2 × carga + 1,5 × problema + 1 × companhia) / 4,5`, com resultado de 0 a 100.
- **Bônus de espera:** +1 ponto por minuto sem responsável, até +20. Ele congela no `acknowledged_at`, para que nada fique esquecido no fim da fila.
- **Vítimas são regra fixa, fora da média:** um incidente com vítimas ativo tem score 200 e fica acima de todos. Entre vítimas, as sem responsável vêm primeiro, depois a mais antiga. Vida não entra em ponderação com valor de carga.
- **Encerrados** não têm bônus e ficam no fim da fila.
- **Cópia da frota:** a carga e o cliente vêm da frota (`trucks`), copiados para o incidente no momento da criação, porque a carga muda a cada viagem. Caminhão desconhecido conta como carga geral e cliente padrão, com um aviso na tela.
- **Fonte única e transparência:**
  - as regras ficam em `app/domain/priority.py` e o cálculo é feito no Postgres;
  - o `GET /config` expõe os pesos e as tabelas;
  - cada incidente traz `priority_breakdown`, e o painel mostra a conta em linguagem simples ("Por que está nesta posição").

## Hipótese a validar

**Os pesos e as notas são uma hipótese, não um dado.** Eles foram escolhidos para refletir a ordem de grandeza do custo de cada tipo de carga e de cliente. Antes de uso real, precisam ser calibrados com a operação do cliente, olhando o histórico (quais incidentes custaram mais) e ouvindo os analistas (a ordem da fila "faz sentido"?). Como tudo está num só módulo, ajustar é trocar números e rodar os testes.

## Consequências

- Os analistas veem **por que** cada incidente está na sua posição, o que gera confiança na fila e facilita contestar um peso errado.
- **Risco:** um cliente estratégico com um problema leve pode passar à frente de um problema mais grave de um cliente padrão. Isso é intencional, mas precisa ser explicitado para a operação.
- **Risco de dados:** caminhões fora da frota caem no padrão neutro. A cobertura da frota precisa ser acompanhada.
