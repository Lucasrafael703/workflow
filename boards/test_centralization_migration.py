"""Dados preservados pela migration que desliga Task de BoardItem."""

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class CentralizationMigrationTests(TransactionTestCase):
    reset_sequences = True
    migrate_from = [
        ("audit", "0011_visualizacoes_de_quadro"),
        ("activities", "0024_activity_board_setup"),
        ("boards", "0007_demand_boards"),
    ]
    migrate_to = [("boards", "0008_centralize_demand_board_items")]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.executor = MigrationExecutor(connection)
        cls.executor.migrate(cls.migrate_from)
        cls.old_apps = cls.executor.loader.project_state(cls.migrate_from).apps

    @classmethod
    def tearDownClass(cls):
        try:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
        finally:
            super().tearDownClass()

    def setUp(self):
        User = self.old_apps.get_model("auth", "User")
        Organization = self.old_apps.get_model("core", "Organization")
        Sector = self.old_apps.get_model("core", "Sector")
        Activity = self.old_apps.get_model("activities", "Activity")
        Task = self.old_apps.get_model("activities", "Task")
        WorkSession = self.old_apps.get_model("activities", "WorkSession")
        QueueEntry = self.old_apps.get_model("activities", "QueueEntry")
        Board = self.old_apps.get_model("boards", "Board")
        BoardGroup = self.old_apps.get_model("boards", "BoardGroup")
        BoardColumn = self.old_apps.get_model("boards", "BoardColumn")
        BoardColumnOption = self.old_apps.get_model("boards", "BoardColumnOption")
        BoardItem = self.old_apps.get_model("boards", "BoardItem")
        BoardCell = self.old_apps.get_model("boards", "BoardCell")
        BoardCellOption = self.old_apps.get_model("boards", "BoardCellOption")

        self.user = User.objects.create(username="migration-owner")
        self.responsible = User.objects.create(username="migration-responsible")
        self.org = Organization.objects.create(name="Organização da migration")
        self.sector = Sector.objects.create(organization_id=self.org.pk, name="Operação")
        self.activity = Activity.objects.create(
            organization_id=self.org.pk,
            title="Demanda migrada",
            owner_id=self.user.pk,
            created_by_id=self.user.pk,
            sector_id=self.sector.pk,
        )
        self.board = Board.objects.create(
            organization_id=self.org.pk,
            name="Quadro migrado",
            item_label="Nome da Tarefa",
            kind="DEMAND",
            activity_id=self.activity.pk,
            sector_id=self.sector.pk,
            created_by_id=self.user.pk,
        )
        self.group = BoardGroup.objects.create(board_id=self.board.pk, name="A fazer", position=1000)
        self.responsible_column = BoardColumn.objects.create(
            board_id=self.board.pk,
            name="Responsável",
            type="PERSON",
            binding="TASK_RESPONSAVEL",
            position=1000,
            width=180,
            created_by_id=self.user.pk,
        )
        self.status_column = BoardColumn.objects.create(
            board_id=self.board.pk,
            name="Status",
            type="STATUS",
            binding="CUSTOM",
            position=2000,
            width=160,
            created_by_id=self.user.pk,
        )
        self.default_option = BoardColumnOption.objects.create(
            column_id=self.status_column.pk,
            label="Não iniciado",
            color="#C4C4C4",
            position=1000,
            is_default=True,
        )
        self.existing_option = BoardColumnOption.objects.create(
            column_id=self.status_column.pk,
            label="Em andamento",
            color="#579BFC",
            position=2000,
        )
        self.open_task = Task.objects.create(
            activity_id=self.activity.pk,
            sector_id=self.sector.pk,
            title="Título operacional",
            status="EM_EXECUCAO",
            responsavel_id=self.responsible.pk,
            created_by_id=self.user.pk,
        )
        self.open_item = BoardItem.objects.create(
            board_id=self.board.pk,
            group_id=self.group.pk,
            task_id=self.open_task.pk,
            name="Nome antigo",
            position=1000,
            created_by_id=self.user.pk,
            updated_by_id=self.user.pk,
        )
        existing_status = BoardCell.objects.create(
            item_id=self.open_item.pk,
            column_id=self.status_column.pk,
            updated_by_id=self.user.pk,
        )
        BoardCellOption.objects.create(cell_id=existing_status.pk, option_id=self.existing_option.pk, position=0)
        self.blank_task = Task.objects.create(
            activity_id=self.activity.pk,
            sector_id=self.sector.pk,
            title="Com padrão",
            status="EM_FILA",
            responsavel_id=self.responsible.pk,
            created_by_id=self.user.pk,
        )
        self.blank_item = BoardItem.objects.create(
            board_id=self.board.pk,
            group_id=self.group.pk,
            task_id=self.blank_task.pk,
            name="",
            position=2000,
            created_by_id=self.user.pk,
            updated_by_id=self.user.pk,
        )
        self.terminal_task = Task.objects.create(
            activity_id=self.activity.pk,
            sector_id=self.sector.pk,
            title="Histórica",
            status="CONCLUIDA",
            responsavel_id=self.responsible.pk,
            created_by_id=self.user.pk,
        )
        WorkSession.objects.create(task_id=self.open_task.pk, user_id=self.responsible.pk, started_at=timezone.now())
        QueueEntry.objects.create(
            task_id=self.open_task.pk,
            sector_id=self.sector.pk,
            position=1,
            queue_size_at_entry=2,
        )
        QueueEntry.objects.create(
            task_id=self.terminal_task.pk,
            sector_id=self.sector.pk,
            position=2,
            queue_size_at_entry=2,
        )

    def test_linked_values_move_to_generic_cells_and_active_work_is_archived(self):
        self.executor.loader.build_graph()
        self.executor.migrate(self.migrate_to)
        apps = self.executor.loader.project_state(self.migrate_to).apps
        Task = apps.get_model("activities", "Task")
        WorkSession = apps.get_model("activities", "WorkSession")
        QueueEntry = apps.get_model("activities", "QueueEntry")
        AuditLog = apps.get_model("audit", "AuditLog")
        BoardItem = apps.get_model("boards", "BoardItem")
        BoardCell = apps.get_model("boards", "BoardCell")
        BoardCellOption = apps.get_model("boards", "BoardCellOption")
        BoardCellUser = apps.get_model("boards", "BoardCellUser")

        migrated = BoardItem.objects.get(pk=self.open_item.pk)
        self.assertEqual(migrated.name, "Título operacional")
        responsible_cell = BoardCell.objects.get(item_id=migrated.pk, column_id=self.responsible_column.pk)
        self.assertEqual(BoardCellUser.objects.get(cell_id=responsible_cell.pk).user_id, self.responsible.pk)
        self.assertTrue(
            BoardCellOption.objects.filter(
                cell__item_id=migrated.pk,
                option_id=self.existing_option.pk,
            ).exists()
        )
        self.assertFalse(
            BoardCellOption.objects.filter(
                cell__item_id=migrated.pk,
                option_id=self.default_option.pk,
            ).exists()
        )
        self.assertTrue(
            BoardCellOption.objects.filter(
                cell__item_id=self.blank_item.pk,
                option_id=self.default_option.pk,
            ).exists()
        )

        archived = Task.objects.get(pk=self.open_task.pk)
        self.assertEqual(archived.status, "CANCELADA")
        self.assertIsNotNone(archived.cancelled_at)
        self.assertIsNotNone(WorkSession.objects.get(task_id=archived.pk).ended_at)
        self.assertIsNotNone(QueueEntry.objects.get(task_id=archived.pk).left_at)
        self.assertEqual(Task.objects.get(pk=self.terminal_task.pk).status, "CONCLUIDA")
        remaining = QueueEntry.objects.get(task_id=self.terminal_task.pk)
        self.assertEqual((remaining.position, remaining.queue_size_at_entry), (1, 1))
        self.assertTrue(
            AuditLog.objects.filter(
                task_id=archived.pk,
                action="CANCEL",
                metadata__migration="centralize_demand_board_items",
            ).exists()
        )
