from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Household


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