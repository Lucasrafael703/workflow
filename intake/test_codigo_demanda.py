"""Migração `intake/0003_codigo_da_demanda_nas_notas`: a nota do evento "Demanda criada" é o código da
demanda e acompanha a troca de `ATV-` por `DEM-`."""

import importlib

from django.apps import apps

from .models import IntakeEvent
from .testing import IntakeTestCase

migration = importlib.import_module("intake.migrations.0003_codigo_da_demanda_nas_notas")


class CodigoNasNotasTests(IntakeTestCase):
    def event(self, note, kind=IntakeEvent.Kind.CONVERTIDA):
        return IntakeEvent.objects.create(item=self.new_item(), user=self.triador, kind=kind, note=note)

    def note_of(self, event):
        return IntakeEvent.objects.get(pk=event.pk).note

    def test_a_note_that_is_exactly_a_code_is_rewritten(self):
        event = self.event("ATV-2026-00003")
        migration.to_demanda(apps, None)
        self.assertEqual(self.note_of(event), "DEM-2026-00003")

    def test_text_around_a_code_and_other_kinds_are_left_alone(self):
        cited = self.event("Ver ATV-2026-00003 antes")
        typed = self.event("ATV-2026-00003", kind=IntakeEvent.Kind.IGNORADA)
        migration.to_demanda(apps, None)
        self.assertEqual(self.note_of(cited), "Ver ATV-2026-00003 antes")
        self.assertEqual(self.note_of(typed), "ATV-2026-00003")

    def test_running_twice_and_reversing(self):
        event = self.event("ATV-2026-00003")
        migration.to_demanda(apps, None)
        migration.to_demanda(apps, None)
        self.assertEqual(self.note_of(event), "DEM-2026-00003")
        migration.to_atividade(apps, None)
        self.assertEqual(self.note_of(event), "ATV-2026-00003")
