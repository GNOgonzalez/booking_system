from django.contrib import admin
from .models import DemoItem, Profile, Session, Booking

admin.site.register(DemoItem)
admin.site.register(Profile)
admin.site.register(Session)
admin.site.register(Booking)