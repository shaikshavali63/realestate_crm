from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.contrib.auth.models import User
from django.db.models import Q

from .models import Property, PropertyImage, PropertySale
from accounts.models import Profile
from leads.models import Lead


# ======================
# PROPERTY LIST
# ======================
@login_required
def property_list(request):
    base_properties = Property.objects.all()
    properties = base_properties.order_by("-created_at")

    query = (request.GET.get("q") or "").strip()
    ptype = (request.GET.get("type") or "").strip()
    status = (request.GET.get("status") or "").strip()
    listing_type = (request.GET.get("listing_type") or "").strip()
    min_price = (request.GET.get("min_price") or "").strip()
    max_price = (request.GET.get("max_price") or "").strip()
    sort = (request.GET.get("sort") or "").strip()
    requested_property_ids = set()

    if not request.user.is_staff:
        lead_filter = Q()
        if request.user.email:
            lead_filter |= Q(email=request.user.email)
        lead_filter |= Q(name=request.user.get_full_name() or request.user.username)

        requested_property_ids = set(
            Lead.objects.filter(lead_filter, property__isnull=False).values_list("property_id", flat=True)
        )

    if query:
        properties = properties.filter(Q(title__icontains=query) | Q(location__icontains=query))
    if ptype:
        properties = properties.filter(property_type=ptype)
    if status:
        properties = properties.filter(status=status)
    if listing_type:
        properties = properties.filter(listing_type=listing_type)
    if min_price:
        properties = properties.filter(price__gte=min_price)
    if max_price:
        properties = properties.filter(price__lte=max_price)

    if sort == "price_asc":
        properties = properties.order_by("price")
    elif sort == "price_desc":
        properties = properties.order_by("-price")
    elif sort == "latest":
        properties = properties.order_by("-created_at")

    property_types = Property.PROPERTY_TYPE_CHOICES
    status_choices = Property.STATUS_CHOICES
    listing_type_choices = Property.LISTING_TYPE_CHOICES
    buy_count = base_properties.filter(listing_type="buy").count()
    rent_count = base_properties.filter(listing_type="rent").count()
    lease_count = base_properties.filter(listing_type="lease").count()
    sold_count = base_properties.filter(status="sold").count()
    return render(request,
                  'properties/property_list.html',
                  {
                      'properties': properties,
                      'property_types': property_types,
                      'status_choices': status_choices,
                      'listing_type_choices': listing_type_choices,
                      'selected_q': query,
                      'selected_type': ptype,
                      'selected_status': status,
                      'selected_listing_type': listing_type,
                      'selected_min_price': min_price,
                      'selected_max_price': max_price,
                      'selected_sort': sort,
                      'total_properties': properties.count(),
                      'requested_property_ids': requested_property_ids,
                      'buy_count': buy_count,
                      'rent_count': rent_count,
                      'lease_count': lease_count,
                      'sold_count': sold_count,
                  })


# ======================
# PROPERTY ADD
# ======================
@login_required
def property_add(request):
    if not request.user.is_staff:
        return HttpResponseForbidden("Not allowed")

    agents = User.objects.filter(is_staff=True)

    def to_int(val):
        return int(val) if val not in (None, "") else None

    if request.method == "POST":
        assigned_to_id = request.POST.get("assigned_to") or None
        assigned_to = User.objects.filter(id=assigned_to_id).first() if assigned_to_id else None

        prop = Property.objects.create(
            title=request.POST.get("title"),
            property_type=request.POST.get("property_type"),
            price=request.POST.get("price"),
            bedrooms=to_int(request.POST.get("bedrooms")),
            bathrooms=to_int(request.POST.get("bathrooms")),
            area=to_int(request.POST.get("area")),
            location=request.POST.get("location"),
            listing_type=request.POST.get("listing_type") or "buy",
            status=request.POST.get("status") or "available",
            assigned_to=assigned_to,
            image=request.FILES.get("image"),
        )

        for f in request.FILES.getlist("gallery"):
            PropertyImage.objects.create(property=prop, image=f)

        return redirect("property-detail", pk=prop.id)

    return render(request, "properties/property_form.html", {"agents": agents})


# ======================
# PROPERTY DETAIL
# ======================
@login_required
def property_detail(request, pk):
    prop = get_object_or_404(Property, pk=pk)
    has_requested = False

    if not request.user.is_staff:
        lead_filter = Q()
        if request.user.email:
            lead_filter |= Q(email=request.user.email)
        lead_filter |= Q(name=request.user.get_full_name() or request.user.username)

        has_requested = Lead.objects.filter(lead_filter, property=prop).exists()

    return render(request,
                  "properties/property_detail.html",
                  {"property": prop, "has_requested": has_requested})


# ======================
# PROPERTY ENQUIRY
# ======================
@login_required
def property_enquiry(request, pk):
    property_obj = get_object_or_404(Property, pk=pk)

    if request.user.is_staff:
        return redirect("property-detail", pk=pk)
    if property_obj.status == "sold":
        return redirect("property-detail", pk=pk)

    profile, _ = Profile.objects.get_or_create(user=request.user)

    email = (request.user.email or "").strip()
    phone = (profile.phone or "").strip()
    address = (profile.address or "").strip()

    def _valid_identity(value):
        v = (value or "").strip().lower()
        return v not in {"", "not provided", "na", "n/a", "none", "null"}

    # Fallback to best lead details if profile is incomplete
    if not _valid_identity(phone) or not _valid_identity(address):
        lead_by_email = Lead.objects.filter(email=email).order_by("-created_at") if email else Lead.objects.none()

        if not _valid_identity(phone):
            phone_lead = lead_by_email.exclude(phone__in=["", "Not Provided"]).exclude(phone__isnull=True).first()
            if phone_lead:
                phone = (phone_lead.phone or "").strip()

        if not _valid_identity(address):
            addr_lead = lead_by_email.exclude(address__in=["", "Not Provided"]).exclude(address__isnull=True).first()
            if addr_lead:
                address = (addr_lead.address or "").strip()

    # Avoid duplicate leads for the same customer/property
    lead = Lead.objects.filter(email=email, property=property_obj).first() if _valid_identity(email) else None

    if lead is None and _valid_identity(email):
        # Reuse the most recent lead created at registration (no property yet)
        reg_lead = Lead.objects.filter(email=email, property__isnull=True).order_by('-created_at').first()
        if reg_lead and (_valid_identity(reg_lead.phone) or _valid_identity(reg_lead.address)):
            lead = reg_lead

    if lead:
        # Auto-mark returning if customer had prior leads
        q = Q()
        if _valid_identity(email):
            q |= Q(email=email)
        if _valid_identity(phone):
            q |= Q(phone=phone)
        has_previous = Lead.objects.filter(q).exclude(id=lead.id).exists() if q else False
        if has_previous and lead.status != "closed":
            lead.status = "returning"
        lead.name = request.user.get_full_name() or request.user.username
        # Prefer profile data if present; otherwise keep existing lead values
        lead.phone = phone if _valid_identity(phone) else (lead.phone if _valid_identity(lead.phone) else "Not Provided")
        lead.email = email if _valid_identity(email) else (lead.email or "")
        lead.address = address if _valid_identity(address) else (lead.address if _valid_identity(lead.address) else "Not Provided")
        lead.source = "Website"
        lead.property = property_obj
        lead.assigned_to = property_obj.assigned_to
        lead.save()
    else:
        q = Q()
        if _valid_identity(email):
            q |= Q(email=email)
        if _valid_identity(phone):
            q |= Q(phone=phone)
        prior = Lead.objects.filter(q).exists() if q else False
        status = "returning" if prior else "fresh"
        Lead.objects.create(
            name=request.user.get_full_name() or request.user.username,
            phone=phone if _valid_identity(phone) else "Not Provided",
            email=email if _valid_identity(email) else "",
            address=address if _valid_identity(address) else "Not Provided",
            source="Website",
            property=property_obj,
            assigned_to=property_obj.assigned_to,
            status=status,
        )

    return redirect("property-detail", pk=pk)

@login_required
def property_edit(request, pk):
    prop = get_object_or_404(Property, pk=pk)

    if not request.user.is_staff:
        return HttpResponseForbidden("Not allowed")

    def to_int(val):
        return int(val) if val not in (None, "") else None

    if request.method == "POST":
        prop.title = request.POST.get("title") or prop.title
        prop.property_type = request.POST.get("property_type") or prop.property_type

        price = request.POST.get("price")
        if price:
            prop.price = price

        prop.bedrooms = to_int(request.POST.get("bedrooms"))
        prop.bathrooms = to_int(request.POST.get("bathrooms"))
        prop.area = to_int(request.POST.get("area"))

        prop.location = request.POST.get("location") or prop.location
        prop.listing_type = request.POST.get("listing_type") or prop.listing_type
        prop.status = request.POST.get("status") or prop.status

        if request.FILES.get("image"):
            prop.image = request.FILES["image"]

        prop.save()

        if prop.status == "sold":
            selected_lead_id = (request.POST.get("buyer_lead_id") or "").strip()
            selected_lead = None
            if selected_lead_id:
                selected_lead = Lead.objects.filter(id=selected_lead_id, property=prop).first()

            buyer_name = (request.POST.get("buyer_name") or "").strip()
            buyer_phone = (request.POST.get("buyer_phone") or "").strip()
            buyer_email = (request.POST.get("buyer_email") or "").strip()

            if selected_lead:
                buyer_name = buyer_name or (selected_lead.name or "")
                buyer_phone = buyer_phone or (selected_lead.phone or "")
                buyer_email = buyer_email or (selected_lead.email or "")

            sold_price = request.POST.get("sold_price")
            if buyer_name and sold_price:
                sale_obj = PropertySale.objects.filter(property=prop).first()
                if not sale_obj:
                    sale_obj = PropertySale(property=prop)
                sale_obj.buyer_lead = selected_lead
                sale_obj.buyer_name = buyer_name
                sale_obj.buyer_phone = buyer_phone
                sale_obj.buyer_email = buyer_email
                sale_obj.sold_price = sold_price
                sale_obj.sold_on = request.POST.get("sold_on") or None
                sale_obj.notes = (request.POST.get("sale_notes") or "").strip()
                sale_obj.save()

        for f in request.FILES.getlist("gallery"):
            PropertyImage.objects.create(property=prop, image=f)

        return redirect("property-detail", pk=pk)

    interested_leads = Lead.objects.filter(property=prop).order_by("-created_at")
    return render(
        request,
        "properties/property_edit.html",
        {
            "property": prop,
            "sale_info": getattr(prop, "sale_info", None),
            "interested_leads": interested_leads,
        },
    )

@login_required
def property_delete(request, pk):
    prop = get_object_or_404(Property, pk=pk)

    if not request.user.is_staff:
        return HttpResponseForbidden("Not allowed")

    prop.delete()
    return redirect("property-list")
