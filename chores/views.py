from datetime import timedelta

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import ChoreForm, CreateHouseholdForm, JoinHouseholdForm, SignUpForm
from .models import Chore, InviteCode, Membership


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


@login_required
def active_chores(request):
	membership = getattr(request.user, "membership", None)
	if membership is None:
		return redirect("onboarding")
	chores = Chore.objects.filter(
		household=membership.household,
		status=Chore.Status.ACTIVE,
	).select_related("assignee__user").order_by("due_date", "name")
	return render(request, "chores/active_chores.html", {
		"household": membership.household,
		"chores": chores,
	})


TEMPLATES = {
	"rubbish": "Take out rubbish",
	"dishes": "Wash dishes",
	"vacuum": "Vacuum",
	"bathroom": "Clean bathroom",
}


@login_required
def create_chore(request):
	membership = get_object_or_404(Membership, user=request.user)
	initial = {"name": TEMPLATES[request.GET["template"]]} if request.method == "GET" and request.GET.get("template") in TEMPLATES else None
	form = ChoreForm(membership.household, request.POST or None, initial=initial)
	if request.method == "POST" and form.is_valid():
		chore = form.save(commit=False)
		chore.household = membership.household
		chore.creator = membership
		chore.save()
		return redirect("active_chores")
	return render(request, "chores/create_chore.html", {"form": form})


@login_required
def edit_chore(request, chore_id):
	membership = get_object_or_404(Membership, user=request.user)
	chore = get_object_or_404(Chore, id=chore_id, household=membership.household)
	form = ChoreForm(membership.household, request.POST or None, instance=chore)
	if request.method == "POST" and form.is_valid():
		form.save()
		return redirect("active_chores")
	return render(request, "chores/edit_chore.html", {"form": form, "chore": chore})


@login_required
@require_POST
def delete_chore(request, chore_id):
	membership = get_object_or_404(Membership, user=request.user)
	get_object_or_404(Chore, id=chore_id, household=membership.household).delete()
	return redirect("active_chores")
