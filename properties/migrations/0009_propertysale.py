from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("properties", "0008_property_listing_type"),
    ]

    operations = [
        migrations.CreateModel(
            name="PropertySale",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("buyer_name", models.CharField(max_length=200)),
                ("buyer_phone", models.CharField(blank=True, max_length=20)),
                ("buyer_email", models.EmailField(blank=True, max_length=254)),
                ("sold_price", models.DecimalField(decimal_places=2, max_digits=12)),
                ("sold_on", models.DateField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("property", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="sale_info", to="properties.property")),
            ],
        ),
    ]
