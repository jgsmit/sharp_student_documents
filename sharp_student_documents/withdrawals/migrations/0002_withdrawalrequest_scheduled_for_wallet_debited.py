from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("withdrawals", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="withdrawalrequest",
            name="scheduled_for",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="withdrawalrequest",
            name="wallet_debited",
            field=models.BooleanField(default=False),
        ),
    ]

