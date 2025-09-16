from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("search/", views.search_trains, name="search_trains"),
    path("book/<int:trainid>/", views.book_ticket, name="book_ticket"),
    path("history/", views.booking_history, name="booking_history"),
    path("admin-panel/", views.admin_panel, name="admin_panel"),  # Custom admin panel
    path("add-train/", views.add_train, name="add_train"),
    path("cancel-train/<int:trainid>/", views.cancel_train, name="cancel_train"),
    path("increase-seats/<int:trainid>/", views.increase_seats, name="increase_seats"),
]
