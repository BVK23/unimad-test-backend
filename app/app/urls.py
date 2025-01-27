"""
URL configuration for app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, re_path
from django.views.generic import RedirectView
from unimadapp import views
from django.conf import settings
from django.conf.urls.static import static  # Import the static function here
from django.templatetags.static import static as static_tag


urlpatterns = [
    path('admin/', admin.site.urls),

    path('_ah/warmup', views.warmup, name='warmup'),
    path('linkedin-login/', views.linkedin_login, name='linkedin_login'),
    path('linkedin-callback/', views.linkedin_callback, name='linkedin_callback'),        
    # path('signup/', views.signup_form, name='signup_form'),
    # path('complete-signup/', views.complete_signup, name='complete_signup'),
    path('logout/', views.logout_user, name='logout'),

    path('api/token/refresh/', views.CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('api/user-data/', views.get_user_data, name='get_user_data'),

   
    path('api/profile-data/', views.get_profile_data, name='get_profile_data'),
  
    path('api/unibot-api/', views.unibot_api, name='unibot_api'),
    path('api/unibot-api-stream/', views.unibot_api_stream, name='unibot_api_stream'),
    path('api/unibot-history/', views.unibot_history, name='unibot_history'),

    re_path(r'^favicon\.ico$', RedirectView.as_view(url=static_tag('favicon.ico'), permanent=True)),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
