from rest_framework.permissions import BasePermission
class IsSelfOrTeachingStaff(BasePermission):
    def has_permission(self, request, view): return bool(request.user and request.user.is_authenticated)
    def has_object_permission(self, request, view, obj):
        learner = getattr(obj, "learner", None) or getattr(getattr(obj, "enrollment", None), "learner", None)
        if learner == request.user: return True
        course = getattr(obj, "course", None) or getattr(getattr(obj, "enrollment", None), "course", None)
        return request.user.role == "admin" or (request.user.role == "instructor" and getattr(course, "instructor_id", None) == request.user.id)
