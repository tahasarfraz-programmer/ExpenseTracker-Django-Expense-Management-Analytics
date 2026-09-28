import datetime
import random
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from expenses.models import Budget, Category, Transaction


class Command(BaseCommand):
    help = "Create a demo user (demo / demo12345) with 6 months of sample data."

    def handle(self, *args, **opts):
        rng = random.Random(42)
        user, created = User.objects.get_or_create(username="demo")
        if not created:
            self.stdout.write("Demo user already exists; nothing to do.")
            return
        user.set_password("demo12345")
        user.save()
        cats = {n: Category.objects.create(user=user, name=n, icon=i, color=c) for n, i, c in [
            ("Food", "🍽", "#4d8df7"), ("Transport", "🚌", "#ef6672"), ("Housing", "🏠", "#18b878"),
            ("Shopping", "🛍", "#f5a442"), ("Bills", "💡", "#8c6ff0"), ("Salary", "💼", "#0b9d63")]}
        today = datetime.date.today()
        for back in range(6):
            first = (today.replace(day=1) - datetime.timedelta(days=30 * back)).replace(day=1)
            Transaction.objects.create(user=user, category=cats["Salary"], title="Monthly salary", amount=Decimal(85000),
                                       transaction_type="income", payment_method="bank", date=first)
            Transaction.objects.create(user=user, category=cats["Housing"], title="Rent", amount=Decimal(25000),
                                       payment_method="bank", date=first + datetime.timedelta(days=2))
            for title, cat, lo, hi in [("Groceries", "Food", 1500, 5000), ("Restaurant", "Food", 800, 3500),
                                       ("Fuel", "Transport", 2000, 4500), ("Electricity bill", "Bills", 3500, 9000),
                                       ("Clothes", "Shopping", 2000, 9000), ("Internet", "Bills", 3000, 3500)]:
                d = min(first + datetime.timedelta(days=rng.randint(3, 27)), today)
                Transaction.objects.create(user=user, category=cats[cat], title=title, amount=Decimal(rng.randint(lo, hi)),
                                           payment_method=rng.choice(["cash", "card", "wallet"]), date=d)
        for n, amt in [("Food", 12000), ("Transport", 6000), ("Shopping", 7000), ("Bills", 12000)]:
            Budget.objects.create(user=user, category=cats[n], amount=amt, month=today.month, year=today.year)
        self.stdout.write(self.style.SUCCESS("Demo data created. Login: demo / demo12345"))
