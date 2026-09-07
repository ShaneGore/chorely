from django.db import migrations, models
import django.db.models.deletion
from chores.models import invite_code


class Migration(migrations.Migration):
	dependencies = [("chores", "0002_chore_chore_name_not_empty_and_more")]
	operations = [
		migrations.CreateModel(
			name="InviteCode",
			fields=[
				("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
				("code", models.CharField(default=invite_code, max_length=64, unique=True)),
				("created_at", models.DateTimeField(auto_now_add=True)),
				("expires_at", models.DateTimeField()),
				("used_at", models.DateTimeField(blank=True, null=True)),
				("household", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="invites", to="chores.household")),
				("used_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="auth.user")),
			],
		),
	]