from django.contrib import admin

from .models import (
    AvailabilityBlock,
    Booking,
    ClassType,
    CurriculumItem,
    DemoItem,
    Membership,
    Message,
    Profile,
    Session,
)

admin.site.register(DemoItem)
admin.site.register(Profile)
admin.site.register(ClassType)
admin.site.register(AvailabilityBlock)
admin.site.register(Session)
admin.site.register(Booking)
admin.site.register(Membership)
admin.site.register(Message)
admin.site.register(CurriculumItem)
