from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("sales", "0006_remove_withdrawalrequest"),
    ]

    operations = [
        migrations.AddField(
            model_name="wallet",
            name="debt_balance",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                help_text="Outstanding amount owed to platform due to refunds after payout (deducted from future earnings).",
                max_digits=12,
                validators=[MinValueValidator(Decimal("0.00"))],
            ),
        ),
    ]

