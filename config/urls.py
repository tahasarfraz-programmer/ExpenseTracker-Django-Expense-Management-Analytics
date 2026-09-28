from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("expenses.auth_urls")),
    path("", include("expenses.urls")),
]
