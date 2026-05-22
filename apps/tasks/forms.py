from django import forms

from apps.tasks.models import Task, TaskComment


FORM_CONTROL = "form-control"


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [
            "title",
            "description",
            "department",
            "team",
            "responsible",
            "planning_period",
            "deadline",
            "priority",
            "tags",
            "estimated_hours",
            "actual_hours",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "deadline": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxSelectMultiple):
                continue
            classes = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{classes} {FORM_CONTROL}".strip()
        self.fields["estimated_hours"].required = False
        self.fields["actual_hours"].required = False

    def clean_responsible(self):
        responsible = self.cleaned_data.get("responsible")
        if responsible and self.user:
            profile = getattr(self.user, "profile", None)
            is_admin = profile and profile.role == "admin"
            
            if not is_admin and responsible == self.user:
                if not self.instance.pk or self.instance.responsible != responsible:
                    raise forms.ValidationError("Вы не можете назначить задачу самому себе.")
        return responsible


class TaskCommentForm(forms.ModelForm):
    class Meta:
        model = TaskComment
        fields = ["text"]
        widgets = {"text": forms.Textarea(attrs={"rows": 3, "placeholder": "Добавьте рабочий комментарий"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["text"].widget.attrs["class"] = FORM_CONTROL
