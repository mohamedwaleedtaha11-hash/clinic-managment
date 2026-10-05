from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.mixins import (
    CreateModelMixin, ListModelMixin, RetrieveModelMixin, UpdateModelMixin
)
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from .models import Appointment, Doctor, DoctorSchedule, MedicalRecord, Patient
from .permissions import (
    IsAppointmentParticipant, IsDoctor, IsDoctorScheduleOrReadOnly,
    IsMedicalRecordParticipant, IsOwnerDoctorOrReadOnly, IsPatientOrReadOnly,
)
from .serializers import (
    AdvancedAppointmentSerializer, AppointmentSerializer,
    AppointmentStatemachineSerializer, DoctorListCreateSerializer,
    DoctorRetrieveUpdateSerializer, DoctorScheduleListSerializer,
    DoctorScheduleSerializer, MedicalRecordSerializer, PatientSerializer,
)

BASE_FILTERS = [DjangoFilterBackend, OrderingFilter, SearchFilter]


def scope_by_user(qs, user):
    """الأدمن يشوف الكل، الدكتور حجوزاته/سجلاته، المريض بتاعه هو بس."""
    if user.is_staff:
        return qs
    if hasattr(user, 'doctor'):
        return qs.filter(doctor=user.doctor)
    return qs.filter(patient__user=user)


class DoctorViewSet(ListModelMixin, RetrieveModelMixin, UpdateModelMixin, GenericViewSet):
    """الكل يشوف الدكاترة، والدكتور بس يعدل بياناته."""
    queryset = Doctor.objects.select_related('user')
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerDoctorOrReadOnly]
    filter_backends = BASE_FILTERS
    filterset_fields = ('speciality', 'price_per_hour')
    search_fields = ('user__username', 'speciality')
    ordering_fields = ('speciality', 'price_per_hour')
    ordering = ('id',)

    def get_serializer_class(self):
        if self.action == 'list':
            return DoctorListCreateSerializer
        return DoctorRetrieveUpdateSerializer


class PatientViewSet(ListModelMixin, RetrieveModelMixin, UpdateModelMixin, GenericViewSet):
    """المريض يشوف ويعدل بياناته هو بس."""
    serializer_class = PatientSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = BASE_FILTERS
    search_fields = ('user__username',)
    ordering = ('id',)

    def get_queryset(self):
        qs = Patient.objects.select_related('user')
        return qs if self.request.user.is_staff else qs.filter(user=self.request.user)


class DoctorScheduleViewSet(ModelViewSet):
    """الكل يشوف الجداول، والدكتور بس يضيف/يعدل/يمسح جدوله."""
    queryset = DoctorSchedule.objects.select_related('doctor__user')
    permission_classes = [IsDoctorScheduleOrReadOnly]
    filter_backends = BASE_FILTERS
    filterset_fields = ('doctor', 'day_of_week')
    search_fields = ('day_of_week',)
    ordering_fields = ('day_of_week', 'start_time', 'end_time')
    ordering = ('day_of_week', 'start_time')

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return DoctorScheduleListSerializer
        return DoctorScheduleSerializer


class AppointmentViewSet(CreateModelMixin, ListModelMixin, RetrieveModelMixin, GenericViewSet):
    permission_classes = [IsAppointmentParticipant]
    filter_backends = BASE_FILTERS
    filterset_fields = ('doctor', 'date', 'status', 'is_paid')
    search_fields = ('patient__user__username', 'doctor__user__username')
    ordering_fields = ('date', 'start_time')
    ordering = ('date', 'start_time')

    def get_queryset(self):
        qs = Appointment.objects.select_related('patient__user', 'doctor__user')
        return scope_by_user(qs, self.request.user)

    def get_permissions(self):
        if self.action == 'create':
            return [IsPatientOrReadOnly()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == 'create':
            return AppointmentSerializer
        if self.action == 'change_status':
            return AppointmentStatemachineSerializer
        return AdvancedAppointmentSerializer

    @action(detail=True, methods=['patch'], url_path='status')
    def change_status(self, request, pk=None):
        appointment = self.get_object()
        serializer = self.get_serializer(appointment, data=request.data)
        serializer.is_valid(raise_exception=True)

        is_doctor = hasattr(request.user, 'doctor') and appointment.doctor_id == request.user.doctor.pk
        if not (is_doctor or request.user.is_staff) and serializer.validated_data['status'] != 'canceled':
            raise PermissionDenied('المريض يقدر يلغي بس، القبول والرفض للدكتور.')

        serializer.save()
        return Response(serializer.data)


class MedicalRecordViewSet(CreateModelMixin, ListModelMixin, RetrieveModelMixin,
                           UpdateModelMixin, GenericViewSet):
    """الدكتور يكتب ويعدل، المريض يقرا سجلاته بس. ومفيش حذف."""
    serializer_class = MedicalRecordSerializer
    filter_backends = BASE_FILTERS
    filterset_fields = ('patient', 'appointment')
    search_fields = ('patient__user__username',)
    ordering_fields = ('created_at',)
    ordering = ('-created_at',)

    def get_queryset(self):
        qs = MedicalRecord.objects.select_related('patient__user', 'doctor__user')
        return scope_by_user(qs, self.request.user)

    def get_permissions(self):
        if self.action == 'create':
            return [IsDoctor()]
        if self.action in ('update', 'partial_update'):
            return [IsDoctor(), IsMedicalRecordParticipant()]
        return [IsMedicalRecordParticipant()]