from django.conf import settings
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Profile, UserSector


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile_for_new_user(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=UserSector)
@receiver(post_delete, sender=UserSector)
def refresh_authorization_cache(sender, instance, **kwargs):
    """Participação em setor alimenta os escopos relacionais do motor.

    Invalidar aqui evita que qualquer caminho de escrita precise lembrar disso.
    """
    from acessos.services import invalidate_sector_cache

    invalidate_sector_cache()
