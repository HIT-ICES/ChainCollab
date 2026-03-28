from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="identitydeployment",
            name="firefly_listeners",
            field=models.JSONField(blank=True, help_text="FireFly listeners registered for identity contract", null=True),
        ),
    ]
