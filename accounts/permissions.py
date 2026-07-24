from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and (request.user.is_superuser or request.user.role == "admin"))

class IsInstructorOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and (request.user.is_superuser or request.user.role in {"instructor", "admin"}))

class IsInstructorOwnerOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or IsInstructorOrAdmin().has_permission(request, view)
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS: return True
        course = obj if obj.__class__.__name__ == "Course" else getattr(obj, "course", None)
        course = course or getattr(getattr(obj, "module", None), "course", None)
        course = course or getattr(getattr(getattr(obj, "lesson", None), "module", None), "course", None)
        question = getattr(obj, "question", None)
        course = course or getattr(getattr(getattr(question, "lesson", None), "module", None), "course", None)
        if getattr(course, "is_archived", False) and not (request.user.is_superuser or request.user.role == "admin"): return False
        if obj.__class__.__name__ == "Concept": return request.user.is_superuser or request.user.role == "admin" or obj.created_by_id == request.user.id
        return request.user.is_superuser or request.user.role == "admin" or getattr(course, "instructor_id", None) == request.user.id
