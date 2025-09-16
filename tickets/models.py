from django.db import models

class Route(models.Model):
    startcity = models.CharField(max_length=100)
    endcity = models.CharField(max_length=100)
    def __str__(self):
        return f"{self.startcity} to {self.endcity}"

class Train(models.Model):
    trainname = models.CharField(max_length=100)
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    totalseats = models.IntegerField()
    availableseats = models.IntegerField()
    def __str__(self):
        return f"{self.trainname} {self.route}"

class Ticket(models.Model):
    CATEGORY_CHOICES = [
        ("ALL", "All"),
        ("LADIES", "Ladies"),
        ("SENIOR", "Senior Citizen"),
    ]
    STATUS_CHOICES = [
        ("CONFIRMED", "Confirmed"),
        ("WAITLIST", "Waitlist"),
    ]
    train = models.ForeignKey(Train, on_delete=models.CASCADE)
    passengername = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="ALL")
    seatsbooked = models.IntegerField()
    confirmedseats = models.IntegerField(default=0)
    waitlistseats = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="CONFIRMED")
    bookedat = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"{self.passengername} - {self.train.trainname} - {self.status}"
