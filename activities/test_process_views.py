"""Telas do processo aplicado: botão e popup "Aplicar processo", painel
"Processo" da ficha, atualização de inputs e critérios, finalização e as
telas de tarefa que esperam a etapa anterior."""

import json

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from acessos import catalog
from acessos.testing import grant_action
from audit.models import AuditLog
from processes.models import ActivityCriterionCheck, ActivityInputValue

from . import process_state
from .models import Activity, Task
from .process_application import ActivityProcessService
from .services import TaskService
from .testing import ProcessTestCase

AJAX = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


class ProcessViewCase(ProcessTestCase):
    def setUp(self):
        super().setUp()
        self.apply_url = reverse("activity-process-apply", args=[self.activity.pk])
        self.detail_url = reverse("activity-detail", args=[self.activity.pk])

    def login(self, user):
        self.client.force_login(user)

    def payload(self, version=None, **extra):
        data = {"process_version": (version or self.version).pk}
        data.update(extra)
        return data

    def post_apply(self, data, ajax=True):
        return self.client.post(self.apply_url, data, **(AJAX if ajax else {}))

    def errors(self, response):
        return json.loads(response.content)["errors"]


# ---------------------------------------------------------------------------
# Botão "Aplicar processo"
# ---------------------------------------------------------------------------


class ApplyButtonTests(ProcessViewCase):
    def test_button_appears_for_someone_who_can_apply(self):
        self.login(self.applier)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.apply_url)
        self.assertContains(response, "Aplicar processo")
        self.assertTrue(response.context["can_apply_process"])

    def test_button_is_hidden_from_someone_who_cannot_apply(self):
        self.login(self.owner)  # dono, mas sem processo.aplicar
        response = self.client.get(self.detail_url)
        self.assertNotContains(response, self.apply_url)
        self.assertFalse(response.context["can_apply_process"])

    def test_button_is_hidden_once_a_process_was_applied(self):
        self.apply()
        self.login(self.applier)
        response = self.client.get(self.detail_url)
        self.assertNotContains(response, self.apply_url)
        self.assertNotContains(response, "Trocar processo")
        self.assertNotContains(response, "Remover processo")

    def test_button_is_hidden_for_closed_activities(self):
        Activity.objects.filter(pk=self.activity.pk).update(status=Activity.Status.CONCLUIDA)
        self.login(self.applier)
        self.assertNotContains(self.client.get(self.detail_url), self.apply_url)

    def test_scoped_permission_shows_the_button_only_where_it_applies(self):
        from acessos.models import Scope
        from acessos.services import ScopeService
        from .testing import make_user

        scoped = make_user("so_outra", self.org)
        grant_action(
            scoped, catalog.PROCESSO_APLICAR, organization=self.org,
            scope=ScopeService.get_or_create(self.org, Scope.Type.EMPRESA, company=self.other_company),
        )
        self.login(scoped)
        self.assertNotContains(self.client.get(self.detail_url), self.apply_url)


# ---------------------------------------------------------------------------
# Popup
# ---------------------------------------------------------------------------


class ApplyModalTests(ProcessViewCase):
    def test_get_requires_the_permission(self):
        self.login(self.owner)
        self.assertEqual(self.client.get(self.apply_url, **AJAX).status_code, 403)

    def test_anonymous_is_sent_to_login(self):
        response = self.client.get(self.apply_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response["Location"])

    def test_other_tenant_gets_404(self):
        self.login(self.foreign)
        self.assertEqual(self.client.get(self.apply_url, **AJAX).status_code, 404)

    def test_lists_only_eligible_processes_with_their_summary(self):
        self.new_process(name="Processo Rascunho", publish=False)
        self.new_process(name="Processo Inativo", is_active=False)
        self.new_process(name="Processo Outra Empresa", company=self.other_company)
        self.login(self.applier)
        response = self.client.get(self.apply_url, **AJAX)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Orçamento")
        self.assertContains(response, "Versão 3")
        self.assertContains(response, "Biasi Engenharia")
        self.assertContains(response, "3 etapas")
        self.assertContains(response, "3 entradas")
        self.assertContains(response, "4 critérios")
        self.assertContains(response, "Proposta comercial pronta para envio")
        for hidden in ("Processo Rascunho", "Processo Inativo", "Processo Outra Empresa"):
            self.assertNotContains(response, hidden)
        self.assertEqual([p["version"].pk for p in response.context["panels"]], [self.version.pk])

    def test_other_tenant_process_is_never_listed(self):
        from processes.testing import build_process

        build_process(
            self.other_org, self.foreign_company, self.foreign, name="Processo Alheio",
            steps=[{"name": "X", "sector": self.foreign_sector, "default_responsavel": self.foreign}],
        )
        self.login(self.applier)
        self.assertNotContains(self.client.get(self.apply_url, **AJAX), "Processo Alheio")

    def test_step_selects_come_with_the_default_selected_and_sector_people_first(self):
        self.login(self.applier)
        response = self.client.get(self.apply_url, **AJAX)
        step2 = self.version.steps.get(order=2)
        row = [r for r in response.context["panels"][0]["steps"] if r["step"].pk == step2.pk][0]
        self.assertEqual(row["selected"], str(self.vitor.pk))
        self.assertEqual([p.username for p in row["sector_people"]], ["vitor"])
        self.assertNotIn(self.foreign, row["other_people"])
        self.assertContains(response, "Do setor Compras")
        self.assertContains(response, "padrão da etapa")

    def test_activity_without_company_explains_what_to_do(self):
        no_company = self.new_activity(company=None, title="Sem empresa")
        self.login(self.applier)
        response = self.client.get(reverse("activity-process-apply", args=[no_company.pk]), **AJAX)
        self.assertContains(response, "ainda não tem empresa")
        self.assertFalse(response.context["panels"])

    def test_already_applied_redirects_back_to_the_activity(self):
        self.apply()
        self.login(self.applier)
        response = self.client.get(self.apply_url)
        self.assertRedirects(response, self.detail_url)


# ---------------------------------------------------------------------------
# Envio do formulário
# ---------------------------------------------------------------------------


class ApplySubmitTests(ProcessViewCase):
    def setUp(self):
        super().setUp()
        self.login(self.applier)

    def test_success_returns_json_and_the_process_is_applied(self):
        response = self.post_apply(self.payload())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)["redirect_url"], self.detail_url + "#processo")
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.process_version, self.version)
        self.assertEqual(self.activity.tasks.count(), 3)

    def test_success_without_javascript_redirects_to_the_activity(self):
        response = self.post_apply(self.payload(), ajax=False)
        self.assertRedirects(response, self.detail_url + "#processo", fetch_redirect_response=False)
        self.assertEqual(self.activity.tasks.count(), 3)

    def test_override_and_initial_inputs_travel_in_the_form(self):
        step2 = self.version.steps.get(order=2)
        projetos = self.version.inputs.get(name="Projetos")
        response = self.post_apply(
            self.payload(**{f"responsavel_{step2.pk}": self.paulo.pk, f"input_{projetos.pk}": "Projeto rev. B"})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.tasks()[1].responsavel, self.paulo)
        self.assertTrue(ActivityInputValue.objects.get(activity=self.activity, process_input=projetos).is_received)

    def test_responsavel_is_required_when_the_step_has_no_default(self):
        version = self.new_process(
            name="Sem padrão",
            steps=[{"name": "A", "sector": self.comercial}, {"name": "B", "sector": self.compras}],
        )
        step_a = version.steps.get(order=1)
        response = self.post_apply(self.payload(version, **{f"responsavel_{step_a.pk}": self.ryan.pk}))
        self.assertEqual(response.status_code, 400)
        errors = self.errors(response)
        step_b = version.steps.get(order=2)
        self.assertIn(f"responsavel_{step_b.pk}", errors)
        self.assertNotIn(f"responsavel_{step_a.pk}", errors)
        self.assertFalse(self.activity.tasks.exists())

    def test_user_from_another_tenant_cannot_be_chosen_as_responsavel(self):
        step2 = self.version.steps.get(order=2)
        response = self.post_apply(self.payload(**{f"responsavel_{step2.pk}": self.foreign.pk}))
        self.assertEqual(response.status_code, 400)
        self.assertIn(f"responsavel_{step2.pk}", self.errors(response))
        self.assertFalse(self.activity.tasks.exists())

    def test_invalid_input_value_is_reported_on_its_field(self):
        prazo = self.version.inputs.get(name="Prazo solicitado")
        response = self.post_apply(self.payload(**{f"input_{prazo.pk}": "quando der"}))
        self.assertEqual(response.status_code, 400)
        self.assertIn(f"input_{prazo.pk}", self.errors(response))

    def test_ineligible_version_is_rejected(self):
        other = self.new_process(name="Outra empresa", company=self.other_company)
        response = self.post_apply(self.payload(other))
        self.assertEqual(response.status_code, 400)
        self.assertIn("process_version", self.errors(response))
        self.assertFalse(self.activity.tasks.exists())

    def test_missing_version_is_rejected(self):
        response = self.post_apply({})
        self.assertEqual(response.status_code, 400)
        self.assertIn("process_version", self.errors(response))

    def test_double_click_creates_the_tasks_only_once(self):
        first = self.post_apply(self.payload())
        second = self.post_apply(self.payload())
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 400)
        self.assertIn("já tem um processo aplicado", json.dumps(self.errors(second), ensure_ascii=False))
        self.assertEqual(self.activity.tasks.count(), 3)

    def test_user_without_the_permission_cannot_post(self):
        self.login(self.owner)
        response = self.post_apply(self.payload())
        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.activity.tasks.exists())

    def test_other_tenant_cannot_post(self):
        self.login(self.foreign)
        self.assertEqual(self.post_apply(self.payload()).status_code, 404)
        self.assertFalse(self.activity.tasks.exists())


# ---------------------------------------------------------------------------
# Painel "Processo" da ficha
# ---------------------------------------------------------------------------


class ProcessPanelTests(ProcessViewCase):
    def setUp(self):
        super().setUp()
        self.apply()
        self.login(self.owner)

    def get_detail(self):
        return self.client.get(self.detail_url)

    def test_panel_shows_process_name_version_company_and_expected_output(self):
        response = self.get_detail()
        self.assertContains(response, 'id="processo"')
        self.assertContains(response, "Orçamento")
        self.assertContains(response, "Versão 3")
        self.assertContains(response, "Biasi Engenharia")
        self.assertContains(response, "Resultado esperado")
        self.assertContains(response, "Proposta comercial pronta para envio")
        self.assertContains(response, "Tipo de evidência: Confirmação simples")

    def test_panel_shows_progress_of_inputs_steps_and_criteria(self):
        response = self.get_detail()
        self.assertContains(response, "0 / 3 recebidas")
        self.assertContains(response, "0 / 3 concluídas")
        self.assertContains(response, "0 / 4 atendidos")

    def test_panel_lists_each_input_step_and_criterion(self):
        response = self.get_detail()
        for text in ("Projetos", "Memorial", "Prazo solicitado", "Levantamento de quantitativos", "Cotação de materiais",
                     "Revisão final", "Escopo revisado", "Quantitativos conferidos", "Cotação revisada", "Aprovação comercial"):
            self.assertContains(response, text)
        self.assertContains(response, "Falta receber:")
        self.assertContains(response, "Obrigatório")
        self.assertContains(response, "Opcional")

    def test_step_states_are_explained(self):
        response = self.get_detail()
        self.assertContains(response, "Na fila")
        self.assertContains(response, "Aguardando etapa anterior")
        self.assertContains(response, "entra na fila quando «Levantamento de quantitativos» for concluída")

    def test_progress_moves_with_the_work(self):
        self.receive_all_required_inputs()
        t1 = self.tasks()[0]
        TaskService.complete(t1, self.ryan)
        check = ActivityCriterionCheck.objects.filter(activity=self.activity).first()
        ActivityProcessService.set_criterion(self.owner, check, True)
        response = self.get_detail()
        self.assertContains(response, "2 / 3 recebidas")
        self.assertContains(response, "1 / 3 concluídas")
        self.assertContains(response, "1 / 4 atendidos")
        panel = response.context["process_panel"]
        self.assertEqual([s["state"] for s in panel["steps"]], ["concluida", "na_fila", "aguardando"])

    def test_activity_without_process_has_no_panel(self):
        plain = self.new_activity(title="Simples")
        response = self.client.get(reverse("activity-detail", args=[plain.pk]))
        self.assertNotContains(response, 'id="processo"')
        self.assertIsNone(response.context["process_panel"])

    def test_the_link_to_the_template_points_to_the_applied_version(self):
        response = self.get_detail()
        self.assertContains(response, f"?v={self.version.pk}")

    def test_editing_controls_only_for_people_who_can_update(self):
        response = self.get_detail()
        self.assertTrue(response.context["can_update_process"])
        self.assertContains(response, reverse("activity-input-update", args=[self.activity.pk, ActivityInputValue.objects.first().pk]))
        self.login(self.stranger)
        response = self.get_detail()
        self.assertFalse(response.context["can_update_process"])
        self.assertNotContains(response, "Registrar</summary>")

    def test_situation_warns_when_tasks_are_done_but_required_criteria_are_open(self):
        for task in self.tasks():
            Task.objects.filter(pk=task.pk).update(status=Task.Status.CONCLUIDA)
        response = self.get_detail()
        self.assertTrue(response.context["is_blocked_by_criteria"])
        self.assertFalse(response.context["is_ready_to_complete"])
        self.assertContains(response, "Faltam critérios de aceite")
        for check in ActivityCriterionCheck.objects.filter(activity=self.activity, process_criterion__is_required=True):
            ActivityProcessService.set_criterion(self.owner, check, True)
        response = self.get_detail()
        self.assertTrue(response.context["is_ready_to_complete"])
        self.assertFalse(response.context["is_blocked_by_criteria"])

    def test_tasks_block_flags_process_steps_and_waiting_ones(self):
        response = self.get_detail()
        self.assertContains(response, "Etapa 1")
        # a espera fica no status da linha (com o motivo no tooltip), sem tirar
        # espaço do título da tarefa
        self.assertContains(response, 'title="Entra na fila quando «Levantamento de quantitativos» for concluída"')
        self.assertContains(response, ">Aguardando etapa anterior</span>")
        counts = response.context["status_counts"]
        self.assertEqual((counts["waiting"], counts["dependency_waiting"]), (1, 2))

    def test_panel_query_count_does_not_grow_with_the_number_of_steps(self):
        def count_queries(activity):
            tasks = list(
                activity.tasks.select_related("sector", "depends_on", "responsavel", "process_step")
                .order_by("order", "created_at")
            )
            activity = Activity.objects.select_related("process_version__process__company").get(pk=activity.pk)
            with CaptureQueriesContext(connection) as ctx:
                process_state.process_panel(activity, tasks=tasks)
            return len(ctx)

        small = count_queries(self.activity)
        many_steps = self.new_process(
            name="Longo",
            steps=[
                {"name": f"Etapa {i}", "sector": self.comercial if i % 2 else self.compras, "default_responsavel": self.ryan}
                for i in range(1, 9)
            ],
            inputs=[{"name": f"Input {i}", "required": False} for i in range(1, 7)],
            criteria=[{"name": f"Critério {i}"} for i in range(1, 7)],
        )
        long_activity = self.new_activity(title="Longa")
        self.apply(activity=long_activity, version=many_steps)
        self.assertEqual(count_queries(long_activity), small)


# ---------------------------------------------------------------------------
# Atualização de inputs e critérios
# ---------------------------------------------------------------------------


class InputCriterionViewTests(ProcessViewCase):
    def setUp(self):
        super().setUp()
        self.apply()
        self.input = ActivityInputValue.objects.get(activity=self.activity, process_input__name="Projetos")
        self.date_input = ActivityInputValue.objects.get(activity=self.activity, process_input__name="Prazo solicitado")
        self.check = ActivityCriterionCheck.objects.get(activity=self.activity, process_criterion__name="Escopo revisado")
        self.input_url = reverse("activity-input-update", args=[self.activity.pk, self.input.pk])
        self.date_url = reverse("activity-input-update", args=[self.activity.pk, self.date_input.pk])
        self.check_url = reverse("activity-criterion-update", args=[self.activity.pk, self.check.pk])

    def test_registering_an_input_redirects_back_to_the_panel(self):
        self.login(self.owner)
        response = self.client.post(self.input_url, {"value": "Projeto rev. C"})
        self.assertRedirects(response, self.detail_url + "#processo", fetch_redirect_response=False)
        self.input.refresh_from_db()
        self.assertTrue(self.input.is_received)
        self.assertEqual(self.input.value, "Projeto rev. C")

    def test_clearing_an_input_marks_it_not_received(self):
        self.login(self.owner)
        self.client.post(self.input_url, {"value": "algo"})
        self.client.post(self.input_url, {"clear": "1"})
        self.input.refresh_from_db()
        self.assertFalse(self.input.is_received)
        self.assertEqual(self.input.value, "")

    def test_invalid_value_shows_the_error_and_changes_nothing(self):
        self.login(self.owner)
        response = self.client.post(self.date_url, {"value": "32/13/2026"}, follow=True)
        self.assertContains(response, "data válida")
        self.date_input.refresh_from_db()
        self.assertFalse(self.date_input.is_received)

    def test_stranger_is_refused(self):
        self.login(self.stranger)
        response = self.client.post(self.input_url, {"value": "x"}, follow=True)
        self.assertContains(response, "permissão")
        self.input.refresh_from_db()
        self.assertFalse(self.input.is_received)

    def test_other_tenant_gets_404(self):
        self.login(self.foreign)
        self.assertEqual(self.client.post(self.input_url, {"value": "x"}).status_code, 404)
        self.assertEqual(self.client.post(self.check_url, {"is_met": "1"}).status_code, 404)

    def test_input_of_another_activity_is_not_reachable_through_this_one(self):
        other = self.new_activity(title="Outra")
        self.apply(activity=other)
        foreign_row = ActivityInputValue.objects.filter(activity=other).first()
        self.login(self.owner)
        url = reverse("activity-input-update", args=[self.activity.pk, foreign_row.pk])
        self.assertEqual(self.client.post(url, {"value": "x"}).status_code, 404)

    def test_marking_and_unmarking_a_criterion(self):
        self.login(self.owner)
        self.client.post(self.check_url, {"is_met": "on"})
        self.check.refresh_from_db()
        self.assertTrue(self.check.is_met)
        self.assertEqual(self.check.met_by, self.owner)
        self.client.post(self.check_url, {})
        self.check.refresh_from_db()
        self.assertFalse(self.check.is_met)
        self.assertEqual(
            AuditLog.objects.filter(activity=self.activity, action=AuditLog.Action.CRITERION_UPDATED).count(), 2
        )

    def test_stranger_cannot_mark_a_criterion(self):
        self.login(self.stranger)
        self.client.post(self.check_url, {"is_met": "on"}, follow=True)
        self.check.refresh_from_db()
        self.assertFalse(self.check.is_met)

    def test_get_is_not_allowed(self):
        self.login(self.owner)
        self.assertEqual(self.client.get(self.check_url).status_code, 405)


# ---------------------------------------------------------------------------
# Finalização (tela)
# ---------------------------------------------------------------------------


class FinalizeViewTests(ProcessViewCase):
    def setUp(self):
        super().setUp()
        self.apply()
        self.receive_all_required_inputs()
        for task in self.tasks():
            Task.objects.filter(pk=task.pk).update(status=Task.Status.CONCLUIDA)
        self.url = reverse("activity-finalize", args=[self.activity.pk])
        self.login(self.owner)

    def test_popup_lists_the_criteria_that_are_still_open(self):
        response = self.client.get(self.url, **AJAX)
        self.assertContains(response, "Critérios de aceite obrigatórios ainda não atendidos")
        self.assertContains(response, "Escopo revisado")
        self.assertNotContains(response, "Aprovação comercial")  # opcional

    def test_success_is_refused_with_the_missing_criteria_named(self):
        response = self.client.post(self.url, {"outcome": "SUCESSO", "comment": "Feito"}, **AJAX)
        self.assertEqual(response.status_code, 400)
        message = json.dumps(self.errors(response), ensure_ascii=False)
        self.assertIn("Falta atender", message)
        self.assertIn("Cotação revisada", message)
        self.activity.refresh_from_db()
        self.assertNotEqual(self.activity.status, Activity.Status.CONCLUIDA)

    def test_cancelling_still_works(self):
        response = self.client.post(self.url, {"outcome": "CANCELADO", "comment": "Cliente desistiu"}, **AJAX)
        self.assertEqual(response.status_code, 200)
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.status, Activity.Status.CANCELADA)

    def test_popup_has_no_warning_when_nothing_is_open(self):
        for check in ActivityCriterionCheck.objects.filter(activity=self.activity, process_criterion__is_required=True):
            ActivityProcessService.set_criterion(self.owner, check, True)
        self.assertNotContains(self.client.get(self.url, **AJAX), "ainda não atendidos")
        response = self.client.post(self.url, {"outcome": "SUCESSO", "comment": "Tudo certo"}, **AJAX)
        self.assertEqual(response.status_code, 200)


# ---------------------------------------------------------------------------
# Telas de tarefa e início do dia
# ---------------------------------------------------------------------------


class WaitingTaskScreenTests(ProcessViewCase):
    def setUp(self):
        super().setUp()
        self.apply()
        self.t1, self.t2, self.t3 = self.tasks()

    def test_task_page_explains_the_wait_and_offers_no_start_button(self):
        self.login(self.vitor)  # responsável da etapa 2
        response = self.client.get(reverse("task-detail", args=[self.t2.pk]))
        self.assertContains(response, "entra na fila do setor quando")
        self.assertContains(response, "Levantamento de quantitativos")
        self.assertNotContains(response, reverse("task-start", args=[self.t2.pk]))
        self.assertContains(response, "Aguardando etapa anterior")

    def test_task_drawer_says_the_same(self):
        self.login(self.vitor)
        response = self.client.get(reverse("task-drawer", args=[self.t2.pk]))
        self.assertContains(response, "entra na fila do setor quando")
        self.assertNotContains(response, reverse("task-start-ajax", args=[self.t2.pk]))

    def test_task_page_points_to_missing_required_inputs(self):
        self.login(self.ryan)
        response = self.client.get(reverse("task-detail", args=[self.t1.pk]))
        self.assertContains(response, "registre o recebimento dos inputs obrigatórios")
        self.assertContains(response, "Projetos; Memorial")
        self.assertNotContains(response, reverse("task-start", args=[self.t1.pk]))

    def test_task_page_offers_start_once_inputs_arrive(self):
        self.receive_all_required_inputs()
        self.login(self.ryan)
        response = self.client.get(reverse("task-detail", args=[self.t1.pk]))
        self.assertContains(response, reverse("task-start", args=[self.t1.pk]))

    def test_starting_through_the_endpoint_is_refused_with_a_message(self):
        self.login(self.vitor)
        response = self.client.post(reverse("task-start-ajax", args=[self.t2.pk]))
        self.assertEqual(response.status_code, 400)
        self.assertIn("depende da conclusão", json.loads(response.content)["error"])

    def test_home_does_not_offer_a_waiting_step_as_next_task(self):
        self.receive_all_required_inputs()
        self.login(self.vitor)  # membro de Compras e responsável da etapa 2
        response = self.client.get(reverse("home"))
        self.assertNotIn(self.t2, list(response.context["next_tasks"]))
        TaskService.complete(self.t1, self.ryan)
        response = self.client.get(reverse("home"))
        self.assertIn(self.t2, list(response.context["next_tasks"]))

    def test_task_list_hides_start_for_waiting_steps_and_labels_them(self):
        self.login(self.vitor)
        response = self.client.get(reverse("task-list"))
        self.assertContains(response, "Aguardando etapa anterior")
        self.assertNotContains(response, reverse("task-start-ajax", args=[self.t2.pk]))
