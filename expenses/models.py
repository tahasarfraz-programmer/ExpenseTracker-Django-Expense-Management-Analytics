from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Category(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=80)
    icon = models.CharField(max_length=8, default="◈")
    color = models.CharField(max_length=7, default="#18b878", help_text="Hex colour, e.g. #18b878")

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["user", "name"], name="uniq_category_per_user")]

    def __str__(self):
        return self.name


class Transaction(models.Model):
    INCOME, EXPENSE = "income", "expense"
    TYPE_CHOICES = [(INCOME, "Income"), (EXPENSE, "Expense")]
    PAYMENT_CHOICES = [("cash", "Cash"), ("bank", "Bank"), ("card", "Card"), ("wallet", "Wallet")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="transactions")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="transactions")
    title = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=EXPENSE)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default="cash")
    date = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]
        indexes = [models.Index(fields=["user", "-date"]), models.Index(fields=["user", "transaction_type"])]

    def __str__(self):
        return f"{self.title} ({self.amount})"

    @property
    def signed_amount(self):
        return self.amount if self.transaction_type == self.INCOME else -self.amount


class Budget(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="budgets")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="budgets")
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    month = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    year = models.PositiveSmallIntegerField(validators=[MinValueValidator(2000), MaxValueValidator(2100)])

    class Meta:
        ordering = ["-year", "-month", "category__name"]
        constraints = [models.UniqueConstraint(fields=["user", "category", "month", "year"], name="uniq_budget_period")]

    def __str__(self):
        return f"{self.category} {self.month}/{self.year}: {self.amount}"
