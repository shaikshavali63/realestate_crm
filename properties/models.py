from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

class Property(models.Model):

    PROPERTY_TYPE_CHOICES = (
    ('house', 'House'),
    ('apartment', 'Apartment / Flat'),
    ('villa', 'Villa'),
    ('building', 'Building'),
    ('complex', 'Residential Complex'),
    ('commercial', 'Commercial Property'),
    ('land', 'Land / Plot'),
)


    STATUS_CHOICES = (
        ('available', 'Available'),
        ('sold', 'Sold'),
        ('hold', 'On Hold'),
    )

    LISTING_TYPE_CHOICES = (
        ('buy', 'Buy'),
        ('rent', 'Rent'),
        ('lease', 'Lease'),
    )

    title = models.CharField(max_length=200)
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPE_CHOICES)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    bedrooms = models.IntegerField(null=True, blank=True)
    bathrooms = models.IntegerField(null=True, blank=True)
    area = models.IntegerField(null=True, blank=True, help_text="Area in sqft")
    location = models.CharField(max_length=255)
    listing_type = models.CharField(max_length=20, choices=LISTING_TYPE_CHOICES, default='buy')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    image = models.ImageField(upload_to='properties/main/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class PropertyImage(models.Model):
    property = models.ForeignKey(
        Property,
        related_name='gallery',
        on_delete=models.CASCADE
    )
    image = models.ImageField(upload_to='properties/gallery/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Gallery image for {self.property.title}"


class PropertySale(models.Model):
    buyer_lead = models.ForeignKey(
        "leads.Lead",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="property_sales",
    )
    property = models.OneToOneField(
        Property,
        on_delete=models.CASCADE,
        related_name="sale_info",
    )
    buyer_name = models.CharField(max_length=200)
    buyer_phone = models.CharField(max_length=20, blank=True)
    buyer_email = models.EmailField(blank=True)
    sold_price = models.DecimalField(max_digits=12, decimal_places=2)
    sold_on = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Sale: {self.property.title} -> {self.buyer_name}"


@receiver(pre_save, sender=Property)
def capture_previous_assignee(sender, instance, **kwargs):
    if not instance.pk:
        instance._old_assigned_to_id = None
        return
    old = Property.objects.filter(pk=instance.pk).values("assigned_to_id").first()
    instance._old_assigned_to_id = old["assigned_to_id"] if old else None


@receiver(post_save, sender=Property)
def sync_property_leads_assignment(sender, instance, **kwargs):
    old_assignee = getattr(instance, "_old_assigned_to_id", None)
    if old_assignee == instance.assigned_to_id:
        return
    from leads.models import Lead
    Lead.objects.filter(property=instance).update(assigned_to=instance.assigned_to)







