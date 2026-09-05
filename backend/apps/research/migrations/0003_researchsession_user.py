import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def assign_default_user_to_existing_sessions(apps, schema_editor):
    user_app, user_model_name = settings.AUTH_USER_MODEL.split(".")
    User = apps.get_model(user_app, user_model_name)
    ResearchSession = apps.get_model("research", "ResearchSession")

    if ResearchSession.objects.filter(user__isnull=True).exists():
        default_user, _ = User.objects.get_or_create(
            username="system_default",
            defaults={
                "email": "system_default@finpilot.local",
                "is_active": False,
            },
        )
        ResearchSession.objects.filter(user__isnull=True).update(user=default_user)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("research", "0002_researchsession_researchevidence"),
    ]

    operations = [
        migrations.AddField(
            model_name="researchsession",
            name="user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="research_sessions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(
            assign_default_user_to_existing_sessions,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="researchsession",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="research_sessions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
