from django import forms

from apps.accounts.models import UserProfile


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["full_name", "position", "department", "team", "workload_index"]
