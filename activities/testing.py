"""Base de testes para processos aplicados a atividades.

Cenário (o "exemplo de aceite" do produto): o processo *Orçamento* v3 tem três
etapas em sequência — Levantamento (Comercial, Ryan), Cotação (Compras,
Vitor), Revisão final (Comercial, Paulo) —, três inputs e quatro critérios.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import UserSector
from acessos import catalog
from acessos.testing import grant_actions
from core.models import Company, Organization, Sector
from processes.models import ActivityInputValue, ProcessInput
from processes.testing import build_process

from .models import QueueEntry
from .process_application import ActivityProcessService, ProcessApplicationService
from .services import ActivityService

User = get_user_model()

WORKER_ACTIONS = [
    catalog.TAREFA_INICIAR,
    catalog.TAREFA_PAUSAR,
    catalog.TAREFA_CONCLUIR,
    catalog.TAREFA_BLOQUEAR,
    catalog.TAREFA_CANCELAR,
    catalog.TAREFA_MOVER_SETOR,
    catalog.TAREFA_EDITAR,
    catalog.COMUNICACAO_PARTICIPAR,
]


def make_user(username, organization, actions=()):
    user = User.objects.create_user(username, email=f"{username}@example.com", password="x")
    user.profile.organization = organization
    user.profile.save(update_fields=["organization"])
    if actions:
        grant_actions(user, list(actions), organization=organization)
    return user


class ProcessTestCase(TestCase):
    """Organização, setores, pessoas e o processo Orçamento v3 já publicado."""

    def setUp(self):
        self.org = Organization.objects.create(name="Biasi")
        self.other_org = Organization.objects.create(name="Outra Empresa")
        self.company = Company.objects.create(organization=self.org, name="Biasi Engenharia")
        self.other_company = Company.objects.create(organization=self.org, name="Biasi Instalações")
        self.foreign_company = Company.objects.create(organization=self.other_org, name="Alheia")

        self.comercial = Sector.objects.create(organization=self.org, name="Comercial")
        self.compras = Sector.objects.create(organization=self.org, name="Compras")
        self.foreign_sector = Sector.objects.create(organization=self.other_org, name="Financeiro")

        # Quem aplica tem SÓ processo.aplicar: o desenho é que aplicar um fluxo
        # não exija tarefa.criar em cada setor do processo.
        self.applier = make_user("ana", self.org, [catalog.PROCESSO_APLICAR])
        self.owner = make_user(
            "dono",
            self.org,
            [catalog.ATIVIDADE_CRIAR, catalog.ATIVIDADE_CONCLUIR, catalog.ATIVIDADE_CANCELAR, *WORKER_ACTIONS],
        )
        self.ryan = make_user("ryan", self.org, WORKER_ACTIONS)
        self.vitor = make_user("vitor", self.org, WORKER_ACTIONS)
        self.paulo = make_user("paulo", self.org, WORKER_ACTIONS)
        self.stranger = make_user("estranho", self.org)
        self.foreign = make_user("alheio", self.other_org, [catalog.PROCESSO_APLICAR, catalog.ATIVIDADE_CRIAR])

        UserSector.objects.create(user=self.ryan, sector=self.comercial)
        UserSector.objects.create(user=self.paulo, sector=self.comercial)
        UserSector.objects.create(user=self.vitor, sector=self.compras)

        self.activity = self.new_activity()
        self.version = self.new_process()

    # -- fábricas -------------------------------------------------------------

    def new_activity(self, company="default", title="Demanda de teste"):
        return ActivityService.create_activity(
            organization=self.org,
            title=title,
            owner=self.owner,
            created_by=self.owner,
            company=self.company if company == "default" else company,
        )

    def new_process(self, **overrides):
        spec = dict(
            organization=self.org,
            company=self.company,
            created_by=self.owner,
            name="Orçamento",
            number=3,
            steps=[
                {"name": "Levantamento de quantitativos", "sector": self.comercial, "depends_on_previous": False,
                 "default_responsavel": self.ryan},
                {"name": "Cotação de materiais", "sector": self.compras, "depends_on_previous": True,
                 "default_responsavel": self.vitor},
                {"name": "Revisão final", "sector": self.comercial, "depends_on_previous": True,
                 "default_responsavel": self.paulo},
            ],
            inputs=[
                {"name": "Projetos", "required": True},
                {"name": "Memorial", "required": True},
                {"name": "Prazo solicitado", "required": False, "type": ProcessInput.InputType.DATA},
            ],
            criteria=[
                {"name": "Escopo revisado"},
                {"name": "Quantitativos conferidos"},
                {"name": "Cotação revisada"},
                {"name": "Aprovação comercial", "required": False},
            ],
        )
        spec.update(overrides)
        return build_process(**spec)

    def apply(self, activity=None, version=None, user=None, **kwargs):
        return ProcessApplicationService.apply(
            user or self.applier, activity or self.activity, version or self.version, **kwargs
        )

    def tasks(self, activity=None):
        return list((activity or self.activity).tasks.select_related("sector", "responsavel").order_by("order"))

    def receive_all_required_inputs(self, activity=None):
        activity = activity or self.activity
        for row in ActivityInputValue.objects.filter(activity=activity, process_input__is_required=True):
            ActivityProcessService.update_input(self.owner, row, value="ok")

    def active_queue(self, sector):
        return QueueEntry.objects.filter(sector=sector, left_at__isnull=True)
