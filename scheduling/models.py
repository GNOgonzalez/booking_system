from django.db import models
from django.conf import settings

class DemoItem(models.Model):
    title = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    display_name = models.CharField(max_length=50, blank=True)
    timezone = models.TextField(default='UTC')

    def __str__(self):
        return self.display_name or self.user.username

