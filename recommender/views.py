from django.shortcuts import render
from django.http import JsonResponse
from .forms import CropInputForm
from .ml.loader import predict_one, load_bundle
# recommender/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Prediction, UserProfile

# recommender/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q

from .models import Prediction, UserProfile
from .ml.loader import predict_one, load_bundle


def home(request):
    context = {
        "total_users": User.objects.filter(is_staff=False).count(),
        "total_predictions": Prediction.objects.count(),
    }
    return render(request, "public/home.html", context)


# ---------- helpers ----------
def _resolve_username(login_str: str) -> str:
    """
    Allow login with email or username.
    If an email matches a user, return its username, else return input as-is.
    """
    login_str = (login_str or "").strip()
    if "@" in login_str:
        try:
            u = User.objects.get(email__iexact=login_str)
            return u.username
        except User.DoesNotExist:
            return login_str
    return login_str


def is_staff(user):
    return user.is_authenticated and user.is_staff


# ---------- Auth (user) ----------
def signup_view(request):
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        phone = (request.POST.get("phone") or "").strip()
        email = (request.POST.get("email") or "").strip().lower()
        password = request.POST.get("password") or ""

        # basic validations
        if not name or not email or not password:
            messages.error(request, "Please fill all required fields.")
            return redirect("signup")
        if len(password) < 6:
            messages.error(request, "Password should be at least 6 characters.")
            return redirect("signup")
        if User.objects.filter(Q(username__iexact=email) | Q(email__iexact=email)).exists():
            messages.error(request, "Account already exists with this email.")
            return redirect("signup")

        # create user (email as username)
        user = User.objects.create_user(username=email, email=email, password=password)
        if " " in name:
            first, last = name.split(" ", 1)
        else:
            first, last = name, ""
        user.first_name, user.last_name = first, last
        user.save()

        # create profile
        UserProfile.objects.create(user=user, phone=phone)

        # login and go to predict
        login(request, user)
        messages.success(request, "Account created successfully. Welcome!")
        return redirect("predict")

    return render(request, "auth/signup.html")


def login_view(request):
    if request.method == "POST":
        username_or_email = request.POST.get("username") or ""
        password = request.POST.get("password") or ""

        resolved_username = _resolve_username(username_or_email)
        user = authenticate(request, username=resolved_username, password=password)
        if not user:
            messages.error(request, "Invalid credentials.")
            return redirect("login")

        login(request, user)
        if user.is_staff:
            messages.success(request, f"Welcome admin {user.username}!")
            return redirect("admin_dashboard")
        messages.success(request, "Logged in successfully.")
        return redirect("predict")

    return render(request, "auth/login.html")


def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect("login")


# ---------- User area ----------
# @login_required
# def predict_view(request):
#     feature_order = load_bundle()["feature_cols"]
#     result = None

#     if request.method == "POST":
#         # read numeric inputs safely
#         data = {}
#         try:
#             for c in feature_order:
#                 data[c] = float(request.POST.get(c, ""))
#         except ValueError:
#             messages.error(request, "Please enter valid numeric values.")
#             return redirect("predict")

#         # predict & save
#         label = predict_one(data)
#         Prediction.objects.create(
#             user=request.user,
#             predicted_label=label,
#             **data
#         )
#         result = label
#         messages.success(request, f"Recommended Crop: {label.title()}")

#     return render(request, "user/predict.html", {
#         "feature_order": feature_order,
#         "result": result
#     })


@login_required
def predict_view(request):
    feature_order = load_bundle()["feature_cols"]
    result = None
    last_data = None

    if request.method == "POST":
        data = {}
        try:
            for c in feature_order:
                data[c] = float(request.POST.get(c, ""))
        except ValueError:
            messages.error(request, "Please enter valid numeric values.")
            return redirect("predict")

        label = predict_one(data)
        Prediction.objects.create(user=request.user, predicted_label=label, **data)
        result = label
        last_data = data
        messages.success(request, f"Recommended Crop: {label.title()}")

    return render(request, "user/predict.html", {
        "feature_order": feature_order,
        "result": result,
        "last_data": last_data
    })



@login_required
def user_history_view(request):
    items = Prediction.objects.filter(user=request.user)
    return render(request, "user/history.html", {"items": items})

@login_required
def user_delete_prediction(request, pk):
    from django.shortcuts import get_object_or_404
    if request.method != "POST":
        messages.error(request, "Invalid request.")
        return redirect("user_history")
    it = get_object_or_404(Prediction, pk=pk, user=request.user)
    it.delete()
    messages.success(request, "Entry removed from history.")
    return redirect("user_history")


@login_required
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        phone = (request.POST.get("phone") or "").strip()
        if name:
            parts = name.split(" ", 1)
            request.user.first_name = parts[0]
            request.user.last_name = parts[1] if len(parts) > 1 else ""
        profile.phone = phone
        request.user.save()
        profile.save()
        messages.success(request, "Profile updated.")
        return redirect("profile")

    full_name = request.user.get_full_name() or request.user.username
    from .models import Prediction
    pred_count = Prediction.objects.filter(user=request.user).count()
    last_pred = Prediction.objects.filter(user=request.user).order_by('-created_at').first()

    return render(request, "user/profile.html", {
        "profile": profile,
        "full_name": full_name,
        "pred_count": pred_count,
        "last_pred": last_pred,
    })



@login_required
def change_password_view(request):
    if request.method == "POST":
        current = request.POST.get("current_password") or ""
        new = request.POST.get("new_password") or ""
        confirm = request.POST.get("confirm_password") or ""

        if not request.user.check_password(current):
            messages.error(request, "Current password is incorrect.")
            return redirect("change_password")
        if len(new) < 6:
            messages.error(request, "New password must be at least 6 characters.")
            return redirect("change_password")
        if new != confirm:
            messages.error(request, "New passwords do not match.")
            return redirect("change_password")

        request.user.set_password(new)
        request.user.save()
        # keep user logged in
        user = authenticate(request, username=request.user.username, password=new)
        if user:
            login(request, user)
        messages.success(request, "Password changed successfully.")
        return redirect("profile")

    return render(request, "user/change_password.html")


# ---------- Admin area ----------
def admin_login_view(request):
    if request.method == "POST":
        username_or_email = request.POST.get("username") or ""
        password = request.POST.get("password") or ""

        resolved_username = _resolve_username(username_or_email)
        user = authenticate(request, username=resolved_username, password=password)
        if not user:
            messages.error(request, "Invalid credentials.")
            return redirect("admin_login")
        if not user.is_staff:
            messages.error(request, "You are not authorized for admin panel.")
            return redirect("admin_login")

        login(request, user)
        messages.success(request, f"Welcome admin {user.username}!")
        return redirect("admin_dashboard")

    return render(request, "adminx/admin_login.html")


@user_passes_test(is_staff, login_url='admin_login')
def admin_dashboard_view(request):
    from django.db.models import Count
    from django.utils import timezone
    import json
    from datetime import timedelta

    total_users = User.objects.filter(is_staff=False).count()
    total_predictions = Prediction.objects.count()

    # Top 10 crops
    crop_qs = (
        Prediction.objects.values('predicted_label')
        .annotate(c=Count('id'))
        .order_by('-c')[:10]
    )
    crop_labels = [r['predicted_label'].title() for r in crop_qs]
    crop_counts = [r['c'] for r in crop_qs]

    # Last 7 days counts
    today = timezone.localdate()
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    day_labels = [d.strftime("%d %b") for d in days]
    day_counts = [
        Prediction.objects.filter(created_at__date=d).count() for d in days
    ]

    context = {
        "total_users": total_users,
        "total_predictions": total_predictions,
        "crop_labels_json": json.dumps(crop_labels),
        "crop_counts_json": json.dumps(crop_counts),
        "day_labels_json": json.dumps(day_labels),
        "day_counts_json": json.dumps(day_counts),
    }
    return render(request, "adminx/dashboard.html", context)



@user_passes_test(is_staff, login_url='admin_login')
def admin_users_view(request):
    users = User.objects.filter(is_staff=False).select_related()
    return render(request, "adminx/users.html", {"users": users})


@user_passes_test(is_staff, login_url='admin_login')
def admin_predictions_view(request):
    from django.utils.dateparse import parse_date
    qs = Prediction.objects.select_related('user')

    # filters
    crop  = (request.GET.get('crop') or '').strip()
    start = (request.GET.get('start') or '').strip()
    end   = (request.GET.get('end') or '').strip()

    if crop:
        qs = qs.filter(predicted_label__iexact=crop)

    d_start = parse_date(start) if start else None
    d_end   = parse_date(end) if end else None
    if d_start:
        qs = qs.filter(created_at__date__gte=d_start)
    if d_end:
        qs = qs.filter(created_at__date__lte=d_end)

    # list of crops for dropdown
    crops = (Prediction.objects
             .order_by('predicted_label')
             .values_list('predicted_label', flat=True).distinct())

    context = {
        "items": qs.order_by('-created_at'),
        "crops": crops,
        "current_crop": crop,
        "start": start,
        "end": end,
    }
    return render(request, "adminx/predictions.html", context)



# ---------- JSON API (as before) ----------
from django.http import JsonResponse
def predict_api(request):
    try:
        params = {k: request.GET.get(k, None) or request.POST.get(k, None)
                  for k in load_bundle()["feature_cols"]}
        if any(v is None for v in params.values()):
            return JsonResponse({"error": "Missing parameters"}, status=400)
        pred = predict_one(params)
        return JsonResponse({"prediction": pred})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    

@user_passes_test(is_staff, login_url='admin_login')
def admin_delete_user(request, user_id):
    from django.shortcuts import get_object_or_404
    if request.method != "POST":
        messages.error(request, "Invalid request.")
        return redirect("admin_users")

    target = get_object_or_404(User, id=user_id)
    if target.is_staff:
        messages.error(request, "Cannot delete staff/admin accounts.")
        return redirect("admin_users")
    if target == request.user:
        messages.error(request, "You cannot delete your own account from here.")
        return redirect("admin_users")

    target.delete()  # cascades Prediction via FK
    messages.success(request, "User deleted.")
    return redirect("admin_users")


@user_passes_test(is_staff, login_url='admin_login')
def admin_delete_prediction(request, pk):
    from django.shortcuts import get_object_or_404
    if request.method != "POST":
        messages.error(request, "Invalid request.")
        return redirect("admin_predictions")

    pred = get_object_or_404(Prediction, pk=pk)
    pred.delete()
    messages.success(request, "Prediction deleted.")
    return redirect("admin_predictions")


import csv
from django.http import HttpResponse

@login_required
def user_history_export_csv(request):
    # filename with username for clarity
    filename = f"predictions_{request.user.username}.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    headers = ["created_at", "predicted_label", "N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
    writer.writerow(headers)

    qs = Prediction.objects.filter(user=request.user).order_by('-created_at')
    for it in qs:
        writer.writerow([
            it.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            it.predicted_label,
            it.N, it.P, it.K,
            it.temperature, it.humidity, it.ph, it.rainfall
        ])
    return response


from django.contrib.auth.decorators import user_passes_test

@user_passes_test(is_staff, login_url='admin_login')
def admin_export_users_csv(request):
    import csv
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="users.csv"'
    w = csv.writer(response)
    w.writerow(["id", "name", "email", "phone", "date_joined", "is_staff"])
    qs = User.objects.all().select_related().order_by('id')
    for u in qs:
        phone = getattr(getattr(u, 'userprofile', None), 'phone', '')
        w.writerow([u.id, u.get_full_name() or u.username, u.email, phone,
                    u.date_joined.strftime("%Y-%m-%d %H:%M:%S"), u.is_staff])
    return response

@user_passes_test(is_staff, login_url='admin_login')
def admin_export_predictions_csv(request):
    import csv
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="predictions.csv"'
    w = csv.writer(response)
    w.writerow(["id","created_at","user_email","predicted_label","N","P","K",
                "temperature","humidity","ph","rainfall"])
    qs = Prediction.objects.select_related('user').order_by('-created_at')
    # (optional) respect same filters as table if present
    crop = (request.GET.get('crop') or '').strip()
    start = (request.GET.get('start') or '').strip()
    end   = (request.GET.get('end') or '').strip()
    from django.utils.dateparse import parse_date
    if crop:
        qs = qs.filter(predicted_label__iexact=crop)
    if start:
        d = parse_date(start)
        if d: qs = qs.filter(created_at__date__gte=d)
    if end:
        d = parse_date(end)
        if d: qs = qs.filter(created_at__date__lte=d)

    for it in qs:
        w.writerow([it.id, it.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    it.user.email, it.predicted_label,
                    it.N, it.P, it.K, it.temperature, it.humidity, it.ph, it.rainfall])
    return response 


def custom_404(request, exception):
    return render(request, '404.html', status=404)

def custom_500(request):
    return render(request, '500.html', status=500)



