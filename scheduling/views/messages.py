from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, render

from scheduling.models import CurriculumItem, Message


@login_required
def inbox(request):
    messages_qs = Message.objects.filter(recipient=request.user)
    return render(request, 'scheduling/inbox.html', {'messages_list': messages_qs})


@login_required
def message_detail(request, message_id):
    message = get_object_or_404(Message, pk=message_id)
    user = request.user
    if user not in (message.sender, message.recipient):
        if not user.groups.filter(name='staff').exists():
            return HttpResponseForbidden("You don't have access to this page.")

    if message.recipient == user and not message.is_read:
        message.is_read = True
        message.save(update_fields=['is_read'])

    return render(request, 'scheduling/message_detail.html', {'message': message})


@login_required
def curriculum_list(request):
    user = request.user
    if user.groups.filter(name='teacher').exists():
        items = CurriculumItem.objects.filter(is_published=True).filter(
            Q(teacher=user) | Q(teacher__isnull=True),
        )
    elif user.groups.filter(name='student').exists():
        items = CurriculumItem.objects.filter(is_published=True)
    elif user.groups.filter(name='staff').exists():
        items = CurriculumItem.objects.filter(is_published=True)
    else:
        return HttpResponseForbidden("You don't have access to this page.")

    return render(request, 'scheduling/curriculum_list.html', {'items': items})
