from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("transactions/", views.transactions, name="transactions"),
    path("transactions/export.csv", views.export_csv, name="export_csv"),
    path("transactions/add/", views.transaction_form, name="transaction_add"),
    path("transactions/<int:pk>/edit/", views.transaction_form, name="transaction_edit"),
    path("transactions/<int:pk>/delete/", views.transaction_delete, name="transaction_delete"),
    path("analytics/", views.analytics, name="analytics"),
    path("budgets/", views.budgets, name="budgets"),
    path("budgets/add/", views.budget_form, name="budget_add"),
    path("budgets/<int:pk>/edit/", views.budget_form, name="budget_edit"),
    path("budgets/<int:pk>/delete/", views.budget_delete, name="budget_delete"),
    path("categories/", views.categories, name="categories"),
    path("categories/add/", views.category_form, name="category_add"),
    path("categories/<int:pk>/edit/", views.category_form, name="category_edit"),
    path("categories/<int:pk>/delete/", views.category_delete, name="category_delete"),
]
