import datetime

from django.test import SimpleTestCase
from django.utils import timezone

from . import textparse


def local(year, month, day, hour=10, minute=0):
    return timezone.make_aware(datetime.datetime(year, month, day, hour, minute), timezone.get_current_timezone())


# 01/10/2026 é uma quinta-feira.
QUINTA = local(2026, 10, 1)


class NormalizeTests(SimpleTestCase):
    def test_removes_accents_case_and_extra_spaces(self):
        self.assertEqual(textparse.normalize("  Orçamento   da ÁGUA\nFria "), "orcamento da agua fria")

    def test_empty_values(self):
        self.assertEqual(textparse.normalize(None), "")
        self.assertEqual(textparse.normalize(""), "")

    def test_contains_phrase_matches_whole_words_only(self):
        text = textparse.normalize("Obra Aurora, bloco B.")
        self.assertTrue(textparse.contains_phrase(text, "aurora"))
        self.assertTrue(textparse.contains_phrase(text, "obra aurora"))
        self.assertFalse(textparse.contains_phrase(textparse.normalize("As auroras boreais"), "aurora"))
        self.assertFalse(textparse.contains_phrase(text, ""))


class SubjectAndDomainTests(SimpleTestCase):
    def test_clean_subject_strips_repeated_prefixes(self):
        self.assertEqual(textparse.clean_subject("RE: ENC: Fwd:  Orçamento   do gerador"), "Orçamento do gerador")
        self.assertEqual(textparse.clean_subject("Re[2]: medição de outubro"), "medição de outubro")

    def test_clean_subject_keeps_words_that_only_look_like_prefixes(self):
        self.assertEqual(textparse.clean_subject("Resumo da obra"), "Resumo da obra")

    def test_clean_subject_limit(self):
        self.assertEqual(len(textparse.clean_subject("a" * 500)), 200)

    def test_email_domain(self):
        self.assertEqual(textparse.email_domain("Maria@Convivy.com.br"), "convivy.com.br")
        self.assertEqual(textparse.email_domain("sem-arroba"), "")
        self.assertEqual(textparse.email_domain(""), "")

    def test_free_domains_are_recognised(self):
        for domain in ("gmail.com", "hotmail.com", "outlook.com.br", "yahoo.com.br", "uol.com.br", "icloud.com"):
            self.assertTrue(textparse.is_free_domain(domain), domain)
        self.assertFalse(textparse.is_free_domain("convivy.com.br"))
        self.assertFalse(textparse.is_free_domain(""))

    def test_same_domain_accepts_subdomains(self):
        self.assertTrue(textparse.same_domain("convivy.com.br", "convivy.com.br"))
        self.assertTrue(textparse.same_domain("mail.convivy.com.br", "convivy.com.br"))
        self.assertFalse(textparse.same_domain("convivy.com.br", "outra.com.br"))
        self.assertFalse(textparse.same_domain("", "convivy.com.br"))


class FirstUsefulLineTests(SimpleTestCase):
    def test_skips_greeting_line(self):
        self.assertEqual(
            textparse.first_useful_line("Bom dia,\n\nPreciso do orçamento do gerador.\nAtt, Maria"),
            "Preciso do orçamento do gerador.",
        )

    def test_strips_greeting_prefix_on_same_line(self):
        self.assertEqual(textparse.first_useful_line("Olá, preciso do gerador"), "preciso do gerador")

    def test_skips_pasted_email_headers(self):
        text = "De: maria@convivy.com.br\nPara: compras@biasi.com.br\nAssunto: gerador\n\nPrecisamos da cotação."
        self.assertEqual(textparse.first_useful_line(text), "Precisamos da cotação.")

    def test_long_line_is_truncated_on_a_word(self):
        line = textparse.first_useful_line("palavra " * 40)
        self.assertTrue(line.endswith("…"))
        self.assertLessEqual(len(line), 120)

    def test_nothing_useful(self):
        self.assertEqual(textparse.first_useful_line("Bom dia\n\n"), "")
        self.assertEqual(textparse.first_useful_line(""), "")


class ParseDeadlineTests(SimpleTestCase):
    def parse(self, text, reference=QUINTA, **kwargs):
        return textparse.parse_deadline(text, reference, **kwargs)

    def assertDeadline(self, text, expected, **kwargs):
        result = self.parse(text, **kwargs)
        self.assertIsNotNone(result, f"não leu prazo em: {text!r}")
        self.assertEqual(timezone.localtime(result.value).replace(tzinfo=None), expected, text)
        self.assertTrue(timezone.is_aware(result.value))

    def test_weekday_is_the_next_one(self):
        self.assertDeadline("Preciso disso até sexta", datetime.datetime(2026, 10, 2, 23, 59))
        self.assertDeadline("entregar na terça-feira", datetime.datetime(2026, 10, 6, 23, 59))
        self.assertDeadline("para sábado", datetime.datetime(2026, 10, 3, 23, 59))

    def test_weekday_equal_to_today_means_next_week(self):
        self.assertDeadline("até quinta", datetime.datetime(2026, 10, 8, 23, 59))

    def test_relative_words(self):
        self.assertDeadline("para hoje", datetime.datetime(2026, 10, 1, 23, 59))
        self.assertDeadline("até amanhã", datetime.datetime(2026, 10, 2, 23, 59))
        self.assertDeadline("para depois de amanhã", datetime.datetime(2026, 10, 3, 23, 59))

    def test_day_of_month(self):
        self.assertDeadline("até dia 15", datetime.datetime(2026, 10, 15, 23, 59))

    def test_day_of_month_already_gone_goes_to_next_month(self):
        result = self.parse("até dia 15", reference=local(2026, 10, 20))
        self.assertEqual(timezone.localtime(result.value).date(), datetime.date(2026, 11, 15))

    def test_day_of_month_skips_months_without_that_day(self):
        result = self.parse("até dia 31", reference=local(2026, 11, 5))
        self.assertEqual(timezone.localtime(result.value).date(), datetime.date(2026, 12, 31))

    def test_numeric_dates(self):
        self.assertDeadline("entregar 15/10", datetime.datetime(2026, 10, 15, 23, 59))
        self.assertDeadline("entregar dia 15/10", datetime.datetime(2026, 10, 15, 23, 59))
        self.assertDeadline("prazo 15-10", datetime.datetime(2026, 10, 15, 23, 59))
        self.assertDeadline("até 15/10/2026", datetime.datetime(2026, 10, 15, 23, 59))
        self.assertDeadline("até 15/10/26", datetime.datetime(2026, 10, 15, 23, 59))
        self.assertDeadline("até 2026-10-15", datetime.datetime(2026, 10, 15, 23, 59))

    def test_written_dates(self):
        self.assertDeadline("até 15 de outubro", datetime.datetime(2026, 10, 15, 23, 59))
        self.assertDeadline("prazo: dia 15 de outubro de 2026", datetime.datetime(2026, 10, 15, 23, 59))
        self.assertDeadline("para 3 de março", datetime.datetime(2027, 3, 3, 23, 59))

    def test_date_without_year_that_passed_rolls_to_next_year(self):
        self.assertDeadline("até 10/09", datetime.datetime(2027, 9, 10, 23, 59))

    def test_explicit_past_date_is_ignored(self):
        self.assertIsNone(self.parse("até 15/10/2025"))

    def test_invalid_dates_are_ignored(self):
        self.assertIsNone(self.parse("até 31/02"))
        self.assertIsNone(self.parse("até 45/10"))

    def test_time_of_day(self):
        self.assertDeadline("até 15/10 às 14h", datetime.datetime(2026, 10, 15, 14, 0))
        self.assertDeadline("até sexta 14:30", datetime.datetime(2026, 10, 2, 14, 30))
        self.assertDeadline("para sexta às 9h30", datetime.datetime(2026, 10, 2, 9, 30))

    def test_words_starting_with_h_are_not_a_time(self):
        self.assertDeadline("até sexta, 10 homens na obra", datetime.datetime(2026, 10, 2, 23, 59))

    def test_invalid_time_falls_back_to_end_of_day(self):
        self.assertDeadline("até sexta 25h", datetime.datetime(2026, 10, 2, 23, 59))

    def test_requires_a_deadline_cue(self):
        self.assertIsNone(self.parse("A reunião é sexta"))
        self.assertIsNone(self.parse("Ligue para 11 3333-4444"))

    def test_cue_too_far_away_does_not_count(self):
        self.assertIsNone(self.parse("para isso " + "x" * 40 + " sexta"))

    def test_without_cue_requirement_any_date_counts(self):
        self.assertDeadline("Orçamento do gerador sexta", datetime.datetime(2026, 10, 2, 23, 59), require_cue=False)

    def test_first_cued_date_wins(self):
        self.assertDeadline("A reunião é terça. Entregar até quarta, depois sexta", datetime.datetime(2026, 10, 7, 23, 59))

    def test_unsupported_vague_expressions(self):
        self.assertIsNone(self.parse("até a semana que vem"))
        self.assertIsNone(self.parse("para o fim do mês"))
        self.assertIsNone(self.parse("é urgente"))

    def test_reason_is_readable(self):
        self.assertEqual(
            self.parse("Preciso disso até sexta").reason,
            'Prazo: "sexta" interpretado como sexta, 02/10/2026',
        )
        self.assertIn("amanhã", self.parse("para amanhã").reason)

    def test_empty_text(self):
        self.assertIsNone(self.parse(""))
        self.assertIsNone(self.parse(None))

    def test_weekday_label(self):
        self.assertEqual(textparse.weekday_label(local(2026, 10, 2)), "sexta")
        self.assertEqual(textparse.weekday_label(local(2026, 10, 3)), "sábado")
