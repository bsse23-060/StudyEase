from django.db.models import Q, QuerySet
from accounts.models import User
from learning.models import Enrollment
from study_tools.models import Document

def authorised_documents(user, *, include_deleted=False) -> QuerySet[Document]:
    qs = Document.objects.select_related("course__instructor", "lesson__module__course")
    if not include_deleted: qs = qs.filter(deleted_at__isnull=True)
    if user.role == User.Role.ADMIN or user.is_superuser: return qs
    owned = Q(owner=user)
    if user.role == User.Role.INSTRUCTOR:
        return qs.filter(owned | Q(visibility=Document.Visibility.COURSE, course__instructor=user)).distinct()
    enrolled = Q(visibility=Document.Visibility.COURSE, course__is_published=True, course__enrollments__learner=user, course__enrollments__status=Enrollment.Status.ACTIVE)
    return qs.filter(owned | enrolled).distinct()

def can_control_document(user, document: Document) -> bool:
    return bool(user.is_superuser or user.role == User.Role.ADMIN or document.owner_id == user.id or (user.role == User.Role.INSTRUCTOR and document.course and document.course.instructor_id == user.id))
