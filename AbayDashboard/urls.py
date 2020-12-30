"""AbayTracker URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from . import views
from .dash_apps import dash_abay
#from .dash_apps import dash_uber
#from .dash_apps import dash_tutorial

app_name = "AbayDashboard"

urlpatterns = [
    path('', views.dashboard, name="dashboard"),  # This runs the working dashboard without django_dash
    path('dash_django', views.dash_django, name="dash_django"),  # This runs the dashboard with dash
    path('dash', views.dash, name="plotly"),
    path('dash_tutorial', views.dash_tutorial, name="plotly_tutorial"),
    path("login", views.login_request, name="login"),
]
