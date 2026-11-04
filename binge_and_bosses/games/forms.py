from django import forms

from .models import Catalog


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Catalog
        fields = ["rating", "review"]
        widgets = {
            # The blank choice lets a player remove a rating and keep their review
            "rating": forms.RadioSelect(choices=[("", "Not rated")] + [
                (value, "1 star" if value == 1 else f"{value} stars")
                for value in range(1, 6)
            ]),
            "review": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
        }
