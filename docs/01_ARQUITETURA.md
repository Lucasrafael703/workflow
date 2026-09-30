# 01 — Arquitetura

> Visão geral de como o código da LPS está organizado: quais apps existem, o que
> cada um faz, como as camadas se relacionam e quais convenções o código segue.
> As regras de negócio que motivam cada decisão estão em `Regras/`; os
> docstrings do código citam essas seções (ex.: "Regras 05 §43").

---

## 1. Apps

O projeto Django fica em `config/` (settings, urls, wsgi/asgi). Os apps de
negócio estão na raiz:

| App | Responsabilidade | Principais arquivos |
|---|---|---|
| `core` | Tenant (`Organization`) e cadastros da organização: empresas, setores, obras, clientes, centros de custo, tags, estágios de Kanban, cores e rótulos de status. Também hospeda as telas de usuários e de segurança e os mixins base. | `models.py`, `services.py`, `mixins.py`, `colors.py`, `sanitize.py`, `widgets.py` |
| `accounts` | Identidade: `Profile` (1:1 com `User`, liga a pessoa a uma organização), participação em setores (`UserSector`), cadastro com confirmação de e-mail, login por e-mail. | `models.py`, `auth_backends.py`, `forms.py`, `signals.py`, `views.py` |
| `acessos` | Motor de autorização: catálogo de ações, perfis de acesso, escopos, concessões. Responde "quem pode fazer o quê, onde e por quê". Não tem telas próprias (ficam em `core`). | `catalog.py`, `models.py`, `services.py`, `testing.py` |
| `activities` | Núcleo operacional: atividades, tarefas, fila por setor, negociação de prazo, bloqueios, devoluções, sessões de trabalho, checklist, anexos, mensagens com @menções. | `models.py`, `services.py`, `views.py`, `templatetags/lps.py` |
| `processes` | Modelos de processo reutilizáveis e versionados (inputs, output, critérios de aceite, fluxo por setor). | `models.py`, `services.py`, `views.py` |
| `notifications` | Notificações in-app, caixa de entrada com categorias, e-mails síncronos. | `models.py`, `services.py`, `recipients.py`, `views.py` |
| `audit` | `AuditLog`: trilha de auditoria somente-inclusão de eventos de negócio e de segurança. | `models.py`, `services.py` |
| `painel` | Telas "em construção" que mantêm o menu lateral fiel a `Telas/MENU_E_SUBMENUS_LPS.md`, mais duas telas de configuração emprestadas de `core`. | `views.py`, `urls.py` |

As pastas `demands/` e `workflows/` são restos de uma versão anterior: não
estão em `INSTALLED_APPS` e não têm código (ver
[13_PENDENCIAS_CONHECIDAS.md](13_PENDENCIAS_CONHECIDAS.md)).

### Dependências entre apps

Levantado a partir dos imports (fora de testes e migrations) e das FKs entre
apps:

| App | Usa |
|---|---|
| `audit` | nenhum app (só FKs para `activities` e `User`) |
| `accounts` | `acessos` (invalidação de cache); FKs para `core` |
| `painel` | `core` |
| `processes` | `acessos`, `core` |
| `notifications` | `accounts`; FKs para `activities` |
| `acessos` | `accounts`, `activities`, `audit`, `core` |
| `core` | `accounts`, `acessos`, `activities`, `audit` |
| `activities` | `acessos`, `audit`, `core`, `notifications`; FK para `processes` |

Há dependências circulares (`core` ↔ `acessos` ↔ `activities`). Elas são
resolvidas com imports **dentro das funções** e FKs por string
(`"core.Organization"`). Ao mover código entre apps, mantenha esse padrão para
não criar erro de import circular na inicialização.

---

## 2. Camadas

```
URL → View (fina) → Service (regra + autorização + auditoria + notificação) → Model
```

- **Views** resolvem a organização, carregam objetos já filtrados por ela,
  validam o formulário e chamam um serviço. Views de ação herdam de
  `ServiceActionView` (em `activities/views.py`): chamam o serviço, convertem
  o erro em mensagem (`django.contrib.messages`) e redirecionam.
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
| `ActivityError` | `activities/services.py` |
| `CadastroError` | `core/services.py` |
| `ProcessError` | `processes/services.py` |
| `AuthorizationError` | `acessos/services.py` (convertida em `ActivityError` por `require_action`) |

---

## 3. Multi-tenancy

`core.Organization` é o tenant. Tudo pertence a uma organização:

1. Uma pessoa pertence a **uma** organização via `accounts.Profile.organization`
   (Regras 05 §7). O `Profile` é criado vazio por signal quando o `User` é
   criado; quem define a organização é um administrador (tela `/usuarios/`).
2. Cadastros e registros de acesso têm FK `organization`. `Activity` tem FK
   direta; `Task` herda pela atividade; `QueueEntry`, pelo setor.
3. `core.mixins.OrganizationRequiredMixin` resolve `self.organization` em toda
   view da LPS. Sem organização, redireciona para `/accounts/me/` com a
   mensagem "Seu usuário ainda não está vinculado a uma organização".
4. As views filtram tudo por `organization=self.organization`
   (ou `activity__organization=...`); objetos de outra organização dão 404.
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
- **Status × estágio.** `status` é o estado de negócio (fixo no código);
  `stage` é a coluna visual do Kanban (configurável por organização). Mover
  um card de estágio nunca altera o status.
- **Cores e rótulos** de status/urgência são configuráveis por organização
  (`core.EnumColor`) mas o **código** do enum nunca muda de significado; a
  resolução passa por `core.colors.EnumColorResolver`.
- **Idioma.** Interface, docstrings e mensagens em português; nomes de
  classes e funções em inglês; valores de enum em português maiúsculo
  (`EM_FILA`, `CONCLUIDA`).
