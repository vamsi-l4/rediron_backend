import logging

from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import CustomUser, UserProfile

logger = logging.getLogger(__name__)


def _delete_file(field_file):
    if not field_file or not field_file.name:
        return
    try:
        field_file.delete(save=False)
    except Exception:
        # Database deletion must not be rolled back merely because an object
        # store is temporarily unavailable. It can be cleaned asynchronously.
        logger.exception('Could not delete profile image %s', field_file.name)


@receiver(post_delete, sender=CustomUser)
def delete_user_profile_image(sender, instance, **kwargs):
    _delete_file(instance.profile_image)


@receiver(post_delete, sender=UserProfile)
def delete_extended_profile_image(sender, instance, **kwargs):
    _delete_file(instance.profile_image)
