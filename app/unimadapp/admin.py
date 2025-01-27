from django.contrib import admin
from .models import UserProfile, UnibotHistory, User
from import_export import resources
from import_export.admin import ImportExportModelAdmin

# Register your models here.

class UserProfileResource(resources.ModelResource):
    class Meta:
        model = UserProfile

class UserProfileAdmin(ImportExportModelAdmin):
    resource_class = UserProfileResource
    list_display = ('user', 'name', 'email', 'joined_at')
    search_fields = ('name', 'email', 'first_name', 'last_name')

class UnibotHistoryResource(resources.ModelResource):
    class Meta:
        model = UnibotHistory

class UnibotHistoryAdmin(ImportExportModelAdmin):
    resource_class = UnibotHistoryResource
    list_display = ('user', 'section_name', 'user_message', 'bot_response', 'created_at', 'total_tokens')
    list_filter = ('user', 'section_name')
    search_fields = ('user__name', 'user__email', 'section_name')


# Register models in the Django admin
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(UnibotHistory, UnibotHistoryAdmin)

# Register the User model with the custom admin
admin.site.unregister(User)  # Unregister the default User admin