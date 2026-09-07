from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Chore, Household, Membership


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
