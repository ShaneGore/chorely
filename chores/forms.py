from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Chore, Household, Membership


class SignUpForm(UserCreationForm):
	class Meta:
		model = User
		fields = ("username", "password1", "password2")


class CreateHouseholdForm(forms.ModelForm):
	class Meta:
		model = Household
		fields = ("name",)

	def clean_name(self):
		name = self.cleaned_data["name"].strip()
		if not name:
			raise forms.ValidationError("Household name cannot be blank.")
		return name


class JoinHouseholdForm(forms.Form):
	code = forms.CharField(max_length=64)


class ChoreForm(forms.ModelForm):
	class Meta:
		model = Chore
		fields = ("name", "description", "assignee", "due_date", "schedule")
		extra_kwargs = {"due_date": {"required": False}}

	def __init__(self, household, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.household = household
		if self.instance._state.adding:
			self.instance.household = household
		self.fields["description"].required = False
		self.fields["assignee"].required = False
		self.fields["assignee"].queryset = household.memberships.select_related("user")
		self.fields["due_date"].required = False

	def clean_name(self):
		name = self.cleaned_data["name"].strip()
		if not name:
			raise forms.ValidationError("Chore name cannot be blank.")
		return name