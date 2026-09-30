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
| `accounts`, `audit`, `processes` | 0 | `tests.py` vazio |

Além disso, `tests/checklist.test.cjs` testa o componente JavaScript do
checklist (seção 4).

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
início.

### Falhas conhecidas

`core.tests.UserFormAjaxTests.test_ajax_request_returns_json_without_redirect`
e `test_non_ajax_request_still_redirects` falham: o payload de teste não envia
`password1`/`password2`, que são obrigatórios ao criar usuário. O teste está
desatualizado, não o código. Ver
[13_PENDENCIAS_CONHECIDAS.md](13_PENDENCIAS_CONHECIDAS.md).

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
