"""Base de testes da Caixa de Entrada.

Cenário: a Biasi com os setores Comercial e Compras, o cliente Convivy (e-mail
contato@convivy.com.br) com a obra "Residencial Aurora", e pessoas com cada
nível de acesso: quem faz a triagem de tudo, quem só registra, quem cuida de um
setor, quem não tem nada e quem é de outra organização.
"""

import datetime

from django.test import TestCase
from django.utils import timezone

from acessos import catalog
from acessos.testing import grant_actions
from activities.models import Activity
from activities.testing import make_user
from core.models import Client, Organization, Sector, Site

from . import textparse
from .models import IntakeItem

TRIAGE_ACTIONS = [
    catalog.ENTRADA_VISUALIZAR,
    catalog.ENTRADA_REGISTRAR,
    catalog.ENTRADA_TRIAR,
    catalog.ATIVIDADE_CRIAR,
    catalog.ATIVIDADE_VISUALIZAR,
]

AJAX = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}

EMAIL_TEXT = (
    "Bom dia,\n\nPrecisamos do orçamento do gerador da obra Residencial Aurora até sexta.\n\nAtt,\nMaria"
)


class IntakeTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Biasi")
        self.other_org = Organization.objects.create(name="Outra Empresa")

        self.comercial = Sector.objects.create(organization=self.org, name="Comercial")
        self.compras = Sector.objects.create(organization=self.org, name="Compras")
        self.foreign_sector = Sector.objects.create(organization=self.other_org, name="Financeiro")

        self.convivy = Client.objects.create(organization=self.org, name="Convivy", email="contato@convivy.com.br")
        self.outra = Client.objects.create(organization=self.org, name="Outra Construtora")
        self.aurora = Site.objects.create(organization=self.org, name="Residencial Aurora", client=self.convivy)
        self.foreign_client = Client.objects.create(organization=self.other_org, name="Cliente Alheio")
        self.foreign_site = Site.objects.create(organization=self.other_org, name="Obra Alheia")

        # Triagem geral: escopo de organização.
        self.triador = make_user("triador", self.org, TRIAGE_ACTIONS)
        self.registrador = make_user("registrador", self.org, [catalog.ENTRADA_REGISTRAR])
        self.sem_acesso = make_user("semacesso", self.org)
        self.estranho = make_user("estranho", self.other_org, TRIAGE_ACTIONS)
        # Gestor de um setor só: escopo de setor, não de organização.
        self.gestor_compras = make_user("gestorcompras", self.org)
        grant_actions(
            self.gestor_compras,
            [catalog.ENTRADA_VISUALIZAR, catalog.ENTRADA_REGISTRAR, catalog.ENTRADA_TRIAR, catalog.ATIVIDADE_CRIAR],
            organization=self.org,
            sector=self.compras,
        )
        # Pessoa interna que pode ser a solicitante.
        self.maria = make_user("maria", self.org)
        self.maria.email = "maria@biasi.com.br"
        self.maria.save(update_fields=["email"])

    def new_item(self, **overrides):
        """Cria a solicitação direto no banco, sem passar pelo serviço."""
        data = dict(
            organization=self.org,
            source=IntakeItem.Source.EMAIL,
            subject="Gerador",
            sender_name="Maria da Convivy",
            sender_email="maria@convivy.com.br",
            raw_content=EMAIL_TEXT,
            received_at=timezone.now() - datetime.timedelta(hours=2),
            created_by=self.triador,
        )
        data.update(overrides)
        data.setdefault(
            "content_hash",
            textparse.content_signature(data["sender_email"], data["subject"], data["raw_content"]),
        )
        return IntakeItem.objects.create(**data)

    def activity_count(self):
        return Activity.objects.filter(organization=self.org).count()
