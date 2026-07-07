from django.db import models
from django.conf import settings


class DownloadLog(models.Model):
    """Track document downloads for analytics and security"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="download_logs",
        db_index=True
    )
    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name="download_logs",
        db_index=True
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    download_time = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["-download_time"]
        indexes = [
            models.Index(fields=['user', 'download_time']),
            models.Index(fields=['document', 'download_time']),
            models.Index(fields=['ip_address', 'download_time']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.document.title} at {self.download_time}"
