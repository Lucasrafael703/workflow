# Workspace de Demandas (fase 1A) — o que é, como ligar e o que ficou de fora

> **Objetivo desta rodada não é construir o Workspace completo. É provar que uma pessoa consegue operar Demandas em um único contexto, sem precisar reaprender a interface ou perder seu estado.**
> Esta é a **fase 1A**: shell único + Lista nova, atrás de uma feature flag. As fases 1C (Kanban), 1D (Calendário) e 1E (extrair abstrações) **não foram feitas**: dependem do resultado do teste com pessoas (ver `LPS_TESTE_USABILIDADE_DEMANDAS.md`).

## 1. Como ligar e desligar

A flag é `WORKSPACE_V2`, lida das variáveis de ambiente (no Render: *Environment* do serviço web). **Desligada por padrão.**

| Valor | Quem vê o Workspace |
|---|---|
| `off` (padrão; qualquer valor desconhecido também) | ninguém: a tela de Demandas de sempre |
| `allowlist` | só quem estiver em `WORKSPACE_V2_USERS` (e-mails ou nomes de usuário, separados por vírgula, sem diferenciar maiúsculas) |
| `on` | todas as pessoas logadas |

Exemplo para o teste com cinco pessoas: `WORKSPACE_V2=allowlist` e `WORKSPACE_V2_USERS=paulo@biasiengenharia.com.br,ana@...,...`.
**Rollback imediato:** voltar `WORKSPACE_V2` para `off` (ou tirar a pessoa da lista). Não exige novo deploy de código. As rotas são as mesmas (`/demandas/`, `/demandas/kanban/`, `/demandas/calendario/`); só o template muda. Quem está fora da lista continua exatamente na tela antiga, que **não foi alterada**.

## 2. O que a pessoa vê

Cabeçalho, abas e barra são **os mesmos nas três visões**; só a área de conteúdo muda.

- **Cabeçalho:** título, contador do universo filtrado ("6 demandas", igual nas três visões) e **Criar demanda**.
- **Abas:** **Lista · Kanban · Calendário** ("Quadro" ficou de fora: colide com o módulo Quadros). Cada link leva a querystring inteira.
- **Barra:** **Escopo** (Minhas · Do meu setor · Participando · Todas, esta só com `ATIVIDADE_VISUALIZAR_TODAS`) · **Mostrar** (Em aberto · Concluídas) · **Buscar** · **Filtros** · **Agrupar** · **Ordenar** · (**Personalizar**, no Kanban, para quem pode configurar). Agrupar e Ordenar são contextuais (Lista e Kanban); o Calendário não os mostra. Nada aparece desabilitado.
- **Uma regra de interação:** *controles simples aplicam ao escolher; o painel Filtros é um rascunho com um único **Aplicar filtros**; a busca aplica com Enter.* Fechar o painel sem aplicar (Esc ou clicar fora) **descarta** o rascunho.
- **Painel Filtros:** Setor, Responsável (várias pessoas), Etapa, Status, Cliente, Obra, Prazo. Etapa e Status só oferecem as opções do setor escolhido. Cliente e Obra usam o seletor com busca (3 letras; a Obra depende do Cliente; "Todos os clientes" limpa). Os filtros ativos aparecem como **chips** removíveis.
- **Escopo não muda sozinho:** escolher outra pessoa em "Minhas" **não** troca o escopo; aparece o aviso *"Você está vendo só 'Minhas'. Fulano pode não aparecer. [Ver Todas]"* (o botão só existe para quem pode ver Todas).
- **Valor inválido** (ex.: `?cliente=abc`) é ignorado com o aviso *"Ignoramos o filtro inválido: …"* (antes dava erro 500).
- **Lista:** 6 colunas — Demanda (com `código · cliente · obra` e o progresso das tarefas), Setor, Responsável, Prazo, Etapa, Status — mais "abrir". **Agrupar** faz seções. A edição inline é a de sempre. Clicar em *cliente · obra* abre a edição direto no passo 2.
- **Voltar da ficha:** a URL guarda tudo (visão, busca, filtros, escopo, agrupar, ordenar, mês) e a rolagem volta também.
- **Celular:** a Lista vira cartões empilhados e o painel de filtros é uma folha inferior (nunca abre sozinha).
- **Ordenar** põe as demandas sem prazo **sempre no fim** (SQLite e PostgreSQL ordenavam o vazio de formas opostas) e aplica o sentido.

## 3. Parâmetros da URL

Mantidos: `tab`, `q`, `setor`, `pessoa` (repetível), `estagio`, `condicao`, `cliente`, `obra`, `tag`, `prazo`, `status`, `urgencia`, `ordem`, `dir`, `next`. Os apelidos antigos (`responsavel`, `grupo`, `sector`, `sort`) continuam funcionando e **todo link novo escreve o nome canônico**. Novos: `agrupar` (`stage`, `condition`, `sector`, `owner`, `urgency`) e `mes`. `page`, `view` e `visao` nunca são levados adiante.
O link antigo `tab=concluidas` continua respondendo: a tela o lê como *Escopo "Minhas" + Mostrar "Concluídas"*.

## 4. Arquitetura (o mínimo)

Nenhuma abstração nova foi criada "porque estava previsto". O que existe:

| Arquivo | Papel |
|---|---|
| `core/feature_flags.py` | `workspace_v2_enabled(user)` (lê as settings a cada chamada) |
| `boards/work_views.py` | `DemandWorkBoardView` escolhe o template pela flag e recebe 3 ganchos pequenos (`arrange_activities`, `requested_group_by`, `workspace_context`); **a consulta é a de sempre** (`filtered_activities_queryset`, com o request real) |
| `boards/demand_workspace.py` | monta o contexto `ws` da barra: abas, escopo, mostrar, agrupar, ordenar, chips, painel, avisos; `query_with`/`hidden_fields` (nada se perde ao filtrar) |
| `activities/filtering.py` | `normalize_workspace_filters` só aceita ids numéricos (o resto vai para `invalid`) |
| `templates/workspace/*` | `demandas.html` + parciais da barra; `_lista*.html` é o renderizador novo; Kanban e Calendário **reusam o conteúdo antigo dentro do shell** |
| `static/js/workspace.js`, `static/css/workspace.css` | comportamento e estilo da barra |
| `static/js/person-picker.js` | `data-allow-empty` vale para qualquer seletor (Cliente/Obra) |

A tela antiga (`templates/boards/demand_work_board.html`) e tudo o que ela usa ficam **intactos**, para o rollback e para a comparação.

## 5. O que ficou de fora de propósito

- **Kanban e Calendário novos** (fases 1C/1D): hoje usam o conteúdo antigo (raias e lista de prazos) dentro do shell. A grade mensal do Calendário e "Mover para…" no Kanban dependem do teste com pessoas.
- **Personalizar da Lista** (colunas) e o **padrão salvo com governança** (permissão própria, pré-visualizar, confirmar, auditar, restaurar): fase 1E.
- **Extrair `WorkspaceState`/contratos genéricos**: só se houver pelo menos dois consumidores reais ou duplicação comprovada.
- **Remover o legado**: só depois de uso real, com novo aval.
- **`activities/views.py`**: não foi tocado (a outra sessão o estava editando). A extração da consulta independente de request (`activities/demand_query.py`) continua pendente e é pré-requisito de qualquer necessidade nova na consulta; por isso "Mostrar → Todas" (abertas + concluídas) ainda não existe.

## 6. Capacidades da tela antiga que o Workspace (e a tela atual) não têm

Já listadas, com a decisão de produto pendente, em `LPS_TRIAGEM_TESTES_DEMANDAS.md`: limite de coluna (WIP), seletor de status no cartão, menu de ações na linha da Lista (Concluir/Cancelar/Reabrir/Transferir só na ficha), paginação, grade do calendário. A 1B pode revelar quais fazem falta.

## 7. Testes

- `activities/test_workspace_demandas.py` (40): flag; mesmo shell nas três visões; estado preservado entre abas; escopo e mostrar; aviso de escopo; filtro inválido; chips; painel; Lista (6 colunas, contrato da edição inline, vazios); ordenação (vazio no fim); consultas constantes.
- `activities/test_demand_filters.py`: filtros, escopos e vazamento entre setores, rodados **duas vezes** (tela de sempre e Workspace) para provar que o recorte não muda de tela para tela.
- `core/test_feature_flags.py`: a flag.
- `tests/workspace.test.cjs` (18, jsdom): a regra de interação da barra, Esc, clicar fora, Etapa/Status por setor, foco, celular, rolagem.
- Chrome real (Playwright, cópia do banco, 41 verificações): o cenário *Setor + Responsável + Cliente* na Lista, no Kanban e no Calendário; rascunho do painel; Agrupar/Ordenar/Mostrar; aviso de escopo; Cliente/Obra; voltar da ficha; edição inline; arrastar no Kanban; quem está fora da lista; celular.
