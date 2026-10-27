from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from inventory import views

urlpatterns = [
    path("", views.catalog, name="catalog"),
    path("accounts/login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("equipment/<int:pk>/reserve/", views.reserve, name="reserve"),
    path("reservations/", views.my_reservations, name="my_reservations"),
    path("review/", views.review_queue, name="review_queue"),
    path("review/<int:pk>/", views.decide, name="decide"),
    path("admin/", admin.site.urls),
]
