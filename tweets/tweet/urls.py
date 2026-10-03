from django.urls import path
from . import views


urlpatterns = [
    path('',views.tweet_list, name='tweet_list'),
    path('following/', views.following_tweets, name='following_tweets'),
    path('people/', views.people_list, name='people_list'),
    path('users/<int:user_id>/', views.user_profile, name='user_profile'),
    path('users/<int:user_id>/follow/', views.follow_user, name='follow_user'),
    path('users/<int:user_id>/unfollow/', views.unfollow_user, name='unfollow_user'),
    path('create/',views.tweet_create, name='tweet_create'),
    path('<int:tweet_id>/reply/', views.tweet_reply, name='tweet_reply'),
    path('<int:tweet_id>/like/', views.toggle_tweet_like, name='toggle_tweet_like'),
    path('<int:tweet_id>/edit/',views.tweet_edit, name='tweet_edit'),
    path('<int:tweet_id>/delete/',views.tweet_delete, name='tweet_delete'),
    path('register/',views.register, name='register'),

]
 