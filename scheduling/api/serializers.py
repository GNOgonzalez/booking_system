from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from scheduling.models import (
    AvailabilityBlock,
    Booking,
    ClassType,
    CurriculumItem,
    Membership,
    Message,
    Profile,
    Session,
)


class SessionSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.username', read_only=True)
    class_type_name = serializers.CharField(source='class_type.name', read_only=True, default=None)
    confirmed_count = serializers.SerializerMethodField()

    class Meta:
        model = Session
        fields = [
            'id',
            'title',
            'teacher_name',
            'class_type',
            'class_type_name',
            'start_time',
            'end_time',
            'capacity',
            'status',
            'meeting_url',
            'confirmed_count',
        ]
        read_only_fields = ['status', 'meeting_url']

    def get_confirmed_count(self, obj):
        return obj.bookings.filter(status='confirmed').count()


class BookingSerializer(serializers.ModelSerializer):
    session_title = serializers.CharField(source='session.title', read_only=True)
    session_start_time = serializers.DateTimeField(source='session.start_time', read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id',
            'session',
            'session_title',
            'session_start_time',
            'status',
            'created_at',
        ]
        read_only_fields = ['status', 'created_at']


class BookingCreateSerializer(serializers.Serializer):
    session_id = serializers.IntegerField()


class AvailabilityBlockSerializer(serializers.ModelSerializer):
    weekday_display = serializers.CharField(source='get_weekday_display', read_only=True)

    class Meta:
        model = AvailabilityBlock
        fields = ['id', 'weekday', 'weekday_display', 'start_time', 'end_time']


class ClassTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClassType
        fields = ['id', 'name', 'description', 'default_capacity', 'is_active']


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.username', read_only=True)
    recipient_name = serializers.CharField(source='recipient.username', read_only=True)

    class Meta:
        model = Message
        fields = [
            'id',
            'sender_name',
            'recipient_name',
            'subject',
            'body',
            'is_read',
            'created_at',
        ]


class CurriculumItemSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.username', read_only=True, default=None)

    class Meta:
        model = CurriculumItem
        fields = ['id', 'title', 'content', 'teacher_name', 'sort_order']


class MembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Membership
        fields = ['id', 'plan_type', 'is_active', 'valid_until']


class MembershipPurchaseSerializer(serializers.Serializer):
    plan_type = serializers.ChoiceField(choices=[c[0] for c in Membership.PLAN_CHOICES])
    months = serializers.IntegerField(min_value=1, max_value=24, default=1)


def serialize_me(user):
    """Plain dict of account + profile info for the current user."""
    profile, _ = Profile.objects.get_or_create(user=user)
    return {
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'display_name': profile.display_name,
        'timezone': profile.timezone,
        'roles': list(user.groups.values_list('name', flat=True)),
    }


class MeUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_blank=True)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    display_name = serializers.CharField(required=False, allow_blank=True, max_length=50)
    timezone = serializers.CharField(required=False, allow_blank=True, max_length=64)

    def save(self):
        user = self.context['request'].user
        data = self.validated_data
        for field in ('email', 'first_name', 'last_name'):
            if field in data:
                setattr(user, field, data[field])
        user.save()

        profile, _ = Profile.objects.get_or_create(user=user)
        if 'display_name' in data:
            profile.display_name = data['display_name']
        if 'timezone' in data:
            profile.timezone = data['timezone']
        profile.save()
        return user


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect.')
        return value

    def validate_new_password(self, value):
        validate_password(value, self.context['request'].user)
        return value

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user
