from datetime import timedelta

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import CreateHouseholdForm, JoinHouseholdForm, SignUpForm
from .models import InviteCode, Membership


def account_redirect(request):
	if not request.user.is_authenticated:
		return redirect("signin")
	if hasattr(request.user, "membership"):
		return redirect("household_detail")
	return redirect("onboarding")


def signup(request):
	form = SignUpForm(request.POST or None)
	if request.method == "POST" and form.is_valid():
		form.save()
		return redirect("signin")
	return render(request, "chores/signup.html", {"form": form})


def signin(request):
	form = AuthenticationForm(request, data=request.POST or None)
	if request.method == "POST" and form.is_valid():
		login(request, form.get_user())
		return account_redirect(request)
	return render(request, "chores/signin.html", {"form": form})


@require_POST
def signout(request):
	logout(request)
	return redirect("signin")


@login_required
def onboarding(request):
	if hasattr(request.user, "membership"):
		return redirect("household_detail")
	return render(request, "chores/onboarding.html")


@login_required
def create_household(request):
	if hasattr(request.user, "membership"):
		return redirect("household_detail")
	form = CreateHouseholdForm(request.POST or None)
	if request.method == "POST" and form.is_valid():
		household = form.save()
		Membership.objects.create(household=household, user=request.user)
		return redirect("household_detail")
	return render(request, "chores/create_household.html", {"form": form})


@login_required
def household_detail(request):
	membership = get_object_or_404(Membership, user=request.user)
	household = membership.household
	invite = None
	if request.method == "POST":
		invite = InviteCode.objects.create(
			household=household,
			expires_at=timezone.now() + timedelta(days=7),
		)
	return render(request, "chores/household_detail.html", {"household": household, "invite": invite})


@login_required
def join_household(request):
	if hasattr(request.user, "membership"):
		return redirect("household_detail")
	form = JoinHouseholdForm(request.POST or None)
	if request.method == "POST" and form.is_valid():
		try:
			with transaction.atomic():
				invite = InviteCode.objects.select_for_update().get(code=form.cleaned_data["code"])
				if not invite.is_valid:
					raise ValueError
				Membership.objects.create(household=invite.household, user=request.user)
				invite.used_at = timezone.now()
				invite.used_by = request.user
				invite.save(update_fields=("used_at", "used_by"))
			return redirect("household_detail")
		except (InviteCode.DoesNotExist, ValueError, IntegrityError):
			form.add_error("code", "This invite is invalid, expired, or already used.")
	return render(request, "chores/join_household.html", {"form": form})
