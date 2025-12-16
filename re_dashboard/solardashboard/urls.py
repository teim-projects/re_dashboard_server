from django.urls import path
from . import views

urlpatterns = [
    path('solar/', views.solar_dashboard, name="solar_dashboard"),
    path('solar_summary1', views.solar_summary1, name="solar_summary1"),
    path('solar_installation_summary2/', views.solar_installation_summary2, name="solar_installation_summary2"),

    path('solar_dashboard_genration', views.solar_dashboard_genration, name="solar_dashboard_genration"),
    path("api/solar-data/", views.api_solar_data, name="api_solar_data"),

    path('solar_plf_dashboard/', views.solar_plf_dashboard, name='solar_plf_dashboard'),
    path('api_solar_plf/', views.api_solar_plf, name='api_solar_plf'),

    path("generation_operating/", views.generation_operating, name="generation_operating"),
    path("api/generation_operating/", views.api_generation_operating, name="api_generation_operating"),

    path("solar_weather_breakdown/", views.solar_weather_breakdown_dashboard, name="solar_weather_breakdown_dashboard"),
    path("api/weather_breakdown/", views.api_weather_breakdown, name="api_weather_breakdown"),

    path("brekdown_genration_whether_dashboard/", views.brekdown_genration_whether_dashboard,
         name="brekdown_genration_whether_dashboard"),

    path("api/brekdown_genration_whether_dashboard/",
         views.api_brekdown_genration_whether_dashboard,
         name="api_brekdown_genration_whether_dashboard"),

    path("solar_generation_by_day/", views.solar_generation_by_day, name="solar_generation_by_day"),

    path('solar/api/generation_by_day/', views.api_generation_by_day, name='api_generation_by_day'
    ),

    path('trend-analysis/', views.trend_analysis, name='trend_analysis'),
    path('api/trend-analysis/', views.api_trend_analysis, name='api_trend_analysis'),



    # NEW DASHBOARD
path("summary_dashboard/", views.summary_dashboard, name="summary_dashboard"),

# NEW API
path("api/solar-summary-dashboard/", views.api_solar_summary_dashboard, name="api_solar_summary_dashboard"),



    # ... your other paths ...
    path("generation-report/", views.generation_report, name="generation_report"),
    path("api/solar/generation-report/", views.api_generation_report, name="api_generation_report"),


    path(
    "overall-breakdown-analysis/",
    views.overall_breakdown_analysis,
    name="overall_breakdown_analysis"
),

path(
    "api/solar/overall-breakdown-analysis/",
    views.api_overall_breakdown_analysis,
    name="api_overall_breakdown_analysis"
),

]
