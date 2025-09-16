from django.contrib import admin
from .models import Route, Train, Ticket

admin.site.register(Route)
admin.site.register(Train)
admin.site.register(Ticket)
