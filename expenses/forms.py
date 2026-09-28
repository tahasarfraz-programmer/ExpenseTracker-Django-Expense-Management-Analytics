import datetime

from django import forms

from .models import Budget, Category, Transaction


class UserScopedForm(forms.ModelForm):
    """Restricts category choices to the current user's categories."""

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if "category" in self.fields:
            self.fields["category"].queryset = Category.objects.filter(user=user)


class TransactionForm(UserScopedForm):
    class Meta:
        model = Transaction
        fields = ["title", "amount", "transaction_type", "category", "payment_method", "date", "notes"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notes": forms.Textarea(attrs={"rows": 3}),
            "amount": forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["date"].initial = datetime.date.today
        self.fields["category"].empty_label = "Uncategorized"


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "icon", "color"]
        widgets = {"color": forms.TextInput(attrs={"type": "color"})}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        qs = Category.objects.filter(user=self.user, name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("You already have a category with this name.")
        return name


class BudgetForm(UserScopedForm):
    class Meta:
        model = Budget
        fields = ["category", "amount", "month", "year"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        today = datetime.date.today()
        self.fields["month"] = forms.TypedChoiceField(
            coerce=int, choices=[(i, datetime.date(2000, i, 1).strftime("%B")) for i in range(1, 13)],
            initial=today.month)
        self.fields["year"].initial = today.year
        self.fields["category"].empty_label = None

    def clean(self):
        data = super().clean()
        if all(k in data for k in ("category", "month", "year")):
            qs = Budget.objects.filter(user=self.user, category=data["category"], month=data["month"], year=data["year"])
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("A budget for this category and month already exists.")
        return data
