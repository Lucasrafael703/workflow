"""Nova atividade e Editar atividade: uma janela só, em três etapas.

    1. Informações principais   2. Informações do cliente   3. Descrição e arquivos

O backend de criação/edição é o de sempre; o que muda é a apresentação, os campos
(sem upload, marcadores, solicitante interno nem anotações internas) e as regras
de obrigatoriedade e de dependência Cliente → Obra → Centro de custo.
"""

import json

from django.urls import reverse
from django.utils import timezone

from acessos import catalog
from acessos.testing import grant_action
from core.models import Client, Company, CostCenter, Site
from core.sanitize import sanitize_description
from core.widgets import CompanyPickerWidget, PersonPickerWidget, RichTextWidget, SitePickerWidget

from .forms import ActivityEditorForm
from .models import Activity
from .test_views import ViewTestCase

AJAX = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


class ModalTestCase(ViewTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.requester)
        self.cliente = Client.objects.create(organization=self.org, name="Construtora Alfa")
        self.outro_cliente = Client.objects.create(organization=self.org, name="Construtora Beta")
        self.obra = Site.objects.create(organization=self.org, name="Arena Norte", client=self.cliente)
        self.obra_solta = Site.objects.create(organization=self.org, name="Obra sem cliente")
        self.centro = CostCenter.objects.create(organization=self.org, name="Elétrica", site=self.obra)
        self.centro_geral = CostCenter.objects.create(organization=self.org, name="Administrativo")
        self.empresa = Company.objects.create(organization=self.org, name="Biasi Engenharia")

    def html(self, name="activity-create", *args):
        response = self.client.get(reverse(name, args=args), **AJAX)
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def payload(self, **changes):
        data = {
            "title": "Entrega organizada", "owner": self.requester.pk, "sector": self.sector.pk,
            "urgency": "MEDIA", "acao": "publicar",
        }
        data.update(changes)
        return data


class StructureTests(ModalTestCase):
    def test_three_steps_with_the_expected_names(self):
        html = self.html()
        for name in ("Informações principais", "Informações do cliente", "Descrição e arquivos"):
            self.assertIn(name, html)
        self.assertEqual(html.count("data-step-panel="), 3)
        self.assertEqual(html.count("data-step-indicator="), 3)
        for subtitle in (
            "Dados básicos da demanda e responsáveis.",
            "Dados relacionados ao cliente, obra e centro de custo.",
            "Informações complementares para a execução da demanda.",
        ):
            self.assertIn(subtitle, html)

    def test_header_and_footer(self):
        html = self.html()
        self.assertIn("Nova demanda", html)
        self.assertIn("Preencha as informações para criar uma nova demanda.", html)
        for marker in ("data-step-prev", "data-step-next", "data-step-submit"):
            self.assertIn(marker, html)
        self.assertIn("Cancelar", html)
        self.assertIn("Criar demanda", html)

    def test_step_one_fields_in_the_expected_order(self):
        html = self.html()
        positions = [html.index(f'data-field="{name}"') for name in ("title", "owner", "sector", "requested_deadline", "urgency", "company")]
        self.assertEqual(positions, sorted(positions))
        for label in ("Nome da demanda", "Atribuído a", "Setor responsável", "Prazo de vencimento", "Urgência", "Organização"):
            self.assertIn(label, html)

    def test_step_two_and_three_fields(self):
        html = self.html()
        for label in ("Cliente", "Obra", "Centro de custo", "Solicitante (Externo)", "Endereço complementar", "Observações", "Link / caminho dos arquivos"):
            self.assertIn(label, html, msg=label)
        for name in ("client", "site", "cost_center", "external_requester", "address", "description", "files_location"):
            self.assertEqual(html.count(f'name="{name}"'), 1, msg=name)

    def test_helper_texts_and_placeholders(self):
        html = self.html()
        for text in (
            "Descreva a entrega esperada. Ex.: Orçamento do gerador aprovado.",
            "Essa pessoa será responsável pela entrega e acompanhará as tarefas.",
            "Escolha o setor que será responsável por esta demanda.",
            "Data e horário para conclusão da demanda. Sem horário, vale até o fim do dia.",
            "Ex.: Comercial, Engenharia, Operações, etc.",
            "Selecione o cliente relacionado a esta demanda.",
            "Selecione a obra relacionada, se houver.",
            "Escolha o centro de custo para apropriação desta demanda.",
            "Pessoa que solicitou a demanda (cliente, fornecedor, etc.).",
            "Informações adicionais do local, se necessário.",
            "Inclua todas as informações necessárias para a execução desta demanda.",
            "Ex.: Material disponível na obra", "Buscar pessoa...", "Selecionar setor", "Selecionar organização",
            "Selecionar cliente", "Selecionar obra", "Selecionar centro de custo", "Nome do solicitante",
            "Ex.: Rua, número, complemento, bairro, cidade", "Cole aqui o link ou caminho dos arquivos",
            "Descreva aqui os detalhes da demanda",
        ):
            self.assertIn(text, html, msg=text)

    def test_required_marks_are_on_name_owner_and_sector_only(self):
        html = self.html()
        self.assertEqual(html.count("data-required"), 3)
        for name in ("title", "owner", "sector"):
            self.assertRegex(html, rf'data-field="{name}" data-required')

    def test_urgency_is_three_pills_with_medium_as_default(self):
        html = self.html()
        for tone in ("low", "medium", "high"):
            self.assertIn(f"activity-urgency-option {tone}", html)
        self.assertRegex(html, r'value="MEDIA"[^>]*checked')
        for label in ("Baixa", "Média", "Alta"):
            self.assertIn(label, html)

    def test_deadline_is_a_date_and_a_time(self):
        html = self.html()
        self.assertIn('name="requested_deadline_0"', html)
        self.assertIn('name="requested_deadline_1"', html)
        self.assertIn('type="date"', html)
        self.assertIn('type="time"', html)
        self.assertIn('for="id_requested_deadline_0"', html)

    def test_there_is_no_upload_and_no_dropped_field(self):
        html = self.html()
        self.assertNotIn('type="file"', html)
        self.assertNotIn("multipart/form-data", html)
        for name in ("internal_notes", "requested_by", "tags", "files"):
            self.assertNotIn(f'name="{name}"', html, msg=name)
        for text in ("Arraste", "Adicionar arquivos", "Anotações para a equipe", "Marcadores", "Contexto da demanda"):
            self.assertNotIn(text, html, msg=text)

    def test_notes_editor_has_the_requested_tools_and_a_counter(self):
        html = self.html()
        for command in ("bold", "italic", "strikeThrough", "insertUnorderedList", "insertOrderedList", "createLink"):
            self.assertIn(f'data-command="{command}"', html, msg=command)
        self.assertIn("0/2000", html)
        self.assertIn("data-rich-text-counter", html)

    def test_editor_is_the_same_for_create_and_edit(self):
        grant_action(self.requester, catalog.ATIVIDADE_EDITAR, organization=self.org)
        create = self.client.get(reverse("activity-create"))
        edit = self.client.get(reverse("activity-edit", args=[self.activity.pk]))
        self.assertTemplateUsed(create, "activities/activity_form.html")
        self.assertTemplateUsed(edit, "activities/activity_form.html")
        create_html, edit_html = create.content.decode(), edit.content.decode()
        for name in ("Informações principais", "Informações do cliente", "Descrição e arquivos", "Link / caminho dos arquivos"):
            self.assertIn(name, edit_html)
        self.assertEqual(create_html.count("data-step-panel="), edit_html.count("data-step-panel="))
        self.assertIn("Editar demanda", edit_html)
        self.assertIn("Atualize as informações da demanda.", edit_html)
        self.assertIn("Salvar alterações", edit_html)
        self.assertNotIn("Criar demanda", edit_html.replace("Nova demanda", ""))
        self.assertEqual(edit.context["form"].initial.get("title") or edit.context["form"]["title"].value(), self.activity.title)

    def test_stepper_and_nav_buttons_are_hidden_until_javascript_runs(self):
        html = self.html()
        self.assertRegex(html, r'data-stepper role="list" aria-label="Etapas" hidden')
        self.assertRegex(html, r"data-step-next hidden")

    def test_links_that_open_the_editor_follow_its_result(self):
        for name, args in (("activity-list", ()), ("home", ())):
            html = self.client.get(reverse(name, args=args)).content.decode()
            self.assertIn("data-activity-navigate", html, msg=name)
        grant_action(self.requester, catalog.ATIVIDADE_EDITAR, organization=self.org)
        detail = self.client.get(reverse("activity-detail", args=[self.activity.pk])).content.decode()
        self.assertRegex(detail, r'activity-edit[^>]*data-activity-action data-activity-navigate|data-activity-action data-activity-navigate[^>]*menu-dots__item')


class ValidationTests(ModalTestCase):
    def test_name_owner_and_sector_are_required(self):
        response = self.client.post(reverse("activity-create"), {"acao": "publicar"})
        self.assertEqual(response.status_code, 200)
        errors = response.context["form"].errors
        for field in ("title", "owner", "sector"):
            self.assertIn(field, errors)
        self.assertEqual(response.context["initial_step"], 1)

    def test_ajax_errors_name_each_field(self):
        response = self.client.post(reverse("activity-create"), {"acao": "publicar", "title": "x"}, **AJAX)
        self.assertEqual(response.status_code, 400)
        errors = response.json()["errors"]
        self.assertIn("owner", errors)
        self.assertIn("sector", errors)
        self.assertNotIn("title", errors)

    def test_nothing_is_created_when_a_later_step_fails(self):
        count = Activity.objects.count()
        response = self.client.post(reverse("activity-create"), self.payload(client=self.cliente.pk, site=self.obra_solta.pk, **{}), **AJAX)
        # obra sem cliente é aceita (vale para qualquer cliente): criou
        self.assertEqual(response.status_code, 200)
        other = Site.objects.create(organization=self.org, name="Obra da Beta", client=self.outro_cliente)
        response = self.client.post(reverse("activity-create"), self.payload(title="Outra", client=self.cliente.pk, site=other.pk), **AJAX)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Activity.objects.count(), count + 1)

    def test_error_in_the_second_step_is_reported_with_its_field(self):
        other = Site.objects.create(organization=self.org, name="Obra da Beta", client=self.outro_cliente)
        response = self.client.post(reverse("activity-create"), self.payload(client=self.cliente.pk, site=other.pk))
        self.assertEqual(response.status_code, 200)
        self.assertIn("site", response.context["form"].errors)
        self.assertEqual(response.context["initial_step"], 2)
        self.assertIn("pertence a outro cliente", response.content.decode())

    def test_cost_center_must_belong_to_the_chosen_site(self):
        other_site = Site.objects.create(organization=self.org, name="Outra obra", client=self.cliente)
        response = self.client.post(reverse("activity-create"), self.payload(site=other_site.pk, cost_center=self.centro.pk))
        self.assertIn("cost_center", response.context["form"].errors)
        ok = self.client.post(reverse("activity-create"), self.payload(title="Certa", site=self.obra.pk, cost_center=self.centro.pk))
        self.assertEqual(ok.status_code, 302)
        general = self.client.post(reverse("activity-create"), self.payload(title="Geral", site=self.obra.pk, cost_center=self.centro_geral.pk))
        self.assertEqual(general.status_code, 302)

    def test_other_organizations_data_is_rejected(self):
        foreign = Client.objects.create(organization=self.other_org, name="De fora")
        response = self.client.post(reverse("activity-create"), self.payload(client=foreign.pk))
        self.assertIn("client", response.context["form"].errors)

    def test_title_only_legacy_picker_submission_still_works(self):
        response = self.client.post(reverse("activity-mini-create"), {"title": "Seletor legado"}, **AJAX)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Activity.objects.get(pk=response.json()["id"]).sector_id, None)

    def test_the_old_draft_flow_does_not_require_the_essentials(self):
        response = self.client.post(reverse("activity-create"), {"acao": "rascunho", "urgency": "MEDIA"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Activity.objects.filter(status=Activity.Status.RASCUNHO).exists())

    def test_files_location_accepts_links_and_paths(self):
        for value in (
            "https://drive.google.com/drive/folders/abc",
            r"C:\Projetos\Arena Center Norte\Elétrica",
            r"\\Servidor\Comercial\Orçamentos\Projeto X",
        ):
            response = self.client.post(reverse("activity-create"), self.payload(title=f"Com {value[:8]}", files_location=f"  {value}  "))
            self.assertEqual(response.status_code, 302, msg=value)
            self.assertEqual(Activity.objects.get(title=f"Com {value[:8]}").files_location, value)

    def test_files_location_is_limited(self):
        response = self.client.post(reverse("activity-create"), self.payload(files_location="x" * 501))
        self.assertIn("files_location", response.context["form"].errors)

    def test_description_keeps_the_new_formatting_and_drops_scripts(self):
        clean = sanitize_description("<p><s>riscado</s> <strike>também</strike> <strong>negrito</strong><script>alert(1)</script></p><ol><li>um</li></ol>")
        self.assertIn("<s>riscado</s>", clean)
        self.assertIn("<strike>também</strike>", clean)
        self.assertIn("<ol><li>um</li></ol>", clean)
        self.assertNotIn("script", clean)
        self.client.post(reverse("activity-create"), self.payload(description="<p><s>x</s></p><script>1</script>"))
        self.assertEqual(Activity.objects.get(title="Entrega organizada").description, "<p><s>x</s></p>")

    def test_a_long_description_is_not_cut_off(self):
        response = self.client.post(reverse("activity-create"), self.payload(description="<p>" + "a" * 2500 + "</p>"))
        self.assertEqual(response.status_code, 302)  # o contador é só orientação


class SubmitTests(ModalTestCase):
    def test_ajax_success_answers_with_the_page_to_go_to(self):
        response = self.client.post(reverse("activity-create"), self.payload(), **AJAX)
        self.assertEqual(response.status_code, 200)
        activity = Activity.objects.get(title="Entrega organizada")
        self.assertIn(reverse("activity-detail", args=[activity.pk]), response.json()["redirect_url"])

    def test_the_activity_is_only_created_on_the_last_submit(self):
        count = Activity.objects.count()
        self.client.get(reverse("activity-create"), **AJAX)
        self.assertEqual(Activity.objects.count(), count)

    def test_edit_saves_everything_and_answers_json(self):
        grant_action(self.requester, catalog.ATIVIDADE_EDITAR, organization=self.org)
        response = self.client.post(
            reverse("activity-edit", args=[self.activity.pk]),
            self.payload(title="Renomeada", client=self.cliente.pk, site=self.obra.pk, cost_center=self.centro.pk,
                         company=self.empresa.pk, external_requester="Fulano", address="Rua B, 2"),
            **AJAX,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("redirect_url", response.json())
        self.activity.refresh_from_db()
        self.assertEqual((self.activity.title, self.activity.client_id, self.activity.site_id), ("Renomeada", self.cliente.pk, self.obra.pk))
        self.assertEqual((self.activity.cost_center_id, self.activity.company_id), (self.centro.pk, self.empresa.pk))
        self.assertEqual((self.activity.external_requester, self.activity.address), ("Fulano", "Rua B, 2"))

    def test_edit_loads_the_current_values_in_every_step(self):
        grant_action(self.requester, catalog.ATIVIDADE_EDITAR, organization=self.org)
        Activity.objects.filter(pk=self.activity.pk).update(
            client=self.cliente, site=self.obra, external_requester="Fulano", files_location="https://x.example/pasta",
            description="<p>Texto atual</p>", address="Rua A",
        )
        response = self.client.get(reverse("activity-edit", args=[self.activity.pk]))
        html = response.content.decode()
        for text in ("Fulano", "https://x.example/pasta", "Texto atual", "Rua A", "Construtora Alfa", "Arena Norte"):
            self.assertIn(text, html, msg=text)

    def test_owner_without_transfer_permission_is_shown_but_not_editable(self):
        grant_action(self.requester, catalog.ATIVIDADE_EDITAR, organization=self.org)
        html = self.client.get(reverse("activity-edit", args=[self.activity.pk])).content.decode()
        self.assertIn("activity-input--static", html)
        self.assertIn("A transferência de responsabilidade exige permissão específica.", html)

    def test_activity_detail_shows_the_new_fields(self):
        Activity.objects.filter(pk=self.activity.pk).update(
            external_requester="Maria Externa", files_location="https://drive.example.com/x"
        )
        html = self.client.get(reverse("activity-detail", args=[self.activity.pk])).content.decode()
        self.assertIn("Maria Externa", html)
        self.assertIn('href="https://drive.example.com/x"', html)
        Activity.objects.filter(pk=self.activity.pk).update(files_location=r"\\Servidor\Pasta")
        html = self.client.get(reverse("activity-detail", args=[self.activity.pk])).content.decode()
        self.assertIn(r"\\Servidor\Pasta", html)
        self.assertNotIn('href="\\\\Servidor', html)


class DependentSearchTests(ModalTestCase):
    def names(self, name, **params):
        response = self.client.get(reverse(name), params)
        return {row["name"] for row in response.json()["results"]}

    def test_sites_are_filtered_by_client(self):
        self.assertEqual(self.names("site-search"), {"Arena Norte", "Obra sem cliente"})
        self.assertEqual(self.names("site-search", client=self.cliente.pk), {"Arena Norte"})
        self.assertEqual(self.names("site-search", client=self.outro_cliente.pk), set())

    def test_an_invalid_client_filter_shows_nothing(self):
        self.assertEqual(self.names("site-search", client="abc"), set())
        self.assertEqual(self.names("site-search", client=""), {"Arena Norte", "Obra sem cliente"})

    def test_cost_centers_are_filtered_by_site_and_keep_the_general_ones(self):
        self.assertEqual(self.names("costcenter-search"), {"Elétrica", "Administrativo"})
        self.assertEqual(self.names("costcenter-search", site=self.obra.pk), {"Elétrica", "Administrativo"})
        self.assertEqual(self.names("costcenter-search", site=self.obra_solta.pk), {"Administrativo"})

    def test_searches_stay_inside_the_organization(self):
        Site.objects.create(organization=self.other_org, name="Obra alheia", client=None)
        self.assertNotIn("Obra alheia", self.names("site-search"))

    def test_the_pickers_are_wired_to_their_parent_field(self):
        html = self.html()
        self.assertIn('data-filter-field="id_client" data-filter-param="client"', html)
        self.assertIn('data-filter-field="id_site" data-filter-param="site"', html)
        self.assertIn('id="id_client"', html)
        self.assertIn('id="id_site"', html)


class WidgetTests(ModalTestCase):
    def test_pickers_carry_their_own_icon(self):
        html = self.html()
        for icon in ("user", "users", "building", "hardhat", "dollar"):
            self.assertIn(f'href="#i-{icon}"', html, msg=icon)

    def test_picker_widgets_accept_a_custom_empty_label(self):
        widget = CompanyPickerWidget(empty_label="Selecionar organização", icon="building")
        self.assertIn("Selecionar organização", widget.render("company", None))
        self.assertIn("#i-building", widget.render("company", None))
        self.assertIn("Selecionar empresa", CompanyPickerWidget().render("company", None))

    def test_dependent_picker_renders_its_filter_attributes_only_when_asked(self):
        plain = SitePickerWidget().render("site", None)
        self.assertNotIn("data-filter-field", plain)
        linked = SitePickerWidget(filter_field_id="id_client", filter_param="client").render("site", None)
        self.assertIn('data-filter-field="id_client" data-filter-param="client"', linked)

    def test_rich_text_widget_options(self):
        plain = RichTextWidget().render("description", "")
        self.assertNotIn("data-rich-text-counter", plain)
        counted = RichTextWidget(placeholder="Escreva aqui", limit=2000).render("description", "<p>oi</p>")
        self.assertIn('data-placeholder="Escreva aqui"', counted)
        self.assertIn("0/2000", counted)
        self.assertIn("<p>oi</p>", counted)

    def test_person_picker_keeps_working_for_other_screens(self):
        self.assertIn("Selecionar pessoa", PersonPickerWidget().render("owner", None))
        self.assertIn("#i-search", PersonPickerWidget().render("owner", None))

    def test_form_steps_cover_every_field_once(self):
        form = ActivityEditorForm(organization=self.org)
        listed = [name for names in form.STEP_FIELDS.values() for name in names]
        self.assertEqual(sorted(listed), sorted(form._meta.fields))
        self.assertEqual(len(listed), len(set(listed)))
        self.assertEqual([step["number"] for step in form.steps], [1, 2, 3])

    def test_deadline_is_shown_in_local_time_in_its_own_inputs(self):
        Activity.objects.filter(pk=self.activity.pk).update(requested_deadline=timezone.make_aware(timezone.datetime(2026, 10, 5, 16, 0)))
        grant_action(self.requester, catalog.ATIVIDADE_EDITAR, organization=self.org)
        html = self.client.get(reverse("activity-edit", args=[self.activity.pk])).content.decode()
        self.assertIn('value="2026-10-05"', html)
        self.assertIn('value="16:00"', html)
