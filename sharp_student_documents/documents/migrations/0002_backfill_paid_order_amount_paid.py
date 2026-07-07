from django.db import migrations


def forwards(apps, schema_editor):
    Order = apps.get_model("documents", "Order")
    Payment = apps.get_model("payments", "Payment")

    # Backfill paid orders that have a zero amount_paid (common when older Stripe webhook
    # payloads didn't include amount_total and we defaulted to 0).
    qs = Order.objects.select_related("document").filter(status="paid", amount_paid=0)
    for order in qs.iterator():
        payment_amount = None
        try:
            payment = Payment.objects.filter(order_id=order.id, status="success").only("amount").first()
            if payment:
                payment_amount = payment.amount
        except Exception:
            payment_amount = None

        if payment_amount and payment_amount != 0:
            order.amount_paid = payment_amount
        else:
            order.amount_paid = getattr(order.document, "price", 0) or 0
        order.save(update_fields=["amount_paid"])


def backwards(apps, schema_editor):
    # No safe reversal for a data backfill.
    return


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0001_initial"),
        ("payments", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]

