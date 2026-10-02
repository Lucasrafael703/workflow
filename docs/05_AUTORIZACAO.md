# 05 — Autorização

> Como a LPS decide se uma pessoa pode fazer algo. O modelo é
> **SUJEITO + AÇÃO + ESCOPO + ORIGEM**: toda permissão é uma ação, vale em um
> escopo e tem uma origem explicável (um perfil ou uma concessão direta). Nega
> por padrão e não existe "negar explícito". Regras de produto em
> `Regras/05_USUARIOS_SETORES_E_AUTORIZACOES.md`; implementação em
> `acessos/`.

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

> `MINHAS_TAREFAS` olha só os **participantes**; o `responsavel` da tarefa não
> entra nesse conjunto.

O "endereço" de um recurso é montado por `ResourceContext.of(recurso)` em
`acessos/services.py`:

| Recurso | Endereço |
|---|---|
| `Activity` | org, empresa, setor designado, obra, centro de custo, dono |
| `Task` | setor da tarefa + resto da atividade + participantes ativos |
| `QueueEntry` | setor da fila + dados da atividade + participantes |
| `DeadlineProposal`, `DeadlineConflict` | o da tarefa |
| `Sector`, `Company`, `Site`, `CostCenter` | org + o próprio id |
| `IntakeItem` (Caixa de Entrada) | org + **setor sugerido** + obra sugerida. Sem setor sugerido só casam escopos de organização |
| `Board`, `BoardGroup`, `BoardColumn`, `BoardColumnOption`, `BoardItem`, `BoardCell` (quadros) | **só a org** (o quadro não pertence a um setor) |
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

Outras funções úteis de `AuthorizationService`:

| Função | Uso |
|---|---|
| `require(user, key, resource)` | Levanta `AuthorizationError` com mensagem legível. |
| `grants_for(user, key, resource)` | Lista de `Grant` com a origem de cada permissão. |
| `explain(user, key, resource)` | Motivos em texto ("Perfil: Gestor de Setor · Escopo: Setor Compras"). |
| `effective_actions(user)` | Todas as ações da pessoa com origem — usado nas telas de segurança. |
| `can_anywhere(user, key)` | Permitido em algum lugar (org ou algum setor)? Usado para menus e listas. |
| `accessible_sector_ids(user, key)` | Setores em que a ação vale. |

Os escopos de setor são memoizados na instância do usuário; qualquer mudança
em `UserSector` invalida o cache via signal (`invalidate_sector_cache`).

---

## 4. Onde a verificação acontece

| Camada | Mecanismo |
|---|---|
| Views de `core` (cadastros, usuários, segurança) | `ActionRequiredMixin` com `required_action = catalog.X`. Deve vir **depois** de `OrganizationRequiredMixin` nas bases. Nega com `PermissionDenied`. Escopo padrão: organização (`get_scope_object()` retorna `None`). |
| Serviços de `activities` | `require_action(user, catalog.X, recurso)` no início de cada método; converte a negação em `ActivityError`. |
| Serviços de `processes` | `_require(...)` com endereço org + empresa; levanta `ProcessError`. |
| Aplicar processo (`ProcessApplicationService.apply`) | `require_action(user, PROCESSO_APLICAR, atividade)` — o recurso é a **atividade**, então escopos de empresa, setor designado, obra, centro de custo e "minhas atividades" valem. Ver a seção 4.1. |
| Inputs e critérios do processo aplicado (`ActivityProcessService`) | Sem ação nova: `ActivityProcessService.can_update` aceita quem pode `demanda.editar` na atividade, o dono e quem é responsável/participante de alguma tarefa dela (mesmo critério do checklist da tarefa), sempre dentro da organização e nunca em atividade encerrada. |
| Caixa de Entrada (`IntakeService`) | `entrada.registrar` e `entrada.visualizar` na **porta** da tela usam `can_anywhere` (`AnywhereActionMixin`, em `intake/views.py`): registrar não tem setor ainda, e `ActionRequiredMixin` só olharia o escopo de organização e negaria quem cuida de um setor. Itens: `entrada.triar` / `entrada.visualizar` sobre o próprio `IntakeItem` (outro tenant = 404, sem a ação = 403). A lista é filtrada por `IntakeService.visible_queryset`. Ver a seção 4.2. |
| Menu lateral | `acessos.context_processors.navigation` — **só UX**, não protege nada. |

Algumas ações do catálogo ainda não são verificadas em nenhum ponto (ex.:
`demanda.visualizar`) — ver
[13_PENDENCIAS_CONHECIDAS.md](13_PENDENCIAS_CONHECIDAS.md).

### 4.1 `processo.aplicar` × `tarefa.criar`

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
| `quadro.editar` | Renomear o quadro, **gerir grupos** (criar, renomear, cor, mover, excluir vazio) e **gerir visualizações** (criar, renomear, configurar e excluir Kanbans). | não |
| `quadro.excluir` | Excluir o quadro inteiro. | **sim** |
| `quadro.gerir_colunas` | Criar, renomear, redimensionar, reordenar, configurar, ocultar, duplicar, **converter** e excluir colunas; gerir etiquetas. | não |
| `quadro.criar_item` | Adicionar item a um grupo. | não |
| `quadro.editar_item` | Renomear item, **mover** (de grupo e de posição) e preencher células. | não |
| `quadro.excluir_item` | Excluir item. | não |

- **Escopo só de organização.** O quadro não tem setor, então `ResourceContext.of` devolve só a organização e as ações
  valem para a organização inteira; um escopo de setor concedido a `quadro.*` **não** casa (a lista dá 403 e o menu não
  mostra "Quadros", que usa `can` com `ResourceContext.for_new(org)`, a mesma pergunta da lista). Quem quiser
  quadros por setor precisa de uma decisão nova (doc 13, F31).
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

---

## 5. Administração pela interface

| Tela | URL | Ação exigida |
|---|---|---|
| Matriz de permissões (perfis × ações) | `/permissoes/` | `seguranca.gerir_perfis` |
| Salvar ações de um perfil | `/permissoes/<pk>/salvar/` | `seguranca.gerir_autorizacoes` |
| Criar/editar perfil | `/perfis/novo/`, `/perfis/<pk>/` | `seguranca.gerir_perfis` |
| Acessos de uma pessoa (perfis e concessões, com origem) | `/usuarios/<pk>/acessos/` | `seguranca.gerir_autorizacoes` |
| Concessão direta | `/usuarios/<pk>/concessoes/` | `seguranca.gerir_autorizacoes` |

Todas as alterações passam por `AccessService` e são auditadas
(`PROFILE_CREATED`, `PROFILE_ASSIGNED`, `ACTION_GRANTED` etc., com
`target_user`). `AccessService.set_profile_actions` só altera as ações que
estavam **visíveis** na tela, para um filtro na matriz não apagar o resto.

---

## 6. Perfis sugeridos

Criados por `seed_lps_demo` a partir de `SUGGESTED_PROFILES`. São ponto de
partida — a organização pode renomear e alterar (doc 05 §11).

| Perfil | Resumo |
|---|---|
| **Colaborador** | Ver e criar atividades; assumir e marcar pendente; executar tarefas (assumir, aceitar, recusar, iniciar, pausar, retomar, concluir, devolver, bloquear); ver a própria posição na fila; propor/aceitar/recusar prazo; conversar; ver e aplicar processos; gerir clientes; registrar solicitações na Caixa de Entrada (`entrada.registrar`). |
| **Gestor de Setor** | Tudo do Colaborador + ver todas as atividades, editar, aprovar pendência; criar/editar/atribuir tarefas, mover de setor, **reabrir tarefa concluída (`tarefa.reabrir`)**, lançar tempo manual; fila completa e reordenar; resolver conflito de prazo; métricas e auditoria; todas as ações de processo; estágios, tags e cores; ver, registrar e triar a Caixa de Entrada (`entrada.*`). |
| **Administrador** | Todas as ações do catálogo. |

> **Ação nova em organização já implantada:** `seed_acoes` cria a ação no
> catálogo, mas **não** a acrescenta a perfis que já existem no banco — nem ao
> Administrador. Depois de rodar `seed_acoes`, marque `tarefa.reabrir` nos
> perfis que devem ter (Matriz de permissões, `/permissoes/`). Rodar
> `seed_lps_demo` de novo também a acrescentaria, mas ele re-adiciona **todas** as
> ações sugeridas (desfazendo remoções feitas de propósito) e recria setores de
> demonstração que faltarem — não use em produção. Reabrir uma tarefa
> de atividade já concluída também exige `demanda.reabrir` (hoje só no
> Administrador). Ver [06_ATIVIDADES_E_TAREFAS.md](06_ATIVIDADES_E_TAREFAS.md) §2.11.

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
