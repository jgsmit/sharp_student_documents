from django.db import models
from django.contrib.auth.models import AbstractUser, Permission as DjangoPermission
from django.contrib.contenttypes.models import ContentType

class Role(models.Model):
    """User roles for permission management"""
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField()
    permissions = models.ManyToManyField(
        DjangoPermission,
        blank=True,
        related_name='roles'
    )
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'roles'
        ordering = ['name']
        verbose_name = 'Role'
        verbose_name_plural = 'Roles'
    
    def __str__(self):
        return self.name

class UserRole(models.Model):
    """User role assignments"""
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='role_assignments')
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        'CustomUser', 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='role_assignments_by'
    )
    
    class Meta:
        db_table = 'user_roles'
        unique_together = ['user', 'role']
        verbose_name = 'User Role'
        verbose_name_plural = 'User Roles'
    
    def __str__(self):
        return f"{self.user.username} - {self.role.name}"

# Extend CustomUser with role relationships
class CustomUser(AbstractUser):
    is_seller = models.BooleanField(default=False)
    bio = models.TextField(blank=True, null=True)
    roles = models.ManyToManyField(Role, through=UserRole, through_fields=('user', 'role'), blank=True, related_name='roles')
    
    def __str__(self):
        return self.username
    
    @property
    def is_admin(self):
        """Check if user has admin role"""
        return self.roles.filter(name='Admin').exists()
    
    @property
    def is_moderator(self):
        """Check if user has moderator role"""
        return self.roles.filter(name='Moderator').exists()
    
    @property
    def is_student(self):
        """Check if user has student role"""
        return self.roles.filter(name='Student').exists()
    
    @property
    def is_teacher(self):
        """Check if user has teacher role"""
        return self.roles.filter(name='Teacher').exists()
    
    def has_role(self, role_name):
        """Check if user has specific role"""
        return self.roles.filter(name=role_name).exists()
    
    def add_role(self, role_name):
        """Add role to user"""
        try:
            role = Role.objects.get(name=role_name)
            UserRole.objects.get_or_create(user=self, role=role)
        except Role.DoesNotExist:
            # Create role if it doesn't exist
            role = Role.objects.create(
                name=role_name,
                description=f"Auto-created role: {role_name}"
            )
            UserRole.objects.get_or_create(user=self, role=role)
    
    def remove_role(self, role_name):
        """Remove role from user"""
        try:
            role = Role.objects.get(name=role_name)
            UserRole.objects.filter(user=self, role=role).delete()
        except Role.DoesNotExist:
            pass
    
    def get_all_roles(self):
        """Get all user roles as names"""
        return list(self.roles.values_list('name', flat=True))

# Create default roles
def create_default_roles():
    """Create default system roles"""
    Role.objects.get_or_create(
        name='Student',
        description='Regular student users who can purchase documents'
    )
    Role.objects.get_or_create(
        name='Teacher',
        description='Educators who can upload and sell documents'
    )
    Role.objects.get_or_create(
        name='Seller',
        description='Document sellers with enhanced dashboard features'
    )
    Role.objects.get_or_create(
        name='Moderator',
        description='Content moderators with review permissions'
    )
    Role.objects.get_or_create(
        name='Admin',
        description='System administrators with full access'
    )
