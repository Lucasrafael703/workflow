# 11 — Testes

> Onde estão os testes, como rodá-los e como escrever novos seguindo o padrão
> do projeto. Atualizado em 03/10/2026 (HEAD `add5acd`); as contagens abaixo vêm
> de `grep` de `def test_` (Python) e de `test(`/`it(` (JavaScript), sem executar
> a suíte.

---

## 1. Onde estão

Testes do Django ficam em cada app (`tests.py` e, conforme o app, vários
módulos `test_*.py`). Há **1667 testes Python** em 33 arquivos (contagem por `def test_`), dos
quais 58 estão ignorados com `@unittest.skip` (55 em `test_process_views.py`, 1 em `test_task_editor.py` e 2 em
`test_views.py`), além dos **378 testes JavaScript** descritos mais abaixo. Contagens "aprox." da tabela = `def test_` por arquivo:

| Arquivo | Testes (`def test_`) | Foco |
|---|---|---|
| `activities/tests.py` | 73 | Serviços: dono único, executores e tempo, sessões, devolução, fila, prazos, pendências, checklist, isolamento entre organizações |
| `activities/test_views.py` | 85 | Views: permissões por escopo, telas, Ajax, redirecionamentos (2 testes de lista/Kanban/Calendário de tarefas estão com `@unittest.skip`: foram substituídos pelo quadro de cada Demanda) |
| `acessos/tests.py` | 36 | Motor de autorização: escopos, perfis, concessões, teto de tenant |
| `core/tests.py` | 34 | Cadastros, busca de pessoas, formulário de usuário |
| `notifications/tests.py` | 42 | Destinatários, categorias, "ação necessária" |
| `processes/tests.py` | 22 | Molde: responsável padrão (tenant, ativo, fora do setor), versão publicada imutável, cópia na nova versão, editor de etapas |
| `activities/test_process_application.py` | 99 | Aplicação de processo: materialização (inputs, critérios, tarefas), validações que não gravam nada, dependências e liberação, inputs e critérios, trava de inputs obrigatórios, atomicidade, reaplicação, versões, isolamento entre organizações, finalização e o cenário de aceite completo |
| `activities/test_process_views.py` | 55 (**todos ignorados**) | Telas do processo — a classe-base `ProcessViewCase` tem `@unittest.skip` porque `processes` foi desativado e as rotas respondem 410: botão e popup "Aplicar processo", painel da ficha, progresso, atualização de inputs/critérios, finalização, tarefas que aguardam |
| `activities/test_reopen.py` | 44 | Reabrir tarefa e atividade concluídas: fila, histórico preservado, permissão por setor, motivo, tarefas seguintes, atividade concluída/cancelada, atomicidade, botões e popup |
| `activities/test_task_actions.py` | 88 | “Já realizei este trabalho”: período informado × conclusão agora, fila e sucessoras, auditoria, permissões (responsável/participante, sem exigir tempo manual), status, limites de data e justificativa, travas de dependência e de inputs do processo, atomicidade; botão, barra “Ações da tarefa” filtrada por permissão, popup (JSON), cartão de tempo cronometrado × informado |
| `activities/test_task_editor.py` | 78 | Editor da tarefa (uma transação: dados, marcadores, responsável, participantes e convites pendentes), Gerenciar dependência (ciclo, fila, tarefa já iniciada), motivo no tempo manual, origem do tempo na gestão, ações da tarefa em janela (JSON) e destaque do menu lateral em toda rota de tarefa (`test_action_page_highlights_tasks` está ignorado) |
| `activities/test_task_popups.py` | 48 | Janelas de tarefa (nova dentro da atividade, nova avulsa e editar): uma tela só, quatro seções numeradas na mesma ordem (Participantes antes de Instruções), sem etapas nem blocos recolhíveis, mesmas palavras e rótulos; data e hora do prazo em campos separados (data sem hora = 23:59, hora sem data é erro, valores preservados quando a página volta com erro); cartão da atividade (resumo, sem "Alterar" dentro da atividade e na edição, atividade de outra organização ignorada, resumo na busca sem uma consulta por atividade e na criação rápida); seletor desenhado uma só vez e com rótulo; salvar com `pk` de tarefa ≠ `pk` de atividade. Também confere o painel lateral (blocos recolhíveis, próprio) |
| `activities/test_activity_modal.py` | 78 | Nova/Editar demanda — a mesma janela em 4 etapas: estrutura, nomes e ajudas, obrigatórios, campos que saíram (upload, marcadores, solicitante interno, anotações), Cliente → Obra → Centro de custo (busca e validação), links e caminhos de arquivos, JSON da janela, edição igual à criação (mesmas etapas e botões), abrir direto numa etapa (`?passo=`: valores inválidos caem na 1ª, ignorado ao criar e com o formulário enviado) e **trocar o quadro ao editar** (`EditBoardSwapTests`: o passo mostra o quadro real e a contagem de tarefas, o diálogo só existe na edição, mesma escolha salva sem perguntar, outra escolha sem confirmação é erro no passo 3 e **não grava nada** (nem os outros campos; `0`/`false` não confirmam), com confirmação as tarefas somem e o quadro nasce no **mesmo pk**, campo do quadro ausente nunca troca, modelo inativo/de outra organização recusado, falha no quadro desfaz a edição inteira, demanda sem quadro cria sem confirmar, quem não gere o quadro vê o passo somente leitura e um pedido forjado não toca nele, outra organização 404) |
| `boards/test_demand_boards.py` | 21 | `DemandBoardTests` (7): Quadro da Demanda com coluna Pessoa e Status padrão, colaborador citado numa célula de Pessoa, contrato da linha em branco, só o controle padrão de adicionar item, itens do modelo copiados sem materializar tarefas operacionais, **rotas antigas de tarefa e processo respondem 410** (`/tarefas/<pk>/`, `/tarefas/nova-rapida/`, `/demandas/<pk>/tarefas/rapida/`, `/demandas/<pk>/processo/aplicar/`, `/processos/`) e Nova demanda com modelo da organização. `ReplaceDemandBoardTests` (14): trocar o quadro da Demanda (`BoardInstantiationService.replace_for_activity`): recusa sem confirmação sem mexer em nada, em branco → modelo e modelo → em branco no **mesmo `Board`** (itens, colunas, grupos e visões antigos somem; o novo nasce completo), cópia independente do modelo nos dois sentidos, mesma escolha não faz nada (mesmo com o modelo desativado depois), auditoria `BOARD_UPDATED` com `items_deleted`, demanda sem quadro, só quem gere a estrutura troca, modelo inativo/de fora recusado sem apagar, **atomicidade** (falha no meio da recriação mantém o quadro antigo), outros quadros intactos, contagem só de tarefas ativas, escolha atual vinda do quadro real |
| `boards/tests.py` | 100 | Quadros, serviços: posição decimal (ponto médio, rebalanceamento, vizinhos que já não são adjacentes), quadro/grupo/coluna (tipos ativos e reservados, nome repetido, largura 40→96 e 900→640, `settings` por tipo), conversão de tipo (segura, com texto → número, destrutiva, confirmação), etiquetas (duplicada, padrão única, excluir limpa células), itens (etiqueta padrão, mover, excluir), células de cada tipo (formato brasileiro, arredondamento, limites, fim de semana, pessoa de outra organização, etiqueta de outra coluna, obrigatória, valor antigo preservado em recusa), auditoria só quando muda, ordenação no banco por tipo, busca, filtro por pessoa, sem N+1, modelo Orçamentos, permissão e isolamento entre organizações |
| `boards/test_kanban.py` | 63 | Visualização Kanban: Kanban padrão em todo quadro e no modelo, migração de dados, validação da configuração (agrupar só por Status/Lista **do quadro**, soma só de Número/Moeda, campos do cartão, ordenação, chaves desconhecidas), coluna agrupadora e campos padrão do cartão, raias (ordem das etiquetas, sem duplicar nem perder item, raia "Em branco" nos três modos, raias vazias, soma formatada, filtros e ordem dentro da raia, renomear/recolorir etiqueta reflete), `ViewService` (permissão, nome único, auditoria por chave, valores inválidos preservam o antigo), página (acesso, 404 entre organizações e de visualização excluída, abas na tabela e no Kanban, controles por permissão, campos/ordem do cartão, soma, XSS, **número de consultas igual com 3 ou 15 cartões**), API (contratos, 403, 404 em todo endpoint, fragmento das raias) e criar o cartão na raia (valor inicial, tudo ou nada) |
| `boards/test_task_center.py` | 35 | Painel Tarefas e prévia do Quadro na ficha: escopo por responsável (e item sem pessoa fora), coluna de Pessoa inativa, Demanda cancelada/rascunho fora e bloqueada dentro, isolamento entre organizações, estado derivado da etiqueta, atrasada/vence hoje pela data local (sem inventar prazo), cards, menções (só não lidas da pessoa), busca/filtros/ordem, filtro de pessoa **autorizado no backend**, Kanban, semana do calendário, `?demanda=` redireciona, "Abrir quadro" = Quadro da Demanda (nunca o modelo), **consultas constantes** com 3 ou 15 itens, selo do menu, "+ Adicionar" (demandas oferecidas, corpo do endpoint, recusa pelo serviço), prévia (≤5 linhas, abertas por prazo, sem misturar quadros, menções da Demanda, Demanda sem quadro, progresso e "pronta para concluir" vindos do quadro) |
| `activities/test_inline_edit.py` | 104 | Edição inline da lista de Demandas (Entrega 1: título, responsável, prazo; Entrega 2: cliente/obra, setor, estágio, status): funções puras do prazo (23:59 como "sem hora", exibição, fuso, datas inválidas, atraso), **invariantes que ficam no Service** (título normalizado/vazio/>200 recusado também fora do inline; dono ativo da mesma organização; `ActivityPermissionError` é subclasse de `ActivityError`), contrato JSON e códigos (200/400/403/404, sem `messages.*`, CSRF, só POST, rascunho 404), auditoria, `OwnerChangeLog` e notificação, valor igual = no-op, demanda concluída/cancelada travada, `field=status` recusado, flags por linha (quem edita, quem só troca título, leitor), página (marcadores só para quem pode, leitor vê o link de sempre), **consultas constantes com 3 ou 15 linhas** e uma só consulta de autorização para a lista; **Entrega 2**: invariantes do Service (autorização no setor de destino, destino ativo, atomicidade com falha no meio, cliente × obra, estado terminal em estágio/status também no Kanban), setor (trocar, criar e aplicar, nome repetido/cor fora da paleta, nada fica criado se a troca falha), listas de opções por campo, estágio/status (limpar, outro setor/inativo/outro domínio recusados, ação legada), criar/editar opções (permissão **no setor da demanda**), flags e marcadores por perfil, a linha “Vencida há N dias” e consultas constantes |
| `boards/test_calendar.py` | 101 | Visualização Calendário: validação da configuração (coluna de Data só do quadro, escala só Mês, cor por Status/Lista/grupo/nenhuma, campos do cartão, chaves do Kanban descartadas), coluna de Data/cor/campos padrão, mês e grade (segunda a domingo, 5 semanas em outubro/2026, ano bissexto), cada item no seu dia **uma vez**, dias de outro mês, **só o intervalo da grade é carregado**, sem data (contador e lista, limpar a data não exclui), dia inteiro × hora (sem hora inventada, fuso local, coluna sem horário), "+ N mais", fins de semana ocultos (nada some do banco, aviso, dias bloqueados), concluídos (filtro visual, só o Status decide) e atrasados (só em coluna de prazo, independente do mês), cor (renomear/recolorir reflete, nunca só a cor), campos do cartão, XSS, busca e pessoa nos links de mês, `ViewService` (congela Data e cor, exige coluna de Data, dois calendários com Datas diferentes sobre os mesmos itens, auditoria por chave, permissão, excluir a visão não apaga itens), página (acesso, abas, controles por permissão, metadados do JS, **consultas iguais com 1 ou 13 cartões**), API (fragmento, 404 entre tipos e organizações, criar no dia **tudo ou nada**, mover só a data com auditoria da data anterior e da nova, manter a hora, recusas, gaveta com histórico só do item) |
| `boards/test_views.py` | 71 | Quadros, telas e API: login, sem organização, 403, 404 entre organizações **em cada endpoint de escrita** (e nada muda), controles só para quem pode, conteúdo da tabela (valores, "vencido", contraste da etiqueta, XSS em nome/texto/título), `?sort`/`?q`/`?pessoa`, **número de consultas igual com 3 ou 15 itens**, contratos JSON (400/403/409, JSON inválido, CSRF, só POST), menu e as 36 rotas mapeadas |
| `boards/test_domain_workboards.py` | 19 | Superfícies de domínio sobre o motor de Quadros (`/demandas/`, `/demandas/kanban/`, `/demandas/calendario/`): quadros padrão idempotentes, título inline pelo serviço com auditoria, prioridade da tarefa, rotas principais, Kanban de Demandas com estágios vazios, configuração do Kanban (raias vazias, nomes dos campos), arrastar pelo serviço de Etapa ou de Status, agrupar por Status, agrupamento inválido e outra organização recusados; `DemandFilterToolbarTests`: barra de filtros na mesma ordem sem controles aposentados, atalhos de prazo exclusivos, setor delimita etapas e status em todas as visões, várias pessoas e "sem responsável" como OU, URLs antigas de pessoa compatíveis, limpar no calendário mantém o mês |
| `boards/test_centralization_migration.py` | 1 | Migração que desliga `Task` de `BoardItem` (centralização das tarefas em quadros por Demanda): preserva os dados (`TransactionTestCase`, parte de `audit 0011`) |
| `activities/test_activity_workspace.py` | 36 | Editor de demanda, anexos e navegação: criar e editar usam o mesmo editor, publicação numa só submissão, rascunho vazio e retomada, responsável obrigatório preserva o formulário |
| `intake/tests.py` | 75 | Caixa de Entrada, serviços: ações no catálogo e perfis sugeridos, endereço do item para o motor de autorização (setor/obra sugeridos), política de estados, registrar (validações, duplicata em 7 dias, `external_id` único por origem, escopo de setor), corrigir sugestões (só em nova, outra organização, obra × cliente, não perder o acesso), ignorar/restaurar, **converter** (atividade publicada, solicitante interno × externo, descrição com origem e link, HTML escapado, **@menção neutralizada**, rollback total, segunda conversão, `demanda.criar` ainda exigido, escopo de setor), visibilidade e contador |
| `intake/test_textparse.py` | 36 | Parser sem banco: normalização, assunto, domínio, primeira linha útil e prazo em português (dia da semana, "amanhã", `dia 15`, `15/10`, `15 de outubro`, hora, pista de prazo, datas inválidas e passadas) |
| `intake/test_suggestions.py` | 27 | Sugestões: cliente por nome e por domínio (desempates, provedores gratuitos), obra limitada ao cliente, setor pelo assunto e pelo histórico, prazo, pontuação e faixas de confiança |
| `intake/test_views.py` | 62 | Acesso (login, sem organização, 403, 404 entre organizações), lista (abas, busca, paginação, escopo de setor, XSS, **número de consultas não cresce com os cartões**), registrar, detalhe, editar, criar demanda, ignorar, restaurar (contratos JSON, aviso que acompanha a navegação) e menu (item, contador, mapa `_NAV_BY_URL_NAME`) |
| `intake/test_inativa.py` | 6 | Caixa de Entrada **desligada** (`INTAKE_ENABLED=False`, o padrão): toda rota dá 404 mesmo para quem tem todas as permissões (página e Ajax, GET e POST), nada é gravado, o menu não mostra "Entrada" nem conta itens (nem consulta `new_count`), e ligar a chave traz tudo de volta. Os demais testes do app rodam com a chave ligada (`IntakeTestCase`) |
| `acessos/test_chaves_demanda.py` | 5 | Migração `acessos/0003_chaves_demanda` ("Atividade" → "Demanda"): o catálogo usa as chaves novas, a renomeação mantém os mesmos registros e **todas as concessões** (diretas e por perfil), reverte, é idempotente e funde quando `seed_acoes` novo rodou antes da migração |
| `notifications/test_demanda_mensagens.py` | 6 | Migração `notifications/0008`: troca só o texto fixo que o sistema gravou (títulos conhecidos e trechos ancorados da mensagem), nunca o título digitado, o motivo, comentários ou menções; idempotente |
| `activities/test_demanda_endereco_e_codigo.py` | 27 | Endereço e código da Demanda: as páginas em `/demandas/…`; **toda** rota com o endereço antigo `/atividades/…` redirecionando (301; 308 em POST; consulta mantida; sem login; nunca leva para fora do site); anexos (`/atividade-arquivos/` → `/demanda-arquivos/`, pasta `DEM-` ou `ATV-`, caminho que sobe de pasta); o código `DEM-AAAA-NNNNN` e a busca com o prefixo antigo (lista e seletor de tarefa); migração `activities/0020` (códigos, pastas e nomes dos anexos; texto digitado intacto; idempotente; reversível; código já ocupado; arquivo ausente ou que não pôde ser movido) |
| `activities/test_kanban.py` | 87 | Quadro Kanban de demandas e de tarefas: setor obrigatório e lembrado, setor que a pessoa não pode abrir ignorado, visibilidade (participante do setor × quem só atua), colunas só do setor, "Sem etapa" só quando preciso, limite que só avisa, filtros e ordenação (prazo vazio por último), valores inválidos ignorados, consultas que **não crescem com os cartões**, arrastar/seletor gravam **só** etapa ou condição (status, fila e cronômetro intactos), recusas (outro setor, inativa, sem ação, outra organização, tipo errado), criar na coluna, limite e novas opções só para quem gere, endpoint do cartão, gaveta da demanda e da tarefa, janela de nova tarefa já com setor e etapa |
| `intake/test_codigo_demanda.py` | 3 | Migração `intake/0003`: só a nota que é exatamente um código (evento "Virou demanda") troca `ATV-` por `DEM-`; texto em volta e outros eventos ficam; idempotente e reversível |
| `accounts`, `audit` | 0 | `tests.py` vazio |

Base compartilhada dos quadros: `boards/testing.py` (`BoardTestCase`, montado uma vez por classe em `setUpTestData`: a Biasi
com o quadro Orçamentos de dois grupos, uma coluna de cada tipo ativo, três itens e pessoas com cada nível de acesso: tudo,
só preenche itens, só vê, sem acesso e de outra organização; `set_cell(item, "texto", valor)`).

`tests/boards-kanban.test.cjs` (29 testes, jsdom) cobre o modo Kanban do `boards.js` sobre o HTML real de `board_kanban.html` (raias montadas por `boards.kanban.build_lanes`): arrastar cartão (otimista, contagens, volta se recusado, raia em branco, mesma raia não envia nada), menu do cartão, renomear título, editar campo no cartão (inclusive o campo que **não é `<td>`**) e redistribuir quando muda o agrupador, criar na raia com valor inicial, renomear/recolorir/editar etiquetas pela raia, agrupar/ordenar pela barra, janela de configuração com autosave e pré-visualização, abas (criar, renomear, excluir) e perfil só de leitura.

`tests/activity-inline-edit.test.cjs` (57 testes, jsdom) cobre `static/js/activity-inline-edit.js` e `activity-inline-options.js` sobre o HTML real de `boards/demand_work_board.html` (bloco `content` renderizado com objetos em memória): marcadores só onde a linha permite, nada acrescentado em repouso (sem seta, lápis ou botão), título (Enter/blur/Esc, vazio nunca salva, CSRF, otimista, recusa e queda de conexão restauram, texto como texto e não HTML), **volta ao último valor confirmado** e não ao HTML inicial, **uma requisição por célula**, responsável (lista, busca com debounce, resposta velha ignorada, mesma pessoa não envia), prazo (data+hora opcional, Limpar, atraso vindo do servidor, recusa restaura), pop-over único, clique fora/Esc e foco de volta, acompanha scroll/resize e teclado. **Entrega 2**: link de Cliente / Obra (só onde a linha permite, sem `data-activity-navigate`), setor (lista colorida, atual marcado, trocar com Estágio/Status travados e redesenhados, recusa volta ao confirmado, busca sem acento, setas/Esc, criar e aplicar com nome + 36 cores, erros no próprio pop-over), estágio e status (escolher, limpar, criar e aplicar, editar nome/cor com propagação a outras linhas, link de gerir só do próprio site) e a linha “Vencida há N dias” (vinda do servidor e atualizada pelo prazo).

`tests/boards-calendar.test.cjs` (59 testes, jsdom) cobre o modo Calendário do `boards.js` sobre o HTML real de `board_calendar.html` (grade montada por `boards.calendar_view.build_month`, sem banco): funções puras da hora (`parseTimeInput` etc.), grade e cartões (cor, texto da etiqueta, "Atrasada", "+ N mais", dias bloqueados), controles por permissão, **criar no dia** (data preenchida, tudo em um pedido, título e hora validados antes de enviar, cancelar não manda nada, recusa mantém a janela, busca de pessoa, grupo), **arrastar entre dias** (otimista, só a data, mantém a hora, volta e avisa se recusado, dia bloqueado e mesmo dia não enviam, dia cheio recontado, leitor não arrasta), **navegar** (sem recarregar, só o novo mês, busca e pessoa mantidas, ctrl-clique é do navegador, falha mantém o mês), listas em pop-over, gaveta (abrir, fechar, Escape em duas etapas, editar campo, renomear, excluir com confirmação, leitor só lê), pop-over de data e hora (rápidos, digitado, limpar horário/data, ativar horário), janela de configuração com autosave e recusa, aviso de fim de semana oculto, quadro sem coluna de Data e a aba "+" criando um Calendário.

`tests/boards.test.cjs` (61 testes, jsdom) cobre `boards.js` sobre o **HTML dos templates reais** (`board_detail.html`
renderizado com objetos em memória, sem banco; mesmo método do `activity-steps.test.cjs`) e um `fetch` falso: o que a tela
manda (URL, corpo, cabeçalhos, CSRF) e o que faz com a resposta, otimismo com reversão, mensagens de erro, permissões visuais,
arraste de item e de coluna (inclusive desfazer quando o servidor recusa), teclado, janelas e pop-overs, a **linha de títulos de cada grupo** (criar, renomear, mover e excluir coluna atuam em todos os grupos; o campo de renomear abre no grupo onde se clicou) e a camada da paleta de cores (z-index do pop-over acima da janela, lido do CSS). Roda como os demais
(`node --test tests/boards.test.cjs`, com `NODE_PATH` apontando para o jsdom).

Base compartilhada da Caixa de Entrada: `intake/testing.py` (`IntakeTestCase`, com a Biasi, os
setores Comercial e Compras, o cliente Convivy com a obra Residencial Aurora e pessoas com cada
nível de acesso: triagem geral, só registra, gestor de um setor, sem acesso e de outra
organização; `new_item(**overrides)` cria a solicitação direto no banco).

Base compartilhada dos testes de processo: `activities/testing.py`
(`make_user(username, organization, actions=())` e `ProcessTestCase`, com o cenário Orçamento v3: três setores/pessoas, três etapas
em sequência, três inputs e quatro critérios) e `processes/testing.py`
(`build_process`, que monta um molde direto pelo ORM, e `publish_version(version, user)`, que publica uma versão). Os testes que ainda usam
`ProcessTestCase` (`test_reopen.py`, `test_task_actions.py`, `test_process_application.py`) exercitam serviços; os que
chamam rotas de tarefa, fila ou processo pelo `client` esbarram nas respostas 410 desde 02/10/2026 e precisam ser revistos
(não foram executados nesta revisão: o Django não estava instalado no ambiente).

Além disso, `tests/checklist.test.cjs` testa o componente JavaScript do
checklist, `tests/process-apply.test.cjs`, o assistente de 4 passos do popup
"Aplicar processo", `tests/retroactive-work.test.cjs`, o popup "Já realizei este
trabalho" (aviso de dia anterior e comentário só quando necessário), e
`tests/activity-steps.test.cjs` (51 testes), a janela de demanda em 4 etapas — criar e editar (inclui o diálogo de troca de quadro: só abre ao editar com escolha diferente, Confirmar reenvia com `confirm_board_replace=1`, Cancelar/Esc/clique fora voltam ao passo 3 sem enviar, foco preso, texto como texto — e a integração
com o `modal.js` real) (seção 4). `tests/task-modal.test.cjs` (8 testes) cobre o cartão da atividade da janela de tarefa (trocar o seletor
pelo cartão, "Alterar", seleção limpa, início repetido e janela injetada depois), inclusive com o
`person-picker.js` real. `tests/kanban.test.cjs` (41 testes) cobre `kanban.js` e `workflow-picker.js` num fixture que espelha os atributos dos templates: arrastar (grava só a etapa, volta se o servidor recusa, "Sem etapa" nunca é destino), contadores e limite, criar na coluna, limite, gaveta e releitura do cartão ao fechar, menus, ações, filtros e o seletor (opções do setor, escolher, limpar condição, criar opção, erros). Uma exceção dentro de um tratador de evento falha o teste. `tests/intake.test.cjs` (12 testes) cobre `static/js/intake.js`
com o `LPSAjax` real: abrir em janela, teclas modificadoras, queda para a página completa,
remover/trocar cartão, redirecionar, recarregar e o envio de "Restaurar" (CSRF, envio duplo e
erros).

### Testes JavaScript (`tests/*.test.cjs`)

Executados com `node --test` (Node 18+) e jsdom 26.1.0: **378 testes em 18 arquivos**. Os marcados com `*` chamam o Python do projeto para renderizar o template Django real.

| Arquivo | Testes | Cobre |
|---|---|---|
| `tests/activity-inline-edit.test.cjs`* | 57 | `activity-inline-edit.js` e `activity-inline-options.js` (lista de Demandas) |
| `tests/activity-steps.test.cjs`* | 51 | `activity-steps.js`: janela de demanda em 4 etapas e diálogo de troca de quadro |
| `tests/activity-workspace.test.cjs` | 8 | `activity-workspace.js` (`LPSAjax`, `data-activity-action`) |
| `tests/boards-calendar.test.cjs`* | 59 | modo Calendário do `boards.js` |
| `tests/boards-kanban.test.cjs`* | 29 | modo Kanban do `boards.js` |
| `tests/boards.test.cjs`* | 61 | tabela de Quadros do `boards.js` |
| `tests/checklist.test.cjs`* | 10 | `checklist.js` (template `_task_checklist.html`; nenhuma tela ativa carrega o script hoje) |
| `tests/intake.test.cjs` | 12 | `intake.js` |
| `tests/kanban.test.cjs` | 41 | `kanban.js` e `workflow-picker.js` |
| `tests/modal.test.cjs` | 5 | `modal.js` |
| `tests/notifications.test.cjs` | 1 | `notifications.js` |
| `tests/process-apply.test.cjs`* | 14 | `process-apply.js` (fluxo desativado) |
| `tests/retroactive-work.test.cjs`* | 8 | `retroactive-work.js` |
| `tests/sector-picker.test.cjs` | 1 | seletor de setor (`person-picker.js`, `data-picker-kind="sector"`) |
| `tests/task-center.test.cjs` | 7 | `task-center.js` (tela Tarefas) |
| `tests/task-modal.test.cjs` | 8 | `task-modal.js` com o `person-picker.js` real |
| `tests/work-board.test.cjs` | 2 | `work-board.js` (visualizações de domínio) |
| `tests/workspace-filters.test.cjs` | 4 | `workspace-filters.js` (barra de filtros compartilhada) |

---

## 2. Rodando

```powershell
python manage.py test                                      # tudo
python manage.py test activities                           # um app
python manage.py test activities.test_views                # um módulo
python manage.py test activities.test_views.TaskChecklistViewTests   # uma classe
python manage.py test core.tests.UserFormAjaxTests.test_non_ajax_request_still_redirects  # um teste
```

Testes JavaScript (Node 18+; o jsdom está em `devDependencies` do `package.json`):

```powershell
npm install                          # uma vez: instala o jsdom em node_modules/
npm run test:js                      # = node --test tests/*.test.cjs
node --test tests/boards.test.cjs    # um arquivo
```

Rode a partir da raiz (`workflow`). Os testes marcados com `*` na tabela chamam o Python do `.venv`
(ou o da variável `PYTHON`) para renderizar o template real; os demais montam o HTML à mão. O `package.json`
existe só para os testes — o deploy no Render continua sem etapa Node.

Opções úteis: `-v 2` (nome de cada teste), `--parallel` (mais rápido),
`--keepdb` (reaproveita o banco de teste entre execuções).

Os testes usam `config.settings.dev` (via `manage.py`) com um banco SQLite em
memória criado e destruído a cada execução — o seu `db.sqlite3` não é tocado.
A suíte completa leva alguns minutos, porque todas as migrations rodam no
início. Grande parte do resto é o hash de senha: cada `create_user(..., password=...)`
usa PBKDF2 (centenas de milissegundos). Para iterar mais rápido **localmente**,
rode com um módulo de settings que herda de `config.settings.dev` e troca só
`PASSWORD_HASHERS` por `["django.contrib.auth.hashers.MD5PasswordHasher"]`
(`--settings=meu_settings_de_teste`); testes novos que não precisam de senha podem
criar o usuário sem ela (`create_user(username, email=...)`) e usar
`client.force_login`. O `--parallel` não funciona no Windows deste projeto (erro
`cannot pickle 'traceback' object` ao reportar uma falha).

### Formulário de usuário

Os testes de criação devem enviar organização, `password1` e `password2`,
assim como a interface atual. Os testes do editor de demanda estão também em
`activities/test_activity_workspace.py` (editor, anexos e navegação).

---

## 3. Escrevendo testes

O padrão é criar organização, usuários e permissões explicitamente no
`setUp`:

```python
from django.contrib.auth import get_user_model
from django.test import TestCase

from acessos import catalog
from acessos.testing import grant_action
from core.models import Organization, Sector

User = get_user_model()


class MinhaFeatureTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Biasi")
        self.sector = Sector.objects.create(organization=self.org, name="Compras")
        self.user = User.objects.create_user("ana", email="ana@example.com", password="x")
        self.user.profile.organization = self.org
        self.user.profile.save(update_fields=["organization"])
        grant_action(self.user, catalog.TAREFA_CRIAR, organization=self.org)
```

Helpers de `acessos/testing.py`:

| Helper | Uso |
|---|---|
| `ensure_catalog()` | Grava o catálogo de ações no banco de teste |
| `grant_action(user, key, organization=None, scope=None, sector=None, relation=None)` | Concessão direta; escopo da organização por padrão, ou de setor/relação |
| `grant_actions(user, keys, **kwargs)` | Várias de uma vez |
| `make_profile(organization, name, keys)` | Cria um perfil de acesso com as ações |
| `assign_profile(user, profile, sector=None, relation=None)` | Atribui o perfil com escopo |

Outras bases por app: `activities/testing.py` (`make_user`, `ProcessTestCase`), `boards/testing.py` (`BoardTestCase`), `intake/testing.py` (`IntakeTestCase`) e `processes/testing.py` (`build_process`, `publish_version`).

Dicas:

- Para testar **negação**, crie o usuário sem conceder a ação e confira que o
  serviço levanta `ActivityError` (ou a view responde 403).
- Para testar **isolamento**, crie uma segunda organização e confira que o
  recurso dela não aparece / dá 404.
- Para views com login: `self.client.force_login(self.user)`.
- Views Ajax: envie `HTTP_X_REQUESTED_WITH="XMLHttpRequest"`.
- Um usuário sem organização (`User.objects.create_user(...)` sem ajustar o
  perfil) serve para testar o redirecionamento do `OrganizationRequiredMixin`.

---

## 4. Teste JavaScript do checklist

`tests/checklist.test.cjs` renderiza o template real
`activities/_task_checklist.html` (chamando o Python do `.venv`, ou o da
variável `PYTHON`) e executa `static/js/checklist.js` no jsdom. Com o jsdom
instalado pelo `npm install` (seção 2), basta, a partir da raiz do repositório:

```powershell
node --test tests/checklist.test.cjs
```

Sem `npm install`, ainda é possível instalar o jsdom numa pasta temporária e
apontar o `NODE_PATH` para ela (método descrito em `tests/README.md`). O jsdom não
valida layout nem o envio por Enter do navegador — confira também manualmente
(ver `tests/README.md`). Observação: `checklist.js` e o parcial `_task_checklist.html`
continuam no repositório, mas nenhuma tela ativa os carrega desde que as tarefas passaram a
viver nos quadros por Demanda; o teste cobre o componente isolado.
