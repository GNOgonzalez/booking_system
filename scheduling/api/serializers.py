from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from scheduling.models import (
    AvailabilityBlock,
    BlogPost,
    Booking,
    ClassOffering,
    ClassRequest,
    ClassTopic,
    CurriculumItem,
    Membership,
    MembershipPlan,
    Message,
    Profile,
    Session,
    SpecialAvailability,
)
from scheduling.services.classes import sync_class_topics
from scheduling.services.llm import ai_available_for_user
from scheduling.services.sessions import session_display_title
from scheduling.services.teacher_permissions import permissions_for_teacher

User = get_user_model()


class SessionSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.username', read_only=True)
    meeting_provider_display = serializers.CharField(source='get_meeting_provider_display', read_only=True)
    class_offering_label = serializers.CharField(source='class_offering.display_name', read_only=True, default=None)
    class_subject = serializers.CharField(source='class_offering.subject', read_only=True, default=None)
    class_level = serializers.CharField(source='class_offering.level', read_only=True, default=None)
    class_focus = serializers.CharField(source='class_offering.focus', read_only=True, default=None)
    class_topic = serializers.SerializerMethodField()
    class_topic_id = serializers.PrimaryKeyRelatedField(
        queryset=ClassTopic.objects.all(),
        source='class_topic',
        required=False,
        allow_null=True,
        write_only=True,
    )
    confirmed_count = serializers.SerializerMethodField()
    ticket_cost = serializers.SerializerMethodField()
    student_booked = serializers.SerializerMethodField()

    class Meta:
        model = Session
        fields = [
            'id',
            'title',
            'teacher',
            'teacher_name',
            'class_offering',
            'class_topic_id',
            'class_offering_label',
            'class_subject',
            'class_level',
            'class_focus',
            'class_topic',
            'start_time',
            'end_time',
            'capacity',
            'status',
            'meeting_provider',
            'meeting_provider_display',
            'meeting_url',
            'confirmed_count',
            'ticket_cost',
            'student_booked',
        ]
        read_only_fields = ['status', 'meeting_url', 'title', 'teacher', 'meeting_provider_display']

    def get_class_topic(self, obj):
        if obj.class_topic_id:
            return obj.class_topic.title
        return None

    def get_confirmed_count(self, obj):
        annotated = getattr(obj, 'confirmed_count', None)
        if annotated is not None:
            return annotated
        return obj.bookings.filter(status='confirmed').count()

    def get_ticket_cost(self, obj):
        if obj.class_offering_id:
            return obj.class_offering.ticket_cost
        return 1

    def get_student_booked(self, obj):
        annotated = getattr(obj, 'student_booked', None)
        if annotated is not None:
            return bool(annotated)
        return False

    def _catalog_teacher(self):
        return self.context.get('acting_teacher') or self.context['request'].user

    def validate_class_offering(self, value):
        if value is None:
            if self.instance is None:
                raise serializers.ValidationError('Choose a class from your catalog.')
            return value
        teacher = self._catalog_teacher()
        if value.teacher_id != teacher.id or not value.is_active:
            raise serializers.ValidationError('Class not found in your catalog.')
        return value

    def validate(self, attrs):
        offering = attrs.get('class_offering') or getattr(self.instance, 'class_offering', None)
        topic = attrs.get('class_topic')
        if topic is not None and offering is not None and topic.class_offering_id != offering.id:
            raise serializers.ValidationError({'class_topic_id': 'Topic does not belong to this class.'})
        return attrs

    def create(self, validated_data):
        offering = validated_data['class_offering']
        topic = validated_data.get('class_topic')
        validated_data['title'] = session_display_title(offering, topic)
        if validated_data.get('capacity') in (None, 0):
            validated_data['capacity'] = offering.default_capacity
        return super().create(validated_data)

    def update(self, instance, validated_data):
        offering = validated_data.get('class_offering', instance.class_offering)
        topic = validated_data.get('class_topic', instance.class_topic)
        if offering is not None:
            validated_data['title'] = session_display_title(offering, topic)
        return super().update(instance, validated_data)


class BookingSerializer(serializers.ModelSerializer):
    session_title = serializers.CharField(source='session.title', read_only=True)
    session_start_time = serializers.DateTimeField(source='session.start_time', read_only=True)
    session_end_time = serializers.DateTimeField(source='session.end_time', read_only=True)
    teacher_name = serializers.CharField(source='session.teacher.username', read_only=True)
    meeting_url = serializers.CharField(source='session.meeting_url', read_only=True)
    meeting_provider = serializers.CharField(source='session.meeting_provider', read_only=True)
    meeting_provider_display = serializers.CharField(
        source='session.get_meeting_provider_display', read_only=True,
    )
    class_offering_label = serializers.CharField(
        source='session.class_offering.display_name', read_only=True, default=None,
    )
    class_subject = serializers.CharField(source='session.class_offering.subject', read_only=True, default=None)
    class_level = serializers.CharField(source='session.class_offering.level', read_only=True, default=None)
    class_focus = serializers.CharField(source='session.class_offering.focus', read_only=True, default=None)
    class_topic = serializers.SerializerMethodField()
    no_ticket_refund = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id',
            'session',
            'session_title',
            'session_start_time',
            'session_end_time',
            'tickets_spent',
            'no_ticket_refund',
            'teacher_name',
            'meeting_url',
            'meeting_provider',
            'meeting_provider_display',
            'class_offering_label',
            'class_subject',
            'class_level',
            'class_focus',
            'class_topic',
            'status',
            'created_at',
        ]
        read_only_fields = ['status', 'created_at']

    def get_class_topic(self, obj):
        session = obj.session
        if session and session.class_topic_id:
            return session.class_topic.title
        return None

    def get_no_ticket_refund(self, obj):
        return obj.class_request_id is not None


class ClassRequestSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.username', read_only=True)
    teacher_name = serializers.SerializerMethodField()
    class_offering_label = serializers.SerializerMethodField()
    class_topic_title = serializers.CharField(source='class_topic.title', read_only=True, default=None)
    session_id = serializers.IntegerField(source='session.id', read_only=True, default=None)
    class_profile_label = serializers.SerializerMethodField()

    class Meta:
        model = ClassRequest
        fields = [
            'id',
            'student',
            'student_name',
            'teacher',
            'teacher_name',
            'open_to_any_teacher',
            'subject',
            'level',
            'focus',
            'class_profile_label',
            'class_offering',
            'class_offering_label',
            'class_topic',
            'class_topic_title',
            'start_time',
            'end_time',
            'tickets_requested',
            'status',
            'session_id',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'student',
            'status',
            'session_id',
            'created_at',
            'updated_at',
        ]

    def get_teacher_name(self, obj):
        if obj.open_to_any_teacher and obj.teacher_id is None:
            return 'Any available teacher'
        if obj.teacher_id:
            return obj.teacher.username
        return ''

    def get_class_profile_label(self, obj):
        return obj.class_profile_label

    def get_class_offering_label(self, obj):
        if obj.class_offering_id:
            return obj.class_offering.display_name
        return obj.class_profile_label


class ClassRequestCreateSerializer(serializers.Serializer):
    teacher = serializers.IntegerField(required=False, allow_null=True)
    open_to_any_teacher = serializers.BooleanField(required=False, default=False)
    class_offering = serializers.IntegerField(required=False, allow_null=True)
    class_topic = serializers.IntegerField(required=False, allow_null=True)
    subject = serializers.CharField(required=False, allow_blank=True)
    level = serializers.CharField(required=False, allow_blank=True)
    focus = serializers.CharField(required=False, allow_blank=True)
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()
    tickets_requested = serializers.IntegerField(min_value=1)


class OpenClassProfileSerializer(serializers.Serializer):
    subject = serializers.CharField()
    level = serializers.CharField()
    focus = serializers.CharField()
    label = serializers.CharField()
    min_ticket_cost = serializers.IntegerField()
    teacher_count = serializers.IntegerField()


class ClassRequestUpdateSerializer(serializers.Serializer):
    class_offering = serializers.IntegerField(required=False)
    class_topic = serializers.IntegerField(required=False, allow_null=True)
    start_time = serializers.DateTimeField(required=False)
    end_time = serializers.DateTimeField(required=False)
    capacity = serializers.IntegerField(required=False, min_value=1)


class TeacherRequestOptionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    label = serializers.CharField()


class BookingCreateSerializer(serializers.Serializer):
    session_id = serializers.IntegerField()


class AvailabilityBlockSerializer(serializers.ModelSerializer):
    weekday_display = serializers.CharField(source='get_weekday_display', read_only=True)

    class Meta:
        model = AvailabilityBlock
        fields = ['id', 'weekday', 'weekday_display', 'start_time', 'end_time']


class StudentOptionSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = ['id', 'username', 'label', 'display_name', 'is_active']

    def get_label(self, obj):
        profile = Profile.objects.filter(user=obj).first()
        if profile and profile.display_name:
            return f"{profile.display_name} ({obj.username})"
        return obj.username

    def get_display_name(self, obj):
        profile = Profile.objects.filter(user=obj).first()
        return profile.display_name if profile else ''


class SpecialAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecialAvailability
        fields = ['id', 'date', 'start_time', 'end_time', 'note']


class ClassTopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClassTopic
        fields = ['id', 'title', 'sort_order']


class ClassOfferingSerializer(serializers.ModelSerializer):
    label = serializers.CharField(source='display_name', read_only=True)
    topics = ClassTopicSerializer(many=True, required=False)

    class Meta:
        model = ClassOffering
        fields = [
            'id',
            'subject',
            'level',
            'focus',
            'topics_ordered',
            'topics',
            'label',
            'default_capacity',
            'ticket_cost',
            'is_active',
        ]
        read_only_fields = ['label']

    def validate_topics(self, value):
        if self.instance is None and not value:
            raise serializers.ValidationError('Add at least one topic.')
        cleaned = []
        for index, item in enumerate(value):
            title = (item.get('title') or '').strip()
            if not title:
                continue
            cleaned.append({
                'id': item.get('id'),
                'title': title,
                'sort_order': item.get('sort_order', index),
            })
        if self.instance is None and not cleaned:
            raise serializers.ValidationError('Add at least one topic.')
        return cleaned

    def create(self, validated_data):
        topics_data = validated_data.pop('topics', [])
        validated_data['teacher'] = self.context.get('acting_teacher') or self.context['request'].user
        offering = ClassOffering.objects.create(**validated_data)
        sync_class_topics(offering, topics_data)
        return offering

    def update(self, instance, validated_data):
        topics_data = validated_data.pop('topics', None)
        offering = super().update(instance, validated_data)
        if topics_data is not None:
            sync_class_topics(offering, topics_data)
        return offering


class TeacherOptionSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = ['id', 'username', 'email', 'label', 'display_name', 'is_active']

    def get_label(self, obj):
        profile = Profile.objects.filter(user=obj).first()
        if profile and profile.display_name:
            return f"{profile.display_name} ({obj.username})"
        return obj.username

    def get_display_name(self, obj):
        profile = Profile.objects.filter(user=obj).first()
        return profile.display_name if profile else ''


class StaffUserUpdateSerializer(serializers.Serializer):
    is_active = serializers.BooleanField(required=False)
    display_name = serializers.CharField(required=False, allow_blank=True, max_length=50)


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


class ClassOfferingOptionSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()
    teacher_name = serializers.CharField(source='teacher.username', read_only=True)
    topics = ClassTopicSerializer(many=True, read_only=True)

    class Meta:
        model = ClassOffering
        fields = [
            'id',
            'label',
            'teacher_name',
            'subject',
            'level',
            'focus',
            'topics_ordered',
            'topics',
            'ticket_cost',
            'is_active',
        ]

    def get_label(self, obj):
        return f"{obj.teacher.username} — {obj.display_name}"


class MembershipPlanSerializer(serializers.ModelSerializer):
    allowed_class_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=ClassOffering.objects.filter(is_active=True),
        source='allowed_classes',
        required=False,
    )
    allowed_classes = ClassOfferingOptionSerializer(many=True, read_only=True)
    includes_all_classes = serializers.BooleanField(read_only=True)
    plan_type_display = serializers.CharField(source='get_plan_type_display', read_only=True)
    price_display = serializers.SerializerMethodField()

    class Meta:
        model = MembershipPlan
        fields = [
            'id',
            'name',
            'description',
            'plan_type',
            'plan_type_display',
            'price_cents',
            'price_display',
            'billing_period_days',
            'ticket_allowance',
            'is_active',
            'subject',
            'includes_all_classes',
            'allowed_class_ids',
            'allowed_classes',
            'created_at',
        ]
        read_only_fields = ['created_at', 'includes_all_classes']

    def get_price_display(self, obj):
        return f'${obj.price_cents / 100:.2f}'


class MembershipPlanPublicSerializer(serializers.ModelSerializer):
    allowed_classes = ClassOfferingOptionSerializer(many=True, read_only=True)
    includes_all_classes = serializers.BooleanField(read_only=True)
    plan_type_display = serializers.CharField(source='get_plan_type_display', read_only=True)
    price_display = serializers.SerializerMethodField()

    class Meta:
        model = MembershipPlan
        fields = [
            'id',
            'name',
            'description',
            'plan_type',
            'plan_type_display',
            'price_cents',
            'price_display',
            'billing_period_days',
            'ticket_allowance',
            'subject',
            'includes_all_classes',
            'allowed_classes',
        ]

    def get_price_display(self, obj):
        return f'${obj.price_cents / 100:.2f}'


class MembershipSerializer(serializers.ModelSerializer):
    plan = MembershipPlanPublicSerializer(read_only=True)
    plan_name = serializers.CharField(source='plan.name', read_only=True)

    class Meta:
        model = Membership
        fields = ['id', 'plan', 'plan_name', 'is_active', 'valid_until', 'tickets_remaining']


class MembershipPurchaseSerializer(serializers.Serializer):
    plan_id = serializers.IntegerField()
    months = serializers.IntegerField(min_value=1, max_value=24, default=1)
    membership_id = serializers.IntegerField(required=False, allow_null=True)


class BlogPostSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.username', read_only=True)
    image_url = serializers.SerializerMethodField()
    body_html = serializers.SerializerMethodField()

    class Meta:
        model = BlogPost
        fields = [
            'id',
            'title',
            'body',
            'body_html',
            'image',
            'image_url',
            'is_published',
            'author',
            'author_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['author', 'created_at', 'updated_at', 'image_url', 'body_html']

    def get_body_html(self, obj):
        from scheduling.services.markdown import render_safe_markdown

        return render_safe_markdown(obj.body)

    def get_image_url(self, obj):
        if not obj.image:
            return None
        request = self.context.get('request')
        url = obj.image.url
        if request is not None:
            return request.build_absolute_uri(url)
        return url


def serialize_me(user):
    """Plain dict of account + profile info for the current user."""
    profile, _ = Profile.objects.get_or_create(user=user)
    roles = list(user.groups.values_list('name', flat=True))
    data = {
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'display_name': profile.display_name,
        'timezone': profile.timezone,
        'theme': profile.theme,
        'roles': roles,
    }
    if 'teacher' in roles:
        data['teacher_permissions'] = permissions_for_teacher(user)
        data['ai_available'] = ai_available_for_user(user)
    elif 'staff' in roles:
        data['ai_available'] = ai_available_for_user(user)
    return data


class MeUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_blank=True)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    display_name = serializers.CharField(required=False, allow_blank=True, max_length=50)
    timezone = serializers.CharField(required=False, allow_blank=True, max_length=64)
    theme = serializers.ChoiceField(
        required=False,
        choices=[Profile.THEME_LIGHT, Profile.THEME_DARK, Profile.THEME_SYSTEM],
    )

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
        if 'theme' in data:
            profile.theme = data['theme']
        profile.save()
        return user


class StudentRegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    display_name = serializers.CharField(required=False, allow_blank=True, max_length=50)

    def validate_username(self, value):
        username = value.strip()
        if not username:
            raise serializers.ValidationError('Username is required.')
        if User.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError('That username is already taken.')
        return username

    def validate_email(self, value):
        email = value.strip()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError('That email is already registered.')
        return email

    def validate_password(self, value):
        validate_password(value)
        return value

    def save(self):
        from scheduling.services.registration import register_student

        user, error = register_student(
            username=self.validated_data['username'],
            email=self.validated_data['email'],
            password=self.validated_data['password'],
            display_name=self.validated_data.get('display_name', ''),
        )
        if error:
            raise serializers.ValidationError(error)
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
