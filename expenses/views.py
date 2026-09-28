import csv
import datetime

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import services
from .forms import BudgetForm, CategoryForm, TransactionForm
from .models import Budget, Category, Transaction


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        for name, icon, color in [("Food", "🍽", "#4d8df7"), ("Transport", "🚌", "#ef6672"), ("Housing", "🏠", "#18b878"),
                                  ("Shopping", "🛍", "#f5a442"), ("Bills", "💡", "#8c6ff0"), ("Salary", "💼", "#0b9d63")]:
            Category.objects.create(user=user, name=name, icon=icon, color=color)
        login(request, user)
        messages.success(request, "Welcome! Your account is ready with a few starter categories.")
        return redirect("dashboard")
    return render(request, "registration/register.html", {"form": form})


@login_required
def dashboard(request):
    user = request.user
    start, end = services.month_bounds()
    prev_start = services.previous_month(start)
    all_tx = Transaction.objects.filter(user=user)
    this_m = all_tx.filter(date__gte=start, date__lt=end)
    last_m = all_tx.filter(date__gte=prev_start, date__lt=start)
    cur, prev, overall = services.totals(this_m), services.totals(last_m), services.totals(all_tx)
    breakdown = services.category_breakdown(this_m)
    series = services.monthly_series(user, 6)
    return render(request, "dashboard.html", {
        "cur": cur, "overall": overall, "month_label": start.strftime("%B %Y"),
        "income_delta": services.pct_change(cur["income"], prev["income"]),
        "expense_delta": services.pct_change(cur["expense"], prev["expense"]),
        "recent": all_tx.select_related("category")[:8],
        "breakdown": breakdown[:6], "budgets": services.budget_progress(user, start.month, start.year)[:5],
        "chart": {"months": series, "categories": [{"name": b["name"], "value": float(b["total"]), "color": b["color"]} for b in breakdown]},
    })


def _filtered(request):
    qs = Transaction.objects.filter(user=request.user).select_related("category")
    q, kind, cat = request.GET.get("q", "").strip(), request.GET.get("type", ""), request.GET.get("category", "")
    d_from, d_to = request.GET.get("from", ""), request.GET.get("to", "")
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(notes__icontains=q) | Q(category__name__icontains=q))
    if kind in (Transaction.INCOME, Transaction.EXPENSE):
        qs = qs.filter(transaction_type=kind)
    if cat.isdigit():
        qs = qs.filter(category_id=int(cat))
    for key, lookup in ((d_from, "date__gte"), (d_to, "date__lte")):
        try:
            qs = qs.filter(**{lookup: datetime.date.fromisoformat(key)})
        except ValueError:
            pass
    return qs


@login_required
def transactions(request):
    qs = _filtered(request)
    page = Paginator(qs, 15).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "transactions.html", {
        "page": page, "totals": services.totals(qs), "qs_string": params.urlencode(),
        "categories": Category.objects.filter(user=request.user), "f": request.GET,
    })


@login_required
def export_csv(request):
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = 'attachment; filename="transactions.csv"'
    w = csv.writer(resp)
    w.writerow(["Date", "Title", "Type", "Category", "Payment", "Amount", "Notes"])

    def safe(v):  # neutralise spreadsheet formula injection
        return "'" + v if v and v[0] in "=+-@\t\r" else v
    for t in _filtered(request):
        w.writerow([t.date, safe(t.title), t.transaction_type, t.category or "", t.payment_method, t.amount, safe(t.notes)])
    return resp


@login_required
def transaction_form(request, pk=None):
    obj = get_object_or_404(Transaction, pk=pk, user=request.user) if pk else None
    form = TransactionForm(request.POST or None, instance=obj, user=request.user)
    if request.method == "POST" and form.is_valid():
        t = form.save(commit=False)
        t.user = request.user
        t.save()
        messages.success(request, "Transaction saved.")
        return redirect("transactions")
    return render(request, "form.html", {"form": form, "title": "Edit transaction" if obj else "Add transaction",
                                         "back": "transactions", "obj": obj, "delete_url": "transaction_delete"})


@login_required
@require_POST
def transaction_delete(request, pk):
    get_object_or_404(Transaction, pk=pk, user=request.user).delete()
    messages.success(request, "Transaction deleted.")
    return redirect("transactions")


@login_required
def analytics(request):
    user = request.user
    try:
        months = int(request.GET.get("months", 12))
    except ValueError:
        months = 12
    months = months if months in (3, 6, 12, 24) else 12
    series = services.monthly_series(user, months)
    qs = Transaction.objects.filter(user=user)
    start = qs.filter(date__gte=datetime.date.today().replace(day=1)).first()
    breakdown = services.category_breakdown(qs)
    exp = [m["expense"] for m in series]
    inc = [m["income"] for m in series]
    insights = []
    if breakdown:
        top = breakdown[0]
        insights.append(f"{top['name']} is your biggest expense at {top['share']:.0f}% of all spending.")
    active = [e for e in exp if e]
    if len(active) >= 2:
        insights.append(f"You spend about Rs. {sum(active) / len(active):,.0f} in an average active month.")
    if sum(inc) and sum(exp):
        rate = (sum(inc) - sum(exp)) / sum(inc) * 100
        insights.append(f"Over this period you saved {rate:.0f}% of your income." if rate >= 0
                        else f"You spent {abs(rate):.0f}% more than you earned over this period.")
    if not insights:
        insights.append("Add a few transactions and personalised insights will appear here.")
    return render(request, "analytics.html", {
        "months": months, "insights": insights, "breakdown": breakdown,
        "chart": {"months": series, "categories": [{"name": b["name"], "value": float(b["total"]), "color": b["color"]} for b in breakdown]},
    })


@login_required
def budgets(request):
    today = datetime.date.today()
    try:
        month, year = int(request.GET.get("month", today.month)), int(request.GET.get("year", today.year))
        datetime.date(year, month, 1)
    except (ValueError, OverflowError):
        month, year = today.month, today.year
    return render(request, "budgets.html", {
        "progress": services.budget_progress(request.user, month, year),
        "period": datetime.date(year, month, 1), "month": month, "year": year,
    })


@login_required
def budget_form(request, pk=None):
    obj = get_object_or_404(Budget, pk=pk, user=request.user) if pk else None
    form = BudgetForm(request.POST or None, instance=obj, user=request.user)
    if request.method == "POST" and form.is_valid():
        b = form.save(commit=False)
        b.user = request.user
        b.save()
        messages.success(request, "Budget saved.")
        return redirect(f"/budgets/?month={b.month}&year={b.year}")
    if not Category.objects.filter(user=request.user).exists():
        messages.info(request, "Create a category first, then set a budget for it.")
        return redirect("category_add")
    return render(request, "form.html", {"form": form, "title": "Edit budget" if obj else "Set budget",
                                         "back": "budgets", "obj": obj, "delete_url": "budget_delete"})


@login_required
@require_POST
def budget_delete(request, pk):
    get_object_or_404(Budget, pk=pk, user=request.user).delete()
    messages.success(request, "Budget removed.")
    return redirect("budgets")


@login_required
def categories(request):
    from django.db.models import Count, Sum
    cats = Category.objects.filter(user=request.user).annotate(n=Count("transactions"), total=Sum("transactions__amount"))
    return render(request, "categories.html", {"categories": cats})


@login_required
def category_form(request, pk=None):
    obj = get_object_or_404(Category, pk=pk, user=request.user) if pk else None
    form = CategoryForm(request.POST or None, instance=obj, user=request.user)
    if request.method == "POST" and form.is_valid():
        c = form.save(commit=False)
        c.user = request.user
        c.save()
        messages.success(request, "Category saved.")
        return redirect("categories")
    return render(request, "form.html", {"form": form, "title": "Edit category" if obj else "New category",
                                         "back": "categories", "obj": obj, "delete_url": "category_delete"})


@login_required
@require_POST
def category_delete(request, pk):
    get_object_or_404(Category, pk=pk, user=request.user).delete()
    messages.success(request, "Category deleted. Its transactions are now uncategorized.")
    return redirect("categories")
