from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    linkedin_id = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=100)
    first_name = models.CharField(max_length=80, blank=True)  # Add this line
    last_name = models.CharField(max_length=60, blank=True)
    email = models.EmailField(null=True, blank=True)
    linkedin_profile_picture = models.URLField(max_length=500, null=True, blank=True)
    unimad_profile_picture = models.URLField(max_length=500, null=True, blank=True)
    linkedin_access_token = models.CharField(max_length=512, blank=True, null=True)
    linkedin_access_token_expiry = models.DateTimeField(null=True, blank=True)
    preferred_name = models.CharField(max_length=100, null=True, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)

class UnibotHistory(models.Model):
    user = models.ForeignKey('UserProfile', on_delete=models.CASCADE)
    section_name = models.CharField(max_length=100)
    user_message = models.TextField()  # This stores the actual detailed prompt used for LLM
    displayed_user_message = models.TextField(default="")  # This stores the original user input
    bot_response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    response_tokens = models.IntegerField()  # Renamed from prompt_tokens to response_tokens
    total_tokens = models.IntegerField()
    message_tokens = models.IntegerField()