from django.urls import path
from .views import *
from customer_dashboard import views


urlpatterns = [
    path('wind_dashboard', wind_dashboard, name="wind_dashboard"),  # Wind
    path('wind_summary1', views.wind_summary1, name="wind_summary1"),  # Solar
    path('wind_installation_summary2/', views.wind_installation_summary2, name="wind_installation_summary2"),  # Wind Installation Summary
    # 👉 New dynamic chart pages
    path('wind_generation_kwh/', views.wind_generation_kwh, name="wind_generation_kwh"),
    path('wind_generation_hours', views.wind_generation_hours, name="wind_generation_hours"),

]
