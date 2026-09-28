"""Aggregation helpers. All heavy lifting is done in the database, not in Python."""
import datetime
from decimal import Decimal

from django.db.models import Count, DecimalField, Q, Sum
from django.db.models.functions import Coalesce, TruncMonth

from .models import Budget, Transaction

ZERO = Decimal("0")


def _sum(kind):
    return Coalesce(Sum("amount", filter=Q(transaction_type=kind)), ZERO, output_field=DecimalField())


def totals(qs):
    agg = qs.aggregate(income=_sum(Transaction.INCOME), expense=_sum(Transaction.EXPENSE), count=Count("id"))
    agg["balance"] = agg["income"] - agg["expense"]
    agg["savings_rate"] = (agg["balance"] / agg["income"] * 100) if agg["income"] else None
    return agg


def month_bounds(day=None):
    day = day or datetime.date.today()
    start = day.replace(day=1)
    end = (start.replace(year=start.year + 1, month=1) if start.month == 12 else start.replace(month=start.month + 1))
    return start, end


def previous_month(start):
    return (start.replace(year=start.year - 1, month=12) if start.month == 1 else start.replace(month=start.month - 1))


def pct_change(current, previous):
    if not previous:
        return None
    return float((current - previous) / previous * 100)


def monthly_series(user, months=12, today=None):
    """Income/expense per month for the trailing N months (zero-filled)."""
    today = today or datetime.date.today()
    start = today.replace(day=1)
    for _ in range(months - 1):
        start = previous_month(start)
    rows = (Transaction.objects.filter(user=user, date__gte=start)
            .annotate(m=TruncMonth("date")).values("m")
            .annotate(income=_sum(Transaction.INCOME), expense=_sum(Transaction.EXPENSE)).order_by("m"))
    by_month = {r["m"]: r for r in rows}
    out, cur = [], start
    for _ in range(months):
        r = by_month.get(cur, {})
        out.append({"label": cur.strftime("%b %y"), "income": float(r.get("income", 0)), "expense": float(r.get("expense", 0))})
        cur = month_bounds(cur)[1]
    return out


def category_breakdown(qs, kind=Transaction.EXPENSE):
    rows = (qs.filter(transaction_type=kind).values("category__name", "category__icon", "category__color")
            .annotate(total=Sum("amount")).order_by("-total"))
    grand = sum((r["total"] for r in rows), ZERO)
    return [{
        "name": r["category__name"] or "Uncategorized", "icon": r["category__icon"] or "◇",
        "color": r["category__color"] or "#a7b0bc", "total": r["total"],
        "share": float(r["total"] / grand * 100) if grand else 0,
    } for r in rows]


def budget_progress(user, month, year):
    budgets = list(Budget.objects.filter(user=user, month=month, year=year).select_related("category"))
    spent = dict(Transaction.objects.filter(
        user=user, transaction_type=Transaction.EXPENSE, date__year=year, date__month=month,
        category__in=[b.category_id for b in budgets]).values_list("category").annotate(s=Sum("amount")))
    out = []
    for b in budgets:
        s = spent.get(b.category_id, ZERO)
        pct = float(s / b.amount * 100)
        out.append({"budget": b, "spent": s, "remaining": b.amount - s, "pct": pct,
                    "state": "over" if pct > 100 else "warn" if pct >= 80 else "ok"})
    return sorted(out, key=lambda x: -x["pct"])
