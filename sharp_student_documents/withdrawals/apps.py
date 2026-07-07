from django.apps import AppConfig

class WithdrawalsConfig(AppConfig):
    name = 'withdrawals'
    verbose_name = 'Withdrawals'
    verbose_name_plural = 'Withdrawals'
    
    def ready(self):
        import withdrawals.signals
