from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    # Default route
    path('', views.index, name='home'),

    path('test_mongo/', views.test_mongo, name='test_mongo'),

    path('index/', views.index, name='index'),
    path('index/index.html', views.index, name='index'),

    # path('index/about.html', views.about, name='about'),
    # path('index/signin.html', views.signin, name='signin'),
    # path('index/signup.html', views.signup, name='signup'),

    path('signup/', views.signup, name='signup'),
    path('signin/', views.signin, name='signin'),
    path('about/', views.about, name='about'),

    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/dashboard.html', views.dashboard, name='dashboard'),
    path('dashboard/chat.html', views.chat, name='chat'),
    path('dashboard/quiz.html', views.quiz, name='quiz'),

    path('google_signin/', views.google_signin, name='google_signin'),

    # Chatbot endpoints
    path('getResponse/', views.getResponse, name='getResponse'),
    path('getChatHistory/', views.getChatHistory, name='getChatHistory'),

    # Quiz endpoints
    path('generate_quiz/', views.generate_quiz, name='generate_quiz'),
    path('save_quiz_result/', views.save_quiz_result, name='save_quiz_result'),

    # Roadmap endpoints
    path('dashboard/roadmap.html/', views.roadmap, name='roadmap'),

    path('generate_roadmap/', views.generate_roadmap, name='generate_roadmap'),
    path('get_user_roadmaps/', views.get_user_roadmaps, name='get_user_roadmaps'),
    path('save_roadmap_progress/', views.save_roadmap_progress, name='save_roadmap_progress'),
    path('delete_roadmap/', views.delete_roadmap, name='delete_roadmap'),

    path('get_roadmap_details/<str:uuid>/', views.get_roadmap_details, name='get_roadmap_details'),
]