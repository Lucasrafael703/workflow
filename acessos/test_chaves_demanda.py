"""Migração `0003_chaves_demanda`: as chaves de permissão acompanham o novo nome da "Demanda"
sem perder nenhuma concessão."""

import importlib

from django.apps import apps
from django.test import TestCase

from activities.testing import make_user
from core.models import Organization

from . import catalog
from .models import Action, ActionGroup, ProfileAction, UserAction
from .services import AuthorizationService
from .testing import grant_action, make_profile, assign_profile

migration = importlib.import_module("acessos.migrations.0003_chaves_demanda")


class ChavesDemandaTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Biasi")
        self.ana = make_user("ana", self.org, [catalog.ATIVIDADE_CRIAR, catalog.ATIVIDADE_VISUALIZAR])
        self.profile = make_profile(self.org, "Gestor", [catalog.ATIVIDADE_EDITAR])
        self.bia = make_user("bia", self.org)
        assign_profile(self.bia, self.profile)

    def keys(self, prefix):
        return set(Action.objects.filter(key__startswith=prefix).values_list("key", flat=True))

    def test_catalog_uses_the_new_keys(self):
        self.assertEqual(catalog.ATIVIDADE_CRIAR, "demanda.criar")
        self.assertEqual(self.keys("atividade."), set())
        self.assertIn("demanda.criar", self.keys("demanda."))
        self.assertEqual(catalog.GROUPS[0][0], "demandas")

    def test_renaming_keeps_the_same_rows_and_every_grant(self):
        before = {a.key: a.pk for a in Action.objects.filter(key__startswith="demanda.")}
        migration.to_atividade(apps, None)  # volta ao estado antigo (também prova a reversão)
        self.assertEqual(self.keys("demanda."), set())
        self.assertIn("atividade.criar", self.keys("atividade."))
        self.assertTrue(ActionGroup.objects.filter(key="atividades").exists())
        migration.to_demanda(apps, None)

        after = {a.key: a.pk for a in Action.objects.filter(key__startswith="demanda.")}
        self.assertEqual(after, before)  # mesmos registros, só a chave mudou
        self.assertTrue(ActionGroup.objects.filter(key="demandas").exists())
        self.assertFalse(ActionGroup.objects.filter(key="atividades").exists())
        self.assertTrue(AuthorizationService.can(self.ana, catalog.ATIVIDADE_CRIAR))
        self.assertTrue(AuthorizationService.can(self.ana, catalog.ATIVIDADE_VISUALIZAR))
        self.assertTrue(AuthorizationService.can(self.bia, catalog.ATIVIDADE_EDITAR))  # pelo perfil
        self.assertFalse(AuthorizationService.can(self.ana, catalog.ATIVIDADE_EDITAR))

    def test_other_actions_are_left_alone(self):
        tarefas = self.keys("tarefa.")
        migration.to_demanda(apps, None)
        self.assertEqual(self.keys("tarefa."), tarefas)

    def test_running_twice_changes_nothing(self):
        migration.to_demanda(apps, None)
        before = set(Action.objects.values_list("pk", "key"))
        migration.to_demanda(apps, None)
        self.assertEqual(set(Action.objects.values_list("pk", "key")), before)

    def test_merges_when_the_new_keys_were_already_seeded_before_the_migration(self):
        """`seed_acoes` do código novo rodou antes do `migrate`: existem as duas chaves."""
        new = Action.objects.get(key="demanda.criar")
        old = Action.objects.create(
            group=new.group, key="atividade.criar", name="Criar atividade", description="antiga"
        )
        # perfil que só tem a ação antiga, concessão direta que só existe na antiga, e uma que existe nas duas
        only_old = make_profile(self.org, "Só antiga", [])
        ProfileAction.objects.create(profile=only_old, action=old)
        ProfileAction.objects.create(profile=self.profile, action=old)
        ProfileAction.objects.create(profile=self.profile, action=new)
        carol = make_user("carol", self.org)
        grant_action(carol, "demanda.criar", organization=self.org)
        old_grant = UserAction.objects.get(user=carol)
        old_grant.action = old
        old_grant.save()
        grant_action(carol, "demanda.criar", organization=self.org)  # a mesma concessão, na ação nova

        migration.to_demanda(apps, None)

        self.assertFalse(Action.objects.filter(key="atividade.criar").exists())
        self.assertTrue(ProfileAction.objects.filter(profile=only_old, action=new).exists())
        self.assertEqual(ProfileAction.objects.filter(profile=self.profile, action=new).count(), 1)
        self.assertEqual(UserAction.objects.filter(user=carol, action=new).count(), 1)
        self.assertTrue(AuthorizationService.can(carol, catalog.ATIVIDADE_CRIAR))
