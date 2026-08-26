from django.conf import settings
from django.db import models


class DemoItem(models.Model):
    title = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Profile(models.Model):
    THEME_LIGHT = 'light'
    THEME_DARK = 'dark'
    THEME_SYSTEM = 'system'
    THEME_CHOICES = [
        (THEME_LIGHT, 'Light'),
        (THEME_DARK, 'Dark'),
        (THEME_SYSTEM, 'System'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    display_name = models.CharField(max_length=50, blank=True)
    timezone = models.TextField(default='UTC')
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default=THEME_SYSTEM)
    onboarding_dismissed_at = models.DateTimeField(null=True, blank=True)
    stripe_customer_id = models.CharField(max_length=100, blank=True)
    external_id = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.display_name or self.user.username


class ClassType(models.Model):
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='class_types',
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    default_capacity = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.teacher.username} — {self.name}"


class ClassOffering(models.Model):
    """Teachable unit in a teacher's catalog (subject → level → focus + topics).

    Session titles are chosen from this list. Per-teacher rows support multi-tenant SaaS.
    """

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='class_offerings',
    )
    subject = models.CharField(max_length=100)
    level = models.CharField(max_length=100)
    focus = models.CharField(max_length=150)
    topics_ordered = models.BooleanField(
        default=False,
        help_text='When enabled, topics are meant to be taught in sort order.',
    )
    default_capacity = models.PositiveIntegerField(default=4)
    ticket_cost = models.PositiveIntegerField(
        default=1,
        help_text='Booking tickets required to reserve a session for this class.',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'scheduling_classes'
        ordering = ['subject', 'level', 'focus']
        verbose_name = 'class'
        verbose_name_plural = 'classes'
        constraints = [
            models.UniqueConstraint(
                fields=['teacher', 'subject', 'level', 'focus'],
                name='unique_class_offering_per_teacher',
            ),
        ]

    @property
    def display_name(self):
        return f"{self.subject} · {self.level} · {self.focus}"

    def __str__(self):
        return self.display_name


class ClassTopic(models.Model):
    """Optional curriculum topic within a class offering."""

    class_offering = models.ForeignKey(
        ClassOffering,
        on_delete=models.CASCADE,
        related_name='topics',
    )
    title = models.CharField(max_length=150)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'title']
        constraints = [
            models.UniqueConstraint(
                fields=['class_offering', 'title'],
                name='unique_topic_per_class',
            ),
        ]

    def __str__(self):
        return self.title


class AvailabilityBlock(models.Model):
    WEEKDAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='availability_blocks',
    )
    weekday = models.IntegerField(choices=WEEKDAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ['weekday', 'start_time']

    def __str__(self):
        return f"{self.teacher.username} — {self.get_weekday_display()} {self.start_time}-{self.end_time}"


class SpecialAvailability(models.Model):
    """One-off availability on a specific calendar date (e.g. holiday makeup day)."""

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='special_availabilities',
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['date', 'start_time']
        verbose_name_plural = 'special availabilities'

    def __str__(self):
        label = f"{self.date} {self.start_time}-{self.end_time}"
        if self.note:
            return f"{self.teacher.username} — {label} ({self.note})"
        return f"{self.teacher.username} — {label}"


class TeacherPermission(models.Model):
    """Per-teacher capability flags — staff enables or disables studio features."""

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='teacher_permissions',
    )
    key = models.CharField(max_length=50)
    is_enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ['key']
        constraints = [
            models.UniqueConstraint(
                fields=['teacher', 'key'],
                name='unique_permission_per_teacher',
            ),
        ]

    def __str__(self):
        state = 'on' if self.is_enabled else 'off'
        return f"{self.teacher.username} — {self.key} ({state})"


class StudioGlossary(models.Model):
    """Customizable UI labels — staff renames students→clients, classes→sessions, etc."""

    key = models.SlugField(max_length=50, unique=True)
    singular = models.CharField(max_length=80)
    plural = models.CharField(max_length=80)

    class Meta:
        ordering = ['key']
        verbose_name_plural = 'studio glossary'

    def __str__(self):
        return f"{self.key}: {self.singular} / {self.plural}"


def studio_logo_upload_path(instance, filename):
    return f'branding/{filename}'


class StudioBranding(models.Model):
    """Sign-in screen and app header — display name and optional logo."""

    display_name = models.CharField(max_length=120, default='Booking Studio')
    logo = models.FileField(upload_to=studio_logo_upload_path, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'studio branding'
        verbose_name_plural = 'studio branding'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={'display_name': 'Booking Studio'})
        return obj

    def __str__(self):
        return self.display_name


class StudioLLMConfig(models.Model):
    """Studio-wide AI provider — staff configures; teachers need use_ai permission."""

    PROVIDER_OPENAI = 'openai'
    PROVIDER_ANTHROPIC = 'anthropic'
    PROVIDER_OLLAMA = 'ollama'
    PROVIDER_OPENAI_COMPATIBLE = 'openai_compatible'
    PROVIDER_CHOICES = [
        (PROVIDER_OPENAI, 'OpenAI'),
        (PROVIDER_ANTHROPIC, 'Anthropic'),
        (PROVIDER_OLLAMA, 'Ollama (local)'),
        (PROVIDER_OPENAI_COMPATIBLE, 'OpenAI-compatible API'),
    ]

    provider = models.CharField(max_length=30, choices=PROVIDER_CHOICES, default=PROVIDER_OPENAI)
    api_key = models.CharField(max_length=500, blank=True)
    base_url = models.URLField(
        blank=True,
        help_text='Optional. Ollama default http://127.0.0.1:11434; custom for OpenAI-compatible hosts.',
    )
    model_name = models.CharField(max_length=120, default='gpt-4o-mini')
    is_enabled = models.BooleanField(default=False)
    max_tokens = models.PositiveIntegerField(default=500)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'studio LLM config'
        verbose_name_plural = 'studio LLM config'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        status = 'on' if self.is_enabled else 'off'
        return f'LLM ({self.provider}, {status})'


class Session(models.Model):
    MEETING_PROVIDER_CHOICES = [
        ('none', 'No video link'),
        ('google_meet', 'Google Meet'),
        ('zoom', 'Zoom'),
    ]

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sessions_taught',
    )
    class_type = models.ForeignKey(
        ClassType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sessions',
    )
    class_offering = models.ForeignKey(
        'ClassOffering',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sessions',
    )
    class_topic = models.ForeignKey(
        'ClassTopic',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sessions',
    )
    title = models.CharField(max_length=200)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    capacity = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=20,
        choices=[('open', 'Open'), ('cancelled', 'Cancelled')],
    )
    meeting_provider = models.CharField(
        max_length=20,
        choices=MEETING_PROVIDER_CHOICES,
        default='google_meet',
    )
    meeting_url = models.URLField(blank=True)
    google_calendar_event_id = models.CharField(
        max_length=200,
        blank=True,
        help_text='Calendar event backing the Meet link — used to sync updates/cancellations.',
    )
    external_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.teacher.username} - {self.title} - {self.start_time}"


class Booking(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookings_made',
    )
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='bookings')
    membership = models.ForeignKey(
        'Membership',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bookings',
    )
    status = models.CharField(
        max_length=20,
        choices=[('confirmed', 'Confirmed'), ('cancelled', 'Cancelled')],
    )
    tickets_spent = models.PositiveIntegerField(default=0)
    class_request = models.OneToOneField(
        'ClassRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='booking',
    )
    external_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.username} - {self.session.title} - {self.status}"


class ClassRequest(models.Model):
    """Student-requested lesson during teacher availability — pending until approved."""

    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_DENIED = 'denied'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_DENIED, 'Denied'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='class_requests',
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='class_requests_received',
        null=True,
        blank=True,
    )
    open_to_any_teacher = models.BooleanField(default=False)
    subject = models.CharField(max_length=100, blank=True)
    level = models.CharField(max_length=100, blank=True)
    focus = models.CharField(max_length=100, blank=True)
    class_offering = models.ForeignKey(
        ClassOffering,
        on_delete=models.PROTECT,
        related_name='class_requests',
        null=True,
        blank=True,
    )
    class_topic = models.ForeignKey(
        ClassTopic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='class_requests',
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    tickets_requested = models.PositiveIntegerField()
    membership = models.ForeignKey(
        'Membership',
        on_delete=models.PROTECT,
        related_name='class_requests',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    session = models.ForeignKey(
        Session,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='class_requests',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        teacher_label = self.teacher.username if self.teacher_id else 'any teacher'
        return f"{self.student.username} → {teacher_label} ({self.status})"

    @property
    def class_profile_label(self):
        if self.class_offering_id:
            return self.class_offering.display_name
        parts = [self.subject, self.level, self.focus]
        return ' · '.join(part for part in parts if part)


class MembershipPlan(models.Model):
    """Studio-defined membership tier — price and which catalog classes students may book."""

    PLAN_SUBSCRIPTION = 'subscription'
    PLAN_TICKET_PACK = 'ticket_pack'
    PLAN_TYPE_CHOICES = [
        (PLAN_SUBSCRIPTION, 'Subscription'),
        (PLAN_TICKET_PACK, 'Ticket pack'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    plan_type = models.CharField(
        max_length=20,
        choices=PLAN_TYPE_CHOICES,
        default=PLAN_SUBSCRIPTION,
    )
    price_cents = models.PositiveIntegerField(default=0)
    billing_period_days = models.PositiveIntegerField(default=30)
    ticket_allowance = models.PositiveIntegerField(
        default=10,
        help_text='Tickets granted each time a student purchases one billing period.',
    )
    is_active = models.BooleanField(default=True)
    subject = models.CharField(
        max_length=100,
        blank=True,
        help_text='When set, members may book any active class with this subject.',
    )
    allowed_classes = models.ManyToManyField(
        ClassOffering,
        blank=True,
        related_name='membership_plans',
        help_text='Leave empty to allow all active classes.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def includes_all_classes(self):
        return not self.subject and not self.allowed_classes.all()


class Membership(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='memberships',
    )
    plan = models.ForeignKey(
        MembershipPlan,
        on_delete=models.PROTECT,
        related_name='memberships',
    )
    is_active = models.BooleanField(default=True)
    valid_until = models.DateField(null=True, blank=True)
    tickets_remaining = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        status = 'active' if self.is_active else 'inactive'
        return f"{self.user.username} — {self.plan.name} ({status})"


class Payment(models.Model):
    """Membership purchase record — mock in sandbox, Stripe when configured."""

    PROVIDER_MOCK = 'mock'
    PROVIDER_STRIPE = 'stripe'
    PROVIDER_STAFF = 'staff'
    PROVIDER_CHOICES = [
        (PROVIDER_MOCK, 'Mock'),
        (PROVIDER_STRIPE, 'Stripe'),
        (PROVIDER_STAFF, 'Recorded by staff'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_REFUNDED = 'refunded'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_REFUNDED, 'Refunded'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments',
    )
    plan = models.ForeignKey(
        MembershipPlan,
        on_delete=models.PROTECT,
        related_name='payments',
    )
    membership = models.ForeignKey(
        Membership,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments',
    )
    amount_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default='usd')
    quantity = models.PositiveIntegerField(
        default=1,
        help_text='Billing periods purchased (e.g. months).',
    )
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default=PROVIDER_MOCK)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_COMPLETED)
    stripe_checkout_session_id = models.CharField(max_length=200, blank=True)
    stripe_payment_intent_id = models.CharField(max_length=200, blank=True)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} — {self.plan.name} — {self.amount_cents}¢ ({self.status})"


def blog_image_upload_path(instance, filename):
    return f'blog/{instance.pk or "draft"}/{filename}'


class BlogPost(models.Model):
    """Studio announcement shown on the home page."""

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='blog_posts',
    )
    title = models.CharField(max_length=200)
    body = models.TextField()
    image = models.FileField(upload_to=blog_image_upload_path, blank=True)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Message(models.Model):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages',
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_messages',
    )
    subject = models.CharField(max_length=200)
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subject} ({self.sender.username} → {self.recipient.username})"


class GoogleCredential(models.Model):
    """Per-user Google OAuth tokens for Calendar/Meet (Phase 20)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='google_credential',
    )
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    scopes = models.TextField(blank=True)
    google_email = models.CharField(max_length=254, blank=True)
    connected_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Google credential for {self.user.username}'


class CatalogSubject(models.Model):
    """Studio-wide subject for class roadmaps (e.g. Japanese, English)."""

    name = models.CharField(max_length=100, unique=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class CatalogLevel(models.Model):
    """Proficiency level within a subject."""

    subject = models.ForeignKey(
        CatalogSubject,
        on_delete=models.CASCADE,
        related_name='levels',
    )
    name = models.CharField(max_length=100)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['sort_order', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['subject', 'name'],
                name='unique_catalog_level_per_subject',
            ),
        ]

    def __str__(self):
        return f'{self.subject.name} · {self.name}'


class CatalogFocus(models.Model):
    """Skill or strand within a level (e.g. Grammar, Speaking)."""

    level = models.ForeignKey(
        CatalogLevel,
        on_delete=models.CASCADE,
        related_name='focuses',
    )
    name = models.CharField(max_length=150)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name_plural = 'catalog focuses'
        constraints = [
            models.UniqueConstraint(
                fields=['level', 'name'],
                name='unique_catalog_focus_per_level',
            ),
        ]

    def __str__(self):
        return f'{self.level} · {self.name}'


class CatalogTopic(models.Model):
    """Ordered roadmap topic within a focus."""

    focus = models.ForeignKey(
        CatalogFocus,
        on_delete=models.CASCADE,
        related_name='topics',
    )
    title = models.CharField(max_length=150)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['sort_order', 'title']
        constraints = [
            models.UniqueConstraint(
                fields=['focus', 'title'],
                name='unique_catalog_topic_per_focus',
            ),
        ]

    def __str__(self):
        return self.title


class CurriculumItem(models.Model):
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='curriculum_items',
    )
    title = models.CharField(max_length=200)
    content = models.TextField()
    sort_order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ['sort_order', 'title']

    def __str__(self):
        return self.title


class StaffAlert(models.Model):
    """In-app activity alert for studio staff (signups, membership, payments)."""

    CATEGORY_USERS = 'users'
    CATEGORY_MEMBERSHIP = 'membership'
    CATEGORY_FINANCIAL = 'financial'
    CATEGORY_CHOICES = [
        (CATEGORY_USERS, 'Users'),
        (CATEGORY_MEMBERSHIP, 'Membership'),
        (CATEGORY_FINANCIAL, 'Financial'),
    ]

    EVENT_STUDENT_REGISTERED = 'student_registered'
    EVENT_MEMBERSHIP_ACTIVATED = 'membership_activated'
    EVENT_MEMBERSHIP_RENEWED = 'membership_renewed'
    EVENT_TICKETS_GRANTED = 'tickets_granted'
    EVENT_PAYMENT_COMPLETED = 'payment_completed'

    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, db_index=True)
    event_type = models.CharField(max_length=40, db_index=True)
    title = models.CharField(max_length=200)
    body = models.CharField(max_length=400, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff_alerts_as_actor',
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.category}:{self.event_type} — {self.title}'


class StaffAlertRead(models.Model):
    """Per-staff read receipt for a StaffAlert."""

    alert = models.ForeignKey(
        StaffAlert,
        on_delete=models.CASCADE,
        related_name='reads',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='staff_alert_reads',
    )
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['alert', 'user'],
                name='unique_staff_alert_read_per_user',
            ),
        ]

    def __str__(self):
        return f'{self.user_id} read alert {self.alert_id}'


class StaffActionLog(models.Model):
    """Audit trail for staff overrides — who changed what, for whom, and when."""

    ACTION_USER_CREATED = 'user_created'
    ACTION_PASSWORD_RESET = 'password_reset'
    ACTION_MEMBERSHIP_GRANTED = 'membership_granted'
    ACTION_MEMBERSHIP_UPDATED = 'membership_updated'
    ACTION_TICKETS_ADJUSTED = 'tickets_adjusted'
    ACTION_BOOKING_CANCELLED = 'booking_cancelled'
    ACTION_CHOICES = [
        (ACTION_USER_CREATED, 'User created'),
        (ACTION_PASSWORD_RESET, 'Password reset'),
        (ACTION_MEMBERSHIP_GRANTED, 'Membership granted'),
        (ACTION_MEMBERSHIP_UPDATED, 'Membership updated'),
        (ACTION_TICKETS_ADJUSTED, 'Tickets adjusted'),
        (ACTION_BOOKING_CANCELLED, 'Booking cancelled'),
    ]

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff_actions',
    )
    action = models.CharField(max_length=40, choices=ACTION_CHOICES, db_index=True)
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff_actions_received',
    )
    summary = models.CharField(max_length=300)
    detail = models.JSONField(default=dict, blank=True)
    note = models.CharField(
        max_length=300,
        blank=True,
        help_text='Optional reason staff typed when making the change.',
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.action} — {self.summary}'
