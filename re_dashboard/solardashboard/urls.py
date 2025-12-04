from django.urls import path
from solardashboard import views

urlpatterns = [
    path('solar/', views.solar_dashboard, name="solar_dashboard"),  # Solar
    path('solar_summary1', views.solar_summary1, name="solar_summary1"),  # Solar
    path('solar_installation_summary2/', views.solar_installation_summary2, name="solar_installation_summary2"),  # Wind Installation Summary
    path('solar_dashboard_genration', views.solar_dashboard_genration, name="solar_dashboard_genration"),  # Wind Installation Summary
    path("api/solar-data/", views.api_solar_data, name="api_solar_data"),

    # ... your other urls
    path('solar_plf_dashboard/', views.solar_plf_dashboard, name='solar_plf_dashboard'),
    path('api_solar_plf/', views.api_solar_plf, name='api_solar_plf'),
    path("generation_operating/", views.generation_operating, name="generation_operating"),
    path("api/generation_operating/", views.api_generation_operating, name="api_generation_operating"),
]
