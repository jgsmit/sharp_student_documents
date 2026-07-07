from datetime import date

from django.db import migrations
from django.utils import timezone


def _next_payout_date(today: date) -> date:
    if today.day <= 14:
        return date(today.year, today.month, 14)
    if today.day <= 28:
        return date(today.year, today.month, 28)
    if today.month == 12:
        return date(today.year + 1, 1, 14)
    return date(today.year, today.month + 1, 14)


def forwards(apps, schema_editor):
    WithdrawalRequest = apps.get_model("withdrawals", "WithdrawalRequest")
    today = timezone.localdate()
    scheduled_for = _next_payout_date(today)

    qs = WithdrawalRequest.objects.filter(payout_type="instant")
    for wr in qs.iterator():
        wr.payout_type = "weekly"
        if not getattr(wr, "scheduled_for", None):
            wr.scheduled_for = scheduled_for
        wr.save(update_fields=["payout_type", "scheduled_for"])


class Migration(migrations.Migration):
    dependencies = [
        ("withdrawals", "0003_alter_withdrawalrequest_payout_type"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]

