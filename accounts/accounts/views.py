from django.shortcuts import render, redirect
from django.http import HttpResponseForbidden
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db.models import Count, Prefetch

from .models import Profile
from leads.models import Lead
from properties.models import Property
from django.db.models import Q


# =========================
# LOGIN
# =========================
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        login_name = username
        if username and "@" in username:
            user_by_email = User.objects.filter(email=username).first()
            if user_by_email:
                login_name = user_by_email.username

        user = authenticate(request,
                            username=login_name,
                            password=password)

        if user:
            login(request, user)

            # ensure profile exists
            profile, _ = Profile.objects.get_or_create(user=user)
            if not profile.phone or not profile.address:
                lead_by_email = None
                if user.email:
                    lead_by_email = Lead.objects.filter(email=user.email).order_by("-created_at")

                if not profile.phone and lead_by_email:
                    phone_lead = lead_by_email.exclude(phone__in=["", "Not Provided"]).exclude(phone__isnull=True).first()
                    if phone_lead:
                        profile.phone = phone_lead.phone

                if not profile.address and lead_by_email:
                    addr_lead = lead_by_email.exclude(address__in=["", "Not Provided"]).exclude(address__isnull=True).first()
                    if addr_lead:
                        profile.address = addr_lead.address

                if profile.phone or profile.address:
                    profile.save()

            if user.is_staff:
                return redirect("dashboard")
            return redirect("property-list")
        else:
            return render(request, "accounts/login.html", {
                "error": "Invalid username/email or password",
                "form": {"username": username},
            })

    return render(request, "accounts/login.html")


# =========================
# LOGOUT
# =========================
def logout_view(request):
    logout(request)
    return redirect("login")


# =========================
# CUSTOMER REGISTER
# =========================
def customer_register(request):

    if request.method == "POST":
        full_name = request.POST.get("full_name")
        phone = request.POST.get("phone")
        email = request.POST.get("email")
        city = request.POST.get("city")
        address = request.POST.get("address")
        username = request.POST.get("username")
        password = request.POST.get("password")

        if User.objects.filter(username=username).exists():
            return render(request, "accounts/customer_register.html", {
                "error": "Username already exists",
                "form": {
                    "full_name": full_name,
                    "phone": phone,
                    "email": email,
                    "city": city,
                    "address": address,
                    "username": username,
                }
            })

        # basic required field validation
        if not username or not password:
            return render(request, "accounts/customer_register.html", {
                "error": "Username and password are required",
                "form": {
                    "full_name": full_name,
                    "phone": phone,
                    "email": email,
                    "city": city,
                    "address": address,
                    "username": username,
                }
            })

        # create user
        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=full_name
        )

        # create or update profile safely
        profile, _ = Profile.objects.get_or_create(user=user)

        profile.full_name = full_name
        profile.phone = phone
        profile.city = city
        profile.address = address
        profile.save()

        # Create a lead for this new customer so admin can see full details
        Lead.objects.create(
            name=full_name or username,
            phone=phone or "Not Provided",
            email=email,
            address=address or "Not Provided",
            source="Website",
            assigned_to=None
        )

        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect("property-list")

    return render(request, "accounts/customer_register.html")


# =========================
# AGENT CREATE (ADMIN ONLY)
# =========================
@login_required
def agent_create(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Not allowed")

    if request.method == "POST":
        full_name = request.POST.get("full_name")
        phone = request.POST.get("phone")
        email = request.POST.get("email")
        city = request.POST.get("city")
        address = request.POST.get("address")
        specialization = request.POST.get("specialization")
        property_id = request.POST.get("property_id")
        username = request.POST.get("username")
        password = request.POST.get("password")

        properties = Property.objects.all()

        if User.objects.filter(username=username).exists():
            return render(request, "accounts/agent_create.html", {
                "error": "Username already exists",
                "form": {
                    "full_name": full_name,
                    "phone": phone,
                    "email": email,
                    "city": city,
                    "address": address,
                    "specialization": specialization,
                    "username": username,
                    "property_id": property_id,
                },
                "properties": properties,
            })

        if not username or not password:
            return render(request, "accounts/agent_create.html", {
                "error": "Username and password are required",
                "form": {
                    "full_name": full_name,
                    "phone": phone,
                    "email": email,
                    "city": city,
                    "address": address,
                    "specialization": specialization,
                    "username": username,
                    "property_id": property_id,
                }
                ,
                "properties": properties,
            })

        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=full_name
        )
        user.is_staff = True
        user.save()

        profile, _ = Profile.objects.get_or_create(user=user)
        profile.full_name = full_name
        profile.phone = phone
        profile.email = email
        profile.city = city
        profile.address = address
        profile.specialization = specialization
        profile.save()

        # Assign agent to a specific property if provided
        if property_id:
            prop = Property.objects.filter(id=property_id).first()
            if prop:
                prop.assigned_to = user
                prop.save()

        return redirect("agent-create")

    properties = Property.objects.all()
    return render(request, "accounts/agent_create.html", {"properties": properties})


@login_required
def agent_list(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Not allowed")

    leads_qs = Lead.objects.select_related("property").order_by("-created_at")
    agents = (
        User.objects.filter(is_staff=True, is_superuser=False)
        .select_related("profile")
        .prefetch_related(Prefetch("leads", queryset=leads_qs))
        .prefetch_related(Prefetch("property_set", queryset=Property.objects.order_by("title")))
        .annotate(total_leads=Count("leads"))
        .order_by("username")
    )

    admin_assigned_properties = Property.objects.filter(assigned_to=request.user).order_by("title")

    return render(
        request,
        "accounts/agent_list.html",
        {
            "agents": agents,
            "admin_assigned_properties": admin_assigned_properties,
        },
    )


@login_required
def agent_assign_property(request, agent_id):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Not allowed")

    agent = User.objects.filter(id=agent_id, is_staff=True, is_superuser=False).select_related("profile").first()
    if not agent:
        return redirect("agent-list")

    all_properties = Property.objects.select_related("assigned_to").order_by("title")
    assigned_properties = Property.objects.filter(assigned_to=agent).order_by("title")

    if request.method == "POST":
        property_id = request.POST.get("property_id")
        action = request.POST.get("action")
        prop = Property.objects.filter(id=property_id).first()
        if prop and action == "assign":
            prop.assigned_to = agent
            prop.save(update_fields=["assigned_to"])
        elif prop and action == "remove" and prop.assigned_to_id == agent.id:
            prop.assigned_to = None
            prop.save(update_fields=["assigned_to"])
        return redirect("agent-list")

    return render(
        request,
        "accounts/agent_assign_property.html",
        {
            "agent": agent,
            "properties": all_properties,
            "assigned_properties": assigned_properties,
        },
    )

