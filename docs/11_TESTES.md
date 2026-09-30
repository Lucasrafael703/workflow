# 11 — Testes

> Onde estão os testes, como rodá-los e como escrever novos seguindo o padrão
> do projeto.

---

## 1. Onde estão

Testes do Django ficam em cada app (`tests.py` e, em `activities`, também
`test_views.py`):

| Arquivo | Testes (aprox.) | Foco |
|---|---|---|
| `activities/tests.py` | 71 | Serviços: dono único, executores e tempo, sessões, devolução, fila, prazos, pendências, checklist, isolamento entre organizações |
| `activities/test_views.py` | 71 | Views: permissões por escopo, telas, Ajax, redirecionamentos |
| `acessos/tests.py` | 36 | Motor de autorização: escopos, perfis, concessões, teto de tenant |
| `core/tests.py` | 28 | Cadastros, busca de pessoas, formulário de usuário |
| `notifications/tests.py` | 23 | Destinatários, categorias, "ação necessária" |
| `processes/tests.py` | 22 | Molde: responsável padrão (tenant, ativo, fora do setor), versão publicada imutável, cópia na nova versão, editor de etapas |
| `activities/test_process_application.py` | 99 | Aplicação de processo: materialização (inputs, critérios, tarefas), validações que não gravam nada, dependências e liberação, inputs e critérios, trava de inputs obrigatórios, atomicidade, reaplicação, versões, isolamento entre organizações, finalização e o cenário de aceite completo |
| `activities/test_process_views.py` | 55 | Telas do processo: botão e popup "Aplicar processo", painel da ficha, progresso, atualização de inputs/critérios, finalização, tarefas que aguardam |
| `activities/test_reopen.py` | 44 | Reabrir tarefa e atividade concluídas: fila, histórico preservado, permissão por setor, motivo, tarefas seguintes, atividade concluída/cancelada, atomicidade, botões e popup |
| `activities/test_task_actions.py` | 88 | “Já realizei este trabalho”: período informado × conclusão agora, fila e sucessoras, auditoria, permissões (responsável/participante, sem exigir tempo manual), status, limites de data e justificativa, travas de dependência e de inputs do processo, atomicidade; botão, barra “Ações da tarefa” filtrada por permissão, popup (JSON), cartão de tempo cronometrado × informado |
| `activities/test_task_editor.py` | 78 | Editor da tarefa (uma transação: dados, marcadores, responsável, participantes e convites pendentes), Gerenciar dependência (ciclo, fila, tarefa já iniciada), motivo no tempo manual, origem do tempo na gestão, ações da tarefa em janela (JSON) e destaque do menu lateral em toda rota de tarefa |
| `accounts`, `audit` | 0 | `tests.py` vazio |

Base compartilhada dos testes de processo: `activities/testing.py`
(`ProcessTestCase`, com o cenário Orçamento v3: três setores/pessoas, três etapas
em sequência, três inputs e quatro critérios) e `processes/testing.py`
(`build_process`, que monta e publica um molde direto pelo ORM).

Além disso, `tests/checklist.test.cjs` testa o componente JavaScript do
checklist, `tests/process-apply.test.cjs`, o assistente de 4 passos do popup
"Aplicar processo", e `tests/retroactive-work.test.cjs`, o popup "Já realizei este
trabalho" (aviso de dia anterior e comentário só quando necessário) (seção 4).

---

## 2. Rodando

```powershell
python manage.py test                                      # tudo
python manage.py test activities                           # um app
python manage.py test activities.test_views                # um módulo
python manage.py test activities.test_views.TaskChecklistViewTests   # uma classe
python manage.py test core.tests.UserFormAjaxTests.test_non_ajax_request_still_redirects  # um teste
```

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
assim como a interface atual. Os testes de atividades estão também em
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
variável `PYTHON`) e executa `static/js/checklist.js` no jsdom. Precisa de
Node 18+; o jsdom é instalado numa pasta temporária, sem criar
`package.json` no projeto:

```powershell
$checklistDeps = Join-Path $env:TEMP 'lps-checklist-test-deps'
npm install --prefix $checklistDeps --no-save --package-lock=false --ignore-scripts jsdom@26.1.0
$env:NODE_PATH = Join-Path $checklistDeps 'node_modules'
node --test tests/checklist.test.cjs
```

Rode a partir da raiz do repositório. O jsdom não valida layout nem o envio
por Enter do navegador — confira também manualmente (ver `tests/README.md`).
