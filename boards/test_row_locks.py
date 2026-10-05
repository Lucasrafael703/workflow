"""Trava de linha que o SQLite não vê e o PostgreSQL recusa.

`select_for_update()` junto de `select_related()` de uma chave **anulável** vira `SELECT ... FOR UPDATE` sobre um
`LEFT OUTER JOIN`, e o PostgreSQL responde `FOR UPDATE cannot be applied to the nullable side of an outer join` (o SQLite
ignora o `FOR UPDATE`, então nenhum teste local acusa). Foi o que derrubou com 500 a criação e a edição de Demandas em
produção. A regra do projeto: com `select_related`, travar só a linha principal: `select_for_update(of=("self",))`.
"""

import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

SKIP = {".venv", "node_modules", "staticfiles", "tmp", "__pycache__", ".git", "migrations"}
# `select_for_update(...)` sem `of=` e, adiante na MESMA expressão, um `select_related(`
RISKY = re.compile(r"select_for_update\((?![^)]*\bof=)[^)]*\)(?:\s*\.\s*\w+\([^)]*\))*?\s*\.\s*select_related\(")


class RowLocksWithJoinsTests(SimpleTestCase):
    def test_a_locked_query_with_select_related_only_locks_its_own_row(self):
        offenders = []
        root = Path(settings.BASE_DIR)
        for path in root.rglob("*.py"):
            if SKIP & set(path.relative_to(root).parts) or path.name.startswith("test"):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for match in RISKY.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                offenders.append(f"{path.relative_to(root)}:{line}")
        self.assertEqual(offenders, [], "select_for_update() com select_related() precisa de of=(\"self\",) (PostgreSQL)")
