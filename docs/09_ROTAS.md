# 09 — Rotas

> Referência de todas as URLs. A coluna "Ação" indica a ação do catálogo
> verificada **na view** (`ActionRequiredMixin` ou `dispatch`); em
> `activities`, a maioria das verificações acontece dentro do serviço chamado —
> ver [06_ATIVIDADES_E_TAREFAS.md](06_ATIVIDADES_E_TAREFAS.md). Toda view da LPS
> exige login e organização (`OrganizationRequiredMixin`), exceto login,
> cadastro, confirmação de e-mail e recuperação de senha.

---

## 1. Raiz (`config/urls.py`)

| Caminho | Nome | Destino |
|---|---|---|
| `admin/` | — | Admin do Django |
| `accounts/login/` | `login` | `LoginView` + `EmailAuthenticationForm` |
| `accounts/logout/` | `logout` | `LogoutView` |
| `accounts/esqueci-senha/`, `.../enviado/` | `password_reset`, `password_reset_done` | views nativas |
| `accounts/redefinir-senha/<uidb64>/<token>/`, `.../concluido/` | `password_reset_confirm`, `password_reset_complete` | views nativas |
| `accounts/` | | `accounts.urls` |
| `notificacoes/` | | `notifications.urls` |
| `processos/` | | `processes.urls` |
| `painel/` | | `painel.urls` |
| `entrada/` | | `intake.urls` (só com `INTAKE_ENABLED`; desligado, 404 em todas as rotas) |
| `` | | `core.urls`, depois `activities.urls` |
| `media/<path>` | | `static.serve` de `MEDIA_ROOT` (sem login) |
| `demanda-arquivos/<path>` | | `static.serve` de `ACTIVITY_FILES_ROOT` (sem login) |
| `atividade-arquivos/<path>` | `legacy-activity-files` | Endereço de antes de 01/10/2026: redireciona (301) para `demanda-arquivos/<path>`; se a pasta do código já foi renomeada, troca `ATV-…` por `DEM-…` |

## 2. `accounts` (`/accounts/`)

| Caminho | Nome | Função |
|---|---|---|
| `me/` | `profile` | Meu perfil (telefone, setor principal) |
| `criar-conta/` | `signup` | Autocadastro |
| `confirmar-email/` | `verify-email` | Digitar o código |
| `confirmar-email/reenviar/` | `verify-email-resend` | Reenviar código (POST) |
| `confirmar-email/alterar/` | `verify-email-change` | Trocar o e-mail pendente |

## 3. `core` (`/`)

**APIs de busca** (JSON, filtradas pela organização): `api/pessoas/`
(`person-search`, aceita `?sector=`), `api/clientes/` (`client-search`),
`api/setores/` (`sector-search`), `api/empresas/` (`company-search`),
`api/obras/` (`site-search`), `api/centros-de-custo/` (`costcenter-search`),
`api/tags/` (`tag-search`).

**Cadastros**

| Caminho | View | Ação |
|---|---|---|
| `cadastros/` (`?tab=`) | `CadastroHomeView` (`cadastros`) | — |
| `cadastros/setores/novo/`, `<pk>/` | `SectorFormView` | `setor.editar` |
| `cadastros/empresas/nova/`, `<pk>/` | `CompanyFormView` | `empresa.gerir` |
| `cadastros/obras/nova/`, `<pk>/` | `SiteFormView` | `obra.gerir` |
| `cadastros/centros-de-custo/novo/`, `<pk>/` | `CostCenterFormView` | `centro_custo.gerir` |
| `cadastros/clientes/novo/`, `<pk>/` | `ClientFormView` (também em popup) | `cliente.gerir` |
| `cadastros/motivos/novo/`, `<pk>/` | `ReturnReasonFormView` | `motivo_devolucao.gerir` |
| `cadastros/estagios-de-tarefa/novo/`, `<pk>/` | `TaskStageFormView` | `estagio_tarefa.gerir` |
| `cadastros/estagios-de-tarefa/reordenar/` | `TaskStageReorderView` | `estagio_tarefa.gerir` |
| `cadastros/tags/novo/`, `<pk>/` | `TagFormView` | `tag.gerir` |
| `cadastros/<tab>/<pk>/situacao/` | `CadastroToggleActiveView` (`cadastro-toggle`) | a da aba |
| `cadastros/<tab>/<pk>/cor/` | `SwatchColorSaveView` (`cadastro-color-save`) | a da aba |

**Configurações**

| Caminho | View | Ação |
|---|---|---|
| `configuracoes/` | `SettingsView` (`settings`) — preferências de notificação (guardadas na sessão) | — |
| `configuracoes/estagios-de-demanda/novo/`, `<pk>/` | `ActivityStageFormView` | `estagio_tarefa.gerir` |
| `configuracoes/estagios-de-atividade/<resto>` | `legacy-activity-stages` | Endereço antigo: redireciona (301; 308 em POST) para `estagios-de-demanda/<resto>` |
| `configuracoes/status/<domain>/novo/`, `<pk>/` | `WorkflowStatusFormView` | `cor_status.gerir` |
| `configuracoes/status/<domain>/<code>/editar/` | `EnumColorLabelFormView` (`enumcolor-label-edit`) | — |
| `configuracoes/cores/<domain>/salvar/` | `EnumColorSaveView` (`enumcolor-save`) | — |
| `configuracoes/cores/<domain>/restaurar/` | `EnumColorResetView` (`enumcolor-reset`) | — |
| `configuracoes/fluxo/<kind>/<pk>/excluir/` | `FlowConfigDeleteView` (`flow-config-delete`) | depende do tipo |

**Usuários e segurança**

| Caminho | View | Ação |
|---|---|---|
| `usuarios/` | `UserListView` (`user-list`) | `usuario.visualizar` |
| `usuarios/novo/`, `<pk>/` | `UserFormView` (`user-create`, `user-edit`) | `usuario.editar` |
| `usuarios/<pk>/acessos/` | `UserAccessView` (`user-access`) | `seguranca.gerir_autorizacoes` |
| `usuarios/<pk>/acessos/<assignment_pk>/remover/` | `UserAccessRemoveView` | `seguranca.gerir_autorizacoes` |
| `usuarios/<pk>/concessoes/` | `UserGrantActionView` (`user-grant`) | `seguranca.gerir_autorizacoes` |
| `usuarios/<pk>/concessoes/<grant_pk>/remover/` | `UserGrantRemoveView` | `seguranca.gerir_autorizacoes` |
| `permissoes/` | `PermissionMatrixView` (`permissions`) | `seguranca.gerir_perfis` |
| `permissoes/<pk>/salvar/` | `PermissionUpdateView` (`permissions-update`) | `seguranca.gerir_autorizacoes` |
| `perfis/novo/`, `<pk>/` | `ProfileFormView` | `seguranca.gerir_perfis` |

## 4. `activities` (`/`)

**Início e visões gerais**

| Caminho | Nome | Função |
|---|---|---|
| `` | `home` | "O que precisa da minha atenção agora?" |
| `fila/`, `fila/<sector_pk>/` | `queue`, `queue-sector` | Fila do setor |
| `fila/entrada/<pk>/reordenar/` | | Reordenar (`fila.reordenar` no serviço) |
| `gestao/` | `management` | Gestão por exceção (`metricas.visualizar` em algum escopo) |
| `historico/` | `history` | Histórico de auditoria (`?event=`) |

**Demandas** (`Activity`; o endereço era `demandas/…` até 01/10/2026)

| Caminho | Função |
|---|---|
| `atividades/<resto>` (`legacy-activities`) | Redireciona (301; **308** em POST, que mantém o método) para `demandas/<resto>`, com a consulta (`?tab=…`). Sem login. Cobre todas as rotas abaixo |
| `demandas/` (`activity-list`) | Lista com abas e filtros. A busca `?q=` também aceita o código antigo (`ATV-2026-00007` acha `DEM-2026-00007`) |
| `demandas/nova/` (`activity-create`) | Janela de 3 etapas de criação (e rascunho antigo). JSON no Ajax: `{redirect_url}` ou `400 {errors}` |
| `demandas/<pk>/nova/contexto/`, `.../detalhes/`, `.../descartar/` | GET das etapas antigas redireciona ao editor; POST legado compatível; descartar rascunho |
| `demandas/nova-rapida/` | Mesmo editor no seletor; resposta JSON em Ajax |
| `demandas/busca/` | Busca de atividades abertas (JSON) |
| `demandas/kanban/` (`activity-kanban`), `demandas/calendario/` | Quadro por etapas de um setor (`activities/kanban.py`), calendário por prazo |
| `demandas/<pk>/` (`activity-detail`) | Ficha da atividade (rascunho redireciona ao editor) |
| `demandas/<pk>/painel/` | Compatibilidade: redireciona à ficha completa |
| `demandas/<pk>/editar/`, `prazo/`, `dono/`, `assumir/` | Editar (a mesma janela de 3 etapas), prazo, trocar dono, assumir |
| `demandas/<pk>/finalizar/`, `concluir/`, `cancelar/`, `reabrir/` | Encerramento e reabertura |
| `demandas/<pk>/processo/aplicar/` (`activity-process-apply`) | Popup "Aplicar processo" — GET mostra os 4 passos (403 sem `processo.aplicar`; redireciona se a atividade já tem processo); POST aplica (JSON `{"redirect_url"}` ou `{"errors"}` no Ajax; redirect sem JS) |
| `demandas/<pk>/processo/inputs/<input_pk>/` (`activity-input-update`) | POST: registrar/corrigir (`value`, `is_received`) ou reabrir (`clear`) um input do processo aplicado |
| `demandas/<pk>/processo/criterios/<check_pk>/` (`activity-criterion-update`) | POST: marcar/desmarcar (`is_met`) um critério de aceite |
| `demandas/<pk>/pendente/`, `pendencia/aprovar/` | Pendência |
| `demandas/<pk>/mensagem/`, `continuar/` | Mensagem; comentário + anexo num envio |
| `demandas/<pk>/anexos/`, `anexos/<attachment_pk>/remover/` | Anexos |
| `demandas/<pk>/mover-estagio/` | Mudar coluna do Kanban (só `stage`) |
| `demandas/<pk>/gaveta/` (`activity-kanban-drawer`) | Gaveta da demanda aberta a partir do quadro (fragmento; rascunho e outra organização dão 404) |
| `demandas/<activity_pk>/tarefas/rapida/` (`task-quick-create`) | Nova tarefa na atividade (Ajax) |

**Tarefas**

| Caminho | Função |
|---|---|
| `tarefas/` (`task-list`), `tarefas/kanban/` (`task-kanban`), `tarefas/calendario/` | Lista, quadro por etapas de um setor, calendário |
| `tarefas/nova-rapida/` | Nova tarefa com seletor de atividade (a busca `demandas/busca/`, `activity-search`, devolve também `summary`: título e "Cliente • Setor • N tarefas", que a janela mostra como cartão) |
| `tarefas/<pk>/` (`task-detail`), `tarefas/<pk>/painel/` | Ficha, painel lateral |
| `tarefas/<pk>/editar/` (`task-edit`) | Editor único: dados, prazo pedido, marcadores, responsável e participantes (`tarefa.editar` na view, já no GET; responsável e participantes exigem as suas ações no serviço). Janela (JSON no Ajax) ou página |
| `tarefas/<pk>/dependencia/` (`task-dependency`) | Gerenciar dependência (`tarefa.editar` na view). Janela (JSON no Ajax) ou página |
| `tarefas/<pk>/assumir/`, `iniciar/`, `pausar/`, `retomar/`, `concluir/`, `desbloquear/` | Ações de execução (`task-assume`, `task-start`...) |
| `tarefas/<pk>/iniciar/ajax/`, `pausar/ajax/`, `concluir/ajax/` | Mesmas ações em JSON, para o painel |
| `tarefas/<pk>/bloquear/` | Bloquear (`tarefa.bloquear` na view). **Todas as ações de formulário abaixo (devolver, bloquear, mover, cancelar, reabrir, já realizei, tempo, prazo, dependência) respondem JSON quando chamadas com `X-Requested-With`** |
| `tarefas/<pk>/devolver/` | Devolver (`tarefa.devolver` na view) |
| `tarefas/<pk>/mover/` | Outro setor (`tarefa.mover_setor` na view) |
| `tarefas/<pk>/cancelar/` | Cancelar (`tarefa.cancelar` na view) |
| `tarefas/<pk>/reabrir/` (`task-reopen`) | Reabrir tarefa concluída (`tarefa.reabrir` na view; motivo obrigatório). Popup (JSON no Ajax) ou página; 403 sem a ação |
| `tarefas/<pk>/executores/`, `executores/<user_pk>/remover/` | Participantes |
| `tarefas/<pk>/alterar-responsavel/` | Responsável |
| `tarefas/<pk>/atribuicoes/<assignment_pk>/aceitar/`, `.../recusar/` | Responder atribuição |
| `tarefas/<pk>/ja-realizei/` (`task-retroactive`) | “Já realizei este trabalho”: informa data, início, fim e motivo; registra o período e conclui a tarefa agora (`tarefa.concluir` na view; além disso só responsável ou participante no serviço). Popup (JSON no Ajax) ou página; 403 sem a ação |
| `tarefas/<pk>/tempo/` | “Adicionar tempo trabalhado” (`tempo.lancar_manual`): só acrescenta tempo, não conclui |
| `tarefas/<pk>/mensagem/` | Mensagem |
| `tarefas/<pk>/mover-estagio/` | Mudar coluna do Kanban (só `stage`) |

**Quadro Kanban — ações** (`activities/kanban_urls.py`; `<dom>` é `demandas` ou `tarefas`, outro valor dá 404). Todas exigem login e organização e respondem JSON; as que gravam passam pelos services e devolvem o cartão novo em `card_html`:

| Caminho | Nome | Função |
|---|---|---|
| `kanban/<dom>/<pk>/cartao/` | `kanban-card` | GET: o cartão como está agora, ou `{"visible": false}` se saiu do quadro. Usa a consulta da URL (setor e filtros) |
| `kanban/<dom>/<pk>/etapa/` | `kanban-set-stage` | POST `stage_id`: grava só a etapa. 403 se o serviço recusa (outro setor, inativa, sem ação); 400 se vazio; 404 se a etapa é de outro tipo ou organização |
| `kanban/<dom>/<pk>/condicao/` | `kanban-set-condition` | POST `condition_id` (vazio remove a condição): grava só a condição |
| `kanban/demandas/criar/` | `kanban-create-card` | POST `title`, `sector_id`, `stage_id`: cria a demanda na coluna (201). Tarefa não se cria aqui (400) |
| `kanban/<dom>/limite/` | `kanban-column-limit` | POST `stage_id`, `limit` (1 a 999; vazio remove): exige `etapa.gerir` no setor |
| `kanban/<dom>/opcoes/` | `kanban-create-option` | POST `kind` (`stage` \| `condition`), `name`, `color`, `sector_id`: nova etapa/condição do setor; exige `etapa.gerir` / `condicao.gerir` |
| `api/setores/<pk>/etapas/`, `.../condicoes/` | `sector-stage-options`, `sector-condition-options` | GET `?dominio=demanda\|tarefa`: as opções do setor que alimentam os seletores |
| `tarefas/<pk>/checklist/`, `checklist/<pk>/alternar/`, `checklist/<pk>/remover/` | Checklist |
| `tarefas/<pk>/prazo/propor/`, `prazos/<pk>/aceitar/`, `prazos/<pk>/recusar/`, `conflitos/<pk>/resolver/` | Prazo e conflito |

## 5. `processes` (`/processos/`)

`` (`process-list`), `novo/` (`process-create`), `<pk>/` (`process-edit`),
`<pk>/informacoes/`, `<pk>/output/`, `<pk>/inputs/` (+ `<input_pk>/remover/`),
`<pk>/criterios/` (+ `<criterion_pk>/remover/`), `<pk>/fluxo/`
(+ `reordenar/`, `<step_pk>/remover/`, `<step_pk>/responsavel/` — define ou limpa
o responsável padrão de uma etapa do rascunho, `process-step-responsavel`),
`<pk>/publicar/`, `<pk>/nova-versao/`, `<pk>/ativo/`. Autorização nos serviços
(`processo.*`). **Aplicar** um processo é uma rota de atividade (seção 4).

## 6. `notifications` (`/notificacoes/`)

| Caminho | Nome | Função |
|---|---|---|
| `` | `notification-list` | Caixa com abas (`?filter=`), busca e paginação |
| `<pk>/read/` | `notification-mark-read` | Marca lida e redireciona para um destino interno validado |
| `mark-all-read/` | | Marca todas |

## 6.1 `intake` (`/entrada/`) — Caixa de Entrada

**Inativa por padrão:** com `INTAKE_ENABLED` desligado (ver [03_CONFIGURACAO.md](03_CONFIGURACAO.md)) toda rota abaixo
responde 404 (o decorador `only_when_enabled`, em `intake/urls.py`, olha a chave a cada pedido) e o item "Entrada" não
aparece no menu.

Nomes de rota são globais (o projeto não usa `app_name`), por isso o prefixo `intake-`. Todas
exigem login e organização; item de outra organização dá 404, sem a ação dá 403 (seção 4.2 de
[05_AUTORIZACAO.md](05_AUTORIZACAO.md)). As telas de formulário abrem em janela (`LPSModal`) e
também funcionam como página; com `X-Requested-With: XMLHttpRequest` respondem JSON.

| Caminho | Nome | Método | Ação | Resposta |
|---|---|---|---|---|
| `` | `intake-list` | GET | `entrada.visualizar` (em algum lugar) | Abas `?status=novos\|convertidos\|ignorados`, busca `?q=`, `?page=` (25 por página) |
| `registrar/` | `intake-capture` | GET/POST | `entrada.registrar` (em algum lugar) | Sucesso: `{"message", "redirect_url"}` |
| `<pk>/` | `intake-detail` | GET | `entrada.visualizar` no item | Texto original, o que a LPS entendeu e histórico |
| `<pk>/editar/` | `intake-edit` | GET/POST | `entrada.triar` no item | Sucesso: `{"message", "html" (cartão novo), "target": "#intake-item-<pk>"}` |
| `<pk>/criar-demanda/` | `intake-convert` | GET/POST | `entrada.triar` no item (+ `demanda.criar` no serviço) | Sucesso: `{"message", "redirect_url": atividade}` |
| `<pk>/ignorar/` | `intake-ignore` | GET/POST | `entrada.triar` no item | Sucesso: `{"message", "remove": "#intake-item-<pk>"}` |
| `<pk>/restaurar/` | `intake-restore` | só POST | `entrada.triar` no item | Sucesso: `{"message", "remove"}`; erro: `400 {"error"}` |

- Formulário inválido: `400 {"errors": {campo: [mensagens]}}`; erro de regra aparece em `__all__`.
- Editar, criar demanda e ignorar numa solicitação que já foi tratada redireciona para o detalhe
  com a mensagem "Esta solicitação já foi tratada.".
- Todos os nomes `intake-*` estão em `_NAV_BY_URL_NAME` (item "Entrada" ativo no menu); um teste
  confere.

## 7. `painel` (`/painel/`)

Telas em branco ("em construção") que mantêm o menu completo:
`equipe/pessoas/`, `equipe/capacidade/`, `equipe/carga-de-trabalho/`,
`filas-e-gargalos/filas/`, `.../gargalos/`, `.../bloqueios/`, `.../devolucoes/`,
`processos/modelos/`, `insights/`, `desenvolvimento/`, `resultados/`,
`integracoes/`, `configuracoes/motivos-de-bloqueio/`,
`configuracoes/motivos-de-devolucao/`.

Telas reais, com views de `core`:

| Caminho | Nome | Ação |
|---|---|---|
| `configuracoes/etapas-e-status/` | `config-etapas-status` | `estagio_tarefa.gerir` ou `cor_status.gerir`, conforme a aba |
| `configuracoes/prioridades/` | `config-prioridades` | `cor_prioridade.gerir` |

Para listar as rotas de verdade a qualquer momento:

```powershell
python manage.py shell -c "from django.urls import get_resolver; [print(p) for p in get_resolver().reverse_dict.keys() if isinstance(p, str)]"
```
