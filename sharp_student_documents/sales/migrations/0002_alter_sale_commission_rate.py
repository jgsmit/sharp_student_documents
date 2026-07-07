from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("sales", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sale",
            name="commission_rate",
            field=models.DecimalField(
                decimal_places=4,
                default=Decimal("0.4000"),
                help_text="Commission rate (40% = 0.4000)",
                max_digits=5,
            ),
        ),
    ]

