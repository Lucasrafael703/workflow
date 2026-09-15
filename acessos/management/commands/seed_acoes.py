from django.core.management.base import BaseCommand
from django.db import transaction

from acessos.catalog import GROUPS
from acessos.models import Action, ActionGroup


class Command(BaseCommand):
    help = (
        "Materializa no banco o catálogo de ações do produto (Regras 05 §13, doc 08 §19). "
        "Idempotente: rodar de novo apenas sincroniza nomes, descrições e situação. "
        "Ações que saíram do catálogo são inativadas, nunca apagadas, para preservar o histórico."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        seen_keys = set()

        for order, (group_key, group_name, actions) in enumerate(GROUPS, start=1):
            group, created = ActionGroup.objects.update_or_create(
                key=group_key,
                defaults={"name": group_name, "order": order, "is_active": True},
            )
            self.stdout.write(f"Grupo {group_name}: {'criado' if created else 'atualizado'}")

            for key, name, description, sensitive in actions:
                Action.objects.update_or_create(
                    key=key,
                    defaults={
                        "group": group,
                        "name": name,
                        "description": description,
                        "is_sensitive": sensitive,
                        "is_active": True,
                    },
                )
                seen_keys.add(key)

        # Uma ação removida do produto perde efeito, mas continua existindo:
        # concessões antigas precisam continuar explicáveis no histórico.
        retired = Action.objects.filter(is_active=True).exclude(key__in=seen_keys)
        count = retired.update(is_active=False)
        if count:
            self.stdout.write(self.style.WARNING(f"{count} ação(ões) fora do catálogo foram inativadas."))

        self.stdout.write(
            self.style.SUCCESS(f"Catálogo sincronizado: {len(seen_keys)} ações em {len(GROUPS)} grupos.")
        )
