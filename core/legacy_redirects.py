"""Endereços antigos que ainda chegam (favoritos, e-mails, links gravados em descrições e comentários).

Em 01/10/2026 a "Atividade" virou "Demanda" também no endereço das páginas e no código gerado. Os
endereços antigos não podem dar 404: cada um manda para o novo, mantendo o resto do caminho e a
consulta (`?tab=…`).
"""

import os
import re

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.http import HttpResponseRedirect
from django.utils._os import safe_join
from django.views import View


class HttpResponsePermanentRedirectKeepMethod(HttpResponseRedirect):
    """308: como o 301, mas o navegador repete o mesmo método (um formulário aberto antes da troca
    e enviado depois não vira um GET sem dados)."""

    status_code = 308


def _permanent_redirect(request, target):
    query = request.META.get("QUERY_STRING", "")
    if query:
        target = f"{target}?{query}"
    if request.method in ("GET", "HEAD"):
        response = HttpResponseRedirect(target)
        response.status_code = 301
        return response
    return HttpResponsePermanentRedirectKeepMethod(target)


class MovedPrefixView(View):
    """`<prefixo antigo><resto>` → `<new_prefix><resto>`. O destino sempre começa por `new_prefix`
    (um caminho do próprio site), então o `resto` nunca escolhe outro domínio."""

    new_prefix = ""

    def dispatch(self, request, *args, **kwargs):
        return _permanent_redirect(request, f"{self.new_prefix}{kwargs.get('rest', '')}")


# `ATV-AAAA-NNNNN` é o código de antes da troca; vira `DEM-AAAA-NNNNN` (ver activities/models.py).
OLD_CODE_SEGMENT = re.compile(r"(^|/)ATV-(\d{4}-\d{5})(?=/)")


class MovedActivityFileView(View):
    """`/atividade-arquivos/<empresa>/ATV-…/<arquivo>` → `/demanda-arquivos/…`. Se a pasta do código já
    foi renomeada para `DEM-…` (migração `activities/0020`), o destino usa o código novo; se o
    arquivo ficou na pasta antiga (a migração não conseguiu movê-lo), o destino mantém o caminho."""

    def dispatch(self, request, *args, **kwargs):
        rest = kwargs.get("rest", "")
        renamed = OLD_CODE_SEGMENT.sub(r"\1DEM-\2", rest)
        target = renamed if renamed != rest and self._is_stored(renamed) else rest
        return _permanent_redirect(request, f"{settings.ACTIVITY_FILES_URL}{target}")

    @staticmethod
    def _is_stored(relative_path):
        try:
            return os.path.isfile(safe_join(settings.ACTIVITY_FILES_ROOT, relative_path))
        except (SuspiciousFileOperation, ValueError):
            return False
