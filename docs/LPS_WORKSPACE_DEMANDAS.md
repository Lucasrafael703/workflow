# Workspace de Demandas (fase 1A) — o que é, como ligar e o que ficou de fora

> **Objetivo desta rodada não é construir o Workspace completo. É provar que uma pessoa consegue operar Demandas em um único contexto, sem precisar reaprender a interface ou perder seu estado.**
> Esta é a **fase 1A**: shell único + Lista nova, atrás de uma feature flag. A **1C (Kanban)** foi feita depois, por pedido explícito (§8): o Kanban de Demandas passou a ser o mesmo de Quadros. As fases 1D (Calendário) e 1E (extrair abstrações) **não foram feitas**: dependem do resultado do teste com pessoas (ver `LPS_TESTE_USABILIDADE_DEMANDAS.md`).

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
| `templates/workspace/*` | `demandas.html` + parciais da barra; `_lista*.html` é o renderizador novo; `_kanban.html` usa o kit `templates/kanban/*` (§8); o Calendário **reusa o conteúdo antigo dentro do shell** |
| `static/js/workspace.js`, `static/css/workspace.css` | comportamento e estilo da barra |
| `static/js/person-picker.js` | `data-allow-empty` vale para qualquer seletor (Cliente/Obra) |

A tela antiga (`templates/boards/demand_work_board.html`) e tudo o que ela usa ficam **intactos**, para o rollback e para a comparação.

## 5. O que ficou de fora de propósito

- **Calendário novo** (fase 1D): hoje usa o conteúdo antigo (lista de prazos) dentro do shell. A grade mensal depende do teste com pessoas. (O Kanban novo existe: §8.)
- **Personalizar da Lista** (colunas) e o **padrão salvo com governança** (permissão própria, pré-visualizar, confirmar, auditar, restaurar): fase 1E.
- **Extrair `WorkspaceState`/contratos genéricos**: só se houver pelo menos dois consumidores reais ou duplicação comprovada.
- **Remover o legado**: só depois de uso real, com novo aval.
- **`activities/views.py`**: não foi tocado (a outra sessão o estava editando). A extração da consulta independente de request (`activities/demand_query.py`) continua pendente e é pré-requisito de qualquer necessidade nova na consulta; por isso "Mostrar → Todas" (abertas + concluídas) ainda não existe.

## 6. Capacidades da tela antiga que o Workspace (e a tela atual) não têm

Já listadas, com a decisão de produto pendente, em `LPS_TRIAGEM_TESTES_DEMANDAS.md`: limite de coluna (WIP), seletor de status no cartão, menu de ações na linha da Lista (Concluir/Cancelar/Reabrir/Transferir só na ficha), paginação, grade do calendário. A 1B pode revelar quais fazem falta. (O "Mover para…" no Kanban agora existe: §8.)

## 7. Testes

- `activities/test_workspace_demandas.py` (40): flag; mesmo shell nas três visões; estado preservado entre abas; escopo e mostrar; aviso de escopo; filtro inválido; chips; painel; Lista (6 colunas, contrato da edição inline, vazios); ordenação (vazio no fim); consultas constantes.
- `activities/test_demand_filters.py`: filtros, escopos e vazamento entre setores, rodados **duas vezes** (tela de sempre e Workspace) para provar que o recorte não muda de tela para tela.
- `core/test_feature_flags.py`: a flag.
- `tests/workspace.test.cjs` (18, jsdom): a regra de interação da barra, Esc, clicar fora, Etapa/Status por setor, foco, celular, rolagem.
- Chrome real (Playwright, cópia do banco, 41 verificações): o cenário *Setor + Responsável + Cliente* na Lista, no Kanban e no Calendário; rascunho do painel; Agrupar/Ordenar/Mostrar; aviso de escopo; Cliente/Obra; voltar da ficha; edição inline; arrastar no Kanban; quem está fora da lista; celular.
- Kanban (§8): `boards/test_kanban_kit.py` (19: marcação do kit **e paridade com o Kanban de Quadros**), `boards/test_demand_kanban.py` (41: regras do construtor, página, quem pode arrastar, fragmento e o **contrato cliente × servidor**), `tests/kanban-core.test.cjs` (27, jsdom) e `tests/demand-kanban.test.cjs` (19, jsdom).

## 8. Kanban de Demandas = o Kanban de Quadros

**O que o usuário pediu:** *"A tela do Kanban que fica em Quadros precisa ser o modelo para todos os outros Kanban."* Nesta rodada só **Demandas** (dentro do Workspace, atrás da mesma flag). **Quadros não foi alterado** (continua com a própria cópia da marcação e do JS); **Tarefas** é a rodada seguinte (3 raias derivadas, sem arrastar).

**O que a pessoa vê (igual a Quadros):** raias de 292px (84vw no celular) com cabeçalho sólido na cor da etapa/status e texto por contraste, pílula de contagem, corpo com rolagem própria, vazio tracejado ("Nenhuma demanda. Arraste uma demanda para cá."), cartão com borda esquerda de 4px na cor da raia e campos tipados (avatar + nome, selo do setor, pílulas de prioridade/etapa/status, prazo com selo **vencido**, progresso das tarefas). Atraso é **selo na data**, nunca fundo do cartão. O nome dos campos fica oculto (só para leitor de tela) até a visão pedir (`show_field_names`; no Workspace o padrão é oculto, o valor salvo vence).

**Mover:** arrastar (a raia de destino diz *"Solte aqui para mover para “X”"*) **ou** ⋯ → *Mover para…* (única forma em toque e no teclado; ↑ ↓ Home End Esc; o foco volta ao ⋯). O cartão vai na hora e volta ao lugar, com a mensagem do servidor, se ele recusar. Depois de gravar, as raias são redesenhadas pelo servidor **preservando rolagem lateral, rolagem de cada raia, rolagem da página e foco**. Mudar o **setor** pede confirmação (*etapa e status voltam ao padrão do setor novo*).

**Quem pode soltar onde (a tela adianta, o servidor decide):**

| Agrupar por | Raia em branco | Restrições |
|---|---|---|
| Etapa / Status | aceita (limpa o valor) | cada raia pertence a **um setor**: só recebe cartões desse setor; com setores misturados a raia mostra o setor sob o título; raia de etapa/status **desativado** aparece (tem cartão) mas não recebe |
| Setor | **fechada** (setor é obrigatório) | demanda em rascunho não muda de setor |
| Responsável | **fechada** | demanda em rascunho não muda de responsável |
| Prioridade | **fechada** | — |

Demanda **concluída ou cancelada** nunca se move. Cartão sem destino possível (ou sem permissão) não tem arrastar nem ⋯ — nada é "desabilitado só para parecer igual". A permissão da etapa aceita `ATIVIDADE_MOVER_ESTAGIO` **ou** `ATIVIDADE_DEFINIR_ETAPA` (como o serviço). O que a tela **não** adivinha: a permissão de editar no setor de **destino**, pendência aguardando aprovação e versão velha — o servidor recusa e a tela mostra a mensagem dele. `test_demand_kanban.ClientServerContractTests` percorre cada cartão × cada raia nos 5 agrupamentos e exige que "pode soltar" na tela ⇔ 200 no servidor (foi ele que pegou a raia "Sem setor" aberta por engano).

**Arquitetura (3 camadas pequenas):**

| Arquivo | Papel |
|---|---|
| `templates/kanban/_lanes.html`, `_lane.html`, `_card.html`, `_fields.html` | marcação neutra com **as mesmas classes e atributos** de `boards/_kanban_*.html`; o contrato de dados está no cabeçalho de `_lanes.html` |
| `static/css/kanban-core.css` | só o que Quadros não tem (sublinha do setor, progresso, links no lugar de botões) e três correções **só no Workspace** (`.ws`): o hover perdia a cor da borda, `cursor: grab` em cartão que não arrasta, ⋯ invisível em toque (agora 36px) |
| `static/js/kanban-core.js` | arrastar, menu, contagem, desfazer, redesenho, janela de confirmação — sem nada do domínio; `LPSKanbanCore.init(root, adapter)` (o nome `LPSKanban` já é do `kanban.js` antigo) |
| `static/js/demand-kanban.js` | adaptador: POST em `workboard-value` (`{value, updated_at}`, CSRF correto), mensagens por status (400 do servidor, 403, 404, 409, rede, sessão vencida) e recarga das raias |
| `boards/demand_kanban.py` | transforma as raias de `_group_items` e as células de `build_cells` em raias/cartões do kit; as regras de "pode soltar" |
| `boards/work_views.py` | `_group_items` registra `sector_id`/`is_active` nas raias de etapa/status (aditivo); `kanban_context`; `?fragmento=raias` devolve só `kanban/_lanes.html` (mesma autorização e mesmo recorte; só na flag e só no Kanban) |

`test_kanban_kit.ParityWithTheBoardsKanbanTests` compara o esqueleto do kit com o da página de Quadros: se alguém mudar a marcação de um sem o outro, o teste acusa (Quadros ainda tem a própria cópia).

**Limites conhecidos:**
- Sem paginação (igual à tela antiga): com ~320 demandas o fragmento pesa ~710 KB sem compressão e responde em ~0,65 s no servidor de desenvolvimento; a página inteira ficou ~58% maior que a antiga (cartões mais ricos), com tempo equivalente. Se crescer, o caminho é um teto por raia (como o das Tarefas).
- **Mover a etapa/status não atualiza `updated_at`** no servidor (`update_fields` sem ele), então o aviso de conflito (409) só aparece quando *outra edição* mexeu na demanda; dois movimentos concorrentes da mesma etapa valem "o último ganha". Pré-existente; não foi alterado.
- "+ Adicionar demanda" de cada raia abre o assistente de sempre **sem** levar a etapa da raia (o assistente não aceita etapa/status/setor por URL): rodada própria.
- O diálogo "Configurar cartões" de Quadros ainda não existe aqui; continua o painel *Personalizar* de sempre (e o Kanban de Quadros mantém a própria cópia da marcação e do JS até migrar).
