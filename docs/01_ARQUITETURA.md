# 01 — Arquitetura

> Visão geral de como o código da LPS está organizado: quais apps existem, o que
> cada um faz, como as camadas se relacionam e quais convenções o código segue.
> As regras de negócio que motivam cada decisão estão em `Regras/`; os
> docstrings do código citam essas seções (ex.: "Regras 05 §43").
> Atualizado em 03/10/2026 (código no commit `add5acd`).

> **Glossário (01/10/2026): na interface, "Atividade" passou a se chamar "Demanda".**
> Mudou tudo o que a pessoa vê: menus, títulos, botões, formulários, mensagens, avisos,
> e-mails, nomes de ações e de grupos de permissão (inclusive as chaves mostradas em
> `/permissoes/`: `demanda.criar`, `demanda.editar`…), rótulos de modelos (no Admin) e as
> notificações já gravadas. **O endereço e o código também mudaram:** as páginas vivem em
> `/demandas/...` (os links `/atividades/...` de antes redirecionam, `core/legacy_redirects.py`),
> o código gerado é `DEM-AAAA-NNNNN` (os já emitidos foram reescritos, junto com as pastas de
> anexos, pela migração `activities/0020`) e os slugs de aba na URL passaram a
> `?tab=estagios-demanda`, `?tab=status-demanda`, `?visao=demanda`, `?sort=demanda` (os valores
> antigos continuam valendo). Os anexos **não** têm mais endereço público: são entregues por
> `/demandas/<id>/anexos/<id>/download/`, que exige login, mesma organização e permissão de ver a
> demanda (ver [03_CONFIGURACAO.md](03_CONFIGURACAO.md) §4); o antigo `/atividade-arquivos/...`
> responde 410.
> Fica como está, de propósito, por ser nome técnico e não o que a pessoa vê: o código (`Activity`,
> `activities/`, `ActivityService`, as constantes `ATIVIDADE_*`), as tabelas, os nomes de rota
> (`activity-*`), a pasta em disco `atividade_arquivos/` (variável `ACTIVITY_FILES_ROOT`) e os valores
> internos (`MINHAS_ATIVIDADES`, `ACTIVITY_CREATED`). Este documento e os demais em `docs/` seguem
> dizendo "atividade" ao falar do modelo `Activity`.

> **Glossário (02/10/2026): "Situação" virou "Etapa" e "Condição" virou "Status" nos textos da
> interface.** A troca foi textual: a "Condição" manual por setor (modelo `WorkflowStatus`, campo
> `condition`, rota `activity-set-condition`) aparece como **Status**, e o que a tela chamava de
> "Situação" aparece como **Etapa** (inclusive a coluna ativo/inativo das telas de cadastro). Os nomes
> de código, tabelas e rotas não mudaram (`ActivityStage`, `TaskStage`, `WorkflowStatus`,
> `ATIVIDADE_DEFINIR_CONDICAO`…). O **estado operacional** (`Activity.status`, `Task.status`) continua
> fixo no código e é outra coisa: ver a convenção "Status × etapa" na seção 4.

---

## 1. Apps

O projeto Django fica em `config/` (settings, urls, wsgi/asgi). Os apps de
negócio estão na raiz:

| App | Responsabilidade | Principais arquivos |
|---|---|---|
| `core` | Tenant (`Organization`) e cadastros da organização: empresas, setores (com cor), obras, clientes, centros de custo, tags, **etapas** (`ActivityStage`, `TaskStage`) e **status** (`WorkflowStatus`) por setor, cores e rótulos configuráveis (`EnumColor`). Hospeda também as telas de usuários, de permissões (`/permissoes/`, `/perfis/`), de cadastros (inclusive o de motivos de devolução, cujo modelo `ReturnReason` fica em `activities`) e de configurações, os mixins base e os redirecionamentos de endereços antigos. | `models.py`, `services.py` (`StageService`, `ConditionService`), `mixins.py`, `colors.py`, `sanitize.py`, `widgets.py`, `legacy_redirects.py` |
| `accounts` | Identidade: `Profile` (1:1 com `User`, liga a pessoa a uma organização), participação em setores (`UserSector`), cadastro com confirmação de e-mail (`EmailVerification`), login por e-mail. | `models.py`, `auth_backends.py`, `forms.py`, `signals.py`, `views.py` |
| `acessos` | Motor de autorização: catálogo de ações, perfis de acesso, escopos, concessões. Responde "quem pode fazer o quê, onde e por quê". Não tem telas próprias (ficam em `core`); o *context processor* `navigation` monta o menu lateral. | `catalog.py`, `models.py`, `services.py`, `context_processors.py`, `testing.py` |
| `activities` | Núcleo operacional das **Demandas** (`Activity`): lista e quadro de Demandas (a tela `/demandas/` é desenhada por `boards`), criação em etapas (wizard) e edição em janela, edição inline, Kanban por setor (`kanban.py`), pendências, conversa com @menções e reações, anexos, histórico. Guarda também o modelo de **Tarefa** (`Task`) com fila, sessões de trabalho, bloqueios, devoluções, prazos e checklist; esse fluxo operacional foi **desativado** (todas as rotas `/tarefas/<id>/...`, `/fila/...`, `/prazos/...` e `/conflitos/...` respondem 410) e as tarefas de uma demanda passaram a ser itens do quadro dela (`boards`). Ver [06_ATIVIDADES_E_TAREFAS.md](06_ATIVIDADES_E_TAREFAS.md). | `models.py`, `services.py`, `views.py`, `policies.py`, `activity_editor.py`, `inline_edit.py`, `inline_views.py`, `kanban.py`, `filtering.py`, `errors.py`, `process_application.py`, `process_state.py`, `templatetags/lps.py` |
| `processes` | Modelos de processo reutilizáveis e versionados (inputs, output, critérios de aceite, fluxo por setor). Os dados continuam preservados, mas o app está **desativado para uso**: todas as rotas de `/processos/` respondem 410 e `/demandas/<id>/processo/...` também ("Processos foram desativados. Use o quadro da Demanda."). | `models.py`, `services.py`, `views.py` |
| `intake` | Caixa de Entrada (**inativa por padrão**, `INTAKE_ENABLED`, doc 03): solicitações que chegaram (e-mail, Teams, pedido verbal) e ainda não viraram demanda. A pessoa decide **Criar demanda**, **Editar** as sugestões ou **Ignorar**; nada vira demanda sozinho. Sugere título, cliente, obra, setor e prazo com regras locais (sem IA). Ver [06_ATIVIDADES_E_TAREFAS.md](06_ATIVIDADES_E_TAREFAS.md) para o que a demanda criada recebe. | `models.py`, `services.py`, `suggestions.py`, `textparse.py`, `policies.py`, `views.py` |
| `boards` | **Quadros**, em duas camadas. (1) *Quadros dinâmicos* (`Board`): o usuário monta o quadro (grupos, colunas de 8 tipos ativos, etiquetas) e preenche itens numa tabela editável, com autosave por célula e as visualizações Kanban e Calendário (`BoardView`). Um quadro pode ser **modelo** (`Board.Kind.TEMPLATE`, de um setor) ou o **quadro de uma Demanda** (`Board.Kind.DEMAND`, 1:1 com `Activity`, instanciado a partir de um modelo ou em branco): esses itens são as tarefas operacionais de hoje. (2) *Quadros de domínio* (`DomainBoard`, `Domain.DEMAND` e `Domain.TASK`): só guardam a configuração das lentes (colunas, campos do cartão, visões) sobre os objetos operacionais; hoje a tela `/demandas/` os usa (Tabela, Kanban e Calendário de `Activity`). O domínio `TASK` e `TaskWorkBoardView` continuam no código, mas `/tarefas/` é servida pelo painel **Tarefas** (`TaskCenterView`: lista, Kanban e Calendário das tarefas — itens dos quadros das Demandas — em que a pessoa é responsável, sem model próprio). A ficha da Demanda mostra uma prévia só de leitura do quadro dela (`demand_preview.py`). Auditoria genérica (`target_type`/`target_id`/`metadata`). Ver [04_MODELOS_DE_DADOS.md](04_MODELOS_DE_DADOS.md) e [09_ROTAS.md](09_ROTAS.md); especificações em `docs/LPS_*.md`. | `models.py`, `validators.py`, `services.py`, `queries.py`, `presentation.py`, `starter_templates.py`, `kanban.py`, `calendar_view.py`, `demand_services.py`, `domain_defaults.py`, `domain_services.py`, `work_views.py`, `task_center.py`, `task_center_views.py`, `demand_preview.py`, `views.py`, `templatetags/lps_board.py` |
| `notifications` | Notificações in-app, caixa de entrada com categorias, e-mails síncronos. | `models.py`, `services.py`, `recipients.py`, `views.py` |
| `audit` | `AuditLog`: trilha de auditoria somente-inclusão de eventos de negócio e de segurança. | `models.py`, `services.py` |
| `painel` | Telas "em construção" que mantêm o menu lateral fiel a `Telas/MENU_E_SUBMENUS_LPS.md`, mais duas telas de configuração emprestadas de `core` (`EtapasEStatusView`, `PrioridadesView`). | `views.py`, `urls.py` |

Fora dos apps: `config/` (settings, urls, wsgi/asgi), `templates/` (um diretório por app, mais `base.html` e parciais),
`static/` (CSS e JS por tela, sem bundler), `tests/` (testes JavaScript) e `Regras/`, `Telas/` (especificação do produto).
A estrutura completa de pastas está na seção 5.

Não há mais as pastas `demands/` e `workflows/` (restos de uma versão anterior, citados em edições antigas deste documento).

### Dependências entre apps

Levantado a partir dos imports (fora de testes e migrations, inclusive os feitos dentro de funções) e das FKs
entre apps:

| App | Usa |
|---|---|
| `audit` | nenhum app (só FKs para `activities` e `User`) |
| `accounts` | `acessos` (invalidação de cache, em `signals.py`); FKs para `core` |
| `painel` | `core` |
| `processes` | `accounts`, `acessos`, `core`; FKs para `activities` e `core` |
| `notifications` | `accounts`; FKs para `activities` |
| `intake` | `acessos`, `activities` (cria a demanda por `ActivityService.save_draft` + `publish_draft`), `core`. `activities` **não** importa `intake`: a ligação de volta é só o `OneToOneField` `IntakeItem.activity` (`activity.intake_item`). |
| `boards` | `acessos`, `activities` (modelos e serviços: o quadro da Demanda e os quadros de domínio leem e mudam `Activity`/`Task` por `ActivityService`/`TaskService`), `audit`, `core`, `notifications` (só leitura de `Notification`, no painel Tarefas e na prévia). FK `Board.activity` (1:1) para `activities`. |
| `acessos` | `accounts`, `audit`, `core`. **Não** importa `activities`, `boards` nem `intake` para decidir acesso: `ResourceContext.of` reconhece cada recurso pelo nome do modelo (`_meta.model_name`). Só o *context processor* `navigation` importa `intake.services` e `boards.task_center` (dentro de funções), para os contadores do menu. |
| `core` | `accounts`, `acessos`, `activities`, `audit` |
| `activities` | `acessos`, `audit`, `boards` (criação do quadro da Demanda, `DemandBoardAccess`, e as telas `DemandWorkBoardView`/`TaskCenterView` ligadas em `activities/urls.py`; FK de `Board` para `Activity`), `core`, `notifications`, `processes` (FKs `Activity.process_version` e `Task.process_step`; código de aplicação do processo em `activities/process_application.py`, hoje sem rota ativa) |
| `config` | `accounts` (`EmailAuthenticationForm`) e `core` (`legacy_redirects`), em `urls.py` |

Há dependências circulares (`core` ↔ `acessos` ↔ `activities` e `activities` ↔ `boards`). Elas são
resolvidas com imports **dentro das funções** e FKs por string (`"core.Organization"`,
`"activities.Activity"`). Ao mover código entre apps, mantenha esse padrão para não criar erro de import
circular na inicialização.

---

## 2. Camadas

```
URL → View (fina) → Service (regra + autorização + auditoria + notificação) → Model
```

- **Views** resolvem a organização, carregam objetos já filtrados por ela,
  validam o formulário e chamam um serviço. Views de ação herdam de
  `ServiceActionView` (em `activities/views.py`): chamam o serviço, convertem
  o erro em mensagem (`django.contrib.messages`) e redirecionam. Os endpoints
  JSON (edição inline da lista de Demandas, Kanban, células e itens dos
  quadros) seguem o mesmo princípio: view fina, regra no serviço. Entre a view
  e o serviço pode haver um *adapter* que só traduz dados de tela em chamadas
  ao serviço, sem regra própria (`activities/inline_edit.py`,
  `boards/domain_services.py`).
- **Services** (`*/services.py`) concentram a regra de negócio. Cada método
  público:
  1. verifica a autorização (`require_action(user, catalog.X, recurso)`);
  2. valida a transição de estado;
  3. grava;
  4. registra em `AuditService.log(...)`;
  5. dispara `NotificationService.notify(...)` e, quando aplicável, e-mail.
- **Models** guardam dados e propriedades de exibição; quase não têm regra.

Erros de negócio são exceções específicas por app, sempre com mensagem pronta
para o usuário:

| Exceção | Onde |
|---|---|
| `ActivityError` | `activities/errors.py` (reexportada por `activities/services.py`) |
| `ActivityPermissionError` | `activities/errors.py`; subclasse de `ActivityError` levantada por `require_action` quando o motor nega (as respostas JSON usam 403 para ela e 400 para os demais) |
| `CadastroError` | `core/services.py` |
| `ProcessError` | `processes/services.py` |
| `IntakeError` | `intake/services.py` (a falha de `ActivityService` ao converter vira `IntakeError`) |
| `BoardError`, `BoardPermissionError` | `boards/services.py` (a segunda é subclasse da primeira e é a recusa do motor de autorização; as views respondem 400/409 e 403) |
| `DomainBoardError`, `DomainBoardConflict` | `boards/domain_services.py` (alterações nas lentes de Demandas e Tarefas; o conflito é o valor que mudou desde a leitura) |
| `AuthorizationError` | `acessos/services.py` (convertida em `ActivityPermissionError` por `require_action`) |

---

## 3. Multi-tenancy

`core.Organization` é o tenant. Tudo pertence a uma organização:

1. Uma pessoa pertence a **uma** organização via `accounts.Profile.organization`
   (Regras 05 §7). O `Profile` é criado vazio por signal quando o `User` é
   criado; quem define a organização é um administrador (tela `/usuarios/`).
2. Cadastros e registros de acesso têm FK `organization`. `Activity` tem FK
   direta; `Task` herda pela atividade; `QueueEntry`, pelo setor. Os modelos
   de `boards` expõem `organization_id` por um caminho curto (por exemplo,
   `BoardItem.organization_id` vem de `board.organization_id`), que é o
   endereço usado pelo motor de autorização.
3. `core.mixins.OrganizationRequiredMixin` resolve `self.organization` em toda
   view da LPS. Sem organização, redireciona para `/accounts/me/` com a
   mensagem "Seu usuário ainda não está vinculado a uma organização".
4. As views filtram tudo por `organization=self.organization`
   (ou `activity__organization=...`); objetos de outra organização dão 404.
   Isso vale também para o download de anexos de demanda.
5. O motor de autorização aplica um **teto de tenant**: se o recurso é de outra
   organização, nenhuma concessão vale (doc 05 §43). Ver
   [05_AUTORIZACAO.md](05_AUTORIZACAO.md).

O Admin do Django (`/admin/`) **não** é filtrado por organização — é a
ferramenta do operador da plataforma.

---

## 4. Convenções do código

- **Autorização nega por padrão.** `ActionRequiredMixin` exige o atributo
  `required_action`; sem ele, levanta `ImproperlyConfigured`.
- **Esconder no menu é UX, não segurança.** O context processor
  `acessos.context_processors.navigation` só decide o que aparece; a
  verificação real acontece na view ou no serviço (doc 09 §11).
- **Auditoria só por `AuditService.log`.** Nenhum código cria `AuditLog`
  diretamente.
- **HTML de usuário só entra por `core/sanitize.py`** (`sanitize_description`,
  baseado em `nh3`, com lista fixa de tags permitidas).
- **Nada é apagado de verdade** quando há histórico: cadastros usam
  `is_active`, vínculos usam `removed_at` (`UserSector`, `TaskExecutor`),
  concessões de acesso usam `is_active=False`. Mudanças de dono/responsável
  geram linhas de log (`OwnerChangeLog`, `TaskResponsavelChangeLog`).
- **Nomes duplicados** em cadastros são checados sem diferenciar maiúsculas
  e espaços (`core.services._assert_unique_name`, Regras 05 §22-23).
- **Status × etapa × status manual.** `Activity.status` e `Task.status` são
  o estado operacional (fixo no código, governam fila, bloqueio e conclusão).
  A **etapa** (`stage`: `ActivityStage`/`TaskStage`) é a coluna visual do
  Kanban e o **status** da interface (`WorkflowStatus`, "condição" no código)
  é uma leitura manual; ambos são configuráveis **por setor** e nunca alteram
  o estado operacional: mover um cartão de etapa grava só a etapa e escolher
  o status grava só o status (`set_stage`/`set_condition`).
- **Cores e rótulos** de status, urgência e prioridade são configuráveis por
  organização (`core.EnumColor`) mas o **código** do enum nunca muda de
  significado; a resolução passa por `core.colors.EnumColorResolver`. Etapas,
  status, setores e etiquetas de quadro guardam a própria cor (hex, paleta de
  `core/colors.py`).
- **Posição sem reescrever listas.** Nos quadros, grupos, colunas, itens e
  etiquetas têm posição decimal (passo 1000): mover algo grava UMA posição
  entre as vizinhas, e o cliente manda os vizinhos, nunca um número
  (`boards/services.py`, `PositionService`).
- **Rotas desativadas respondem 410, não 404.** O que foi retirado de uso
  (fluxo operacional de tarefa, fila, processos, links de anexo antigos)
  continua reconhecível e responde `410 Gone` com uma mensagem
  (`RetiredFeatureView`, `RetiredProcessView`, `MovedActivityFileView`);
  endereços que apenas mudaram de nome redirecionam (301; 308 em POST).
  Não escreva código novo que dependa das rotas desativadas.
- **Recurso opcional por settings.** A Caixa de Entrada só existe com
  `INTAKE_ENABLED=true` (rotas dão 404 e o item some do menu; ver
  [03_CONFIGURACAO.md](03_CONFIGURACAO.md)).
- **Idioma.** Interface, docstrings e mensagens em português; nomes de
  classes e funções em inglês; valores de enum em português maiúsculo
  (`EM_FILA`, `CONCLUIDA`).

---

## 5. Estrutura de pastas

```
workflow/
├── config/            # settings (base/dev/prod), urls, wsgi, asgi
├── core/ accounts/ acessos/ activities/ boards/ processes/
│   intake/ notifications/ audit/ painel/      # apps (seção 1)
├── templates/         # base.html, parciais (_icon, _sector_picker...) e um diretório por app
├── static/            # css/, js/, img/ (sem bundler; collectstatic gera staticfiles/)
├── tests/             # testes JavaScript (*.test.cjs, rodam com Node + jsdom)
├── docs/              # esta documentação, os docs LPS_*.md e o PDF compilado
├── Regras/            # regras de negócio (o "porquê"; citadas nos docstrings)
├── Telas/             # especificação das telas e do menu
├── manage.py  requirements.txt  package.json  render.yaml
├── .env.example       # modelo das variáveis de ambiente (o .env real não vai para o Git)
├── iniciar_lps.bat    # atalho para subir o servidor no Windows
└── atividade_arquivos/  db.sqlite3  staticfiles/    # gerados em execução, ignorados pelo Git
```

Os testes Python ficam ao lado do código de cada app (`<app>/tests.py` e
`<app>/test_*.py`); ver [11_TESTES.md](11_TESTES.md).
