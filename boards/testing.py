"""Base de testes dos quadros.

Cenário: a Biasi com um quadro de orçamentos pequeno (dois grupos, uma coluna de cada tipo ativo, três itens) e
pessoas com cada nível de acesso: quem faz de tudo, quem só preenche itens, quem só olha, quem não tem nada e quem é
de outra organização. Montado uma vez por classe (`setUpTestData`): criar usuário é o que mais pesa.
"""

from django.test import TestCase

from acessos import catalog
from activities.testing import make_user
from core.models import Organization

from .models import BoardColumn
from .services import BoardService, CellService, ColumnService, GroupService, ItemService, OptionService

T = BoardColumn.Type

ALL_BOARD_ACTIONS = [
    catalog.QUADRO_VISUALIZAR,
    catalog.QUADRO_CRIAR,
    catalog.QUADRO_EDITAR,
    catalog.QUADRO_EXCLUIR,
    catalog.QUADRO_GERIR_COLUNAS,
    catalog.QUADRO_CRIAR_ITEM,
    catalog.QUADRO_EDITAR_ITEM,
    catalog.QUADRO_EXCLUIR_ITEM,
]
FILL_ACTIONS = [catalog.QUADRO_VISUALIZAR, catalog.QUADRO_CRIAR_ITEM, catalog.QUADRO_EDITAR_ITEM]

JSON = "application/json"


class BoardTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Biasi")
        cls.other_org = Organization.objects.create(name="Outra Empresa")

        cls.admin = make_user("admin", cls.org, ALL_BOARD_ACTIONS)
        cls.editor = make_user("editor", cls.org, FILL_ACTIONS)
        cls.viewer = make_user("viewer", cls.org, [catalog.QUADRO_VISUALIZAR])
        cls.sem_acesso = make_user("semacesso", cls.org)
        cls.estranho = make_user("estranho", cls.other_org, ALL_BOARD_ACTIONS)
        cls.ana = make_user("ana", cls.org)
        cls.ana.first_name, cls.ana.last_name = "Ana", "Souza"
        cls.ana.save(update_fields=["first_name", "last_name"])
        cls.bruno = make_user("bruno", cls.org)
        cls.bruno.first_name = "Bruno"
        cls.bruno.save(update_fields=["first_name"])
        cls.foreign_person = make_user("alheio", cls.other_org)

        cls.board = BoardService.create(user=cls.admin, organization=cls.org, name="Orçamentos")
        cls.kanban = cls.board.views.get()  # todo quadro nasce com um Kanban
        cls.group_a = cls.board.groups.get()
        GroupService.update(user=cls.admin, group=cls.group_a, name="Oportunidades")
        cls.group_b = GroupService.create(user=cls.admin, board=cls.board, name="Em andamento", color="#00C875")

        cls.col = {}
        for key, column_type in (
            ("texto", T.TEXT), ("numero", T.NUMBER), ("moeda", T.CURRENCY), ("data", T.DATE),
            ("pessoa", T.PERSON), ("status", T.STATUS),
            ("lista", T.DROPDOWN), ("check", T.CHECKBOX),
        ):
            cls.col[key] = ColumnService.create(user=cls.admin, board=cls.board, column_type=column_type)
        cls.novo, cls.andamento, cls.concluido = list(cls.col["status"].options.order_by("position"))
        cls.opt_a = OptionService.create(user=cls.admin, column=cls.col["lista"], label="Comercial", color="#00C875")
        cls.opt_b = OptionService.create(user=cls.admin, column=cls.col["lista"], label="Engenharia", color="#A25DDC")

        cls.item1 = ItemService.create(user=cls.admin, board=cls.board, group=cls.group_a, name="Arena Norte")
        cls.item2 = ItemService.create(user=cls.admin, board=cls.board, group=cls.group_a, name="Condomínio Cotia")
        cls.item3 = ItemService.create(user=cls.admin, board=cls.board, group=cls.group_b, name="Hospital Vida")

    # -- apoio -----------------------------------------------------------------------------------

    def set_cell(self, item, key, value, user=None):
        return CellService.set_value(user=user or self.admin, item=item, column=self.col[key], raw_value=value)

    def login(self, user):
        self.client.force_login(user)
