from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.db import OperationalError
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .forms import IntervalForm, SearchForm
from .models import Equipment, Reservation
from .services import conflicts, request_reservation, review_reservation

@login_required
def catalog(request):
    form = SearchForm(request.GET or None)
    items = Equipment.objects.filter(is_active=True)
    if request.GET:
        if form.is_valid():
            data = form.cleaned_data
            items = items.filter(Q(name__icontains=data["q"]) | Q(category__icontains=data["q"]))
            for item in items:
                item.available = not conflicts(item, data["start"], data["end"]).exists()
        else:
            items = []
    return render(request, "inventory/catalog.html", {"form": form, "items": items})

@login_required
def reserve(request, pk):
    item = get_object_or_404(Equipment, pk=pk, is_active=True)
    form = IntervalForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            request_reservation(request.user, item.pk, **form.cleaned_data)
        except ValidationError as exc:
            form.add_error(None, exc)
        except OperationalError:
            form.add_error(None, "Database is busy. Please retry.")
        else:
            messages.success(request, "Your reservation request is pending review.")
            return redirect("my_reservations")
    return render(request, "inventory/reserve.html", {"form": form, "item": item})

@login_required
def my_reservations(request):
    rows = Reservation.objects.filter(borrower=request.user).select_related("equipment")
    return render(request, "inventory/reservations.html", {"rows": rows})

@login_required
@permission_required("inventory.review_reservation", raise_exception=True)
def review_queue(request):
    rows = Reservation.objects.select_related("equipment", "borrower")
    return render(request, "inventory/reservations.html", {"rows": rows, "review": True})

@login_required
@permission_required("inventory.review_reservation", raise_exception=True)
@require_POST
def decide(request, pk):
    try:
        review_reservation(request.user, pk, request.POST.get("decision"))
    except Reservation.DoesNotExist:
        raise Http404
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    except OperationalError:
        messages.error(request, "Database is busy. No approval was completed; retry.")
    else:
        messages.success(request, "Reservation decision saved.")
    return redirect("review_queue")
