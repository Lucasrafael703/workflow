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
| Menu lateral | `acessos.context_processors.navigation` — **só UX**, não protege nada. |

Algumas ações do catálogo ainda não são verificadas em nenhum ponto (ex.:
`atividade.visualizar`) — ver
[13_PENDENCIAS_CONHECIDAS.md](13_PENDENCIAS_CONHECIDAS.md).

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
| **Colaborador** | Ver e criar atividades; assumir e marcar pendente; executar tarefas (assumir, aceitar, recusar, iniciar, pausar, retomar, concluir, devolver, bloquear); ver a própria posição na fila; propor/aceitar/recusar prazo; conversar; ver e aplicar processos; gerir clientes. |
| **Gestor de Setor** | Tudo do Colaborador + ver todas as atividades, editar, aprovar pendência; criar/editar/atribuir tarefas, mover de setor, lançar tempo manual; fila completa e reordenar; resolver conflito de prazo; métricas e auditoria; todas as ações de processo; estágios, tags e cores. |
| **Administrador** | Todas as ações do catálogo. |

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
