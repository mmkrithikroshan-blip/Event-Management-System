from django.db import models
from django.conf import settings

class SystemSetting(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['key']

    def __str__(self):
        return f"{self.key}: {self.value}"

    @classmethod
    def get_val(cls, key, default=''):
        obj = cls.objects.filter(key=key).first()
        return obj.value if obj else default


class AuditLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100)
    entity = models.CharField(max_length=50)
    entity_id = models.CharField(max_length=50)
    details = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        actor_name = self.actor.full_name if self.actor else 'System'
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {actor_name} - {self.action} on {self.entity} #{self.entity_id}"
