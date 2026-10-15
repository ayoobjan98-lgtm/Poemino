from django.urls import path, include, re_path

from api.views import CreatePoemsAPIView, CreatePoemDetailAPIView

from .views import HomeView, AddPoemView, NotFoundPageView, PoemDetailView, PoemUpdateView, PoemDeleteView, RecentPoemsView

app_name = "MakePoem"

urlpatterns = [
    path('', HomeView.as_view(), name="home"),
    path('0.1/poems/', CreatePoemsAPIView.as_view(), name="api-poems"),
    path('0.1/poems/<int:pk>', CreatePoemDetailAPIView.as_view(), name="api-poem-detail"),

    path('add/', AddPoemView.as_view(), name="add_poem"),
    path('poem/<int:pk>/', PoemDetailView.as_view(), name='detail_poem'),
    path('poem/<int:pk>/edit/', PoemUpdateView.as_view(), name='update_poem'),
    path('poem/<int:pk>/delete/', PoemDeleteView.as_view(), name='delete_poem'),
    path('recent-poems/', RecentPoemsView.as_view(), name="recent_poems"),
    path('not-found-page/', NotFoundPageView.as_view(), name="404"),    
]
