from django.contrib.auth.models import Group, Permission, User
from django.test import TestCase
from django.utils import timezone

from .models import Priority, Process, ProcessStep, ProcessTemplate, ProcessTemplateStep
from .services import WorkflowError, WorkflowService


def grant(user, codename):
    perm = Permission.objects.get(codename=codename)
    user.user_permissions.add(perm)


class WorkflowServiceTestCase(TestCase):
    def setUp(self):
        self.comercial = Group.objects.create(name="COMERCIAL")
        self.engenharia = Group.objects.create(name="ENGENHARIA")

        self.admin_user = User.objects.create_user("admin", password="x")
        self.comercial_user = User.objects.create_user("com1", password="x")
        self.comercial_user.groups.add(self.comercial)
        self.other_comercial_user = User.objects.create_user("com2", password="x")
        self.other_comercial_user.groups.add(self.comercial)
        self.engenharia_user = User.objects.create_user("eng1", password="x")
        self.engenharia_user.groups.add(self.engenharia)

        self.template = ProcessTemplate.objects.create(name="Template Teste", created_by=self.admin_user)
        ProcessTemplateStep.objects.create(
            template=self.template,
            order=1,
            name="Etapa 1",
            responsible_group=self.comercial,
            default_deadline_days=1,
            default_priority=Priority.NORMAL,
        )
        ProcessTemplateStep.objects.create(
            template=self.template,
            order=2,
            name="Etapa 2",
            responsible_group=self.engenharia,
            default_deadline_days=2,
            default_priority=Priority.NORMAL,
        )

    def create_process(self):
        return WorkflowService.instanciar_processo(
            template=self.template, title="Processo Teste", criado_por=self.comercial_user
        )

    def test_instanciar_processo_releases_first_step_only(self):
        process = self.create_process()
        steps = list(process.steps.order_by("order"))
        self.assertIsNotNone(steps[0].released_at)
        self.assertIsNotNone(steps[0].deadline_at)
        self.assertIsNone(steps[1].released_at)

    def test_assumir_atividade_requires_group_membership(self):
        process = self.create_process()
        step1 = process.steps.get(order=1)
        with self.assertRaises(WorkflowError):
            WorkflowService.assumir_atividade(step1, self.engenharia_user)

    def test_assumir_atividade_fails_when_not_released(self):
        process = self.create_process()
        step2 = process.steps.get(order=2)
        with self.assertRaises(WorkflowError):
            WorkflowService.assumir_atividade(step2, self.engenharia_user)

    def test_concluir_atividade_requires_assignee(self):
        process = self.create_process()
        step1 = process.steps.get(order=1)
        WorkflowService.assumir_atividade(step1, self.comercial_user)
        with self.assertRaises(WorkflowError):
            WorkflowService.concluir_atividade(step1, self.other_comercial_user)

    def test_concluir_atividade_releases_next_step(self):
        process = self.create_process()
        step1 = process.steps.get(order=1)
        WorkflowService.assumir_atividade(step1, self.comercial_user)
        WorkflowService.concluir_atividade(step1, self.comercial_user)

        step2 = process.steps.get(order=2)
        step2.refresh_from_db()
        self.assertIsNotNone(step2.released_at)
        self.assertEqual(step2.status, ProcessStep.Status.PENDENTE)

    def test_concluir_ultima_atividade_finaliza_processo(self):
        process = self.create_process()
        step1 = process.steps.get(order=1)
        step2 = process.steps.get(order=2)

        WorkflowService.assumir_atividade(step1, self.comercial_user)
        WorkflowService.concluir_atividade(step1, self.comercial_user)
        step2.refresh_from_db()
        WorkflowService.assumir_atividade(step2, self.engenharia_user)
        WorkflowService.concluir_atividade(step2, self.engenharia_user)

        process.refresh_from_db()
        self.assertEqual(process.status, Process.Status.FINALIZADO)
        self.assertIsNotNone(process.finalized_at)

    def test_reabrir_atividade_requires_permission(self):
        process = self.create_process()
        step1 = process.steps.get(order=1)
        WorkflowService.assumir_atividade(step1, self.comercial_user)
        WorkflowService.concluir_atividade(step1, self.comercial_user)

        with self.assertRaises(WorkflowError):
            WorkflowService.reabrir_atividade(step1, self.comercial_user, "motivo qualquer")

    def test_reabrir_atividade_relocks_untouched_next_step(self):
        process = self.create_process()
        step1 = process.steps.get(order=1)
        step2 = process.steps.get(order=2)
        WorkflowService.assumir_atividade(step1, self.comercial_user)
        WorkflowService.concluir_atividade(step1, self.comercial_user)

        grant(self.admin_user, "can_reopen_activity")
        WorkflowService.reabrir_atividade(step1, self.admin_user, "corrigir informação")

        step1.refresh_from_db()
        step2.refresh_from_db()
        self.assertEqual(step1.status, ProcessStep.Status.EM_ANDAMENTO)
        self.assertIsNone(step2.released_at)

    def test_reabrir_atividade_bloqueada_se_proxima_avancou(self):
        process = self.create_process()
        step1 = process.steps.get(order=1)
        step2 = process.steps.get(order=2)
        WorkflowService.assumir_atividade(step1, self.comercial_user)
        WorkflowService.concluir_atividade(step1, self.comercial_user)
        step2.refresh_from_db()
        WorkflowService.assumir_atividade(step2, self.engenharia_user)

        grant(self.admin_user, "can_reopen_activity")
        step1.refresh_from_db()
        with self.assertRaises(WorkflowError):
            WorkflowService.reabrir_atividade(step1, self.admin_user, "motivo")

    def test_cancelar_processo_requires_permission(self):
        process = self.create_process()
        with self.assertRaises(WorkflowError):
            WorkflowService.cancelar_processo(process, self.comercial_user, "motivo")

    def test_cancelar_processo_ok_com_permissao(self):
        process = self.create_process()
        grant(self.admin_user, "can_cancel_process")
        WorkflowService.cancelar_processo(process, self.admin_user, "cliente desistiu")
        process.refresh_from_db()
        self.assertEqual(process.status, Process.Status.CANCELADO)

    def test_marcar_atividades_atrasadas_nao_duplica(self):
        process = self.create_process()
        step1 = process.steps.get(order=1)
        step1.deadline_at = timezone.now() - timezone.timedelta(days=1)
        step1.save(update_fields=["deadline_at"])

        count_first = WorkflowService.marcar_atividades_atrasadas()
        count_second = WorkflowService.marcar_atividades_atrasadas()

        self.assertEqual(count_first, 1)
        self.assertEqual(count_second, 0)
