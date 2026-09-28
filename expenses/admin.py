from django.contrib import admin

from .models import Budget, Category, Transaction


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "icon", "color", "user")
    list_filter = ("user",)
    search_fields = ("name",)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("title", "amount", "transaction_type", "category", "payment_method", "date", "user")
    list_filter = ("transaction_type", "payment_method", "category", "date")
    search_fields = ("title", "notes")
    date_hierarchy = "date"


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ("category", "amount", "month", "year", "user")
    list_filter = ("year", "month")
