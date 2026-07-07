from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("sales", "0002_alter_sale_commission_rate"),
    ]

    operations = [
        migrations.AddField(
            model_name="sale",
            name="wallet_released_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="wallet",
            name="pending_balance",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                help_text="Earnings on hold (not yet withdrawable)",
                max_digits=12,
                validators=[MinValueValidator(Decimal("0.00"))],
            ),
        ),
    ]

