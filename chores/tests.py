from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from .models import Chore, Household, InviteCode, Membership


class DomainModelTests(TestCase):
	def setUp(self):
		self.household = Household.objects.create(name="Home")
		self.other_household = Household.objects.create(name="Other home")
		self.user = User.objects.create_user(username="alex")
		self.other_user = User.objects.create_user(username="sam")
		self.membership = Membership.objects.create(
			household=self.household,
			user=self.user,
		)
		self.other_membership = Membership.objects.create(
			household=self.other_household,
			user=self.other_user,
		)

	def test_user_can_have_only_one_membership(self):
		duplicate = Membership(
			household=self.other_household,
			user=self.user,
		)

		with self.assertRaises(ValidationError):
			duplicate.full_clean()
		with self.assertRaises(IntegrityError):
			with transaction.atomic():
				duplicate.save()

	def test_chore_defaults_to_active_one_off(self):
		chore = Chore.objects.create(
			household=self.household,
			creator=self.membership,
			name="Wash dishes",
		)

		self.assertEqual(chore.schedule, Chore.Schedule.ONE_OFF)
		self.assertEqual(chore.status, Chore.Status.ACTIVE)

	def test_chore_requires_a_name(self):
		chore = Chore(
			household=self.household,
			creator=self.membership,
		)

		with self.assertRaises(ValidationError):
			chore.save()

		with self.assertRaises(ValidationError):
			Chore.objects.create(
				household=self.household,
				creator=self.membership,
				name="   ",
			)

	def test_all_schedule_and_status_choices_are_valid(self):
		for schedule, _ in Chore.Schedule.choices:
			for status, _ in Chore.Status.choices:
				chore = Chore(
					household=self.household,
					creator=self.membership,
					name=f"{schedule} {status}",
					schedule=schedule,
					status=status,
				)
				chore.full_clean()

	def test_invalid_schedule_and_status_cannot_be_saved(self):
		with self.assertRaises(ValidationError):
			Chore.objects.create(
				household=self.household,
				creator=self.membership,
				name="Invalid schedule",
				schedule="invalid",
			)
		with self.assertRaises(ValidationError):
			Chore.objects.create(
				household=self.household,
				creator=self.membership,
				name="Invalid status",
				status="invalid",
			)

	def test_creator_and_assignee_must_share_household(self):
		creator_mismatch = Chore(
			household=self.household,
			creator=self.other_membership,
			name="Vacuum",
		)
		assignee_mismatch = Chore(
			household=self.household,
			creator=self.membership,
			assignee=self.other_membership,
			name="Vacuum",
		)

		with self.assertRaises(ValidationError):
			creator_mismatch.full_clean()
		with self.assertRaises(ValidationError):
			assignee_mismatch.full_clean()
		with self.assertRaises(ValidationError):
			assignee_mismatch.save()


class OnboardingTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username="alex", password="correct-password")
		self.other_user = User.objects.create_user(username="sam", password="correct-password")

	def test_anonymous_users_are_sent_to_signin(self):
		response = self.client.get(reverse("onboarding"))
		self.assertRedirects(response, f"{reverse('signin')}?next={reverse('onboarding')}")

	def test_signup_and_signin(self):
		response = self.client.post(reverse("signup"), {"username": "new", "password1": "strong-password-123", "password2": "strong-password-123"})
		self.assertRedirects(response, reverse("signin"))
		response = self.client.post(reverse("signin"), {"username": "new", "password": "strong-password-123"})
		self.assertRedirects(response, reverse("onboarding"))

	def test_create_household_adds_creator_and_lists_members(self):
		self.client.force_login(self.user)
		response = self.client.post(reverse("create_household"), {"name": "Home"})
		self.assertRedirects(response, reverse("household_detail"))
		self.assertTrue(Membership.objects.filter(user=self.user, household__name="Home").exists())
		response = self.client.get(reverse("household_detail"))
		self.assertContains(response, "alex")

	def test_invite_can_be_used_once_and_expired_invites_fail(self):
		self.client.force_login(self.user)
		self.client.post(reverse("create_household"), {"name": "Home"})
		response = self.client.post(reverse("household_detail"))
		code = response.context["invite"].code
		self.client.force_login(self.other_user)
		response = self.client.post(reverse("join_household"), {"code": code})
		self.assertRedirects(response, reverse("household_detail"))
		self.client.logout()
		third = User.objects.create_user(username="third", password="correct-password")
		self.client.force_login(third)
		response = self.client.post(reverse("join_household"), {"code": code})
		self.assertContains(response, "invalid, expired, or already used")
		invite = InviteCode.objects.get(code=code)
		invite.expires_at = timezone.now() - timedelta(days=1)
		invite.used_at = None
		invite.save(update_fields=("expires_at", "used_at"))
		response = self.client.post(reverse("join_household"), {"code": code})
		self.assertContains(response, "invalid, expired, or already used")


class ChoreWorkflowTests(TestCase):
	def setUp(self):
		self.household = Household.objects.create(name="Home")
		self.other_household = Household.objects.create(name="Other")
		self.user = User.objects.create_user(username="alex", password="password-123")
		self.other_user = User.objects.create_user(username="sam", password="password-123")
		self.membership = Membership.objects.create(household=self.household, user=self.user)
		self.other_membership = Membership.objects.create(household=self.household, user=self.other_user)
		self.client.force_login(self.user)

	def test_active_list_is_shared_and_excludes_completed_and_other_household(self):
		Chore.objects.create(household=self.household, creator=self.membership, name="Dishes")
		Chore.objects.create(household=self.household, creator=self.membership, name="Done", status=Chore.Status.COMPLETED)
		other_membership = Membership.objects.create(household=self.other_household, user=User.objects.create_user(username="other"))
		Chore.objects.create(household=self.other_household, creator=other_membership, name="Secret")
		response = self.client.get(reverse("active_chores"))
		self.assertContains(response, "Dishes")
		self.assertNotContains(response, "Done")
		self.assertNotContains(response, "Secret")
		self.assertContains(response, "Unassigned")

	def test_user_without_membership_gets_onboarding(self):
		user = User.objects.create_user(username="solo", password="password-123")
		self.client.force_login(user)
		self.assertRedirects(self.client.get(reverse("active_chores")), reverse("onboarding"))

	def test_create_edit_delete_and_template_prefill(self):
		response = self.client.get(reverse("create_chore") + "?template=vacuum")
		self.assertContains(response, "Vacuum")
		response = self.client.post(reverse("create_chore"), {"name": "  ", "schedule": "one_off"})
		self.assertContains(response, "cannot be blank")
		response = self.client.post(reverse("create_chore"), {"name": "Dishes", "description": "Daily", "schedule": "daily", "assignee": self.other_membership.id})
		self.assertRedirects(response, reverse("active_chores"))
		chore = Chore.objects.get(name="Dishes")
		self.assertEqual(chore.assignee, self.other_membership)
		self.client.post(reverse("edit_chore", args=[chore.id]), {"name": "New dishes", "schedule": "weekly", "assignee": ""})
		self.assertTrue(Chore.objects.filter(name="New dishes", schedule="weekly").exists())
		self.client.post(reverse("delete_chore", args=[chore.id]))
		self.assertFalse(Chore.objects.filter(pk=chore.id).exists())

	def test_chore_object_isolated_from_other_household(self):
		other_membership = Membership.objects.create(household=self.other_household, user=User.objects.create_user(username="other"))
		chore = Chore.objects.create(household=self.other_household, creator=other_membership, name="Secret")
		self.assertEqual(self.client.get(reverse("edit_chore", args=[chore.id])).status_code, 404)
		self.assertEqual(self.client.post(reverse("delete_chore", args=[chore.id])).status_code, 404)
