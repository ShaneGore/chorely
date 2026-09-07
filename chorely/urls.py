"""
URL configuration for chorely project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
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
from django.contrib import admin
from django.urls import path

from chores import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.account_redirect, name='account_redirect'),
    path('accounts/signup/', views.signup, name='signup'),
    path('accounts/signin/', views.signin, name='signin'),
    path('accounts/signout/', views.signout, name='signout'),
    path('onboarding/', views.onboarding, name='onboarding'),
    path('household/create/', views.create_household, name='create_household'),
    path('household/join/', views.join_household, name='join_household'),
    path('household/', views.household_detail, name='household_detail'),
    path('chores/', views.active_chores, name='active_chores'),
    path('chores/create/', views.create_chore, name='create_chore'),
    path('chores/<int:chore_id>/edit/', views.edit_chore, name='edit_chore'),
    path('chores/<int:chore_id>/delete/', views.delete_chore, name='delete_chore'),
    path('chores/<int:chore_id>/claim/', views.claim_chore, name='claim_chore'),
    path('chores/<int:chore_id>/complete/', views.complete_chore, name='complete_chore'),
    path('chores/completed/', views.completed_chores, name='completed_chores'),
]
