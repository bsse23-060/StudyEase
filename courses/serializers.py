from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from accounts.models import User
from .models import Concept, Course, Lesson, Module, Quiz, QuizAnswerOption, QuizQuestion

class QuizAnswerOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizAnswerOption
        fields = ("id", "question", "text", "position", "is_correct")
        extra_kwargs = {"is_correct": {"write_only": True}}
    def validate_question(self, question):
        request = self.context["request"]
        if request.user.role != User.Role.ADMIN and question.lesson.module.course.instructor_id != request.user.id:
            raise serializers.ValidationError("You may only manage options in your own course.")
        return question

class QuizQuestionSerializer(serializers.ModelSerializer):
    answer_options = QuizAnswerOptionSerializer(many=True, read_only=True)
    class Meta:
        model = QuizQuestion
        fields = "__all__"
        extra_kwargs = {"correct_answer": {"write_only": True}}
    def validate(self, attrs):
        kind = attrs.get("kind", getattr(self.instance, "kind", None)); options = attrs.get("options", getattr(self.instance, "options", [])); answer = attrs.get("correct_answer", getattr(self.instance, "correct_answer", None))
        if kind == QuizQuestion.Kind.MULTIPLE_CHOICE:
            if len(options) < 2: raise serializers.ValidationError({"options": "Multiple-choice questions need at least two options."})
            if not isinstance(answer, int) or not 0 <= answer < len(options): raise serializers.ValidationError({"correct_answer": "Must be a valid option index."})
        elif kind == QuizQuestion.Kind.TRUE_FALSE and not isinstance(answer, bool): raise serializers.ValidationError({"correct_answer": "Must be true or false."})
        elif kind == QuizQuestion.Kind.SHORT_ANSWER and not isinstance(answer, str): raise serializers.ValidationError({"correct_answer": "Must be text."})
        request = self.context.get("request"); lesson = attrs.get("lesson", getattr(self.instance, "lesson", None)); quiz = attrs.get("quiz", getattr(self.instance, "quiz", None))
        if quiz and lesson and quiz.lesson_id != lesson.id: raise serializers.ValidationError({"quiz": "The quiz and question lesson must match."})
        if quiz: lesson = quiz.lesson
        concept = attrs.get("concept", getattr(self.instance, "concept", None))
        if concept and concept.course_id and lesson and concept.course_id != lesson.module.course_id: raise serializers.ValidationError({"concept": "The concept must belong to the question course."})
        if request and lesson and request.method not in ("GET", "HEAD", "OPTIONS") and request.user.role != User.Role.ADMIN and lesson.module.course.instructor_id != request.user.id:
            raise serializers.ValidationError({"lesson": "You may only author questions in your own course."})
        return attrs
    def _sync_options(self, question):
        if question.kind != QuizQuestion.Kind.MULTIPLE_CHOICE: question.answer_options.all().delete(); return
        question.answer_options.all().delete()
        for position, text in enumerate(question.options, start=1): QuizAnswerOption.objects.create(question=question, text=str(text), position=position, is_correct=question.correct_answer == position - 1)
    def create(self, validated_data):
        question = super().create(validated_data); self._sync_options(question); return question
    def update(self, instance, validated_data):
        question = super().update(instance, validated_data); self._sync_options(question); return question

class QuizSerializer(serializers.ModelSerializer):
    questions = QuizQuestionSerializer(many=True, read_only=True)
    attempt_count = serializers.SerializerMethodField()
    class Meta:
        model = Quiz
        fields = ("id", "lesson", "title", "instructions", "pass_mark", "maximum_attempts", "available_from", "available_until", "time_limit_minutes", "is_published", "questions", "attempt_count", "created_at", "updated_at")
        read_only_fields = ("attempt_count", "created_at", "updated_at")
    def get_attempt_count(self, obj) -> int:
        request = self.context.get("request")
        return obj.submissions.filter(learner=request.user, status="submitted").count() if request and request.user.role == User.Role.STUDENT else obj.submissions.count()
    def validate_lesson(self, lesson):
        request = self.context["request"]
        if request.user.role != User.Role.ADMIN and lesson.module.course.instructor_id != request.user.id: raise serializers.ValidationError("You may only manage quizzes in your own course.")
        return lesson
    def validate(self, attrs):
        start = attrs.get("available_from", getattr(self.instance, "available_from", None)); end = attrs.get("available_until", getattr(self.instance, "available_until", None))
        if start and end and end <= start: raise serializers.ValidationError({"available_until": "Availability end must follow the start."})
        return attrs

class LessonSerializer(serializers.ModelSerializer):
    questions = QuizQuestionSerializer(many=True, read_only=True)
    class Meta:
        model = Lesson
        fields = ("id", "module", "title", "kind", "content", "resource_url", "estimated_minutes", "position", "questions")
    def validate_module(self, module):
        request = self.context.get("request")
        if request and request.user.role != User.Role.ADMIN and module.course.instructor_id != request.user.id: raise serializers.ValidationError("You may only author lessons in your own course.")
        return module

class ModuleSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)
    class Meta:
        model = Module
        fields = ("id", "course", "title", "summary", "position", "lessons")
    def validate_course(self, course):
        request = self.context.get("request")
        if request and request.user.role != User.Role.ADMIN and course.instructor_id != request.user.id: raise serializers.ValidationError("You may only author modules in your own course.")
        return course

class CourseSerializer(serializers.ModelSerializer):
    modules = serializers.SerializerMethodField()
    instructor_name = serializers.CharField(source="instructor.full_name", read_only=True)
    class Meta:
        model = Course
        fields = ("id", "slug", "title", "description", "instructor", "instructor_name", "is_published", "is_archived", "archived_at", "archived_by", "metadata", "created_at", "updated_at", "modules")
        read_only_fields = ("instructor", "is_archived", "archived_at", "archived_by", "created_at", "updated_at")
    @extend_schema_field(ModuleSerializer(many=True))
    def get_modules(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated: return []
        if getattr(self.context.get("view"), "action", None) == "list": return []
        allowed = request.user.role == User.Role.ADMIN or obj.instructor_id == request.user.id or obj.enrollments.filter(learner=request.user, status="active").exists()
        return ModuleSerializer(obj.modules.all(), many=True, context=self.context).data if allowed else []

class ConceptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Concept
        fields = ("id", "created_by", "course", "slug", "name", "description", "lessons", "prerequisites")
        read_only_fields = ("created_by",)
    def validate_lessons(self, lessons):
        request = self.context["request"]
        if request.user.role != User.Role.ADMIN and any(lesson.module.course.instructor_id != request.user.id for lesson in lessons): raise serializers.ValidationError("Concepts may only be attached to your own lessons.")
        return lessons
    def validate_course(self, course):
        request = self.context["request"]
        if course and request.user.role != User.Role.ADMIN and course.instructor_id != request.user.id: raise serializers.ValidationError("You may only author concepts in your own course.")
        return course
    def validate_prerequisites(self, value):
        if self.instance and self.instance in value: raise serializers.ValidationError("A concept cannot require itself.")
        if self.instance:
            def reaches_self(node, seen):
                if node.pk == self.instance.pk: return True
                if node.pk in seen: return False
                return any(reaches_self(parent, seen | {node.pk}) for parent in node.prerequisites.all())
            if any(reaches_self(item, set()) for item in value): raise serializers.ValidationError("Prerequisites must form an acyclic graph.")
        course = self.initial_data.get("course") or getattr(self.instance, "course_id", None)
        if course and any(item.course_id != int(course) for item in value): raise serializers.ValidationError("Prerequisites must belong to the same course.")
        return value
    def validate(self, attrs):
        course = attrs.get("course", getattr(self.instance, "course", None)); lessons = attrs.get("lessons", [])
        if course and any(lesson.module.course_id != course.id for lesson in lessons): raise serializers.ValidationError({"lessons": "Every lesson must belong to the concept course."})
        return attrs
