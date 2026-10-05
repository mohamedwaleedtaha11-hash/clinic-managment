from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.utils import timezone
from rest_framework import serializers

from .models import Appointment, Doctor, DoctorSchedule, MedicalRecord, Patient

class DoctorSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Doctor
        fields = ['id', 'doctor_name', 'speciality', 'bio', 'price_per_hour']
        read_only_fields = ['id']

class DoctorListCreateSerializer(DoctorSerializer):
    """عرض فقط (list)."""
    class Meta(DoctorSerializer.Meta):
        read_only_fields = DoctorSerializer.Meta.fields

class DoctorRetrieveUpdateSerializer(DoctorSerializer):
    """الدكتور يعدل speciality / bio / price بس."""
    class Meta(DoctorSerializer.Meta):
        pass

class PatientSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Patient
        fields = ['id', 'patient_name', 'phone_number', 'date_of_birth']
        read_only_fields = ['id']

    def validate_date_of_birth(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError('تاريخ الميلاد مينفعش يكون في المستقبل.')
        return value

class DoctorScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorSchedule
        fields = ['id', 'day_of_week', 'start_time', 'end_time']
        read_only_fields = ['id']

    def validate(self, attrs):
        doctor = self.context['request'].user.doctor
        day = attrs.get('day_of_week', getattr(self.instance, 'day_of_week', None))
        start = attrs.get('start_time', getattr(self.instance, 'start_time', None))
        end = attrs.get('end_time', getattr(self.instance, 'end_time', None))

        if start >= end:
            raise serializers.ValidationError({'end_time': 'وقت النهاية لازم يكون بعد البداية.'})

        overlapping = DoctorSchedule.objects.filter(
            doctor=doctor, day_of_week=day, start_time__lt=end, end_time__gt=start
        )
        if self.instance:
            overlapping = overlapping.exclude(pk=self.instance.pk)
        if overlapping.exists():
            raise serializers.ValidationError({'day_of_week': 'في فترة متداخلة في نفس اليوم.'})
        return attrs

    def create(self, validated_data):
        validated_data['doctor'] = self.context['request'].user.doctor
        return super().create(validated_data)


class DoctorScheduleListSerializer(serializers.ModelSerializer):
    """عرض فقط (list / retrieve)."""
    class Meta:
        model = DoctorSchedule
        fields = ['id', 'doctor', 'day_of_week', 'start_time', 'end_time']
        read_only_fields = fields

class AppointmentSerializer(serializers.ModelSerializer):
    """الحجز: المريض يبعت doctor + date + start_time بس."""
    class Meta:
        model = Appointment
        fields = ['id', 'doctor', 'date', 'start_time', 'status', 'is_paid']
        read_only_fields = ['id', 'status', 'is_paid']

    def validate(self, attrs):
        patient = self.context['request'].user.patient
        try:
            Appointment(patient=patient, **attrs).clean()
        except DjangoValidationError as e:
            raise serializers.ValidationError(
                e.message_dict if hasattr(e, 'error_dict') else e.messages
            )

        taken = Appointment.objects.filter(
            doctor=attrs['doctor'], date=attrs['date'], start_time=attrs['start_time'],
            status__in=[Appointment.Status.PENDING, Appointment.Status.ACCEPTED],
        ).exists()
        if taken:
            raise serializers.ValidationError({'start_time': 'الميعاد ده محجوز بالفعل.'})
        return attrs

    def create(self, validated_data):
        validated_data['patient'] = self.context['request'].user.patient
        try:
            return super().create(validated_data)
        except IntegrityError: 
            raise serializers.ValidationError({'start_time': 'الميعاد ده محجوز بالفعل.'})


class AdvancedAppointmentSerializer(serializers.ModelSerializer):
    """عرض تفصيلي بأسماء المريض والدكتور (قراءة فقط)."""
    patient_name = serializers.CharField(source='patient.user.username', read_only=True)
    doctor_name = serializers.CharField(source='doctor.user.username', read_only=True)

    class Meta:
        model = Appointment
        fields = ['id', 'patient', 'doctor', 'date', 'start_time', 'status',
                  'is_paid', 'patient_name', 'doctor_name']
        read_only_fields = fields


class AppointmentStatemachineSerializer(serializers.ModelSerializer):
    """تغيير الحالة فقط، مع التحكم في الانتقالات المسموحة."""
    ALLOWED = {
        'pending': {'accepted', 'rejected', 'canceled'},
        'accepted': {'canceled'},
        'rejected': set(),
        'canceled': set(),
    }

    class Meta:
        model = Appointment
        fields = ['id', 'status']
        read_only_fields = ['id']
        extra_kwargs = {'status': {'required': True}}

    def validate_status(self, new):
        if new not in self.ALLOWED[self.instance.status]:
            raise serializers.ValidationError(
                f'مينفعش تنقل من {self.instance.status} إلى {new}.'
            )
        return new

class MedicalRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalRecord
        fields = ['id', 'patient', 'doctor', 'appointment', 'diagnosis', 'prescription', 'created_at']
        read_only_fields = ['id', 'doctor', 'created_at']

    def validate(self, attrs):
        doctor = self.context['request'].user.doctor
        appt = attrs.get('appointment')
        patient = attrs.get('patient')
        if appt and (appt.doctor_id != doctor.pk or (patient and appt.patient_id != patient.pk)):
            raise serializers.ValidationError({'appointment': 'الحجز ده مش بتاعك مع المريض ده.'})
        return attrs

    def create(self, validated_data):
        validated_data['doctor'] = self.context['request'].user.doctor
        return super().create(validated_data)

    def update(self, instance, validated_data):

        validated_data.pop('patient', None)
        validated_data.pop('appointment', None)
        return super().update(instance, validated_data)