from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import date, timedelta

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
					due_date=date(2026, 9, 8) if schedule != Chore.Schedule.ONE_OFF else None,
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

	def test_recurring_chore_requires_a_due_date(self):
		with self.assertRaises(ValidationError):
			Chore.objects.create(
				household=self.household,
				creator=self.membership,
				name="No anchor",
				schedule=Chore.Schedule.DAILY,
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
		response = self.client.post(reverse("create_chore"), {"name": "Dishes", "description": "Daily", "schedule": "daily", "due_date": "2026-09-08", "assignee": self.other_membership.id})
		self.assertRedirects(response, reverse("active_chores"))
		chore = Chore.objects.get(name="Dishes")
		self.assertEqual(chore.assignee, self.other_membership)
		self.client.post(reverse("edit_chore", args=[chore.id]), {"name": "New dishes", "schedule": "weekly", "due_date": "2026-09-08", "assignee": ""})
		self.assertTrue(Chore.objects.filter(name="New dishes", schedule="weekly").exists())
		self.client.post(reverse("delete_chore", args=[chore.id]))
		self.assertFalse(Chore.objects.filter(pk=chore.id).exists())

	def test_chore_object_isolated_from_other_household(self):
		other_membership = Membership.objects.create(household=self.other_household, user=User.objects.create_user(username="other"))
		chore = Chore.objects.create(household=self.other_household, creator=other_membership, name="Secret")
		self.assertEqual(self.client.get(reverse("edit_chore", args=[chore.id])).status_code, 404)
		self.assertEqual(self.client.post(reverse("delete_chore", args=[chore.id])).status_code, 404)


class ClaimAndCompletionTests(TestCase):
	def setUp(self):
		self.household = Household.objects.create(name="Home")
		self.other_household = Household.objects.create(name="Other")
		self.user = User.objects.create_user(username="alex", password="password-123")
		self.other_user = User.objects.create_user(username="sam", password="password-123")
		self.membership = Membership.objects.create(household=self.household, user=self.user)
		self.other_membership = Membership.objects.create(household=self.household, user=self.other_user)
		self.outsider_membership = Membership.objects.create(household=self.other_household, user=User.objects.create_user(username="outsider"))

	def make_chore(self, name="Dishes", **kwargs):
		return Chore.objects.create(household=self.household, creator=self.membership, name=name, **kwargs)

	def test_claim_assigns_chore_to_requesting_member(self):
		chore = self.make_chore()
		self.client.force_login(self.user)
		response = self.client.post(reverse("claim_chore", args=[chore.id]))
		self.assertRedirects(response, reverse("active_chores"))
		chore.refresh_from_db()
		self.assertEqual(chore.assignee, self.membership)
		response = self.client.get(reverse("active_chores"))
		self.assertContains(response, "alex")

	def test_claim_action_only_shown_for_unassigned_active_chore(self):
		chore = self.make_chore(assignee=self.other_membership)
		self.client.force_login(self.user)
		response = self.client.get(reverse("active_chores"))
		self.assertNotContains(response, "Claim")
		unassigned = self.make_chore(name="Bins")
		response = self.client.get(reverse("active_chores"))
		self.assertContains(response, "Claim")

	def test_second_claim_does_not_overwrite_existing_assignee(self):
		chore = self.make_chore()
		self.client.force_login(self.user)
		self.client.post(reverse("claim_chore", args=[chore.id]))
		self.client.force_login(self.other_user)
		self.client.post(reverse("claim_chore", args=[chore.id]))
		chore.refresh_from_db()
		self.assertEqual(chore.assignee, self.membership)

	def test_complete_records_member_and_time(self):
		chore = self.make_chore()
		self.client.force_login(self.user)
		before = timezone.now()
		response = self.client.post(reverse("complete_chore", args=[chore.id]))
		self.assertRedirects(response, reverse("active_chores"))
		chore.refresh_from_db()
		self.assertEqual(chore.status, Chore.Status.COMPLETED)
		self.assertEqual(chore.completed_by, self.membership)
		self.assertLessEqual(chore.completed_at, timezone.now())
		self.assertGreaterEqual(chore.completed_at, before)

	def test_completed_one_off_leaves_active_list_and_shows_in_history(self):
		chore = self.make_chore()
		self.client.force_login(self.user)
		self.client.post(reverse("complete_chore", args=[chore.id]))
		response = self.client.get(reverse("active_chores"))
		self.assertNotContains(response, "Dishes")
		response = self.client.get(reverse("completed_chores"))
		self.assertContains(response, "Dishes")
		self.assertContains(response, "alex")
		self.assertContains(response, "Completed by")

	def test_repeated_complete_does_not_change_completion_record(self):
		chore = self.make_chore()
		self.client.force_login(self.user)
		self.client.post(reverse("complete_chore", args=[chore.id]))
		chore.refresh_from_db()
		original_time = chore.completed_at
		self.client.force_login(self.other_user)
		self.client.post(reverse("complete_chore", args=[chore.id]))
		chore.refresh_from_db()
		self.assertEqual(chore.completed_by, self.membership)
		self.assertEqual(chore.completed_at, original_time)

	def test_completed_chore_cannot_be_claimed(self):
		chore = self.make_chore()
		self.client.force_login(self.user)
		self.client.post(reverse("complete_chore", args=[chore.id]))
		self.client.force_login(self.other_user)
		self.client.post(reverse("claim_chore", args=[chore.id]))
		chore.refresh_from_db()
		self.assertIsNone(chore.assignee)

	def test_anonymous_user_cannot_claim_or_complete(self):
		chore = self.make_chore()
		response = self.client.post(reverse("claim_chore", args=[chore.id]))
		self.assertEqual(response.status_code, 302)
		self.assertIn("signin", response["Location"])
		response = self.client.post(reverse("complete_chore", args=[chore.id]))
		self.assertEqual(response.status_code, 302)
		self.assertIn("signin", response["Location"])
		chore.refresh_from_db()
		self.assertIsNone(chore.assignee)
		self.assertEqual(chore.status, Chore.Status.ACTIVE)

	def test_member_of_other_household_cannot_claim_or_complete(self):
		chore = self.make_chore()
		self.client.force_login(User.objects.get(username="outsider"))
		response = self.client.post(reverse("claim_chore", args=[chore.id]))
		self.assertEqual(response.status_code, 404)
		response = self.client.post(reverse("complete_chore", args=[chore.id]))
		self.assertEqual(response.status_code, 404)
		chore.refresh_from_db()
		self.assertIsNone(chore.assignee)
		self.assertEqual(chore.status, Chore.Status.ACTIVE)


class RecurrenceTests(TestCase):
	def setUp(self):
		self.household = Household.objects.create(name="Home")
		self.user = User.objects.create_user(username="alex", password="password-123")
		self.membership = Membership.objects.create(household=self.household, user=self.user)
		self.client.force_login(self.user)

	def make_recurring(self, name, schedule, due, **kwargs):
		return Chore.objects.create(
			household=self.household,
			creator=self.membership,
			name=name,
			schedule=schedule,
			due_date=due,
			**kwargs,
		)

	def complete(self, chore):
		response = self.client.post(reverse("complete_chore", args=[chore.id]))
		self.assertRedirects(response, reverse("active_chores"))

	def test_daily_occurrence_is_due_next_day(self):
		chore = self.make_recurring("Recurring", Chore.Schedule.DAILY, date(2026, 9, 8))
		self.complete(chore)
		next_occurrence = Chore.objects.get(status=Chore.Status.ACTIVE, name="Recurring")
		self.assertEqual(next_occurrence.due_date, date(2026, 9, 9))
		self.assertIsNone(next_occurrence.completed_at)
		self.assertIsNone(next_occurrence.completed_by)

	def test_weekly_occurrence_is_due_in_seven_days(self):
		chore = self.make_recurring("Recurring", Chore.Schedule.WEEKLY, date(2026, 9, 8))
		self.complete(chore)
		next_occurrence = Chore.objects.get(status=Chore.Status.ACTIVE, name="Recurring")
		self.assertEqual(next_occurrence.due_date, date(2026, 9, 15))

	def test_monthly_occurrence_preserves_day_of_month(self):
		chore = self.make_recurring("Recurring", Chore.Schedule.MONTHLY, date(2026, 1, 31))
		self.complete(chore)
		next_occurrence = Chore.objects.get(status=Chore.Status.ACTIVE, name="Recurring")
		self.assertEqual(next_occurrence.due_date, date(2026, 2, 28))
		self.complete(next_occurrence)
		next2 = Chore.objects.get(status=Chore.Status.ACTIVE, name="Recurring")
		# The intended day (31st) returns once the month contains it again.
		self.assertEqual(next2.due_date, date(2026, 3, 31))

	def test_month_end_clamps_across_year_boundary(self):
		chore = self.make_recurring("Recurring", Chore.Schedule.MONTHLY, date(2026, 12, 31))
		self.complete(chore)
		next_occurrence = Chore.objects.get(status=Chore.Status.ACTIVE, name="Recurring")
		self.assertEqual(next_occurrence.due_date, date(2027, 1, 31))
		self.complete(next_occurrence)
		next2 = Chore.objects.get(status=Chore.Status.ACTIVE, name="Recurring")
		self.assertEqual(next2.due_date, date(2027, 2, 28))

	def test_completed_occurrence_is_recorded_separately(self):
		chore = self.make_recurring("Recurring", Chore.Schedule.WEEKLY, date(2026, 9, 8))
		self.complete(chore)
		completed = Chore.objects.filter(status=Chore.Status.COMPLETED, name="Recurring")
		self.assertEqual(completed.count(), 1)
		occurrence = completed.get()
		self.assertEqual(occurrence.completed_by, self.membership)
		self.assertIsNotNone(occurrence.completed_at)
		self.assertEqual(occurrence.due_date, date(2026, 9, 8))
		self.assertEqual(occurrence.household, self.household)
		self.assertEqual(occurrence.schedule, Chore.Schedule.WEEKLY)

	def test_repeated_completion_does_not_duplicate_occurrences(self):
		chore = self.make_recurring("Recurring", Chore.Schedule.DAILY, date(2026, 9, 8))
		self.complete(chore)
		self.complete(chore)
		completed = Chore.objects.filter(status=Chore.Status.COMPLETED, name="Recurring")
		self.assertEqual(completed.count(), 1)
		active = Chore.objects.filter(status=Chore.Status.ACTIVE, name="Recurring")
		self.assertEqual(active.count(), 1)
		self.assertEqual(active.get().due_date, date(2026, 9, 9))

	def test_next_occurrence_keeps_assignment_policy(self):
		chore = self.make_recurring("Recurring", Chore.Schedule.WEEKLY, date(2026, 9, 8))
		self.complete(chore)
		next_occurrence = Chore.objects.get(status=Chore.Status.ACTIVE, name="Recurring")
		self.assertIsNone(next_occurrence.assignee)
		assigned = self.make_recurring(
			"Assigned",
			Chore.Schedule.WEEKLY,
			date(2026, 9, 8),
			assignee=self.membership,
		)
		self.complete(assigned)
		next_occurrence = Chore.objects.get(status=Chore.Status.ACTIVE, name="Assigned")
		self.assertEqual(next_occurrence.assignee, self.membership)

	def test_recurring_chore_without_due_date_is_rejected(self):
		response = self.client.post(reverse("create_chore"), {"name": "No date", "schedule": "daily"})
		self.assertContains(response, "needs a due date")
		self.assertFalse(Chore.objects.filter(name="No date").exists())
		with self.assertRaises(ValidationError):
			Chore.objects.create(
				household=self.household,
				creator=self.membership,
				name="Model level",
				schedule=Chore.Schedule.WEEKLY,
			)


class HistoryAndFilterTests(TestCase):
	def setUp(self):
		self.household = Household.objects.create(name="Home")
		self.other_household = Household.objects.create(name="Other")
		self.user = User.objects.create_user(username="alex", password="password-123")
		self.other_user = User.objects.create_user(username="sam", password="password-123")
		self.membership = Membership.objects.create(household=self.household, user=self.user)
		self.other_membership = Membership.objects.create(household=self.household, user=self.other_user)
		self.client.force_login(self.user)

	def make_chore(self, name="Dishes", **kwargs):
		return Chore.objects.create(household=self.household, creator=self.membership, name=name, **kwargs)

	def complete(self, chore):
		self.client.post(reverse("complete_chore", args=[chore.id]))

	def test_history_shows_only_own_household_newest_first(self):
		first = self.make_chore(name="First")
		second = self.make_chore(name="Second")
		self.complete(first)
		self.complete(second)
		outsider_membership = Membership.objects.create(household=self.other_household, user=User.objects.create_user(username="outsider"))
		Chore.objects.create(household=self.other_household, creator=outsider_membership, name="Secret", status=Chore.Status.COMPLETED)
		response = self.client.get(reverse("completed_chores"))
		self.assertContains(response, "First")
		self.assertContains(response, "Second")
		self.assertNotContains(response, "Secret")
		second_pos = response.content.decode().index("Second")
		first_pos = response.content.decode().index("First")
		self.assertLess(second_pos, first_pos)
		self.assertContains(response, "alex")
		self.assertContains(response, "Completed by")

	def test_empty_history_shows_clear_state(self):
		response = self.client.get(reverse("completed_chores"))
		self.assertContains(response, "No completed chores yet")

	def test_my_chores_filter_includes_assigned_and_own_unassigned(self):
		assigned_to_me = self.make_chore(name="Mine assigned", assignee=self.membership)
		created_unassigned = self.make_chore(name="Mine unassigned")
		assigned_away = self.make_chore(name="Assigned away", assignee=self.other_membership)
		response = self.client.get(reverse("active_chores") + "?filter=mine")
		self.assertContains(response, "Mine assigned")
		self.assertContains(response, "Mine unassigned")
		self.assertNotContains(response, "Assigned away")
		response = self.client.get(reverse("active_chores"))
		self.assertContains(response, "Mine assigned")
		self.assertContains(response, "Assigned away")

	def test_dated_chores_order_before_undated(self):
		late = self.make_chore(name="Late", due_date=date(2026, 9, 20))
		early = self.make_chore(name="Early", due_date=date(2026, 9, 10))
		undated = self.make_chore(name="Undated")
		response = self.client.get(reverse("active_chores"))
		content = response.content.decode()
		self.assertLess(content.index("Early"), content.index("Late"))
		self.assertLess(content.index("Late"), content.index("Undated"))

	def test_filters_and_history_are_household_scoped(self):
		outsider_membership = Membership.objects.create(household=self.other_household, user=User.objects.create_user(username="outsider"))
		Chore.objects.create(household=self.other_household, creator=outsider_membership, name="Secret", assignee=outsider_membership)
		response = self.client.get(reverse("active_chores") + "?filter=mine")
		self.assertNotContains(response, "Secret")
		response = self.client.get(reverse("completed_chores"))
		self.assertNotContains(response, "Secret")

	def test_navigation_links_expose_main_flows(self):
		response = self.client.get(reverse("active_chores"))
		self.assertContains(response, "History")
		self.assertContains(response, "Household")
		self.assertContains(response, "Create chore")
		response = self.client.get(reverse("household_detail"))
		self.assertContains(response, "Active chores")

	def test_signed_out_user_redirected_and_household_less_user_onboarded(self):
		self.client.logout()
		response = self.client.get(reverse("completed_chores"))
		self.assertEqual(response.status_code, 302)
		self.assertIn("signin", response["Location"])
		response = self.client.get(reverse("active_chores") + "?filter=mine")
		self.assertEqual(response.status_code, 302)
		self.assertIn("signin", response["Location"])
		solo = User.objects.create_user(username="solo", password="password-123")
		self.client.force_login(solo)
		self.assertRedirects(self.client.get(reverse("completed_chores")), reverse("onboarding"))


class SmokeJourneyTests(TestCase):
	"""End-to-end journey: two members, claim, recurrence, edit, history."""

	def test_full_mvp_journey_from_fresh_database(self):
		# Sign up two members.
		self.client.post(reverse("signup"), {"username": "alex", "password1": "strong-password-123", "password2": "strong-password-123"})
		self.client.post(reverse("signin"), {"username": "alex", "password": "strong-password-123"})
		# Alex creates the household.
		self.client.post(reverse("create_household"), {"name": "Home"})
		# Alex generates an invite and Sam joins with it.
		response = self.client.post(reverse("household_detail"))
		code = response.context["invite"].code
		self.client.post(reverse("signup"), {"username": "sam", "password1": "strong-password-123", "password2": "strong-password-123"})
		self.client.post(reverse("signin"), {"username": "sam", "password": "strong-password-123"})
		self.assertRedirects(self.client.post(reverse("join_household"), {"code": code}), reverse("household_detail"))
		household = Household.objects.get(name="Home")
		self.assertEqual(household.memberships.count(), 2)
		alex = Membership.objects.get(user__username="alex")
		sam = Membership.objects.get(user__username="sam")
		# Alex creates a recurring chore assigned to Sam.
		self.client.force_login(alex.user)
		self.client.post(reverse("create_chore"), {"name": "Vacuum", "schedule": "weekly", "due_date": "2026-09-08", "assignee": sam.id})
		recurring = Chore.objects.get(name="Vacuum")
		self.assertEqual(recurring.assignee, sam)
		# Sam creates a one-off chore left unassigned.
		self.client.force_login(sam.user)
		self.client.post(reverse("create_chore"), {"name": "Bins", "schedule": "one_off"})
		bins = Chore.objects.get(name="Bins")
		self.assertIsNone(bins.assignee)
		# Alex claims the unassigned chore.
		self.client.force_login(alex.user)
		self.client.post(reverse("claim_chore", args=[bins.id]))
		bins.refresh_from_db()
		self.assertEqual(bins.assignee, alex)
		# Sam completes the recurring chore; the next occurrence appears.
		self.client.force_login(sam.user)
		self.client.post(reverse("complete_chore", args=[recurring.id]))
		next_occurrence = Chore.objects.get(name="Vacuum", status=Chore.Status.ACTIVE)
		self.assertEqual(next_occurrence.due_date, date(2026, 9, 15))
		# Alex completes the one-off chore and edits the next occurrence.
		self.client.force_login(alex.user)
		self.client.post(reverse("complete_chore", args=[bins.id]))
		self.client.post(reverse("edit_chore", args=[next_occurrence.id]), {"name": "Vacuum downstairs", "schedule": "weekly", "due_date": "2026-09-15", "assignee": ""})
		self.assertTrue(Chore.objects.filter(name="Vacuum downstairs", status=Chore.Status.ACTIVE).exists())
		# History shows both completions with completer and time.
		response = self.client.get(reverse("completed_chores"))
		self.assertContains(response, "Bins")
		self.assertContains(response, "Vacuum")
		self.assertContains(response, "Completed by")
		# Sam deletes the edited chore.
		self.client.force_login(sam.user)
		self.client.post(reverse("delete_chore", args=[next_occurrence.id]))
		self.assertFalse(Chore.objects.filter(name="Vacuum downstairs").exists())


class HardeningTests(TestCase):
	"""Sweep tests for the cross-cutting hardening criteria."""

	def setUp(self):
		self.household = Household.objects.create(name="Home")
		self.user = User.objects.create_user(username="alex", password="password-123")
		self.membership = Membership.objects.create(household=self.household, user=self.user)
		self.chore = Chore.objects.create(household=self.household, creator=self.membership, name="Dishes")
		self.client.force_login(self.user)

	def test_state_changing_endpoints_reject_missing_csrf_token(self):
		from django.test import Client

		enforce_csrf = Client(enforce_csrf_checks=True)
		enforce_csrf.force_login(self.user)
		endpoints = [
			("post", reverse("signout"), {}),
			("post", reverse("household_detail"), {}),
			("post", reverse("create_chore"), {"name": "X", "schedule": "one_off"}),
			("post", reverse("delete_chore", args=[self.chore.id]), {}),
			("post", reverse("claim_chore", args=[self.chore.id]), {}),
			("post", reverse("complete_chore", args=[self.chore.id]), {}),
		]
		for method, url, data in endpoints:
			response = getattr(enforce_csrf, method)(url, data)
			self.assertEqual(response.status_code, 403, f"{url} accepted a request without a CSRF token")
		self.chore.refresh_from_db()
		self.assertEqual(self.chore.status, Chore.Status.ACTIVE)

	def test_get_requests_cannot_change_state(self):
		for url in (reverse("delete_chore", args=[self.chore.id]), reverse("claim_chore", args=[self.chore.id]), reverse("complete_chore", args=[self.chore.id])):
			response = self.client.get(url)
			self.assertEqual(response.status_code, 405, f"{url} accepted GET")
		self.chore.refresh_from_db()
		self.assertEqual(self.chore.status, Chore.Status.ACTIVE)

	def test_anonymous_users_are_redirected_consistently(self):
		self.client.logout()
		protected_gets = ["onboarding", "household_detail", "active_chores", "completed_chores", "create_chore", "edit_chore"]
		for name in protected_gets:
			url = reverse(name) if name != "edit_chore" else reverse("edit_chore", args=[self.chore.id])
			response = self.client.get(url)
			self.assertEqual(response.status_code, 302, f"{url} did not redirect anonymous users")
			self.assertIn("signin", response["Location"], f"{url} did not redirect to signin")
		protected_posts = ["signout", "household_detail", "create_chore", "delete_chore", "claim_chore", "complete_chore"]
		for name in protected_posts:
			url = reverse(name) if name not in ("delete_chore", "claim_chore", "complete_chore") else reverse(name, args=[self.chore.id])
			response = self.client.post(url, {})
			self.assertEqual(response.status_code, 302, f"{url} did not redirect anonymous users")
			self.assertIn("signin", response["Location"], f"{url} did not redirect to signin")
