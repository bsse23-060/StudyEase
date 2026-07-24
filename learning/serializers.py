from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from accounts.models import User
from courses.models import Quiz, QuizQuestion
from .models import EngagementEvent, Enrollment, LearningProfile, Mastery, QuizAttempt, QuizSubmission, QuizSubmissionAnswer, RoadmapStep

class EnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enrollment
        fields = ("id", "learner", "course", "status", "enrolled_at", "completed_at")
        read_only_fields = ("learner", "enrolled_at", "completed_at")
    def validate_course(self, course):
        request = self.context["request"]
        if request.user.role != User.Role.STUDENT: raise serializers.ValidationError("Only students can self-enroll.")
        if course.is_archived or not course.is_published: raise serializers.ValidationError("This course is not open for enrollment.")
        return course

class MasterySerializer(serializers.ModelSerializer):
    concept_name = serializers.CharField(source="concept.name", read_only=True)
    class Meta:
        model = Mastery
        fields = ("id", "learner", "concept", "concept_name", "probability", "stability_days", "last_seen_at", "updated_at")
        read_only_fields = fields

class LearningProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningProfile
        fields = ("id", "user", "modality", "depth", "pace", "abstraction", "preferred_time", "updated_at")
        read_only_fields = ("user", "updated_at")
    def validate(self, attrs):
        if not self.instance and LearningProfile.objects.filter(user=self.context["request"].user).exists(): raise serializers.ValidationError("A learning profile already exists.")
        return attrs

class QuizAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizAttempt
        fields = ("id", "learner", "question", "answer", "is_correct", "points_earned", "seconds_spent", "feedback", "created_at")
        read_only_fields = ("learner", "is_correct", "points_earned", "feedback", "created_at")
    @transaction.atomic
    def create(self, validated_data):
        question = validated_data["question"]; answer = validated_data["answer"]
        if question.kind == QuizQuestion.Kind.SHORT_ANSWER:
            correct = isinstance(answer, str) and answer.strip().casefold() == str(question.correct_answer).strip().casefold()
        else: correct = answer == question.correct_answer
        attempt = QuizAttempt.objects.create(learner=self.context["request"].user, is_correct=correct, points_earned=question.points if correct else 0, feedback=question.explanation, **validated_data)
        if question.concept_id:
            mastery, _ = Mastery.objects.get_or_create(learner=attempt.learner, concept=question.concept)
            mastery.probability = min(1, mastery.probability + .1) if correct else max(0, mastery.probability - .05)
            mastery.last_seen_at = timezone.now(); mastery.save()
        return attempt
    def validate(self, attrs):
        question = attrs.get("question"); answer = attrs.get("answer"); user = self.context["request"].user
        if not question.lesson.module.course.enrollments.filter(learner=user, status=Enrollment.Status.ACTIVE).exists(): raise serializers.ValidationError("You must be actively enrolled in this course.")
        if question.kind == QuizQuestion.Kind.MULTIPLE_CHOICE and (not isinstance(answer, int) or isinstance(answer, bool) or not 0 <= answer < len(question.options)): raise serializers.ValidationError({"answer": "Must be a valid option index."})
        if question.kind == QuizQuestion.Kind.TRUE_FALSE and not isinstance(answer, bool): raise serializers.ValidationError({"answer": "Must be true or false."})
        if question.kind == QuizQuestion.Kind.SHORT_ANSWER and not isinstance(answer, str): raise serializers.ValidationError({"answer": "Must be text."})
        return attrs

class QuizSubmissionAnswerSerializer(serializers.ModelSerializer):
    prompt = serializers.CharField(source="question.prompt", read_only=True)
    class Meta:
        model = QuizSubmissionAnswer
        fields = ("id", "question", "prompt", "answer", "is_correct", "points_earned", "feedback")
        read_only_fields = fields

class QuizSubmissionSerializer(serializers.ModelSerializer):
    answers = QuizSubmissionAnswerSerializer(many=True, read_only=True)
    class Meta:
        model = QuizSubmission
        fields = ("id", "learner", "quiz", "status", "started_at", "submitted_at", "total_score", "maximum_score", "percentage_score", "passed", "idempotency_key", "answers")
        read_only_fields = ("learner", "status", "started_at", "submitted_at", "total_score", "maximum_score", "percentage_score", "passed", "answers")
    def validate_quiz(self, quiz):
        user = self.context["request"].user; now = timezone.now()
        if user.role != User.Role.STUDENT: raise serializers.ValidationError("Only students can start quiz attempts.")
        if not quiz.is_published: raise serializers.ValidationError("This quiz is not published.")
        if quiz.available_from and now < quiz.available_from: raise serializers.ValidationError("This quiz is not available yet.")
        if quiz.available_until and now > quiz.available_until: raise serializers.ValidationError("This quiz is no longer available.")
        if not quiz.lesson.module.course.enrollments.filter(learner=user, status=Enrollment.Status.ACTIVE).exists(): raise serializers.ValidationError("You must be actively enrolled in this course.")
        if quiz.maximum_attempts is not None and quiz.submissions.filter(learner=user, status=QuizSubmission.Status.SUBMITTED).count() >= quiz.maximum_attempts: raise serializers.ValidationError("Maximum attempts reached.")
        return quiz
    def validate(self, attrs):
        key = attrs.get("idempotency_key", "")
        if key and QuizSubmission.objects.filter(learner=self.context["request"].user, quiz=attrs.get("quiz"), idempotency_key=key).exists(): raise serializers.ValidationError({"idempotency_key": "This start request was already accepted."})
        return attrs

class QuizAnswerInputSerializer(serializers.Serializer):
    question_id = serializers.IntegerField(min_value=1)
    answer = serializers.JSONField()

class QuizSubmitSerializer(serializers.Serializer):
    answers = QuizAnswerInputSerializer(many=True, allow_empty=False)
    idempotency_key = serializers.CharField(max_length=64, required=False, allow_blank=True)
    def validate(self, attrs):
        submission = self.context["submission"]
        if submission.status == QuizSubmission.Status.SUBMITTED: raise serializers.ValidationError("This attempt has already been submitted.")
        now = timezone.now()
        if not submission.quiz.is_published: raise serializers.ValidationError("This quiz is no longer published.")
        if submission.quiz.available_from and now < submission.quiz.available_from: raise serializers.ValidationError("This quiz is not available yet.")
        if submission.quiz.available_until and now > submission.quiz.available_until: raise serializers.ValidationError("This quiz is no longer available.")
        if submission.quiz.time_limit_minutes and timezone.now() > submission.started_at + timedelta(minutes=submission.quiz.time_limit_minutes): raise serializers.ValidationError("The quiz time limit has expired.")
        ids = [item["question_id"] for item in attrs["answers"]]
        if len(ids) != len(set(ids)): raise serializers.ValidationError({"answers": "A question may only be answered once."})
        questions = {q.id: q for q in submission.quiz.questions.all()}
        unknown = set(ids) - set(questions)
        if unknown: raise serializers.ValidationError({"answers": f"Questions do not belong to this quiz: {sorted(unknown)}."})
        missing = [q.id for q in questions.values() if q.is_required and q.id not in ids]
        if missing: raise serializers.ValidationError({"answers": f"Required questions are missing: {missing}."})
        for item in attrs["answers"]:
            q = questions[item["question_id"]]; answer = item["answer"]
            if q.kind == QuizQuestion.Kind.MULTIPLE_CHOICE and (not isinstance(answer, int) or isinstance(answer, bool) or not 0 <= answer < len(q.options)): raise serializers.ValidationError({"answers": f"Question {q.id} requires a valid option index."})
            if q.kind == QuizQuestion.Kind.TRUE_FALSE and not isinstance(answer, bool): raise serializers.ValidationError({"answers": f"Question {q.id} requires true or false."})
            if q.kind == QuizQuestion.Kind.SHORT_ANSWER and not isinstance(answer, str): raise serializers.ValidationError({"answers": f"Question {q.id} requires text."})
        attrs["question_map"] = questions
        return attrs
    @transaction.atomic
    def save(self):
        submission = QuizSubmission.objects.select_for_update().get(pk=self.context["submission"].pk)
        if submission.status == QuizSubmission.Status.SUBMITTED: raise serializers.ValidationError("This attempt has already been submitted.")
        total = 0; maximum = sum(q.points for q in submission.quiz.questions.all())
        for item in self.validated_data["answers"]:
            question = self.validated_data["question_map"][item["question_id"]]; answer = item["answer"]
            correct = answer.strip().casefold() == str(question.correct_answer).strip().casefold() if question.kind == QuizQuestion.Kind.SHORT_ANSWER else answer == question.correct_answer
            points = question.points if correct else 0; total += points
            QuizSubmissionAnswer.objects.create(submission=submission, question=question, answer=answer, is_correct=correct, points_earned=points, feedback=question.explanation)
            if question.concept_id:
                mastery, _ = Mastery.objects.get_or_create(learner=submission.learner, concept=question.concept)
                mastery.probability = min(1, mastery.probability + .1) if correct else max(0, mastery.probability - .05); mastery.last_seen_at = timezone.now(); mastery.save()
        percentage = (total / maximum * 100) if maximum else 0
        submission.status = QuizSubmission.Status.SUBMITTED; submission.submitted_at = timezone.now(); submission.total_score = total; submission.maximum_score = maximum; submission.percentage_score = percentage
        submission.passed = None if submission.quiz.pass_mark is None else percentage >= submission.quiz.pass_mark
        submission.idempotency_key = self.validated_data.get("idempotency_key", submission.idempotency_key); submission.save()
        return submission

class RoadmapStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoadmapStep
        fields = "__all__"
        read_only_fields = ("completed_at",)
    def validate(self, attrs):
        enrollment = attrs.get("enrollment", getattr(self.instance, "enrollment", None)); module = attrs.get("module", getattr(self.instance, "module", None))
        if enrollment and module and enrollment.course_id != module.course_id: raise serializers.ValidationError("The module must belong to the enrolled course.")
        request = self.context.get("request")
        if request and request.method not in ("GET", "HEAD", "OPTIONS") and request.user.role == User.Role.INSTRUCTOR and enrollment.course.instructor_id != request.user.id: raise serializers.ValidationError("You may only manage roadmaps for your own courses.")
        return attrs

class EngagementEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = EngagementEvent
        fields = ("id", "learner", "kind", "module", "payload", "occurred_at")
        read_only_fields = ("learner", "occurred_at")
    def validate_module(self, module):
        if module and not module.course.enrollments.filter(learner=self.context["request"].user, status=Enrollment.Status.ACTIVE).exists(): raise serializers.ValidationError("The module is not in one of your active enrollments.")
        return module
