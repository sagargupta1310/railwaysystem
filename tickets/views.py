from django.http import JsonResponse
from django.shortcuts import render, redirect
from .models import Train, Ticket, Route
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum

def home(request):
    return render(request, 'tickets/home.html')

def search_trains(request):
    route = request.GET.get("route", "")
    trains = []
    if route:
        trains = Train.objects.filter(route__startcity__icontains=route) | Train.objects.filter(route__endcity__icontains=route)
    # For API requests
    if request.headers.get('Accept') == 'application/json':
        out = []
        for t in trains:
            out.append({
                "id": t.id,
                "trainname": t.trainname,
                "route": str(t.route),
                "availableseats": t.availableseats,
            })
        return JsonResponse({"trains": out})
    return render(request, 'tickets/search.html', {'trains': trains})

def book_ticket(request, trainid):
    try:
        train = Train.objects.get(id=trainid)
    except Train.DoesNotExist:
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse({"error": "Train not found"}, status=404)
        return render(request, 'tickets/book.html', {'train': None})

    waiting_list_capacity = getattr(train, 'waiting_list_capacity', 10)

    available = train.availableseats
    waiting_list_count = Ticket.objects.filter(train=train).aggregate(
        total_waitlist=Sum('waitlistseats')
    )['total_waitlist'] or 0

    if request.method == "POST":
        passenger = request.POST.get("passengername")
        seats_requested = int(request.POST.get("seats", 1))
        category = request.POST.get("category", "ALL")

        if seats_requested > 6:
            if request.headers.get('Accept') == 'application/json':
                return JsonResponse({"error": "Max 6 tickets allowed"}, status=400)
            return render(request, 'tickets/book.html', {'train': train, 'error': 'Maximum 6 tickets allowed'})

        confirmed = min(seats_requested, available)
        waitlist = seats_requested - confirmed
        new_waiting_list_count = waiting_list_count + waitlist
        if available > 0:
            train.availableseats -= confirmed
        else:
            train.availableseats = 0
        train.save()
        status_val = "CONFIRMED" if confirmed > 0 and waitlist == 0 else "WAITLIST" if confirmed == 0 else "CONFIRMED"
        Ticket.objects.create(
            train=train,
            passengername=passenger,
            category=category,
            seatsbooked=seats_requested,
            confirmedseats=confirmed,
            waitlistseats=waitlist,
            status=status_val
        )
        # Updated sum after booking
        waiting_list_count = Ticket.objects.filter(train=train).aggregate(
            total_waitlist=Sum('waitlistseats')
        )['total_waitlist'] or 0
        booking_data = {
            "train": train.trainname,
            "passenger": passenger,
            "requested": seats_requested,
            "confirmed": confirmed,
            "waitlist": waitlist,
            "updated_availableseats": train.availableseats,
            "waiting_list_count": waiting_list_count
        }
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse(booking_data)
        return render(request, 'tickets/book.html', {
            'train': train,
            'success': True,
            'booking': booking_data,
            'waiting_list_count': waiting_list_count,
            'available': train.availableseats
        })

    return render(request, 'tickets/book.html', {
        'train': train,
        'waiting_list_count': waiting_list_count,
        'available': available
    })

def booking_history(request):
    passenger = request.GET.get("passengername", "")
    if passenger:
        tickets = Ticket.objects.filter(passengername__icontains=passenger)
    else:
        tickets = Ticket.objects.all()
    history = []
    for t in tickets.order_by("-bookedat"):
        history.append({
            "train": t.train.trainname,
            "route": str(t.train.route),
            "passenger": t.passengername,
            "category": t.category,
            "requested": t.seatsbooked,
            "confirmed": t.confirmedseats,
            "waitlist": t.waitlistseats,
            "status": t.status,
            "bookedat": t.bookedat,
        })
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({"history": history})
    return render(request, 'tickets/history.html', {'history': history})

def admin_panel(request):
    message = None
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "increase_seats":
            trainid = int(request.POST.get("trainid"))
            extra = int(request.POST.get("extra", 0))
            try:
                train = Train.objects.get(id=trainid)
                train.availableseats += extra
                train.totalseats += extra
                train.save()
                promote_waitlist(train)  # <--- Call helper to promote waiting list
                message = f"Seats increased for train {train.trainname}. Now available: {train.availableseats}"
            except Train.DoesNotExist:
                message = "Train not found"
        elif action == "cancel_train":
            trainid = int(request.POST.get("trainid"))
            try:
                train = Train.objects.get(id=trainid)
                train_name = train.trainname
                train.delete()
                message = f"Train {train_name} cancelled successfully"
            except Train.DoesNotExist:
                message = "Train not found"
    return render(request, 'tickets/admin_panel.html', {'message': message})

def promote_waitlist(train):
    available = train.availableseats
    if available <= 0:
        return
    waitlist_tickets = Ticket.objects.filter(train=train, status='WAITLIST').order_by('bookedat')
    for ticket in waitlist_tickets:
        if available <= 0:
            break
        to_confirm = min(ticket.waitlistseats, available)
        ticket.confirmedseats += to_confirm
        ticket.waitlistseats -= to_confirm
        available -= to_confirm
        if ticket.waitlistseats == 0:
            ticket.status = 'CONFIRMED'
        ticket.save()
    train.availableseats = available
    train.save()

@csrf_exempt
def add_train(request):
    if request.method == "POST":
        trainname = request.POST.get("trainname")
        startcity = request.POST.get("startcity")
        endcity = request.POST.get("endcity")
        totalseats = int(request.POST.get("totalseats", 100))
        route, _ = Route.objects.get_or_create(startcity=startcity, endcity=endcity)
        tr = Train.objects.create(trainname=trainname, route=route, totalseats=totalseats, availableseats=totalseats)
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse({"id": tr.id, "message": "Train added"})
        return redirect('admin_panel')
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({"msg": "POST new train with trainname, startcity, endcity, totalseats"})
    return redirect('admin_panel')

@csrf_exempt
def cancel_train(request, trainid):
    try:
        t = Train.objects.get(id=trainid)
        t.delete()
        return JsonResponse({"message": "Train cancelled"})
    except Train.DoesNotExist:
        return JsonResponse({"error": "Train not found"}, status=404)

@csrf_exempt
def increase_seats(request, trainid):
    if request.method == "POST":
        extra = int(request.POST.get("extra", 0))
        try:
            train = Train.objects.get(id=trainid)
            train.availableseats += extra
            train.totalseats += extra
            train.save()
            promote_waitlist(train)  # <--- Promote waiting list to confirmed after increasing seats
            return JsonResponse({"message": f"Seats increased, now available: {train.availableseats}"})
        except Train.DoesNotExist:
            return JsonResponse({"error": "Train not found"}, status=404)
    else:
        return JsonResponse({"msg": "POST extra=<seats_to_increase>"})

@csrf_exempt
def view_all_trains(request):
    trains = Train.objects.all()
    return render(request, 'tickets/all_trains.html', {'trains': trains})
