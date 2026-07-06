from rest_framework import serializers

from progress.models import ProgressReport, ScoreDimension, SessionFeedback, Skill
from progress.services import apply_feedback_scores, feedback_scores, subject_for_session


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['id', 'name']



class ProgressReportSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.username', read_only=True)
    teacher_name = serializers.CharField(source='teacher.username', read_only=True)
    skill_name = serializers.CharField(source='skill.name', read_only=True, default=None)

    class Meta:
        model = ProgressReport
        fields = [
            'id',
            'student',
            'student_name',
            'teacher_name',
            'skill',
            'skill_name',
            'rating',
            'note',
            'created_at',
        ]
        read_only_fields = ['teacher_name', 'created_at']



class SessionFeedbackSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.username', read_only=True)
    teacher_name = serializers.CharField(source='teacher.username', read_only=True)
    session_title = serializers.CharField(source='session.title', read_only=True, default=None)
    session_start_time = serializers.DateTimeField(
        source='session.start_time', read_only=True, default=None
    )
    session_subject = serializers.SerializerMethodField()
    scores = serializers.JSONField(required=False)

    class Meta:
        model = SessionFeedback
        fields = [
            'id',
            'student',
            'student_name',
            'teacher_name',
            'session',
            'session_title',
            'session_start_time',
            'session_subject',
            'scores',
            'class_notes',
            'created_at',
        ]
        read_only_fields = ['teacher_name', 'created_at']

    def get_session_subject(self, obj):
        return subject_for_session(obj.session)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['scores'] = feedback_scores(instance)
        return data

    def _apply_scores(self, feedback, scores):
        apply_feedback_scores(feedback, scores or {}, session=feedback.session)

    def create(self, validated_data):
        scores = validated_data.pop('scores', {})
        feedback = SessionFeedback.objects.create(**validated_data)
        self._apply_scores(feedback, scores)
        return feedback

    def update(self, instance, validated_data):
        scores = validated_data.pop('scores', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if scores is not None:
            self._apply_scores(instance, scores)
        return instance



class ScoreDimensionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScoreDimension
        fields = ['key', 'label', 'sort_order', 'subject', 'min_score', 'max_score']



class StaffScoreDimensionSerializer(serializers.ModelSerializer):
    teacher_username = serializers.CharField(source='teacher.username', read_only=True, default=None)
    scope = serializers.SerializerMethodField()

    class Meta:
        model = ScoreDimension
        fields = [
            'id',
            'key',
            'label',
            'subject',
            'sort_order',
            'min_score',
            'max_score',
            'is_active',
            'teacher',
            'teacher_username',
            'scope',
        ]
        read_only_fields = ['key', 'teacher_username', 'scope']

    def get_scope(self, obj):
        if obj.subject:
            return obj.subject
        return 'all subjects'

    def validate(self, attrs):
        min_score = attrs.get('min_score', getattr(self.instance, 'min_score', 0))
        max_score = attrs.get('max_score', getattr(self.instance, 'max_score', 5))
        from progress.services import _validate_score_range

        min_score, max_score, error = _validate_score_range(min_score, max_score)
        if error:
            raise serializers.ValidationError(error)
        attrs['min_score'] = min_score
        attrs['max_score'] = max_score
        return attrs



class StaffScoreDimensionCreateSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=100)
    subject = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    min_score = serializers.IntegerField(required=False, default=0)
    max_score = serializers.IntegerField(required=False, default=5)


