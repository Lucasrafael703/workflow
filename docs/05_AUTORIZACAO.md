# 05 — Autorização

> Como a LPS decide se uma pessoa pode fazer algo. O modelo é
> **SUJEITO + AÇÃO + ESCOPO + ORIGEM**: toda permissão é uma ação, vale em um
> escopo e tem uma origem explicável (um perfil ou uma concessão direta). Nega
> por padrão e não existe "negar explícito". Regras de produto em
> `Regras/05_USUARIOS_SETORES_E_AUTORIZACOES.md`; implementação em
> `acessos/`. Atualizado em 03/10/2026 (código no commit `add5acd`): na
> interface "Atividade" virou **Demanda** (as constantes continuam
> `ATIVIDADE_*`, as chaves gravadas são `demanda.*`), e fila, processos e as
> telas de tarefa foram desativados em favor dos **quadros** (seções 4.4 e 8).

---

## 1. Peças

| Peça | Onde | O que é |
|---|---|---|
| Catálogo de ações | `acessos/catalog.py` | Constantes (`catalog.TAREFA_INICIAR = "tarefa.iniciar"`) e a lista `GROUPS`. **Única fonte da verdade**: o código referencia as constantes; `seed_acoes` grava no banco. |
| `Action` / `ActionGroup` | `acessos/models.py` | O catálogo materializado. Uma ação só existe se a aplicação tiver comportamento correspondente (doc 05 §14). |
| Perfil de acesso (`acessos.Profile`) | por organização | Conjunto reutilizável de ações (`ProfileAction`). |
| `Scope` | por organização | "Onde vale": a organização toda, uma empresa, um setor, uma obra, um centro de custo ou uma relação. |
| `UserProfile` | por pessoa | Atribuição: pessoa + perfil + escopo. |
| `UserAction` | por pessoa | Concessão direta: pessoa + ação + escopo. Exceção pontual, não a forma padrão (doc 05 §27). |

Participar de um setor (`accounts.UserSector`), mesmo como GESTOR, **não
concede nada** por si só. Só alimenta os escopos relacionais `MEUS_SETORES` e
`SETORES_GERENCIADOS` e os destinatários de notificações.

---

## 2. Escopos

| `Scope.type` | Cobre o recurso quando... |
|---|---|
| `ORGANIZACAO` | sempre (dentro da organização) |
| `EMPRESA` | `recurso.company_id == scope.company_id` |
| `SETOR` | `recurso.sector_id == scope.sector_id` (para tarefa, é o setor **da tarefa**) |
| `OBRA` | `recurso.site_id == scope.site_id` |
| `CENTRO_CUSTO` | `recurso.cost_center_id == scope.cost_center_id` |
| `RELACIONAL` + `MINHAS_ATIVIDADES` | a pessoa é dona da atividade |
| `RELACIONAL` + `MINHAS_TAREFAS` | a pessoa é participante ativa (`TaskExecutor`) da tarefa |
| `RELACIONAL` + `MEUS_SETORES` | o setor do recurso é um dos setores da pessoa |
| `RELACIONAL` + `SETORES_GERENCIADOS` | o setor do recurso é um que a pessoa gerencia (GESTOR) |

> `MINHAS_TAREFAS` olha só os **participantes** (`TaskExecutor`); o
> `responsavel` da tarefa não entra nesse conjunto. Desde a centralização em
> quadros (02/10/2026) a `Task` operacional é histórico: quem trabalha numa
> tarefa é a pessoa na célula **Pessoa** do item do quadro da Demanda, e isso
> **não** passa por escopo (ver `DemandBoardAccess`, seção 4.3). Na prática
> `MINHAS_TAREFAS` ficou sem efeito sobre o trabalho novo.

O "endereço" de um recurso é montado por `ResourceContext.of(recurso)` em
`acessos/services.py`:

| Recurso | Endereço |
|---|---|
| `Activity` | org, empresa, setor designado, obra, centro de custo, dono |
| `Task` | setor da tarefa + resto da atividade + participantes ativos |
| `QueueEntry` | setor da fila + dados da atividade + participantes (legado: a fila foi desativada) |
| `DeadlineProposal`, `DeadlineConflict` | o da tarefa (legado: prazos de tarefa desativados) |
| `Sector`, `Company`, `Site`, `CostCenter` | org + o próprio id |
| `IntakeItem` (Caixa de Entrada) | org + **setor sugerido** + obra sugerida. Sem setor sugerido só casam escopos de organização |
| `ActivityStage`, `TaskStage`, `WorkflowStatus` (etapas e status do setor) | org + setor do cadastro |
| `Board`, `BoardGroup`, `BoardColumn`, `BoardColumnOption`, `BoardItem`, `BoardCell`, `BoardView` e os modelos de quadro de domínio (`DomainBoard`, `DomainBoardField`, `DomainBoardChoice`, `DomainBoardView`, `DomainBoardViewColumn`, `DomainBoardCardField`, `DomainCustomValue`) | **só a org**, mesmo que o `Board` tenha `sector` (setor do modelo ou da Demanda): o setor não entra no endereço |
| outro model com `organization_id` | só a org |
| qualquer outra coisa | `unresolved` → **nega** |
| `None` | vazio: só escopos `ORGANIZACAO` (e relacionais) casam |

Para **criar** algo que ainda não existe, os serviços passam
`ResourceContext.for_new(organization=..., sector=..., ...)`.

---

## 3. Como `AuthorizationService.can()` decide

```python
AuthorizationService.can(user, catalog.TAREFA_INICIAR, task)
```

1. Superusuário ativo → **permitido** (`is_platform_admin`). É o operador da
   plataforma; ainda precisa de organização no `Profile` para usar as telas.
2. Usuário anônimo, inativo ou sem organização → **negado**.
3. Monta o endereço com `ResourceContext.of(resource)`.
4. **Teto de tenant**: recurso de outra organização → **negado** (doc 05 §43).
5. Busca atribuições ativas (`UserProfile`) cujo perfil ativo contém a ação
   ativa, e concessões diretas ativas (`UserAction`) para a ação.
6. Mantém as que têm escopo ativo que **cobre** o endereço (`scope_contains`).
7. Sobrou alguma → **permitido**.
8. Nenhuma sobrou: só para `demanda.visualizar` sobre uma `Activity` da própria
   organização vale a **relação** (`_demand_relation_allows`): o dono, o criador
   ou o responsável de uma `Task` não cancelada da demanda pode **ler** a
   própria Demanda, sem concessão. A regra é só de leitura; nenhuma outra ação
   usa relação.

Outras funções úteis de `AuthorizationService`:

| Função | Uso |
|---|---|
| `require(user, key, resource)` | Levanta `AuthorizationError` com mensagem legível. |
| `grants_for(user, key, resource)` | Lista de `Grant` com a origem de cada permissão. |
| `explain(user, key, resource)` | Motivos em texto ("Perfil: Gestor de Setor · Escopo: Setor Compras"). |
| `effective_actions(user)` | Todas as ações da pessoa com origem — usado nas telas de segurança. |
| `can_many(user, [(ação, recurso), ...])` | Várias verificações com **uma** consulta de perfis/concessões por chamada; devolve `{(ação, pk): bool}`. Usada nas listas e quadros para evitar uma consulta por linha (`can_many` aplica a mesma relação de leitura da Demanda). |
| `can_anywhere(user, key)` | Permitido em algum lugar (org ou algum setor)? Usado para menus e listas. |
| `accessible_sector_ids(user, key)` | Setores em que a ação vale. |

Os escopos de setor são memoizados na instância do usuário; qualquer mudança
em `UserSector` invalida o cache via signal (`invalidate_sector_cache`).

---

## 4. Onde a verificação acontece

| Camada | Mecanismo |
|---|---|
| Views de `core` (cadastros, usuários, segurança) | `ActionRequiredMixin` com `required_action = catalog.X`. Deve vir **depois** de `OrganizationRequiredMixin` nas bases. Nega com `PermissionDenied`. Escopo padrão: organização (`get_scope_object()` retorna `None`). |
| Serviços de `activities` | `require_action(user, catalog.X, recurso)` no início de cada método; converte a negação em `ActivityError`. Os de **Demanda** (`ActivityService`) estão em uso; os de **Tarefa**, fila e prazo (`TaskService`, `QueueService`, `DeadlineService`) continuam no código e na autorização, mas **as telas que os chamavam respondem 410** (seção 4.4). |
| Ficha, lista e anexos da Demanda | `ActivityDetailView` exige `DemandBoardAccess.can_view_activity` (participante do quadro ou `demanda.visualizar`); o download de anexo exige `demanda.visualizar` e a visibilidade da mensagem; a lista `/demandas/` filtra as linhas com `can_many(demanda.visualizar)`. |
| Quadros (`boards`) | `boards.services._require` (e `BoardAPIView.require`): ação `quadro.*` sobre o quadro; para quadro de **Demanda** (`Board.Kind.DEMAND`) a regra relacional de `DemandBoardAccess` (seção 4.3). |
| Central de tarefas (`/tarefas/`, `TaskCenterQuery`) | Sem ação própria: mostra os itens de quadro em que a pessoa é a Pessoa responsável; ver "outras pessoas/todas" exige `quadro.visualizar` ou `demanda.visualizar_todas` na organização; os quadros de outras pessoas passam por `can_many(demanda.visualizar)`. |
| Serviços de `processes` | `_require(...)` com endereço org + empresa; levanta `ProcessError`. **Inalcançáveis pela interface**: `/processos/*` responde 410 (`RetiredProcessView`). |
| Aplicar processo (`ProcessApplicationService.apply`) | `require_action(user, PROCESSO_APLICAR, atividade)` — o recurso é a **atividade**. **Desativado**: `/demandas/<pk>/processo/aplicar/` e as rotas de inputs e critérios respondem 410. Ver a seção 4.1. |
| Inputs e critérios do processo aplicado (`ActivityProcessService`) | Sem ação nova: `ActivityProcessService.can_update` aceita quem pode `demanda.editar` na atividade, o dono e quem é responsável/participante de alguma tarefa dela, sempre dentro da organização e nunca em atividade encerrada. Hoje sem rota ativa. |
| Caixa de Entrada (`IntakeService`) — **inativa por padrão** (`INTAKE_ENABLED=false`: toda rota `/entrada/` dá 404) | `entrada.registrar` e `entrada.visualizar` na **porta** da tela usam `can_anywhere` (`AnywhereActionMixin`, em `intake/views.py`): registrar não tem setor ainda, e `ActionRequiredMixin` só olharia o escopo de organização e negaria quem cuida de um setor. Itens: `entrada.triar` / `entrada.visualizar` sobre o próprio `IntakeItem` (outro tenant = 404, sem a ação = 403). A lista é filtrada por `IntakeService.visible_queryset`. Ver a seção 4.2. |
| Menu lateral | `acessos.context_processors.navigation` — **só UX**, não protege nada. |

Algumas ações do catálogo não são verificadas em ponto nenhum, e outras só
são verificadas em código que a interface já não alcança — a lista completa
está na seção 8 e as pendências em
[13_PENDENCIAS_CONHECIDAS.md](13_PENDENCIAS_CONHECIDAS.md).

### 4.1 `processo.aplicar` × `tarefa.criar`

> **Desativado em 02/10/2026.** Aplicar processo, os inputs e critérios do
> processo aplicado e todo o CRUD de processos respondem 410; o texto abaixo
> descreve o desenho que continua no código (`ProcessApplicationService`) e
> nos testes, útil caso o recurso volte.

Aplicar um processo cria tarefas em **vários setores**, e quem aplica (o
`Colaborador` sugerido, por exemplo) normalmente não tem `tarefa.criar` em todos
eles. O desenho é:

1. `ProcessApplicationService.apply` exige **`processo.aplicar`** na atividade
   (e que a pessoa seja da mesma organização dela);
2. as tarefas são criadas por `TaskService._create_task_core`, o mesmo núcleo que
   `create_task` usa **depois** de exigir `tarefa.criar`. O núcleo **não autoriza**
   — por isso é privado, só `create_task` e `apply` o chamam e nenhuma view o
   chama —, mas valida organização, setor, título e responsável como qualquer
   criação;
3. a auditoria registra as tarefas como criadas por quem aplicou o processo.

Ou seja, `processo.aplicar` autoriza materializar **o fluxo de uma versão já
publicada** (o molde é imutável e foi aprovado por quem tem `processo.publicar`);
não autoriza criar tarefas avulsas, e `tarefa.criar` continua sendo exigido para
elas. As Regras não dizem se aplicar processo dispensa o escopo de setor de
`tarefa.criar`; a decisão segue `Regras/05` §2057 (usar o fluxo padrão não exige
poder editar o fluxo) e está registrada em `Regras/12` §41.

### 4.2 Caixa de Entrada: `entrada.*` × `demanda.criar`

> **Inativa desde 01/10/2026** (`INTAKE_ENABLED`, padrão `false`): o item
> "Entrada" some do menu e `/entrada/…` dá 404. As regras abaixo valem quando
> ela for religada (`INTAKE_ENABLED=true`).

| Ação | Permite |
|---|---|
| `entrada.visualizar` | Ver a Caixa de Entrada e o texto das solicitações do escopo. |
| `entrada.registrar` | Colocar uma solicitação na Caixa de Entrada (e-mail, Teams, pedido verbal). |
| `entrada.triar` | Corrigir as sugestões, **criar a demanda**, ignorar e restaurar. |

- **Criar demanda exige também `demanda.criar`** no contexto final (setor, obra e
  organização escolhidos). Quem garante é o `ActivityService` (`save_draft` +
  `publish_draft`), que a `IntakeService.convert` chama; o `intake` não repete a regra. Quem
  só tem `entrada.triar` recebe a recusa e a solicitação continua nova, sem atividade nem
  efeito pela metade (tudo roda numa transação).
- **Visibilidade:** escopo de organização enxerga tudo, inclusive solicitações **sem setor
  sugerido** (a triagem geral). Escopo de setor enxerga só as do seu setor. Uma solicitação
  sem setor é invisível para o gestor de setor até alguém com escopo de organização
  atribuí-la a um.
- **Editar sem perder o acesso:** ao corrigir o setor sugerido, a `IntakeService` reverifica
  `entrada.triar` no setor novo; quem gerencia só um setor não consegue mandar o item para um
  setor que não enxerga (erro claro, em vez de o item sumir da lista).
- **Limitação conhecida:** a lista usa `accessible_sector_ids`, que só entende escopos de
  organização e de setor (inclusive `MEUS_SETORES` e `SETORES_GERENCIADOS`). Escopos de
  empresa, obra e centro de custo não ampliam o que se vê na Caixa de Entrada.
- **Perfis sugeridos:** Colaborador recebe `entrada.registrar`; Gestor de Setor recebe as três;
  Administrador, todas.

---

### 4.3 Quadros dinâmicos: `quadro.*`

| Ação | O que permite | Sensível |
|---|---|---|
| `quadro.visualizar` | Ver a lista e o conteúdo dos quadros da organização, o histórico e a busca/ordem/filtro. | não |
| `quadro.criar` | Criar quadro (em branco ou de um modelo). | não |
| `quadro.editar` | Renomear o quadro, **gerir grupos** (criar, renomear, cor, mover, excluir vazio) e **gerir visualizações** (criar, renomear, configurar e excluir Kanbans e Calendários). | não |
| `quadro.excluir` | Excluir o quadro inteiro. | **sim** |
| `quadro.gerir_colunas` | Criar, renomear, redimensionar, reordenar, configurar, ocultar, duplicar, **converter** e excluir colunas; gerir etiquetas. | não |
| `quadro.criar_item` | Adicionar item a um grupo. | não |
| `quadro.editar_item` | Renomear item, **mover** (de grupo e de posição) e preencher células. | não |
| `quadro.excluir_item` | Excluir item. | não |

- **Escopo só de organização.** O endereço do quadro não inclui setor (mesmo que o `Board` tenha `sector`), então `ResourceContext.of` devolve só a organização e as ações
  valem para a organização inteira; um escopo de setor concedido a `quadro.*` **não** casa (a lista dá 403 e o menu não
  mostra "Quadros", que usa `can` com `ResourceContext.for_new(org)`, a mesma pergunta da lista). Quem quiser
  quadros por setor precisa de uma decisão nova (doc 13, F31).
- **Quadro de Demanda (`Board.Kind.DEMAND`): regra relacional.** Cada Demanda publicada tem um quadro próprio, e
  `boards.demand_services.DemandBoardAccess` decide o acesso **antes** do motor de escopos (que continua valendo
  como alternativa): *participa* quem é dono ou criador da Demanda ou aparece em uma célula **Pessoa** de um item ativo
  do quadro. Participante vê o quadro (`quadro.visualizar`) e colabora (`quadro.criar_item`, `quadro.editar_item`:
  criar item, editar célula, mover). Mexer na **estrutura** (`quadro.editar`, `quadro.gerir_colunas`,
  `quadro.excluir`: colunas, grupos, visualizações) é só do dono, do criador ou de quem tem `quadro.gerir_colunas` na
  organização; participante comum não vira administrador de colunas. `quadro.excluir_item` num quadro de Demanda não tem
  regra relacional: segue o escopo de organização. Quadros-modelo (`Board.Kind.TEMPLATE`) seguem só o escopo de organização.
- **Visualizações são compartilhadas**: quem vê o quadro vê todas as abas e usa qualquer Kanban (arrastar cartão, preencher campo
  e criar item seguem `criar_item`/`editar_item`); mexer na **configuração** da visualização (agrupar por, ordem, campos do cartão,
  soma, nome, criar e excluir aba) é `quadro.editar`, e mexer nas **etiquetas das raias** é `quadro.gerir_colunas`. Não há
  visualização pessoal (doc 13, F31).
- **A permissão é checada no serviço**, a cada ação, e de novo a cada gravação de célula. Esconder botão (a tela recebe
  `permissions` calculado uma vez por `can_many`) é só experiência de uso. Endpoints que só **leem** (`.../fragmento/`, a
  prévia de conversão de tipo, `.../configuracoes/` sem campos) também exigem a ação (`BoardAPIView.require`): sem isso
  eles vazariam o desenho e a contagem de valores.
- **Outra organização recebe 404** em tudo (página e API): o quadro é carregado sempre por `organization=<a da pessoa>`.
  Um objeto de **outro quadro da mesma organização** usado como âncora (coluna, grupo) também dá 404.
- **Perfis sugeridos** (`SUGGESTED_PROFILES`): Colaborador recebe `visualizar`, `criar_item`, `editar_item`; Gestor de Setor
  soma `criar`, `editar`, `gerir_colunas` e `excluir_item`; Administrador, todas. Em bases que já existem, a migração
  `acessos/0005` concede por mapeamento (ver doc 04 §7.2) e `seed_acoes` cria as ações; marque o que faltar em
  `/permissoes/`.

### 4.4 O que mudou com a desativação de fila, processos e tarefas (02/10/2026)

As tarefas passaram a viver em **quadros por Demanda** (`boards`): a "tarefa" é um item do quadro da Demanda, com a
pessoa em uma célula **Pessoa** e o andamento numa coluna de **Status**. A migração `boards/0008` cancelou as `Task`
operacionais (ficam só como histórico). Efeito sobre a autorização:

| Rota | Resposta | Consequência |
|---|---|---|
| `/fila/…`, `/processos/…`, `/prazos/…`, `/conflitos/…`, `/checklist/…`, `/tarefas/<pk>/…` (todas as ações, painel, tempo, prazo, devolução...), `/demandas/<pk>/processo/…`, `/demandas/<pk>/tarefas/rapida/`, `/tarefas/lista-legada/`, `/tarefas/nova-rapida/` | **410** (`RetiredFeatureView` / `RetiredProcessView`) | As ações de tarefa, fila, prazo e processo não têm mais ponto de entrada na interface. |
| `/tarefas/`, `/tarefas/kanban/`, `/tarefas/calendario/` | `TaskCenterView` | Central de tarefas **sobre itens de quadro**: o recorte é "onde sou a Pessoa responsável"; sem ação própria (ver seção 4). |
| `/demandas/`, `/demandas/kanban/`, `/demandas/calendario/` | `DemandWorkBoardView` | Lista/Kanban/Calendário de Demandas; linhas filtradas por `demanda.visualizar`. |

- Os **serviços** (`TaskService`, `QueueService`, `DeadlineService`, `ProcessApplicationService`, `ProcessService`)
  continuam exigindo suas ações; só não há tela que os chame (restam as rotas auxiliares `kanban/tarefas/<pk>/etapa|condicao/`, que
  operam sobre as `Task` arquivadas, e a criação de `TaskService.create_task` com `board=`, que usa `DemandBoardAccess` em vez de `tarefa.criar`).
- **Quem trabalha numa tarefa** não precisa de nenhuma ação `tarefa.*`: basta participar do quadro da Demanda (acima).
  Por isso conceder `tarefa.*` ou `fila.*` a um perfil hoje não muda nada para o usuário.
- A **visibilidade** da Demanda deixou de ser só pela organização: ficha, anexos e lista exigem `demanda.visualizar` (ou
  a relação de leitura do dono, criador e responsável).
- **Grupos de acesso por tela** (commit `be4b9ee`) foram revertidos em `6fb95b9`: não existem no código; o modelo é só perfil + escopo.

---

## 5. Administração pela interface

O caminho do dia a dia é por **tela e nível** (seção 5.1): o usuário numa página só, os grupos de
acesso e o menu. As telas por ação, abaixo, continuam existindo como **ajuste fino** (avançado).

| Tela | URL | Ação exigida |
|---|---|---|
| Lista de usuários | `/usuarios/` | `usuario.visualizar` |
| Novo usuário / editar usuário (dados, equipe, grupo, telas) | `/usuarios/novo/`, `/usuarios/<pk>/` | `usuario.criar` / `usuario.editar` (grupo e telas: também `seguranca.gerir_autorizacoes`) |
| Grupos de acesso (editar) | `/grupos-de-acesso/` | ver: `seguranca.gerir_perfis`; gravar: `seguranca.gerir_autorizacoes` |
| Comparar grupos | `/grupos-de-acesso/comparar/` | `seguranca.gerir_perfis` |
| Matriz de permissões (perfis × ações) | `/permissoes/` | `seguranca.gerir_perfis` |
| Salvar ações de um perfil | `/permissoes/<pk>/salvar/` | `seguranca.gerir_autorizacoes` |
| Criar/editar perfil | `/perfis/novo/`, `/perfis/<pk>/` | `seguranca.gerir_perfis` |
| Acessos de uma pessoa (perfis e concessões, com origem) | `/usuarios/<pk>/acessos/` | `seguranca.gerir_autorizacoes` |
| Concessão direta | `/usuarios/<pk>/concessoes/` | `seguranca.gerir_autorizacoes` |

Todas as alterações passam por `AccessService` e são auditadas
(`PROFILE_CREATED`, `PROFILE_ASSIGNED`, `ACTION_GRANTED` etc., com
`target_user`). `AccessService.set_profile_actions` só altera as ações que
estavam **visíveis** na tela, para um filtro na matriz não apagar o resto.

### 5.1 Telas e níveis (grupos de acesso)

O motor continua sendo **ação + escopo + origem**. Por cima dele, `acessos/screens.py` é a tabela que liga
cada **tela** do menu e cada **nível** às ações; `acessos/screen_services.py` lê e grava por ela. Não há
modelo novo:

| Na tela | No motor |
|---|---|
| Grupo de acesso | `acessos.Profile` (perfil) |
| Equipe (Membro / Gestor da equipe / principal) | `accounts.UserSector` e `Profile.main_sector` |
| Vale para | o `Scope` da atribuição: organização inteira, `MEUS_SETORES` (as equipes da pessoa) ou `SETORES_GERENCIADOS` |
| Tela + nível | as ações da tabela abaixo |
| Ajuste individual | `UserAction` (concessão direta) para aquela pessoa |
| Menu | o nível de cada tela, lido das ações efetivas da pessoa |

Níveis: **Sem acesso** (nenhuma ação da tela), **Ver** (`view`) e **Editar** (`view` + `edit`). Cada tela
declara três listas: `view`, `edit` e `extra` (avançadas e sensíveis, como cancelar e reabrir). A primeira
ação de `edit` é o *marcador* que decide se um perfil lido está em "Editar". As 21 telas, em 4 seções (Dia a
dia, Gestão, Processos e cadastros, Administração), estão em `screens.SCREENS`; o teste `ScreenMapTests`
garante que toda ação existe no catálogo e pertence a **uma** tela só.

Regras que importam:

- **Só se grava o que mudou.** Salvar um grupo compara o nível lido com o pedido, tela a tela
  (`GroupService.changes_for`). O que não mudou — inclusive ações avançadas e perfis montados à mão na
  matriz — fica exatamente como estava. Descer de "Editar" para "Ver" tira as ações de edição e as
  avançadas da tela; "Sem acesso" tira tudo dela.
- **Não existe "negar".** O motor só concede (seção 1), então, na tela da pessoa, um nível abaixo do
  grupo fica desabilitado: para tirar uma tela, mude o grupo. O servidor ignora um pedido abaixo do grupo.
- **Ajuste individual** só sobe o nível. Ações que só funcionam sobre a organização inteira
  (`screens.ORG_ONLY_ACTIONS`: quadros, usuários, grupos, cadastros…) são concedidas no escopo de
  organização; as demais, no escopo da atribuição do grupo. "Voltar ao padrão do grupo" revoga essas
  concessões. Concessões manuais em outros escopos (feitas em *Acessos avançados*) não são tocadas.
- **Vale para × telas só de organização.** Num grupo atribuído a "as equipes da pessoa", telas cuja ação é
  verificada sobre a organização inteira (quadros, cadastros, usuários…) não autorizam nem aparecem no menu.
  A tela avisa e oferece "Usar a organização inteira".
- **Quem tem mais de um grupo** (ou um escopo "personalizado": empresa, obra, setor fixo) continua com a
  atribuição como está; a página da pessoa mostra os grupos e só edita dados, equipe e situação.
- **Ninguém se tranca para fora:** salvar um grupo que tiraria de quem salva o poder de gerir grupos, ou
  mudar o próprio grupo de um modo que tire `usuario.editar`/`seguranca.gerir_autorizacoes`, é recusado.
- **Super usuário** (`is_superuser`) continua passando direto pelo motor. Só outro super usuário o concede ou
  retira (auditado como `SUPERUSER_CHANGED`) e sempre sobra ao menos um ativo. A lista de usuários mostra a
  etiqueta e conta quem está "como Administrador" (super usuário ou grupo com todas as telas).

**Menu.** Cada item da barra lateral aparece conforme o nível da tela
(`acessos.screen_services.menu_levels`, 2 consultas por página). Ações verificadas só sobre a organização
contam só se vierem de escopo de organização; as demais contam em qualquer escopo. Isto é experiência de uso
— a proteção real continua nas views e serviços (seção 4). As telas que só existiam como item de menu
ganharam ações `tela.*` (grupo `telas` do catálogo): `tela.inicio`, `notificacoes`, `equipe`, `gargalos`,
`insights`, `empresas`, `setores`, `clientes`, `obras`, `centros_custo`, `configuracoes`, `integracoes`.

**Migração `acessos/0006_telas_do_menu`.** Cria as ações `tela.*` e concede a quem já enxergava cada item
o que o mantém visível (perfis e concessões diretas, no mesmo escopo): Início e Notificações para todos;
Equipe, Filas e gargalos e Insights para quem tem `metricas.visualizar`; os cinco cadastros para quem já
abria Cadastros; Configurações e Integrações para quem já via a seção Administração. Nenhum perfil existente
(inclusive o Administrador) nem nenhum super usuário perde acesso; reversível.

> Uma pessoa **sem nenhum grupo nem concessão** não vê nenhum item no menu (antes via Início, Demandas,
> Tarefas e Notificações, sem poder usar nada). Atribua um grupo em *Usuários*.

---

## 6. Perfis sugeridos

Criados por `seed_lps_demo` a partir de `SUGGESTED_PROFILES`. São ponto de
partida — a organização pode renomear e alterar (doc 05 §11).

| Perfil | Resumo |
|---|---|
| **Colaborador** | **Demandas:** ver, criar, assumir, marcar pendente, mover estágio, definir etapa e status. **Tarefas** (`tarefa.*`, hoje sem tela): ver, assumir, aceitar, recusar, iniciar, pausar, retomar, concluir, devolver, bloquear. Ver a própria posição na fila; propor/aceitar/recusar prazo; conversar; ver e aplicar processos; gerir clientes; registrar solicitações na Caixa de Entrada (`entrada.registrar`). **Quadros:** ver, criar item, editar item. |
| **Gestor de Setor** | **Demandas:** ver, ver todas, criar, editar, assumir, marcar pendente, aprovar pendência. **Não** recebe mover estágio, definir etapa/status, alterar dono, concluir, cancelar nem reabrir demanda (ficam com o Administrador ou com concessão direta). **Tarefas:** as do Colaborador (menos mover estágio de demanda) + criar, editar, atribuir, mover de setor, mover estágio, definir etapa e status, **reabrir (`tarefa.reabrir`)**, lançar tempo manual; não recebe cancelar nem alterar responsável. Fila completa e reordenar; propor/aceitar/recusar/alterar prazo solicitado e resolver conflito; métricas e auditoria; todas as ações de processo; clientes, estágios de tarefa, etapas, status, marcadores, cores de status e de prioridade; ver, registrar e triar a Caixa de Entrada (`entrada.*`). **Quadros:** ver, criar, editar, gerir colunas, criar/editar/excluir item (não excluir quadro). |
| **Administrador** | Todas as ações do catálogo (84). Setores, empresas, obras, centros de custo, motivos de devolução, usuários e segurança só ele recebe por perfil. |

> **Ação nova em organização já implantada:** vale para qualquer ação nova
> (também `quadro.*`, `etapa.gerir`, `condicao.gerir`, `entrada.*`). `seed_acoes` cria a ação no
> catálogo, mas **não** a acrescenta a perfis que já existem no banco — nem ao
> Administrador. Depois de rodar `seed_acoes`, marque `tarefa.reabrir` nos
> perfis que devem ter (Matriz de permissões, `/permissoes/`). Rodar
> `seed_lps_demo` de novo também a acrescentaria, mas ele re-adiciona **todas** as
> ações sugeridas (desfazendo remoções feitas de propósito) e recria setores de
> demonstração que faltarem — não use em produção. Reabrir uma tarefa
> de atividade já concluída também exige `demanda.reabrir` (hoje só no
> Administrador). A reabertura de tarefa saiu da interface junto com as rotas `/tarefas/<pk>/` (seção 4.4); a de demanda continua. Ver [06_ATIVIDADES_E_TAREFAS.md](06_ATIVIDADES_E_TAREFAS.md) §2.11.

---

## 7. Receita: adicionar uma ação nova

1. Em `acessos/catalog.py`, crie a constante (`MINHA_ACAO = "grupo.minha_acao"`)
   e adicione a tupla `(chave, nome, descrição, sensível)` ao grupo certo em
   `GROUPS`. Se fizer sentido, inclua em `SUGGESTED_PROFILES`.
2. Use a constante no código:
   - view de `core`: `required_action = catalog.MINHA_ACAO`;
   - serviço: `require_action(user, catalog.MINHA_ACAO, recurso)`.
3. Se o recurso for um model novo, ensine `ResourceContext.of` a endereçá-lo —
   senão ele só terá o escopo da organização (ou será negado, se não tiver
   `organization_id`).
4. Rode `python manage.py seed_acoes` (local e no deploy) para gravar a ação.
5. Teste com os helpers de `acessos/testing.py`
   (`grant_action(user, catalog.MINHA_ACAO, organization=org)`).

Para **remover** uma ação: tire do catálogo e rode `seed_acoes`; ela fica
`is_active=False` e deixa de conceder, mas o histórico é preservado.

---

## 8. Catálogo completo de ações (84) e onde são verificadas

Fonte: `acessos/catalog.py` (`GROUPS`). A coluna "Verificação hoje" diz onde o código **realmente** consulta a ação a
partir do que a interface ainda alcança (seção 4.4). "Sem tela" = a verificação existe no serviço, mas a rota está desativada (410).
Chaves gravadas: `demanda.*` (renomeadas de `atividade.*` pela migração `acessos/0003`).

| Grupo (nº) | Ações | Verificação hoje |
|---|---|---|
| Demandas (14) | `demanda.visualizar` | Ficha, anexos, lista/Kanban/Calendário de Demandas, quadro da Demanda e Central de tarefas, mais a relação de leitura (dono, criador, responsável). |
| | `demanda.visualizar_todas` | Aba "Todas" e recortes de `filtered_activities_queryset`, Kanban legado, "outras pessoas/todas" na Central de tarefas. |
| | `demanda.criar`, `.editar`, `.alterar_dono` | `ActivityService` (`save_draft`/`publish_draft`/`create_activity`, `update_activity`, `change_owner`), editor de 4 etapas, edição inline e campos de quadro de domínio. |
| | `demanda.assumir`, `.marcar_pendente`, `.aprovar_pendencia`, `.concluir`, `.cancelar`, `.reabrir` | `ActivityService` (`claim`, `mark_pending`, `approve_pendency`, `finalize`/`complete_activity`, `cancel_activity`, `reopen_activity`). `resolve_pendency` também exige `marcar_pendente`, mas não tem rota (doc 13). |
| | `demanda.mover_estagio`, `.definir_etapa`, `.definir_condicao` | `set_stage` aceita `definir_etapa` **ou** a legada `mover_estagio`; `set_condition` exige `definir_condicao`. Kanban de Demandas e edição inline. |
| Tarefas (21) | `tarefa.visualizar`, `.criar`, `.editar`, `.atribuir`, `.alterar_responsavel`, `.assumir`, `.aceitar`, `.recusar`, `.iniciar`, `.pausar`, `.retomar`, `.devolver`, `.concluir`, `.cancelar`, `.reabrir`, `.bloquear`, `.mover_setor`, `.mover_estagio`, `.definir_etapa`, `.definir_condicao`, `tempo.lancar_manual` | **Sem tela** (`TaskService`; telas `/tarefas/<pk>/…` em 410). `tarefa.visualizar` só aparece na ramificação de tarefas do quadro de domínio, sem rota. Única via viva: `kanban/tarefas/<pk>/etapa\|condicao/` (`definir_etapa`/`definir_condicao`), sobre `Task` arquivada. |
| Filas (3) | `fila.visualizar_posicao_propria` | **Nenhuma** verificação em ponto algum. |
| | `fila.visualizar_completa`, `fila.reordenar` | Sem tela (`QueueView`, `QueueReorderView`, `QueueService.reorder`; `/fila/` em 410). |
| Prazos (5) | `prazo.propor`, `.aceitar`, `.recusar`, `escalonamento.resolver` | Sem tela (`DeadlineService`; `/prazos/…`, `/conflitos/…` em 410). |
| | `prazo.alterar_solicitado` | `DomainBoardMutationService.set_value` (campo "prazo solicitado" de quadro de domínio). |
| Comunicação (1) | `comunicacao.participar` | Mensagens da Demanda (`MessageService.post_activity_message`) e menções. |
| Cadastros (14) | `setor.editar`, `setor.inativar` | Telas de Setores (`core/views.py`), criar setor ao trocar o setor de uma Demanda; `setor.inativar` na ativação/inativação. |
| | `setor.criar` | **Nenhuma** (o cadastro usa `setor.editar`). |
| | `empresa.gerir`, `obra.gerir`, `centro_custo.gerir`, `cliente.gerir`, `motivo_devolucao.gerir`, `tag.gerir`, `cor_status.gerir`, `cor_prioridade.gerir` | Telas de Cadastros e de Prioridades (`core/views.py`); `cliente.gerir`/`empresa.gerir`/`obra.gerir`/`centro_custo.gerir` também mostram "criar" nos seletores da Demanda. |
| | `etapa.gerir`, `condicao.gerir` | "Etapas e status" (`core/views.py`), criar/editar opção no pop-over da lista e do Kanban. |
| | `estagio_tarefa.gerir` | **Só menu**: decide se "Cadastros" aparece; a tela de estágios de tarefa usa `etapa.gerir`. |
| Processos (7) | `processo.criar`, `.editar_rascunho`, `.publicar`, `.criar_versao`, `.inativar`, `.aplicar` | Sem tela (`ProcessService`, `ProcessApplicationService`; `/processos/…` e `…/processo/aplicar/` em 410). |
| | `processo.visualizar` | Só o menu. |
| Segurança (6) | `usuario.visualizar`, `usuario.editar`, `seguranca.gerir_perfis`, `seguranca.gerir_autorizacoes` | `ActionRequiredMixin` nas telas de `core` (seção 5); `usuario.editar` também protege `/usuarios/novo/`. |
| | `usuario.criar` | Só decide se o botão "criar pessoa" aparece nos seletores da Demanda. |
| | `usuario.inativar` | **Nenhuma**. |
| Auditoria (2) | `auditoria.visualizar` | **Nenhuma**: o Histórico (`/historico/`) só é limitado pela organização. |
| | `metricas.visualizar` | Menu "Visão do gestor" e `ManagementView` (`can_anywhere`). |
| Caixa de entrada (3) | `entrada.visualizar`, `.registrar`, `.triar` | `IntakeService`/views (seção 4.2), **inativa** por padrão (`INTAKE_ENABLED`). |
| Quadros (8) | `quadro.visualizar`, `.criar`, `.editar`, `.excluir`, `.gerir_colunas`, `.criar_item`, `.editar_item`, `.excluir_item` | `boards.services` e `boards/views.py`; quadros de Demanda passam por `DemandBoardAccess` (seção 4.3). |
