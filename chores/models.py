import calendar
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
import secrets


def invite_code():
	return secrets.token_urlsafe(32)


class Household(models.Model):
	name = models.CharField(max_length=100)

	def __str__(self):
		return self.name


class Membership(models.Model):
	household = models.ForeignKey(
		Household,
		on_delete=models.CASCADE,
		related_name="memberships",
	)
	user = models.OneToOneField(
		"auth.User",
		on_delete=models.CASCADE,
		related_name="membership",
	)

	def __str__(self):
		return f"{self.user} in {self.household}"


class InviteCode(models.Model):
	household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="invites")
	code = models.CharField(max_length=64, unique=True, default=invite_code)
	created_at = models.DateTimeField(auto_now_add=True)
	expires_at = models.DateTimeField()
	used_at = models.DateTimeField(blank=True, null=True)
	used_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL, blank=True, null=True)

	@property
	def is_valid(self):
		return self.used_at is None and self.expires_at > timezone.now()


class Chore(models.Model):
	class Schedule(models.TextChoices):
		ONE_OFF = "one_off", "One-off"
		DAILY = "daily", "Daily"
		WEEKLY = "weekly", "Weekly"
		MONTHLY = "monthly", "Monthly"

	class Status(models.TextChoices):
		ACTIVE = "active", "Active"
		COMPLETED = "completed", "Completed"

	household = models.ForeignKey(
		Household,
		on_delete=models.CASCADE,
		related_name="chores",
	)
	creator = models.ForeignKey(
		Membership,
		on_delete=models.PROTECT,
		related_name="created_chores",
	)
	assignee = models.ForeignKey(
		Membership,
		on_delete=models.PROTECT,
		related_name="assigned_chores",
		blank=True,
		null=True,
	)
	name = models.CharField(max_length=200)
	description = models.TextField(blank=True)
	due_date = models.DateField(blank=True, null=True)
	schedule = models.CharField(
		max_length=10,
		choices=Schedule,
		default=Schedule.ONE_OFF,
	)
	status = models.CharField(
		max_length=10,
		choices=Status,
		default=Status.ACTIVE,
	)
	recurrence_day = models.PositiveSmallIntegerField(blank=True, null=True)
	completed_by = models.ForeignKey(
		Membership,
		on_delete=models.PROTECT,
		related_name="completed_chores",
		blank=True,
		null=True,
	)
	completed_at = models.DateTimeField(blank=True, null=True)

	class Meta:
		constraints = [
			models.CheckConstraint(
				condition=~models.Q(name=""),
				name="chore_name_not_empty",
			),
			models.CheckConstraint(
				condition=models.Q(
					schedule__in=["one_off", "daily", "weekly", "monthly"]
				),
				name="chore_schedule_valid",
			),
			models.CheckConstraint(
				condition=models.Q(
					status__in=["active", "completed"]
				),
				name="chore_status_valid",
			),
		]

	def clean(self):
		errors = {}
		if not self.name or not self.name.strip():
			errors["name"] = "The chore name cannot be blank."
		if self.creator_id and self.creator.household_id != self.household_id:
			errors["creator"] = "The creator must belong to the chore's household."
		if self.assignee_id and self.assignee.household_id != self.household_id:
			errors["assignee"] = "The assignee must belong to the chore's household."
		if self.schedule != self.Schedule.ONE_OFF and self.due_date is None:
			errors["due_date"] = "A recurring chore needs a due date so the next occurrence can be scheduled."
		if errors:
			raise ValidationError(errors)

	def save(self, *args, **kwargs):
		if self.schedule == self.Schedule.MONTHLY and self.recurrence_day is None and self.due_date:
			self.recurrence_day = self.due_date.day
		self.full_clean()
		super().save(*args, **kwargs)

	def next_due_date(self, from_date):
		"""Return the due date of the next occurrence after ``from_date``.

		Monthly chores keep the intended day of month when the target month
		contains it. When the day is missing (for example the 31st in
		February) the next occurrence falls on the last valid day of that
		month, and the following month returns to the original day.
		"""
		if self.schedule == self.Schedule.DAILY:
			return from_date + timedelta(days=1)
		if self.schedule == self.Schedule.WEEKLY:
			return from_date + timedelta(weeks=1)
		if self.schedule == self.Schedule.MONTHLY:
			month = from_date.month + 1
			year = from_date.year
			if month > 12:
				month = 1
				year += 1
			last_day = calendar.monthrange(year, month)[1]
			day = min(self.recurrence_day or from_date.day, last_day)
			return from_date.replace(year=year, month=month, day=day)
		raise ValueError("One-off chores do not recur.")

	def __str__(self):
		return self.name
