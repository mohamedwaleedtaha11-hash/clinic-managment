import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

User = settings.AUTH_USER_MODEL


class Doctor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor')
    speciality = models.CharField(max_length=100)
    bio = models.TextField(blank=True)
    price_per_hour = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Dr. {self.user.username} ({self.speciality})'


class Patient(models.Model):
    phone_validator = RegexValidator(r'^\+?\d{8,15}$', 'Enter a valid phone number.')

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patient')
    phone_number = models.CharField(max_length=16, validators=[phone_validator])
    date_of_birth = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.date_of_birth and self.date_of_birth > timezone.localdate():
            raise ValidationError({'date_of_birth': 'Date of birth cannot be in the future.'})

    def __str__(self):
        return self.user.username


class DoctorSchedule(models.Model):
    class Day(models.TextChoices):
        MON = 'mon', 'Monday'
        TUE = 'tue', 'Tuesday'
        WED = 'wed', 'Wednesday'
        THU = 'thu', 'Thursday'
        FRI = 'fri', 'Friday'
        SAT = 'sat', 'Saturday'
        SUN = 'sun', 'Sunday'

    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='schedule')
    day_of_week = models.CharField(max_length=3, choices=Day.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['doctor', 'day_of_week', 'start_time'], name='unique_doctor_day_start'
            )
        ]

    def clean(self):
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError('End time must be after start time.')

    def __str__(self):
        return f'{self.doctor} - {self.day_of_week} {self.start_time}-{self.end_time}'


class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACCEPTED = 'accepted', 'Accepted'
        REJECTED = 'rejected', 'Rejected'
        CANCELED = 'canceled', 'Canceled'

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='appointments')
    date = models.DateField()
    start_time = models.TimeField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('date', 'start_time')
        constraints = [
            models.UniqueConstraint(
                fields=['doctor', 'date', 'start_time'],
                condition=Q(status__in=['pending', 'accepted']),
                name='unique_active_doctor_slot',
            )
        ]

    def clean(self):
        if self.date and self.date < timezone.localdate():
            raise ValidationError({'date': 'Cannot book an appointment in the past.'})

        if self.date and self.start_time and self.doctor_id:
            day_codes = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
            in_schedule = DoctorSchedule.objects.filter(
                doctor=self.doctor,
                day_of_week=day_codes[self.date.weekday()],
                start_time__lte=self.start_time,
                end_time__gt=self.start_time,
            ).exists()
            if not in_schedule:
                raise ValidationError("This time is outside the doctor's schedule.")

    def __str__(self):
        return f'{self.patient} with {self.doctor} on {self.date} at {self.start_time}'


class MedicalRecord(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='medical_records')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='medical_records')
    appointment = models.OneToOneField(
        Appointment, on_delete=models.SET_NULL, null=True, blank=True, related_name='medical_record'
    )
    diagnosis = models.TextField()
    prescription = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f'Record for {self.patient} by {self.doctor}'