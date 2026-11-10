from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import LoginForm

urlpatterns = [
    # Главная
    path("", views.home, name="home"),

    # Авторизация
    path("signup/", views.signup, name="signup"),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="main/login.html",
            authentication_form=LoginForm,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # Распознавание
    path("recognition/", views.recognition, name="recognition"),
    path("recognition/<int:pk>/", views.recognition_detail, name="recognition_detail"),
    path("recognition/<int:pk>/excel/", views.download_result, name="download_result"),
    path("recognition/<int:pk>/source/", views.download_source, name="download_source"),
    path("recognition/<int:pk>/delete/", views.recognition_delete, name="recognition_delete"),

    # История (логирование)
    path("history/", views.history, name="history"),

    # Пользователь
    path("profile/", views.profile, name="profile"),
]
