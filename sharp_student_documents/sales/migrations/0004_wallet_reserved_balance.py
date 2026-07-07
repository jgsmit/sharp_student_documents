from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("sales", "0003_sale_wallet_release_and_wallet_pending_balance"),
    ]

    operations = [
        migrations.AddField(
            model_name="wallet",
            name="reserved_balance",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                help_text="Amount reserved for pending withdrawals",
                max_digits=12,
                validators=[MinValueValidator(Decimal("0.00"))],
            ),
        ),
    ]

