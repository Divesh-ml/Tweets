from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.contrib.auth.urls import views as auth_views
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('tweet/', include('tweet.urls')), 
    path('accounts/',include('django.contrib.auth.urls')),

]

def serve_media(request, path):
    return serve(request, path, document_root=settings.MEDIA_ROOT)


urlpatterns += [
    path('media/<path:path>', serve_media),
]