"""As janelas de tarefa — Nova tarefa (dentro de uma atividade e fora dela) e
Editar tarefa — têm o mesmo padrão:

    título · setor · responsável
    ▸ Participantes (opcional)
    ▸ Prazo e detalhes (opcional)

Também trava o defeito que existia antes: os seletores (setor, responsável,
atividade) herdavam de campo escondido, então apareciam sem rótulo e, no popup
de Nova tarefa, desenhados duas vezes.
"""

import re

from django.urls import reverse

from acessos import catalog
from core.widgets import (
    ActivityPickerWidget,
    ClientPickerWidget,
    PersonPickerWidget,
    SectorPickerWidget,
)
from django import forms

from .forms import TASK_LABELS, TaskEditorForm, TaskQuickCreateForm, TaskQuickCreateStandaloneForm
from .models import Task
from .services import TaskService
from .test_task_editor import AJAX, MANAGER_ACTIONS, EditorTestCase
from .testing import make_user


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
        return re.findall(r'<details class="fold"( open)?>', html)


class SamePatternTests(PopupTestCase):
    def test_the_three_windows_share_the_same_order_of_blocks(self):
        for key in ("nova", "nova_global", "editar"):
            html = self.html(key)
            positions = [
                html.index('name="title"'),
                html.index('for="id_sector"') if key != "editar" else html.index("<label>Setor</label>"),
                html.index('for="id_responsavel"'),
                html.index("Participantes <span"),
                html.index("Prazo e detalhes <span"),
                html.index('name="modal-foot"') if 'name="modal-foot"' in html else html.index("modal__foot"),
            ]
            self.assertEqual(positions, sorted(positions), msg=key)

    def test_exactly_two_collapsible_blocks_in_each(self):
        for key in ("nova", "nova_global", "editar"):
            self.assertEqual(len(self.folds(self.html(key))), 2, msg=key)

    def test_same_questions_in_every_window(self):
        for key in ("nova", "nova_global", "editar"):
            html = self.html(key)
            for text in (
                "O que precisa ser feito?", "Setor", "Responsável", "Participantes", "Prazo pedido pelo solicitante",
                "Instruções para fazer a tarefa", "Marcadores", "Adicione outras pessoas para ajudar na tarefa.",
                "Defina o prazo, adicione instruções e marcadores.",
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
        placeholder = "Ex.: Entrevistar os candidatos"
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


class NoDuplicatedPickersTests(PopupTestCase):
    def test_each_picker_is_rendered_once_with_its_label(self):
        """Antes: setor e responsável apareciam soltos no topo e de novo na seção."""
        for key in ("nova", "nova_global"):
            html = self.html(key)
            self.assertEqual(html.count('name="sector"'), 1, msg=key)
            self.assertEqual(html.count('name="responsavel"'), 1, msg=key)
            self.assertIn('<label for="id_sector"', html, msg=key)
            self.assertIn('<label for="id_responsavel"', html, msg=key)
        self.assertEqual(self.html("nova_global").count('name="activity"'), 1)
        self.assertIn('<label for="id_activity"', self.html("nova_global"))
        self.assertIn("De qual atividade esta tarefa faz parte?", self.html("nova_global"))

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


class FoldStateTests(PopupTestCase):
    def test_new_task_starts_with_both_blocks_closed(self):
        self.assertEqual(self.folds(self.html("nova")), ["", ""])
        self.assertEqual(self.folds(self.html("nova_global")), ["", ""])

    def test_a_block_opens_when_it_has_an_error_or_content(self):
        url = self.urls["nova"]
        # sem título (erro) mas com instruções preenchidas: "Prazo e detalhes" abre
        response = self.client.post(url, {"description": "<p>Conferir</p>", "sector": self.comercial.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.folds(response.content.decode()), ["", " open"])
        # com um participante escolhido, "Participantes" abre
        response = self.client.post(url, {"participantes": [self.vitor.pk]})
        self.assertEqual(self.folds(response.content.decode())[0], " open")

    def test_edit_opens_what_is_already_filled(self):
        self.assertEqual(self.folds(self.html("editar")), ["", ""])  # tarefa sem nada a mostrar
        Task.objects.filter(pk=self.task.pk).update(description="<p>Conduzir as entrevistas.</p>")
        TaskService.add_executor(self.task, self.vitor, added_by=self.manager)  # convite pendente
        self.assertEqual(self.folds(self.html("editar")), [" open", " open"])

    def test_edit_with_a_participant_opens_participants(self):
        from .models import TaskExecutor

        TaskExecutor.objects.create(task=self.task, user=self.vitor, added_by=self.owner)
        self.assertEqual(self.folds(self.html("editar"))[0], " open")

    def test_the_modal_script_opens_a_block_that_hides_an_error(self):
        # modal.js faz `target.closest("details").open = true` ao mostrar um erro de campo;
        # a estrutura precisa manter o campo DENTRO do <details>.
        html = self.html("nova")
        start = html.index('<details class="fold">')
        fold = html[start:html.index("</details>", start)]
        self.assertIn('name="participantes"', fold)
        second = html[html.index("Prazo e detalhes <span"):]
        for name in ("requested_deadline", "description", "tags"):
            self.assertIn(f'name="{name}"', second, msg=name)


class CreateStillWorksTests(PopupTestCase):
    def test_creating_a_task_from_the_new_window(self):
        grants = make_user("criador", self.org, [*MANAGER_ACTIONS, catalog.TAREFA_CRIAR])
        self.client.force_login(grants)
        payload = {
            "title": "Entrevistar os candidatos",
            "sector": self.comercial.pk,
            "responsavel": self.ryan.pk,
            "participantes": [self.vitor.pk],
            "requested_deadline": "2026-12-15T10:00",
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

    def test_the_same_fields_are_posted_when_editing(self):
        response = self.client.post(
            self.urls["editar"],
            {
                "title": "Entrevistar os candidatos",
                "responsavel": self.ryan.pk,
                "participantes": [self.vitor.pk],
                "requested_deadline": "2026-12-15T10:00",
                "tags": [self.urgente.pk],
                "description": "<p>Conduzir as entrevistas.</p>",
            },
            **AJAX,
        )
        self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, "Entrevistar os candidatos")
        self.assertTrue(self.task.assignments.filter(user=self.vitor, status="PENDENTE").exists())


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
            "Atividade: ", "Prazo pedido pelo solicitante", "Prazo que a equipe se comprometeu a cumprir",
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
