from django.urls import path

from . import views

app_name = 'about'

urlpatterns = [
    path('author/', views.Author.as_view(), name='author'),
    path('tech/', views.Technologies.as_view(), name='tech')
]
