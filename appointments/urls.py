from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('doctors', views.DoctorViewSet, basename='doctor')
router.register('patients', views.PatientViewSet, basename='patient')
router.register('schedules', views.DoctorScheduleViewSet, basename='schedule')
router.register('appointments', views.AppointmentViewSet, basename='appointment')
router.register('medical-records', views.MedicalRecordViewSet, basename='medical-record')

urlpatterns = router.urls