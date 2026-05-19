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
            "watchers",
            "planning_period",
            "parent_task",
            "annual_goal",
            "deadline",
            "priority",
            "status",
            "progress",
            "tags",
            "estimated_hours",
            "actual_hours",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "deadline": forms.DateInput(attrs={"type": "date"}),
            "watchers": forms.CheckboxSelectMultiple(attrs={"class": "checkbox-list"}),
            "progress": forms.NumberInput(attrs={"min": 0, "max": 100}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxSelectMultiple):
                continue
            classes = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{classes} {FORM_CONTROL}".strip()
        self.fields["estimated_hours"].required = False
        self.fields["actual_hours"].required = False


class TaskCommentForm(forms.ModelForm):
    class Meta:
        model = TaskComment
        fields = ["text"]
        widgets = {"text": forms.Textarea(attrs={"rows": 3, "placeholder": "Добавьте рабочий комментарий"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["text"].widget.attrs["class"] = FORM_CONTROL
