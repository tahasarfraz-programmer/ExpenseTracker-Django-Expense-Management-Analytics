import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from . import services
from .models import Budget, Category, Transaction

TODAY = datetime.date.today()


class Base(TestCase):
    def setUp(self):
        self.u = User.objects.create_user("alice", password="pw-12345-x")
        self.other = User.objects.create_user("bob", password="pw-12345-x")
        self.food = Category.objects.create(user=self.u, name="Food")
        self.client.login(username="alice", password="pw-12345-x")

    def tx(self, amount, kind="expense", user=None, cat=None, date=None, title="t"):
        return Transaction.objects.create(user=user or self.u, category=cat, title=title, amount=Decimal(amount),
                                          transaction_type=kind, date=date or TODAY)


class AuthTests(Base):
    def test_anonymous_redirected(self):
        self.client.logout()
        for name in ["dashboard", "transactions", "analytics", "budgets", "categories"]:
            r = self.client.get(reverse(name))
            self.assertEqual(r.status_code, 302)
            self.assertIn("/accounts/login/", r["Location"])

    def test_register_creates_starter_categories(self):
        self.client.logout()
        r = self.client.post(reverse("register"), {"username": "newu", "password1": "Str0ng-pass-99", "password2": "Str0ng-pass-99"})
        self.assertRedirects(r, reverse("dashboard"))
        self.assertTrue(Category.objects.filter(user__username="newu").count() >= 5)


class IsolationTests(Base):
    def test_cannot_touch_other_users_data(self):
        t = self.tx(10, user=self.other)
        self.assertEqual(self.client.get(reverse("transaction_edit", args=[t.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("transaction_delete", args=[t.pk])).status_code, 404)
        self.assertTrue(Transaction.objects.filter(pk=t.pk).exists())

    def test_totals_only_include_own_data(self):
        self.tx(100, "income"); self.tx(500, "income", user=self.other)
        self.assertEqual(services.totals(Transaction.objects.filter(user=self.u))["income"], Decimal(100))

    def test_cannot_use_other_users_category(self):
        foreign = Category.objects.create(user=self.other, name="Secret")
        r = self.client.post(reverse("transaction_add"), {"title": "x", "amount": "5", "transaction_type": "expense",
                             "category": foreign.pk, "payment_method": "cash", "date": TODAY})
        self.assertEqual(r.status_code, 200)  # form re-rendered with error
        self.assertFalse(Transaction.objects.filter(title="x").exists())


class CrudTests(Base):
    def test_create_edit_delete(self):
        r = self.client.post(reverse("transaction_add"), {"title": "Lunch", "amount": "12.50", "transaction_type": "expense",
                             "category": self.food.pk, "payment_method": "card", "date": TODAY})
        self.assertRedirects(r, reverse("transactions"))
        t = Transaction.objects.get(title="Lunch")
        self.assertEqual(t.user, self.u)
        self.client.post(reverse("transaction_edit", args=[t.pk]), {"title": "Dinner", "amount": "20", "transaction_type": "expense",
                         "payment_method": "cash", "date": TODAY})
        t.refresh_from_db(); self.assertEqual(t.title, "Dinner")
        self.client.post(reverse("transaction_delete", args=[t.pk]))
        self.assertFalse(Transaction.objects.exists())

    def test_rejects_non_positive_amount(self):
        r = self.client.post(reverse("transaction_add"), {"title": "x", "amount": "-5", "transaction_type": "expense",
                             "payment_method": "cash", "date": TODAY})
        self.assertEqual(r.status_code, 200); self.assertFalse(Transaction.objects.exists())

    def test_delete_requires_post(self):
        t = self.tx(1)
        self.assertEqual(self.client.get(reverse("transaction_delete", args=[t.pk])).status_code, 405)

    def test_duplicate_category_rejected(self):
        r = self.client.post(reverse("category_add"), {"name": "food", "icon": "x", "color": "#ffffff"})
        self.assertEqual(r.status_code, 200); self.assertEqual(Category.objects.filter(user=self.u).count(), 1)


class ServiceTests(Base):
    def test_monthly_series_zero_fills_and_orders(self):
        self.tx(100, "income"); self.tx(40)
        s = services.monthly_series(self.u, 6)
        self.assertEqual(len(s), 6)
        self.assertEqual((s[-1]["income"], s[-1]["expense"]), (100.0, 40.0))
        self.assertTrue(all(m["income"] == 0 for m in s[:-1]))

    def test_month_helpers_across_year_boundary(self):
        self.assertEqual(services.month_bounds(datetime.date(2025, 12, 15)), (datetime.date(2025, 12, 1), datetime.date(2026, 1, 1)))
        self.assertEqual(services.previous_month(datetime.date(2026, 1, 1)), datetime.date(2025, 12, 1))

    def test_category_breakdown_shares(self):
        self.tx(75, cat=self.food); self.tx(25)
        b = services.category_breakdown(Transaction.objects.filter(user=self.u))
        self.assertEqual([x["name"] for x in b], ["Food", "Uncategorized"])
        self.assertAlmostEqual(b[0]["share"], 75.0)

    def test_budget_progress_states(self):
        Budget.objects.create(user=self.u, category=self.food, amount=100, month=TODAY.month, year=TODAY.year)
        self.tx(85, cat=self.food)
        p = services.budget_progress(self.u, TODAY.month, TODAY.year)
        self.assertEqual(p[0]["state"], "warn")
        self.tx(30, cat=self.food)
        self.assertEqual(services.budget_progress(self.u, TODAY.month, TODAY.year)[0]["state"], "over")

    def test_pct_change_handles_zero(self):
        self.assertIsNone(services.pct_change(Decimal(5), Decimal(0)))


class ViewTests(Base):
    def test_pages_render_with_and_without_data(self):
        for name in ["dashboard", "transactions", "analytics", "budgets", "categories"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        self.tx(50, "income", cat=self.food); self.tx(20, cat=self.food)
        for name in ["dashboard", "transactions", "analytics"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

    def test_filters(self):
        self.tx(10, title="Coffee"); self.tx(99, "income", title="Pay")
        r = self.client.get(reverse("transactions"), {"type": "income"})
        self.assertEqual([t.title for t in r.context["page"]], ["Pay"])
        r = self.client.get(reverse("transactions"), {"q": "coff"})
        self.assertEqual([t.title for t in r.context["page"]], ["Coffee"])
        r = self.client.get(reverse("transactions"), {"from": "garbage", "category": "abc"})
        self.assertEqual(r.status_code, 200)

    def test_bad_query_params_do_not_crash(self):
        self.assertEqual(self.client.get(reverse("budgets"), {"month": "13", "year": "x"}).status_code, 200)
        self.assertEqual(self.client.get(reverse("analytics"), {"months": "zzz"}).status_code, 200)

    def test_csv_export_neutralises_formulas(self):
        self.tx(5, title="=HYPERLINK(\"evil\")")
        r = self.client.get(reverse("export_csv"))
        body = r.content.decode()
        self.assertIn("'=HYPERLINK", body); self.assertEqual(r["Content-Type"], "text/csv")

    def test_duplicate_budget_rejected(self):
        data = {"category": self.food.pk, "amount": "50", "month": TODAY.month, "year": TODAY.year}
        self.client.post(reverse("budget_add"), data)
        r = self.client.post(reverse("budget_add"), data)
        self.assertEqual(r.status_code, 200); self.assertEqual(Budget.objects.count(), 1)
