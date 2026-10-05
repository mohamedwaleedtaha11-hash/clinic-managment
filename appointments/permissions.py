from rest_framework import permissions
from rest_framework.permissions import SAFE_METHODS


def _is_authenticated(user):
    return bool(user and user.is_authenticated)

class IsDoctor(permissions.BasePermission):
    """اليوزر لازم يكون دكتور."""

    def has_permission(self, request, view):
        return _is_authenticated(request.user) and hasattr(request.user, "doctor")

class IsPatientOrReadOnly(permissions.BasePermission):
    """القراءة للكل، والكتابة للمرضى بس."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return _is_authenticated(request.user) and hasattr(request.user, "patient")


class IsOwnerDoctorOrReadOnly(permissions.BasePermission):
    """
    للـ Doctor: القراءة للكل، والتعديل للدكتور صاحب الحساب (أو الأدمن).
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return _is_authenticated(request.user)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        if user.is_staff:
            return True
        owner_id = obj.doctor.user_id if hasattr(obj, "doctor") else obj.user_id
        return owner_id == user.id


class IsDoctorScheduleOrReadOnly(IsOwnerDoctorOrReadOnly):
    """
    للـ DoctorSchedule: القراءة للكل، والكتابة للدكتور (أو الأدمن) بس،
    والتعديل/الحذف لصاحب الجدول نفسه.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        return _is_authenticated(user) and (hasattr(user, "doctor") or user.is_staff)


class IsAppointmentParticipant(permissions.BasePermission):
    """الحجز يشوفه ويعدله المريض والدكتور بتوعه بس (والأدمن)."""

    def has_permission(self, request, view):
        return _is_authenticated(request.user)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_staff:
            return True
        return user.id in (obj.patient.user_id, obj.doctor.user_id)


class IsMedicalRecordParticipant(permissions.BasePermission):
    """السجل الطبي: القراءة للمريض والدكتور بتوعه، والتعديل للدكتور بس."""

    def has_permission(self, request, view):
        return _is_authenticated(request.user)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_staff:
            return True
        if request.method in SAFE_METHODS:
            return user.id in (obj.patient.user_id, obj.doctor.user_id)
        return user.id == obj.doctor.user_id

IsDoctorReadOnly = IsOwnerDoctorOrReadOnly
IsDoctorListcreateOrReadOnly = IsOwnerDoctorOrReadOnly
IsDoctorRetrieveUpdateOrReadOnly = IsOwnerDoctorOrReadOnly
IsDoctorSheduleOrReadOnly = IsDoctorScheduleOrReadOnly
IsDoctorSheduleListcreateOrReadOnly = IsDoctorScheduleOrReadOnly
IsDoctorSheduleRetrieveUpdateOrReadOnly = IsDoctorScheduleOrReadOnly
IsAppointmentOrReadOnly = IsAppointmentParticipant
IsMedicalRecordOrReadOnly = IsMedicalRecordParticipant