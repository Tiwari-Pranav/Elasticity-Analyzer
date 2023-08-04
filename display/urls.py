from django.urls import path
from . import views

urlpatterns = [
    path('', views.input_view, name='view'),
    path('results/<str:merchant>/<str:category>/', views.result_view, name='results'),
]
