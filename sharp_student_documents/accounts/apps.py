from django.apps import AppConfig

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
    verbose_name = 'Accounts'
    verbose_name_plural = 'Accounts'
    
    def ready(self):
        import accounts.signals
