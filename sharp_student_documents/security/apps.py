# Security app for SharpDocs marketplace
# Provides two-factor authentication, identity verification, fraud detection, and watermarking

from django.apps import AppConfig

class SecurityConfig(AppConfig):
    name = 'security'
    verbose_name = 'Security'
    verbose_name_plural = 'Security'
    
    def ready(self):
        import security.signals
