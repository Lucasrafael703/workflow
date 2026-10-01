import datetime

from django.utils import timezone

from activities.services import ActivityService
from core.models import Client, Site

from . import suggestions
from .models import IntakeItem
from .testing import IntakeTestCase

# 01/10/2026 é uma quinta-feira.
QUINTA = timezone.make_aware(datetime.datetime(2026, 10, 1, 10, 0), timezone.get_current_timezone())


class SuggestTests(IntakeTestCase):
    def suggest(self, **kwargs):
        kwargs.setdefault("received_at", QUINTA)
        return suggestions.suggest(self.org, **kwargs)

    # -- cliente ---------------------------------------------------------------

    def test_client_by_name_in_text(self):
        result = self.suggest(subject="Pedido", raw_content="Somos da Convivy e precisamos de uma cotação.")
        self.assertEqual(result.client, self.convivy)
        self.assertTrue(any("Convivy" in reason for reason in result.reasons))

    def test_client_name_ignores_accents_and_case(self):
        Client.objects.create(organization=self.org, name="Construção Ágil")
        result = self.suggest(raw_content="Contato da CONSTRUCAO AGIL sobre a medição.")
        self.assertEqual(result.client.name, "Construção Ágil")

    def test_client_by_sender_domain(self):
        result = self.suggest(raw_content="Precisamos de uma cotação.", sender_email="joao@convivy.com.br")
        self.assertEqual(result.client, self.convivy)
        self.assertTrue(any("domínio" in reason for reason in result.reasons))

    def test_client_by_sender_subdomain(self):
        result = self.suggest(raw_content="Cotação.", sender_email="joao@mail.convivy.com.br")
        self.assertEqual(result.client, self.convivy)

    def test_free_mail_domain_is_ignored(self):
        Client.objects.create(organization=self.org, name="Pessoa Física", email="fulano@gmail.com")
        result = self.suggest(raw_content="Preciso de uma cotação.", sender_email="outro@gmail.com")
        self.assertIsNone(result.client)

    def test_two_clients_cited_means_none(self):
        result = self.suggest(raw_content="Reunião da Convivy com a Outra Construtora sobre o contrato.")
        self.assertIsNone(result.client)
        self.assertTrue(any("mais de um cliente" in reason for reason in result.reasons))

    def test_sender_domain_breaks_a_tie_between_named_clients(self):
        result = self.suggest(
            raw_content="Reunião da Convivy com a Outra Construtora.", sender_email="ana@convivy.com.br"
        )
        self.assertEqual(result.client, self.convivy)

    def test_longer_name_wins_over_the_name_it_contains(self):
        longer = Client.objects.create(organization=self.org, name="Convivy Engenharia")
        result = self.suggest(raw_content="Pedido da Convivy Engenharia para o próximo mês.")
        self.assertEqual(result.client, longer)

    def test_inactive_and_foreign_clients_are_not_suggested(self):
        self.convivy.is_active = False
        self.convivy.save()
        result = self.suggest(raw_content="Convivy e Cliente Alheio pedem uma cotação.")
        self.assertIsNone(result.client)

    # -- obra ------------------------------------------------------------------

    def test_site_by_name_also_gives_its_client(self):
        result = self.suggest(raw_content="Orçamento para a obra Residencial Aurora.")
        self.assertEqual(result.site, self.aurora)
        self.assertEqual(result.client, self.convivy)
        self.assertTrue(any("pertence" in reason for reason in result.reasons))

    def test_site_of_another_client_is_not_suggested(self):
        result = self.suggest(raw_content="Outra Construtora pede orçamento para Residencial Aurora.")
        self.assertEqual(result.client, self.outra)
        self.assertIsNone(result.site)

    def test_site_without_client_serves_any_client(self):
        free = Site.objects.create(organization=self.org, name="Galpão Norte")
        result = self.suggest(raw_content="Outra Construtora quer visitar o Galpão Norte.")
        self.assertEqual(result.client, self.outra)
        self.assertEqual(result.site, free)

    def test_foreign_site_is_not_suggested(self):
        result = self.suggest(raw_content="Orçamento para a Obra Alheia.")
        self.assertIsNone(result.site)

    # -- setor -----------------------------------------------------------------

    def test_sector_named_in_subject(self):
        result = self.suggest(subject="Compras: cotação de cabos", raw_content="Segue a lista.")
        self.assertEqual(result.sector, self.compras)

    def test_sector_named_only_in_body_is_not_used(self):
        result = self.suggest(subject="Cotação de cabos", raw_content="Pedir ao pessoal de compras.")
        self.assertIsNone(result.sector)

    def test_sector_from_client_history(self):
        for index in range(2):
            ActivityService.create_activity(
                self.org, f"Anterior {index}", self.triador, self.triador, client=self.convivy, sector=self.comercial
            )
        result = self.suggest(raw_content="A Convivy precisa de nova proposta.")
        self.assertEqual(result.sector, self.comercial)
        self.assertTrue(any("últimas demandas" in reason for reason in result.reasons))

    def test_history_with_a_single_activity_is_not_enough(self):
        ActivityService.create_activity(
            self.org, "Anterior", self.triador, self.triador, client=self.convivy, sector=self.comercial
        )
        result = self.suggest(raw_content="A Convivy precisa de nova proposta.")
        self.assertIsNone(result.sector)

    def test_history_tie_means_no_sector(self):
        for sector in (self.comercial, self.comercial, self.compras, self.compras):
            ActivityService.create_activity(
                self.org, "Anterior", self.triador, self.triador, client=self.convivy, sector=sector
            )
        result = self.suggest(raw_content="A Convivy precisa de nova proposta.")
        self.assertIsNone(result.sector)

    # -- título e prazo --------------------------------------------------------

    def test_title_from_subject(self):
        result = self.suggest(subject="RE: Orçamento do gerador", raw_content="Bom dia")
        self.assertEqual(result.title, "Orçamento do gerador")

    def test_title_from_first_line_without_subject(self):
        result = self.suggest(raw_content="Bom dia,\n\nPrecisamos do orçamento do gerador.")
        self.assertEqual(result.title, "Precisamos do orçamento do gerador.")

    def test_deadline_in_body_needs_a_cue(self):
        with_cue = self.suggest(raw_content="Precisamos disso até sexta.")
        without = self.suggest(raw_content="A reunião é sexta.")
        self.assertEqual(timezone.localtime(with_cue.deadline).date(), datetime.date(2026, 10, 2))
        self.assertIsNone(without.deadline)

    def test_deadline_in_subject_does_not_need_a_cue(self):
        result = self.suggest(subject="Medição outubro - sexta", raw_content="Segue.")
        self.assertEqual(timezone.localtime(result.deadline).date(), datetime.date(2026, 10, 2))

    # -- confiança -------------------------------------------------------------

    def test_full_match_scores_one_hundred(self):
        for index in range(2):
            ActivityService.create_activity(
                self.org, f"Anterior {index}", self.triador, self.triador, client=self.convivy, sector=self.comercial
            )
        result = self.suggest(
            subject="Comercial: gerador",
            raw_content="Convivy precisa de orçamento na obra Residencial Aurora até sexta.",
        )
        self.assertEqual(result.confidence, 100)

    def test_partial_scores_add_up(self):
        result = self.suggest(subject="Gerador", raw_content="A Convivy pede uma proposta até sexta.")
        # título do assunto 15 + cliente 35 + prazo 25
        self.assertEqual(result.confidence, 75)

    def test_nothing_recognised_scores_only_the_title(self):
        result = self.suggest(raw_content="Preciso de ajuda com uma coisa.")
        self.assertEqual(result.confidence, 5)
        self.assertEqual(result.client, None)
        self.assertEqual(result.deadline, None)

    def test_empty_input_does_not_break(self):
        result = self.suggest(raw_content="")
        self.assertEqual(result.confidence, 0)
        self.assertEqual(result.title, "")
        self.assertEqual(result.reasons, [])


class ConfidenceLevelTests(IntakeTestCase):
    def test_level_boundaries(self):
        cases = {0: "BAIXA", 39: "BAIXA", 40: "MEDIA", 69: "MEDIA", 70: "ALTA", 100: "ALTA"}
        for score, expected in cases.items():
            item = IntakeItem(confidence=score)
            self.assertEqual(item.confidence_level, expected, score)
        self.assertEqual(IntakeItem(confidence=70).confidence_label, "Alta")
