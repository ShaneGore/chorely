# Chorely MVP Backlog

A small, dependency-ordered backlog for the shared household chores MVP. Each task should leave the application in a usable state and include focused tests before moving on.

## 1. Establish the domain model

**Scope**
- Add `Household` and `Membership` models.
- Enforce the MVP rule that a user belongs to at most one household.
- Add the `Chore` model with name, description, household, creator, optional assignee, due date, schedule, and status.
- Use explicit choices for one-off/daily/weekly/monthly schedules and active/completed status.
- Add model validation for required names and household-consistent creator/assignee relationships.

**Done when**
- Migrations run successfully.
- Model tests cover required fields, schedule/status choices, and household membership constraints.

## 2. Add authentication and household onboarding

**Scope**
- Add sign-up, sign-in, sign-out, and account redirect flows using Django authentication.
- Let an authenticated user create a household.
- Let an authenticated user join a household with a single-use invite code or link.
- Show the current household and its members.

**Done when**
- An unauthenticated user cannot access household or chore pages.
- A user cannot join a second household.
- Invalid, expired, or already-used invite codes are rejected.
- The creator is added as the first household member.

## 3. Build the shared active chore list

**Scope**
- Add a household-scoped active chore list view.
- Display name, assignee or `Unassigned`, due date, schedule, and completion control.
- Add clear empty states for no household and no active chores.
- Ensure every query is restricted to the signed-in user's household.

**Done when**
- Household members see the same active chore list.
- Users cannot view chores from another household by changing a URL or query parameter.
- Completed chores are excluded from the active list.

## 4. Implement chore creation and editing

**Scope**
- Add create and edit forms for custom chores.
- Support optional description, assignee, due date, and schedule.
- Limit assignee choices to members of the current household.
- Add predefined templates for rubbish, dishes, vacuuming, and bathroom cleaning that prefill the form.

**Done when**
- A household member can create a valid one-off or recurring chore.
- Blank names and invalid dates are rejected.
- A chore cannot be assigned to someone outside the household.
- Any household member can edit or delete a household chore.

## 5. Add claim and completion workflows

**Scope**
- Let a member claim an unassigned active chore.
- Prevent claiming an already-assigned chore unless it is explicitly unassigned first.
- Add a completion action that records who completed the chore and when.
- Move completed one-off chores to history.

**Done when**
- Only household members can claim or complete chores.
- Claiming and completion are protected against invalid or repeated state changes.
- Completion history shows the chore, completer, and completion time.

## 6. Support recurring chore occurrences

**Scope**
- Preserve the recurring chore definition after an occurrence is completed.
- Create the next daily, weekly, or monthly occurrence with the appropriate due date.
- Keep each occurrence's completion record separate from the recurring definition.
- Define simple month-end behavior for monthly chores, such as clamping to the last valid day.

**Done when**
- Completing a recurring chore removes only the current occurrence from active work.
- The next occurrence appears with the expected schedule and remains completable.
- Tests cover daily, weekly, monthly, and month-end recurrence behavior.

## 7. Add history, filters, and household navigation

**Scope**
- Add a completed/history view with newest completions first.
- Add an optional `All chores` versus `My chores` filter.
- Add basic due-date ordering for active chores.
- Add navigation between active chores, history, household members, and invite flows.

**Done when**
- Empty history has a clear empty state.
- The `My chores` filter includes assigned chores and chores created by the current user only if that is the chosen product rule.
- Filters and ordering remain household-scoped.

## 8. Harden the MVP and document local use

**Scope**
- Add request-level tests for authentication, household isolation, permissions, CRUD, claiming, completion, and recurrence.
- Add CSRF protection and use POST for state-changing actions.
- Review settings for local versus production configuration, including secrets and allowed hosts.
- Update the README with virtual-environment, migration, test, and development-server commands.

**Done when**
- The full test suite passes with `python manage.py test`.
- The main user journeys work from a fresh database without manual data edits.
- No reminder, notification, gamification, multi-household, analytics, or integration work is included in the MVP.

## Suggested first milestone

Complete tasks 1 through 4 first. That produces a usable authenticated household with a shared active chore list and create/edit/delete flows. Then implement claiming, completion, and recurrence as the second milestone.
