# your_app/urls.py
from django.urls import path
from . import views as local_views
from customer_dashboard import views as cd_views

urlpatterns = [
    # wind_dashboard appears to be in your local views (unchanged)
    path('wind_dashboard/', local_views.wind_dashboard, name="wind_dashboard"),
       
       
       
           # routes served by customer_dashboard.views
    path('wind_summary1/', cd_views.wind_summary1, name="wind_summary1"),
    path('wind_installation_summary2/', cd_views.wind_installation_summary2, name="wind_installation_summary2"),
    path('wind_generation_kwh/', cd_views.wind_generation_kwh, name="wind_generation_kwh"),
    path('wind_generation_hours/', cd_views.wind_generation_hours, name="wind_generation_hours"),
    path('wind_avg_genration/', cd_views.wind_avg_genration, name="wind_avg_genration"),
    path('wind_Grid_Availability_and_Machine/', cd_views.wind_Grid_Availability_and_Machine, name="wind_Grid_Availability_and_Machine"),
    path('wind_drill_down/', cd_views.wind_drill_down, name="wind_drill_down"),
    path('wind_breakdown_log/', cd_views.wind_breakdown_log, name="wind_breakdown_log"),
    path('wind_Avg_Machine_Availability/', cd_views.wind_Avg_Machine_Availability, name="wind_Avg_Machine_Availability"),
    path('customer_upload/', cd_views.customer_upload, name="customer_upload"),
    path('Modifydata/', cd_views.Modifydata, name="Modifydata"),
    path('wind_wtg_plf/', cd_views.wind_wtg_plf, name="wind_wtg_plf"),
    path('wind_Grid_Availability/', cd_views.wind_Grid_Availability, name="wind_Grid_Availability"),
    path('wind_breakdown_hours/', cd_views.wind_breakdown_hours, name="wind_breakdown_hours"),

    # Open Access calculator (local views)
    path('open_access_calculator/', local_views.open_access_calculator, name="open_access_calculator"),
    path('open-access-pdf/', local_views.open_access_pdf, name="open_access_pdf"),

    # Charge Master CRUD (local views)
    path('charge_master_list', local_views.charge_master_list, name='charge_master_list'),
    path('charge-master/add/', local_views.charge_master_add, name='charge_master_add'),
    path('charge-master/edit/<int:pk>/', local_views.charge_master_edit, name='charge_master_edit'),
    path('charge-master/delete/<int:pk>/', local_views.charge_master_delete, name='charge_master_delete'),

    path('open_access_history', cd_views.open_access_history, name='open_access_history'),
    path('dashboard_breakdown', cd_views.dashboard_breakdown, name='dashboard_breakdown'),
    path("open-access/delete/<int:calc_id>/", cd_views.delete_calculation, name="delete_calculation"),

]
 