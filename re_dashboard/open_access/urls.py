from django.urls import path
from . import views
from django.urls import include

urlpatterns = [

    # path('open-access/',views.open_access,name='open_access')
    path('', views.open_access, name='open_access'),
    path("calculator/", views.calculator_view, name="calculator"),
]