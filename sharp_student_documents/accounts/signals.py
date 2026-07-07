from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Role, UserRole

User = get_user_model()

@receiver(post_save, sender=User)
def create_default_roles_for_user(sender, instance, created, **kwargs):
    """Create default roles for new users"""
    if created and not instance.roles.exists():
        # Assign default 'Student' role to new users
        try:
            student_role = Role.objects.get(name='Student')
            UserRole.objects.create(user=instance, role=student_role)
        except Role.DoesNotExist:
            # Create the role if it doesn't exist
            student_role = Role.objects.create(
                name='Student',
                description='Regular student users who can purchase documents'
            )
            UserRole.objects.create(user=instance, role=student_role)

@receiver(post_save, sender=Role)
def create_default_role(sender, instance, created, **kwargs):
    """Create default user when role is created"""
    if created and instance.is_default:
        # Assign role to all existing users without roles
        users_without_roles = User.objects.filter(user_roles__isnull=True)
        for user in users_without_roles:
            UserRole.objects.create(user=user, role=instance)
