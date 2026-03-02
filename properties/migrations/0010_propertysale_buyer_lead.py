from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("leads", "0003_lead_address"),
        ("properties", "0009_propertysale"),
    ]

    operations = [
        migrations.AddField(
            model_name="propertysale",
            name="buyer_lead",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="property_sales", to="leads.lead"),
        ),
    ]
