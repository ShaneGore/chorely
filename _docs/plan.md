# Shared Household Chores Tool — MVP Plan

## 1. MVP goal
Build a simple shared-household chores tool for **any shared household**. The MVP should let household members create, assign, claim, complete, edit, delete, and review chores without adding reminders or complex automation.

## 2. Users and households
- Users have individual accounts.
- A user can join a household.
- A household contains its members and one shared chore list.
- Everyone in the household can see all current chores.
- **MVP assumption:** a user belongs to one household at a time. This keeps the data model and UI simple; multi-household support can be added later.

## 3. Core chore features
Each chore contains:
- **Name** — required.
- **Description** — optional.
- **Assignee** — optional; can be a specific household member or left unassigned.
- **Due date** — optional.
- **Schedule** — either one-off or recurring.

### Creating chores
Any household member can create a chore.

The tool should provide predefined chore templates as a convenience, while still allowing fully custom chores.

Examples of templates could include:
- Take out rubbish
- Wash dishes
- Vacuum
- Clean bathroom

### Assignment
A chore can be:
- assigned directly by its creator to a household member, or
- left unassigned so a household member can claim it.

No automatic rotation is included in the MVP.

### Recurrence
Support:
- one-off chores
- daily recurring chores
- weekly recurring chores
- monthly recurring chores

**MVP assumption:** recurring chores use simple fixed schedules rather than advanced rules such as “every second Tuesday.”

## 4. Completion and history
- Completing a chore is a simple checkbox/action.
- No proof or photo is required.
- When completed, the chore moves out of the active list into a **completed/history** section.
- **MVP assumption:** completion records only need to preserve enough information to show what was completed and by whom; a full audit log is unnecessary unless the implementation naturally supports it.

## 5. Editing and deletion
- Any household member can edit any chore.
- Any household member can delete any chore.
- No special admin permission is required for these actions in the MVP.

## 6. Active chore list
The main screen should show one shared list of active chores.

Useful minimum display fields:
- chore name
- assignee (or “Unassigned”)
- due date, when present
- recurring indicator, when present
- completion control

A simple filter for **all chores vs. my chores** is optional but useful; it does not change the underlying scope.

## 7. Authentication and household membership
Minimum account flows:
- sign up / sign in
- create a household
- join a household through an invitation
- view household members

**MVP assumption:** household invitations can use a simple invite link or code. Email invitation delivery is not required unless the homework specifically needs it.

## 8. Notifications
- No reminders.
- No push notifications.
- No email notifications.

This is intentionally excluded to keep the MVP focused on task management rather than communication infrastructure.

## 9. Explicitly out of scope
The MVP does **not** include:
- automatic/fair chore rotation
- points, rewards, gamification, or leaderboards
- reminders or notifications
- photo proof
- room/area-based lists
- advanced recurring schedules
- admin-only permissions
- multiple-household membership
- analytics or productivity statistics
- integrations with calendars or smart-home systems

## 10. Critical elements added by best judgement
### Household identifier and membership model
A chore needs to belong to a household, and users need membership in that household. This is essential for preventing chores from appearing across unrelated households.

### Stable chore status
The system should distinguish at least **active** and **completed** states. This is necessary to implement the shared list plus history cleanly.

### Recurring-chore behavior
For a recurring chore, completing one occurrence should complete that occurrence while preserving the recurrence for the next scheduled occurrence. This is essential; otherwise a recurring chore would disappear permanently after its first completion.

### Basic validation and permissions
The system should reject invalid operations such as creating a chore without a name or assigning a chore to someone outside the household. A user must only be able to access chores belonging to their household.

### Empty states
The UI should handle an empty active list and an empty history section clearly, so the MVP is usable from a brand-new household onward.

## 11. Suggested MVP screens
1. **Sign in / Sign up**
2. **Create or Join Household**
3. **Active Chores** — shared household chore list
4. **Create/Edit Chore**
5. **Completed History**
6. **Household Members / Invite**

## 12. Core user stories
- As a household member, I can create a chore so that it appears in the shared list.
- As a household member, I can assign a chore to another member.
- As a household member, I can leave a chore unassigned so someone can claim it.
- As a household member, I can claim an unassigned chore.
- As a household member, I can mark a chore complete.
- As a household member, I can view completed chores in history.
- As a household member, I can edit or delete any chore.
- As a household member, I can create a one-off or recurring chore.
- As a household member, I can see all active chores in my household.

## 13. MVP success criteria
The MVP is complete when a small household can:
1. create/join a household,
2. see a shared chore list,
3. create one-off and recurring chores,
4. assign or claim chores,
5. optionally set due dates,
6. mark chores complete,
7. view completed history, and
8. edit or delete chores,
without needing any manual data manipulation.

## 14. Recommended priority
**Must have:** accounts, household membership, shared active list, create/edit/delete, assignment/claiming, completion, history, one-off + simple recurring chores, optional due dates, predefined templates.

**Nice to have within MVP if time allows:** simple “My chores” filter and basic sorting by due date.
