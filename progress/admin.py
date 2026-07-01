from django.contrib import admin

from .models import ProgressReport, Skill

admin.site.register(Skill)
admin.site.register(ProgressReport)
