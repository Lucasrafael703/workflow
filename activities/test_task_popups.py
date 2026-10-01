"""As janelas de tarefa — Nova tarefa (dentro de uma atividade e fora dela) e
Editar tarefa — têm o mesmo modelo: uma tela só, sem etapas, em quatro seções
numeradas:

    1 Tarefa (atividade · o que fazer · setor · responsável)
    2 Prazo e organização (data do prazo · hora do prazo · marcadores)
    3 Participantes (opcional)
    4 Instruções

O painel lateral da tarefa segue um padrão próprio (blocos recolhíveis), conferido
no fim do arquivo. Também trava o defeito que existia antes: os seletores (setor,
responsável, atividade) herdavam de campo escondido, então apareciam sem rótulo
e, no popup de Nova tarefa, desenhados duas vezes.
"""

import datetime
import json
import re

from django import forms
from django.urls import reverse
from django.utils import timezone

from acessos import catalog
from core.widgets import (
    ActivityPickerWidget,
    ClientPickerWidget,
    PersonPickerWidget,
    SectorPickerWidget,
)

from .forms import (
    TASK_LABELS,
    TaskEditorForm,
    TaskQuickCreateForm,
    TaskQuickCreateStandaloneForm,
    activity_summary,
)
from .models import Task
from .services import TaskService
from .test_task_editor import AJAX, MANAGER_ACTIONS, EditorTestCase
from .testing import make_user

SECTIONS = [("1", "Tarefa"), ("2", "Prazo e organização"), ("3", "Participantes"), ("4", "Instruções")]


class PopupTestCase(EditorTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.manager)
        self.urls = {
            "nova": reverse("task-quick-create", args=[self.activity.pk]),
            "nova_global": reverse("task-quick-create-standalone"),
            "editar": reverse("task-edit", args=[self.task.pk]),
        }

    def html(self, key, **extra):
        response = self.client.get(self.urls[key], **AJAX, **extra)
        self.assertEqual(response.status_code, 200, msg=key)
        return response.content.decode()

    @staticmethod
    def folds(html):
        """Blocos recolhíveis do painel lateral (as janelas não têm mais)."""
        return re.findall(r'<details class="fold"( open)?>', html)

    @staticmethod
    def sections(html):
        return re.findall(r'<h3 class="task-section-title" id="task-section-(\d)">\s*([^<]*?)\s*(?:<span|</h3>)', html)


class SamePatternTests(PopupTestCase):
    def test_the_three_windows_share_the_same_order_of_blocks(self):
        for key in ("nova", "nova_global", "editar"):
            html = self.html(key)
            positions = [
                html.index('name="title"'),
                html.index('for="id_sector"') if key != "editar" else html.index('<span class="task-label">Setor</span>'),
                html.index('for="id_responsavel"'),
                html.index("Prazo e organização"),
                html.index('name="requested_deadline_0"'),
                html.index('name="requested_deadline_1"'),
                html.index('name="tags"'),
                html.index("Participantes <span"),
                html.index('name="participantes"'),
                html.index('id="task-section-4"'),
                html.index('name="description"'),
                html.index("modal__foot"),
            ]
            self.assertEqual(positions, sorted(positions), msg=key)

    def test_four_numbered_sections_in_this_order_in_every_window(self):
        for key in ("nova", "nova_global", "editar"):
            self.assertEqual(self.sections(self.html(key)), SECTIONS, msg=key)

    def test_participants_come_before_instructions(self):
        for key in ("nova", "nova_global", "editar"):
            html = self.html(key)
            self.assertLess(html.index('id="task-section-3"'), html.index('id="task-section-4"'), msg=key)

    def test_one_screen_only_no_stepper_and_nothing_collapsible(self):
        for key in ("nova", "nova_global", "editar"):
            window = self.html(key)
            window = window[window.index("modal-backdrop"):]  # a página em volta tem os seus próprios formulários
            self.assertEqual(self.folds(window), [], msg=key)
            self.assertNotIn("data-activity-stepper", window, msg=key)
            self.assertNotIn("data-step-next", window, msg=key)
            self.assertEqual(window.count("<form"), 1, msg=key)

    def test_same_questions_in_every_window(self):
        for key in ("nova", "nova_global", "editar"):
            html = self.html(key)
            for text in (
                "O que precisa ser feito?", "Setor", "Responsável", "Participantes", "Data do prazo", "Hora do prazo",
                "Instruções", "Marcadores", "Adicione outras pessoas para ajudar na execução desta tarefa.",
                "Defina o prazo e adicione marcadores para facilitar o acompanhamento.",
                "Explique o que fazer e como saber que o trabalho está pronto.",
                "Descreva as instruções para executar a tarefa, critérios de conclusão e outras informações importantes...",
            ):
                self.assertIn(text, html, msg=f"{key}: {text}")

    def test_the_forms_use_one_set_of_labels(self):
        create = TaskQuickCreateForm(organization=self.org, activity=self.activity)
        standalone = TaskQuickCreateStandaloneForm(organization=self.org)
        edit = TaskEditorForm(organization=self.org, task=self.task, can_change_responsavel=True, can_assign=True)
        for name, label in TASK_LABELS.items():
            for form in (create, standalone, edit):
                if name in form.fields:
                    self.assertEqual(form.fields[name].label, label, msg=f"{type(form).__name__}.{name}")

    def test_create_and_edit_have_the_same_title_placeholder(self):
        placeholder = "Ex.: Levantar quantitativo da garagem"
        for key in ("nova", "nova_global", "editar"):
            self.assertIn(f'placeholder="{placeholder}"', self.html(key), msg=key)

    def test_only_the_edit_window_shows_the_committed_deadline_and_sector_as_information(self):
        self.assertNotIn("Prazo que a equipe se comprometeu a cumprir", self.html("nova"))
        edit = self.html("editar")
        self.assertIn("Prazo que a equipe se comprometeu a cumprir", edit)
        self.assertIn("Para mudar de setor, use Mais ações", edit)
        self.assertNotIn('name="sector"', edit)

    def test_the_hashtag_shortcut_hint_is_only_for_new_tasks(self):
        self.assertIn("#marcador", self.html("nova"))
        self.assertNotIn("#marcador", self.html("editar"))

    def test_footer_buttons(self):
        for key in ("nova", "nova_global"):
            html = self.html(key)
            self.assertIn("Adicionar tarefa", html, msg=key)
            self.assertIn("Cancelar", html, msg=key)
        self.assertIn("Salvar alterações", self.html("editar"))
        self.assertNotIn("Adicionar tarefa", self.html("editar"))


class DeadlineFieldsTests(PopupTestCase):
    """Data e hora do prazo são dois campos, cada um com o seu rótulo."""

    def test_date_and_time_are_separate_inputs_with_their_own_labels(self):
        for key in ("nova", "nova_global", "editar"):
            html = self.html(key)
            self.assertRegex(html, r'<label class="task-label" for="id_requested_deadline_0">Data do prazo')
            self.assertRegex(html, r'<label class="task-label" for="id_requested_deadline_1">Hora do prazo')
            self.assertRegex(html, r'<input[^>]*type="date"[^>]*name="requested_deadline_0"|<input[^>]*name="requested_deadline_0"[^>]*type="date"')
            self.assertRegex(html, r'<input[^>]*type="time"[^>]*name="requested_deadline_1"|<input[^>]*name="requested_deadline_1"[^>]*type="time"')
            self.assertNotIn("datetime-local", html, msg=key)
            self.assertNotIn('name="requested_deadline"', html, msg=key)

    def test_edit_starts_with_the_current_deadline_split_in_two(self):
        Task.objects.filter(pk=self.task.pk).update(
            requested_deadline=timezone.make_aware(datetime.datetime(2026, 12, 15, 10, 30))
        )
        html = self.html("editar")
        self.assertIn('value="2026-12-15"', html)
        self.assertIn('value="10:30"', html)

    def post_new(self, **fields):
        creator = make_user("criador_prazo", self.org, [*MANAGER_ACTIONS, catalog.TAREFA_CRIAR])
        self.client.force_login(creator)
        payload = {"title": "Levantar quantitativo", "sector": self.comercial.pk, "responsavel": self.ryan.pk}
        payload.update(fields)
        return self.client.post(self.urls["nova"], payload, **AJAX)

    def deadline(self, task):
        return timezone.localtime(task.requested_deadline)

    def test_date_and_time(self):
        response = self.post_new(requested_deadline_0="2026-12-15", requested_deadline_1="10:30")
        self.assertEqual(response.status_code, 200)
        local = self.deadline(Task.objects.get(title="Levantar quantitativo"))
        self.assertEqual((local.date(), local.hour, local.minute), (datetime.date(2026, 12, 15), 10, 30))

    def test_date_without_time_lasts_until_the_end_of_the_day(self):
        response = self.post_new(requested_deadline_0="2026-12-15", requested_deadline_1="")
        self.assertEqual(response.status_code, 200)
        local = self.deadline(Task.objects.get(title="Levantar quantitativo"))
        self.assertEqual((local.date(), local.hour, local.minute), (datetime.date(2026, 12, 15), 23, 59))

    def test_no_deadline_stays_empty(self):
        response = self.post_new(requested_deadline_0="", requested_deadline_1="")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(Task.objects.get(title="Levantar quantitativo").requested_deadline)

    def test_time_without_date_is_reported_instead_of_silently_dropped(self):
        response = self.post_new(requested_deadline_0="", requested_deadline_1="10:30")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content)["errors"]["requested_deadline"], ["Informe a data do prazo."])
        self.assertFalse(Task.objects.filter(title="Levantar quantitativo").exists())

    def test_invalid_date_is_reported(self):
        response = self.post_new(requested_deadline_0="31/02/2026", requested_deadline_1="")
        self.assertEqual(response.status_code, 400)
        self.assertIn("requested_deadline", json.loads(response.content)["errors"])

    def test_the_error_is_shown_under_the_deadline_when_the_page_comes_back(self):
        self.client.force_login(self.manager)
        response = self.client.post(
            self.urls["nova"], {"title": "x", "sector": self.comercial.pk, "responsavel": self.ryan.pk,
                                "requested_deadline_0": "", "requested_deadline_1": "09:00"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Informe a data do prazo.")
        self.assertContains(response, 'value="09:00"')  # o que foi digitado não se perde


class ActivitySummaryTests(PopupTestCase):
    """A atividade aparece como cartão: título e "Cliente • Setor • N tarefas"."""

    def test_activity_summary_text(self):
        summary = activity_summary(self.activity)
        self.assertEqual(summary["title"], self.activity.title)
        self.assertIn("tarefa", summary["meta"])
        self.assertNotIn("Cliente", summary["meta"])  # só o nome do cliente, quando há
        self.assertIsNone(activity_summary(None))

    def test_summary_names_client_sector_and_counts_tasks(self):
        from core.models import Client

        client = Client.objects.create(organization=self.org, name="Convivy")
        self.activity.client = client
        self.activity.sector = self.compras
        self.activity.save(update_fields=["client", "sector"])
        total = self.activity.tasks.count()
        self.assertEqual(
            activity_summary(self.activity)["meta"], f"Convivy • Setor: Compras • {total} tarefa" + ("s" if total != 1 else "")
        )

    def test_singular_and_empty(self):
        other = self.new_activity(title="Vazia")
        self.assertEqual(activity_summary(other)["meta"], "Sem tarefas ainda")
        self.queued_task("Única", activity=other)
        self.assertEqual(activity_summary(other)["meta"], "1 tarefa")

    def test_inside_an_activity_the_summary_is_read_only(self):
        html = self.html("nova")
        self.assertIn(self.activity.title, html)
        self.assertIn("data-task-activity-summary>", html)  # visível
        self.assertNotIn("data-task-activity-change", html)
        self.assertNotIn('name="activity"', html)

    def test_edit_shows_the_activity_and_does_not_let_it_change(self):
        html = self.html("editar")
        self.assertIn(self.activity.title, html)
        self.assertIn("data-task-activity-summary>", html)
        self.assertNotIn("data-task-activity-change", html)

    def test_standalone_starts_with_the_picker_and_a_hidden_summary_with_change_button(self):
        html = self.html("nova_global")
        self.assertIn("data-task-activity-summary hidden", html)
        self.assertNotIn("data-task-activity-picker hidden", html)
        self.assertIn("data-task-activity-change", html)
        self.assertEqual(html.count('name="activity"'), 1)

    def test_standalone_keeps_the_chosen_activity_when_the_page_comes_back_with_an_error(self):
        response = self.client.post(self.urls["nova_global"], {"activity": self.activity.pk, "title": ""})
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("data-task-activity-picker hidden", html)
        self.assertIn("data-task-activity-summary>", html)
        self.assertIn(self.activity.title, html)
        self.assertEqual(response.context["activity_summary"]["id"], self.activity.pk)

    def test_standalone_ignores_an_activity_from_another_organization(self):
        from .models import Activity

        foreign = Activity.objects.create(
            organization=self.other_org, title="Alheia", owner=self.foreign, created_by=self.foreign
        )
        response = self.client.post(self.urls["nova_global"], {"activity": foreign.pk, "title": ""})
        self.assertIsNone(response.context["activity_summary"])
        self.assertNotIn("Alheia", response.content.decode())

    def test_search_returns_the_summary_for_the_card(self):
        response = self.client.get(reverse("activity-search"), {"q": self.activity.title}, **AJAX)
        result = response.json()["results"][0]
        self.assertEqual(result["id"], self.activity.pk)
        self.assertEqual(result["summary"], activity_summary(self.activity))

    def test_search_does_not_run_a_query_per_activity(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        def queries():
            with CaptureQueriesContext(connection) as context:
                self.client.get(reverse("activity-search"), {"q": "DEM"}, **AJAX)
            return len(context)

        few = queries()
        for index in range(8):
            self.new_activity(title=f"DEM extra {index}")
        self.assertEqual(queries(), few)

    def test_quick_create_of_an_activity_inside_the_picker_also_returns_the_summary(self):
        creator = make_user("criador_ativ", self.org, [catalog.ATIVIDADE_CRIAR])
        self.client.force_login(creator)
        response = self.client.post(
            reverse("activity-mini-create"),
            {"title": "Criada no seletor", "owner": creator.pk, "sector": self.comercial.pk},
            **AJAX,
        )
        self.assertEqual(response.status_code, 200)
        summary = response.json()["summary"]
        self.assertEqual(summary["title"], "Criada no seletor")
        self.assertIn("Sem tarefas ainda", summary["meta"])


class NoDuplicatedPickersTests(PopupTestCase):
    def test_each_picker_is_rendered_once_with_its_label(self):
        """Antes: setor e responsável apareciam soltos no topo e de novo na seção."""
        for key in ("nova", "nova_global"):
            html = self.html(key)
            self.assertEqual(html.count('name="sector"'), 1, msg=key)
            self.assertEqual(html.count('name="responsavel"'), 1, msg=key)
            self.assertRegex(html, r'<label[^>]*for="id_sector"', msg=key)
            self.assertRegex(html, r'<label[^>]*for="id_responsavel"', msg=key)
        self.assertEqual(self.html("nova_global").count('name="activity"'), 1)
        self.assertRegex(self.html("nova_global"), r'<label[^>]*for="id_activity"')
        self.assertIn("De qual demanda esta tarefa faz parte?", self.html("nova_global"))

    def test_edit_window_renders_the_responsavel_picker_once(self):
        html = self.html("editar")
        self.assertEqual(html.count('name="responsavel"'), 1)
        self.assertEqual(html.count('name="participantes"'), 1)

    def test_picker_widgets_count_as_visible_fields(self):
        for widget in (PersonPickerWidget(), ClientPickerWidget(), ActivityPickerWidget(), SectorPickerWidget()):
            self.assertFalse(widget.is_hidden, msg=type(widget).__name__)
        self.assertTrue(forms.HiddenInput().is_hidden)  # o hidden de verdade continua escondido

    def test_a_real_hidden_input_is_still_hidden(self):
        class F(forms.Form):
            token = forms.CharField(widget=forms.HiddenInput())
            person = forms.CharField(widget=PersonPickerWidget())

        form = F()
        self.assertEqual([field.name for field in form.hidden_fields()], ["token"])
        self.assertEqual([field.name for field in form.visible_fields()], ["person"])

    def test_other_windows_with_a_picker_show_their_label_and_help(self):
        self.client.force_login(self.owner)
        grant = make_user("trocador", self.org, [catalog.TAREFA_ALTERAR_RESPONSAVEL, catalog.ATIVIDADE_ALTERAR_DONO])
        self.client.force_login(grant)
        change_responsavel = self.client.get(reverse("task-change-responsavel", args=[self.task.pk]), **AJAX).content.decode()
        self.assertIn("Quem será o novo responsável?", change_responsavel)
        self.assertIn("Escolha a pessoa que acompanhará a tarefa até a conclusão.", change_responsavel)


class SectionContentTests(PopupTestCase):
    """As seções ficam sempre à vista; o que a pessoa preencheu não se perde quando a página volta com erro."""

    def test_nothing_is_hidden_behind_a_collapsed_block(self):
        for key in ("nova", "nova_global", "editar"):
            html = self.html(key)
            for name in ("participantes", "tags", "description", "requested_deadline_0"):
                self.assertIn(f'name="{name}"', html, msg=f"{key}: {name}")

    def test_what_was_filled_is_kept_when_the_page_comes_back_with_an_error(self):
        response = self.client.post(
            self.urls["nova"],
            {"description": "<p>Conferir</p>", "sector": self.comercial.pk, "participantes": [self.vitor.pk],
             "requested_deadline_0": "2026-12-15", "requested_deadline_1": "10:00", "tags": [self.urgente.pk]},
        )
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("Conferir", html)
        self.assertIn('value="2026-12-15"', html)
        self.assertIn('value="10:00"', html)
        self.assertIn("Urgente", html)  # o marcador escolhido segue na lista
        self.assertIn("vitor", html)  # o participante escolhido segue na lista
        self.assertContains(response, "Este campo é obrigatório.")  # título e responsável

    def test_edit_lists_pending_invites_and_participants_inside_section_three(self):
        from .models import TaskExecutor

        TaskExecutor.objects.create(task=self.task, user=self.paulo, added_by=self.owner)
        TaskService.add_executor(self.task, self.vitor, added_by=self.manager)  # convite pendente
        html = self.html("editar")
        section = html[html.index('id="task-section-3"'): html.index('id="task-section-4"')]
        self.assertIn("aguardando aceite", section)
        self.assertIn("paulo", section)

    def test_edit_shows_participants_as_information_to_who_cannot_assign(self):
        self.client.force_login(self.editor_only)
        html = self.html("editar")
        self.assertIn("Você não tem permissão para incluir ou remover participantes.", html)
        self.assertIn("Você não tem permissão para trocar o responsável.", html)


class CreateStillWorksTests(PopupTestCase):
    def test_creating_a_task_from_the_new_window(self):
        grants = make_user("criador", self.org, [*MANAGER_ACTIONS, catalog.TAREFA_CRIAR])
        self.client.force_login(grants)
        payload = {
            "title": "Entrevistar os candidatos",
            "sector": self.comercial.pk,
            "responsavel": self.ryan.pk,
            "participantes": [self.vitor.pk],
            "requested_deadline_0": "2026-12-15",
            "requested_deadline_1": "10:00",
            "tags": [self.urgente.pk],
            "description": "<p>Conduzir as entrevistas.</p>",
        }
        response = self.client.post(self.urls["nova"], payload, **AJAX)
        self.assertEqual(response.status_code, 200)
        task = Task.objects.get(title="Entrevistar os candidatos")
        self.assertEqual(task.responsavel, self.ryan)
        self.assertEqual(list(task.tags.all()), [self.urgente])
        self.assertTrue(task.assignments.filter(user=self.vitor, status="PENDENTE").exists())  # convite, não participante
        self.assertFalse(task.executors.filter(user=self.vitor).exists())
        self.assertEqual(timezone.localtime(task.requested_deadline).hour, 10)

    def test_creating_from_the_standalone_window_goes_to_the_chosen_activity(self):
        grants = make_user("criador2", self.org, [*MANAGER_ACTIONS, catalog.TAREFA_CRIAR])
        self.client.force_login(grants)
        response = self.client.post(
            self.urls["nova_global"],
            {"activity": self.activity.pk, "title": "Pela tela de tarefas", "sector": self.comercial.pk,
             "responsavel": self.ryan.pk},
            **AJAX,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Task.objects.get(title="Pela tela de tarefas").activity, self.activity)

    def test_the_same_fields_are_posted_when_editing(self):
        response = self.client.post(
            self.urls["editar"],
            {
                "title": "Entrevistar os candidatos",
                "responsavel": self.ryan.pk,
                "participantes": [self.vitor.pk],
                "requested_deadline_0": "2026-12-15",
                "requested_deadline_1": "10:00",
                "tags": [self.urgente.pk],
                "description": "<p>Conduzir as entrevistas.</p>",
            },
            **AJAX,
        )
        self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, "Entrevistar os candidatos")
        self.assertTrue(self.task.assignments.filter(user=self.vitor, status="PENDENTE").exists())

    def test_saving_works_when_the_task_id_is_not_an_activity_id(self):
        """O `pk` da URL é da tarefa. Nos outros testes tarefa e atividade têm o mesmo id (1) por acaso."""
        for index in range(4):
            last = self.queued_task(f"Tarefa de enchimento {index}")
        self.assertFalse(self.activity.__class__.objects.filter(pk=last.pk).exists())
        response = self.client.post(
            reverse("task-edit", args=[last.pk]),
            {"title": "Título novo", "responsavel": self.ryan.pk, "requested_deadline_0": "", "requested_deadline_1": ""},
            **AJAX,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {"redirect_url": reverse("task-detail", args=[last.pk])})
        last.refresh_from_db()
        self.assertEqual(last.title, "Título novo")

    def test_clearing_the_deadline_when_editing(self):
        Task.objects.filter(pk=self.task.pk).update(requested_deadline=timezone.now())
        response = self.client.post(
            self.urls["editar"],
            {"title": "Entrevista com Jovem Aprendizes", "responsavel": self.ryan.pk,
             "requested_deadline_0": "", "requested_deadline_1": ""},
            **AJAX,
        )
        self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.assertIsNone(self.task.requested_deadline)


class DrawerPatternTests(PopupTestCase):
    """O painel lateral da tarefa segue o mesmo padrão das janelas."""

    def drawer(self, task=None):
        response = self.client.get(reverse("task-drawer", args=[(task or self.task).pk]))
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def test_same_blocks_and_words_as_the_windows(self):
        html = self.drawer()
        positions = [
            html.index("<label>Setor</label>"),
            html.index("<label>Responsável</label>"),
            html.index("Participantes <span"),
            html.index("Prazo e detalhes <span"),
        ]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(len(self.folds(html)), 2)
        for text in (
            "Demanda: ", "Prazo pedido pelo solicitante", "Prazo que a equipe se comprometeu a cumprir",
            "Instruções para fazer a tarefa", "Marcadores", "Adicione outras pessoas para ajudar na tarefa.",
        ):
            self.assertIn(text, html, msg=text)

    def test_participants_and_invites_are_listed(self):
        from .models import TaskExecutor

        TaskExecutor.objects.create(task=self.task, user=self.paulo, added_by=self.owner)
        TaskService.add_executor(self.task, self.vitor, added_by=self.manager)
        html = self.drawer()
        self.assertEqual(self.folds(html)[0], " open")
        self.assertIn("paulo", html)
        self.assertIn("aguardando aceite", html)
        self.assertNotIn("Ainda não há participantes adicionais.", html)

    def test_empty_task_keeps_the_blocks_closed_but_says_so_inside(self):
        html = self.drawer()
        self.assertIn("Ainda não há participantes adicionais.", html)
        self.assertIn("Sem marcadores.", html)
        self.assertIn("Sem instruções.", html)

    def test_edit_button_only_for_who_can_edit_an_open_task(self):
        url = reverse("task-edit", args=[self.task.pk])
        self.assertIn(f'href="{url}" data-activity-action', self.drawer())
        self.client.force_login(self.stranger)
        self.assertNotIn(url, self.drawer())
        self.client.force_login(self.manager)
        TaskService.complete(self.task, self.ryan)
        self.assertNotIn(url, self.drawer())

    def test_tags_and_instructions_show_inside_the_details_block(self):
        Task.objects.filter(pk=self.task.pk).update(description="<p>Conduzir as entrevistas.</p>")
        self.task.tags.set([self.urgente])
        html = self.drawer()
        self.assertEqual(self.folds(html)[1], " open")
        self.assertIn("Conduzir as entrevistas.", html)
        self.assertIn("Urgente", html)
