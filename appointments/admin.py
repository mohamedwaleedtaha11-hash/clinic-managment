from django.contrib import admin

from .models import Appointment, Doctor, DoctorSchedule, MedicalRecord, Patient

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('user', 'speciality', 'price_per_hour', 'created_at')
    list_select_related = ('user',)
    search_fields = ('user__username', 'user__email', 'speciality')
    list_filter = ('speciality',)
@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'date_of_birth')
    list_select_related = ('user',)
    search_fields = ('user__username', 'user__email', 'phone_number')
    list_filter = ('date_of_birth',)


@admin.register(DoctorSchedule)
class DoctorScheduleAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'day_of_week', 'start_time', 'end_time')
    list_select_related = ('doctor__user',)
    search_fields = ('doctor__user__username',)
    list_filter = ('day_of_week', 'doctor')
    ordering = ('doctor', 'day_of_week', 'start_time')


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'date', 'start_time', 'status', 'is_paid')
    list_select_related = ('patient__user', 'doctor__user')
    search_fields = (
        'patient__user__username', 'patient__user__email',
        'doctor__user__username', 'doctor__user__email',
    )
    list_filter = ('status', 'is_paid', 'date')
    date_hierarchy = 'date'
    ordering = ('-date', 'start_time')


@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'created_at')
    list_select_related = ('patient__user', 'doctor__user')
    search_fields = ('patient__user__username', 'doctor__user__username')
    list_filter = ('doctor', 'created_at')
    date_hierarchy = 'created_at'
    readonly_fields = ('patient', 'doctor', 'appointment', 'diagnosis',
                       'prescription', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False