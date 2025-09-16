from django.http import JsonResponse
from django.shortcuts import render, redirect
from .models import Train, Ticket, Route
from django.views.decorators.csrf import csrf_exempt

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
    
    if request.method == "POST":
        passenger = request.POST.get("passengername")
        seats_requested = int(request.POST.get("seats", 1))
        category = request.POST.get("category", "ALL")
        
        if seats_requested > 6:
            if request.headers.get('Accept') == 'application/json':
                return JsonResponse({"error": "Max 6 tickets allowed"}, status=400)
            return render(request, 'tickets/book.html', {'train': train, 'error': 'Maximum 6 tickets allowed'})
        
        available = train.availableseats
        if seats_requested <= available:
            confirmed = seats_requested
            waitlist = 0
            train.availableseats -= seats_requested
            status_val = "CONFIRMED"
        else:
            confirmed = available
            waitlist = seats_requested - available
            train.availableseats = 0
            status_val = "WAITLIST" if confirmed == 0 else "CONFIRMED"
        
        train.save()
        Ticket.objects.create(
            train=train,
            passengername=passenger,
            category=category,
            seatsbooked=seats_requested,
            confirmedseats=confirmed,
            waitlistseats=waitlist,
            status=status_val
        )
        
        booking_data = {
            "train": train.trainname,
            "passenger": passenger,
            "requested": seats_requested,
            "confirmed": confirmed,
            "waitlist": waitlist,
            "updated_availableseats": train.availableseats
        }
        
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse(booking_data)
        
        return render(request, 'tickets/book.html', {
            'train': train, 
            'success': True, 
            'booking': booking_data
        })
    
    return render(request, 'tickets/book.html', {'train': train})

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
            return JsonResponse({"message": f"Seats increased, now available: {train.availableseats}"})
        except Train.DoesNotExist:
            return JsonResponse({"error": "Train not found"}, status=404)
    else:
        return JsonResponse({"msg": "POST extra=<seats_to_increase>"})

@csrf_exempt
def view_all_trains(request):
    trains = Train.objects.all()
    return render(request, 'tickets/all_trains.html', {'trains': trains})
