from django.shortcuts import render
import re
import uuid
import shortuuid
from slugify import slugify
import requests
from django.conf import settings
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse, StreamingHttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth import login, logout
from urllib.parse import urlencode
# import jwt
from jwcrypto import jwt, jwk
from jwcrypto.common import json_decode
from datetime import datetime, timedelta
from django.utils import timezone
import base64
import json
from .models import User, UserProfile, UnibotHistory
from .serializers import UnibotHistorySerializer, ChatHistorySerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from rest_framework.decorators import api_view, permission_classes, parser_classes, renderer_classes
from rest_framework.parsers import JSONParser, MultiPartParser, FileUploadParser, FormParser
from rest_framework.permissions import IsAuthenticated, AllowAny

from rest_framework.views import APIView
from rest_framework.response import Response

import vertexai
from vertexai.generative_models import GenerativeModel, Content, Part
from google.cloud import storage
from google.api_core.exceptions import ResourceExhausted

from unimadapp.server_sent_event_renderer import ServerSentEventRenderer
import time

import logging
logger = logging.getLogger(__name__)

from decimal import Decimal

def warmup(request):
    # Add any warmup logic here, like warming up caches, etc.
    return HttpResponse('Warmup successful', content_type='text/plain')

def linkedin_login(request):
    state = uuid.uuid4().hex
    request.session['linkedin_auth_state'] = state

    params = {
        'response_type': 'code',
        'client_id': settings.SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY,
        'redirect_uri': request.build_absolute_uri(reverse('linkedin_callback')),
        'state': state,
        'scope': 'openid profile email w_member_social',
    }
    auth_url = 'https://www.linkedin.com/oauth/v2/authorization?' + urlencode(params)
    return HttpResponseRedirect(auth_url)

def get_access_token(code, request):
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'client_id': settings.SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY,
        'client_secret': settings.SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET,
        'redirect_uri': request.build_absolute_uri(reverse('linkedin_callback')),
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    try:
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            response = requests.post('https://www.linkedin.com/oauth/v2/accessToken', data=data, headers=headers)
            logger.info(f"LinkedIn access token response status: {response.status_code}")
            logger.info(f"LinkedIn access token response headers: {response.headers}")
            
            if response.status_code == 429:
                if attempt < max_retries - 1:
                    retry_after = int(response.headers.get('Retry-After', retry_delay))
                    logger.warning(f"Rate limited by LinkedIn (attempt {attempt + 1}/{max_retries}). Retrying in {retry_after} seconds...")
                    time.sleep(retry_after)
                    retry_delay *= 2  # Exponential backoff
                    continue
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get access token. Status: {response.status_code}, Response: {response.text}")
                raise Exception(f"Failed to get access token. Status: {response.status_code}, Response: {response.text}")
                
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while getting access token: {str(e)}")
        raise
    
# Store LinkedIn's JWKS as a constant
LINKEDIN_JWKS = {
    "keys": [{
        "kty": "RSA",
        "e": "AQAB",
        "kid": "d929668a-bab1-4c69-9598-4373149723ff",
        "n": "zm2NAknfJAdRtrFw7xDmxcO0STPFDkLeZMvi3T7nP7QsNlQUjGxZoYuocpVzGpB_ZssIfKHuzOEMYZh40VD7JcU6dX-6sBH9y1V45TzT2_XvpfGcjM-5snlAF-wMN6Sl1zf4eapyqHjixkxh8in5LAE1vyfmGkgtcRabadoU6nmqUr-smTWL-8hPWxqP2GkVmzSZ2WRrxLtxXIERMgT8MddhHsT4bE51TOWN8egdpcMngGYS2kjlp6BLVXgBmypM0KRb_pRrWCJaVXPTl7z_esqUvqs0BYN1Z6whl7ncHZgUUmf3i2SqyZy0btpyrh-lZnxM0wx9Sb1gOLRkByREiHLNy4IzLqwxv0pxRsJLQah4BKezOFcO6VXWVEO0HGZhRN-SHhLBsrHiybcMlxEODczKB4-nqDLog6xjtFJTj_LndDJwJpiZsSTWUwp0-PzbCayl8s0h--U1SPSr1ux-A9ScHUXOVfYr0wL4gfOtrx-XfD0SrO_qADb3lZ94aBastesh5_Ha4abqtltGmdDkmMG90WdaGvICsdv0c2VtrZ8QUIaOv0yjDWVocR3PEr8j3VQn3ox-LdGkPU8X-ZdQdyWytQBUtsT-e5tZqxHR8HSLcHAG60Kg0nCTE5UP6rbEyTRd2-t_ST33qkUohcn64kXl8SNB30lY1fF1_LKtFwc"
    }]
}

def decode_id_token(id_token):
    try:
        # Decode the JWT header to get the Key ID (kid)
        header_segment = id_token.split('.')[0]
        header_data = base64.urlsafe_b64decode(header_segment + '==')
        header_json = json.loads(header_data.decode('utf-8'))
        kid = header_json['kid']

        # Use the stored JWKS instead of fetching
        jwks = jwk.JWKSet.from_json(json.dumps(LINKEDIN_JWKS))
        key = jwks.get_key(kid)
        
        if not key:
            raise Exception(f"Key ID {kid} not found in stored JWKS")

        # Verify and decode the ID token
        verified_token = jwt.JWT(key=key, jwt=id_token)
        decoded_id_token = json_decode(verified_token.claims)
        
        return decoded_id_token
    except Exception as e:
        logger.error(f"Error decoding ID token: {str(e)}")
        raise

def linkedin_callback(request):
    try:
        code = request.GET.get('code')
        if not code:
            logger.error("No code parameter in LinkedIn Callback View for user trying to login")
            message = base64.b64encode("Login failed. Please try again.".encode()).decode()
            return HttpResponseRedirect(f'{settings.FRONTEND_URL}/?error=auth_required&message={message}')

        state = request.GET.get('state')
        stored_state = request.session.get('linkedin_auth_state')

        # Compare the stored state with the received state for CSRF protection
        if not stored_state or stored_state != state:
            logger.error("Invalid state parameter in Linkedin Callback View for user trying to login")
            message = base64.b64encode("Login failed. Please refresh and try logging in again".encode()).decode()
            return HttpResponseRedirect(f'{settings.FRONTEND_URL}/?error=session_expired&message={message}')
        
        # Only wrap the access token call in try-except
        try:
            token_response = get_access_token(code, request)
        except Exception as e:
            if "Failed to get access token. Status: 429" in str(e):
                logger.error("LinkedIn rate limit exceeded during login attempt")
                message = base64.b64encode(
                    "We're experiencing high traffic with LinkedIn authentication. Please try again in a few minutes."
                    .encode()).decode()
                return HttpResponseRedirect(
                    f'{settings.FRONTEND_URL}/?error=linkedin_auth_error&message={message}'
                )
            # For other access token errors
            logger.error(f"Failed to get LinkedIn access token: {str(e)}")
            message = base64.b64encode(
                "We're having trouble connecting with LinkedIn. Please try again in a few minutes."
                .encode()).decode()
            return HttpResponseRedirect(f'{settings.FRONTEND_URL}/?error=linkedin_auth_error&message={message}')
        
        linkedin_access_token = token_response.get('access_token')
        linkedin_access_token_expiry_seconds = token_response.get('expires_in')
        linkedin_access_token_expiry = datetime.now(timezone.utc) + timedelta(seconds=(linkedin_access_token_expiry_seconds - 300))
        
        id_token = token_response.get('id_token')
        decoded_id_token = decode_id_token(id_token)
        
        user_data = {
            'id': decoded_id_token.get('sub'),
            'name': decoded_id_token.get('name'),
            'first_name': decoded_id_token.get('given_name'),
            'last_name': decoded_id_token.get('family_name'),
            'email': decoded_id_token.get('email'),
            'picture': decoded_id_token.get('picture'),
            'linkedin_access_token': linkedin_access_token,
            'linkedin_access_token_expiry': linkedin_access_token_expiry.isoformat(),                
        }
        
        linkedin_id = user_data['id']
       
        # Check if user already exists in your database
        user_profiles = UserProfile.objects.filter(linkedin_id=linkedin_id)

        if user_profiles.exists():
            user_profile = user_profiles.first()
            user = user_profile.user

            # Update the access token and expiry
            user_profile.linkedin_access_token = linkedin_access_token
            user_profile.linkedin_access_token_expiry = linkedin_access_token_expiry

            # Check if the linkedin_profile_picture needs to be updated
            if user_profile.linkedin_profile_picture != user_data['picture']:
                user_profile.linkedin_profile_picture = user_data['picture']
                user_profile.save(update_fields=['linkedin_profile_picture', 'linkedin_access_token', 'linkedin_access_token_expiry'])
            else:
                user_profile.save(update_fields=['linkedin_access_token', 'linkedin_access_token_expiry'])    
                
        else:
            
            user = User.objects.create_user(username=user_data['id'], email=user_data['email'], first_name=user_data['first_name'], last_name=user_data['last_name'])
            UserProfile.objects.create(
                user=user,
                linkedin_id=user_data['id'],
                name=user_data['name'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                email=user_data['email'],
                linkedin_profile_picture=user_data['picture'],
                linkedin_access_token=user_data['linkedin_access_token'],
                linkedin_access_token_expiry=linkedin_access_token_expiry,
            )
                
        login(request, user)
        refresh = RefreshToken.for_user(user)
        jwt_token = str(refresh.access_token)
        response = HttpResponseRedirect(f'{settings.FRONTEND_URL}/uniboard/home')

        cookie_settings = {
            'httponly': True,
            'path': '/',
        }

        response.set_cookie('access_token', jwt_token, **cookie_settings)  # access_token -> _ut (user token)
        response.set_cookie('refresh_token', str(refresh), **cookie_settings)
        return response

    except Exception as e:
        logger.error(f"An error occurred at LinkedIn Callback view for user trying to login: {str(e)}")
        message = base64.b64encode("Login failed. Please refresh and try logging in again".encode()).decode()
        return HttpResponseRedirect(f'{settings.FRONTEND_URL}/?error=auth_required&message={message}')
    
def beta_full(request):
    return render(request, 'beta_full.html')  
    
class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        # First, call the superclass's post method to try to get a new token
        response = super().post(request, *args, **kwargs)

        # If the refresh was successful, set the new tokens as cookies
        if response.status_code == 200:
            return response

        # If the refresh was not successful, especially if it's a 401, clear the cookies
        else :            
            return response

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_user(request):
    logout(request)  # Logs out the user and clears the session
    return Response({"message": "Logged out successfully"}, status=200)

# DRF APIs 
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_data(request):
    user_profile = request.user.userprofile

    response_data = {
        'name': user_profile.preferred_name,
        'profilePictureUrl': user_profile.unimad_profile_picture or user_profile.linkedin_profile_picture,
        'linkedinProfilePictureUrl': user_profile.linkedin_profile_picture,
        'fullName': user_profile.name,
        'firstName': user_profile.first_name,
        'email': user_profile.email,
    }

    return JsonResponse(response_data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_profile_data(request):
    user_profile = request.user.userprofile

    response_data = {
        'name': user_profile.preferred_name,
        'profilePictureUrl': user_profile.unimad_profile_picture or user_profile.linkedin_profile_picture,
        'email': user_profile.email,
        'role': user_profile.role,
        'uni': user_profile.uni,
        'course': user_profile.course,
        'phone_number': user_profile.phone_number,
        'headline': user_profile.headline,
        'linkedin_url': user_profile.linkedin_url,
        'portfolio_url': user_profile.portfolio_url,
        'city': user_profile.city,
        'country': user_profile.country
        }

    return JsonResponse(response_data)

# Below are the APIs for the unibot, you can use any LLM provider you want to use and simulate the actual working of Unibot (unimad.ai's chatbot)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def unibot_api(request):
    user = request.user
    user_profile = UserProfile.objects.get(user=user)
    user_input = request.data.get('message')
    section_name = request.data.get('sectionName')

    #TODO: Implement the unibot_api or the unibot_api_stream

    # Call the reusable function to get Unibot's response
    # result = get_unibot_response(
    #     model_name="flash",  # or "pro" depending on your logic
    #     user_input=input_prompt,
    #     context=context,
    #     gen_conf=gen_conf,
    #     message_history=message_history,
    #     last_total_tokens=last_total_tokens
    # )
         
    # Create history entry
    # UnibotHistory.objects.create(
    #     user=user_profile,
    #     section_name=section_name,
    #     user_message=input_prompt,
    #     displayed_user_message=user_input if user_input != input_prompt else "",
    #     bot_response=result["response_text"],
    #     response_tokens=result["response_token_count"],
    #     total_tokens=result["total_tokens"],
    #     message_tokens=result["current_message_tokens"]
    # )
    result = {}

    # Return the response from Unibot
    return JsonResponse({"response": result["response_text"]})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@renderer_classes([ServerSentEventRenderer]) 
def unibot_api_stream(request):
    user = request.user
    user_profile = UserProfile.objects.get(user=user)
    user_input = request.data.get('message')
    section_name = request.data.get('sectionName')
    
    try:

        def event_stream():
            accumulated_response = []

            try:
                #TODO: Implement the streaming response for unibot_api_stream
                responses=[]                
                
                for chunk in responses:
                    # Stream the current chunk to the client
                    data = json.dumps({"text": chunk.text})
                    accumulated_response.append(chunk.text)
                    yield f'data: {data}\n\n'

            except Exception as e:
                yield f'data: {json.dumps({"error": "An error occurred while streaming"})}\n\n'

            # Store the complete response in the database
            # UnibotHistory.objects.create(
            #     user=user_profile,
            #     section_name=section_name,
            #     user_message=input_prompt,
            #     displayed_user_message=user_input if user_input != input_prompt else "",
            #     bot_response=complete_response,
            #     response_tokens=response_token_count,
            #     total_tokens=total_tokens,
            #     message_tokens=current_message_tokens
            # )

        # Return the streaming response
        response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
        response['X-Accel-Buffering'] = 'no'  # Disable buffering in nginx
        response['Cache-Control'] = 'no-cache'  # Ensure clients don't cache the data
        return response    
    
    except ResourceExhausted as e:
        # Handle ResourceExhausted exception and inform the user
        logger.error(f"503: {str(e)} error occurred at unibot_window_api")
        return JsonResponse({
            'error': 'Unibot service limit reached. Please try again in sometime. Bear with us until we upgrade our systems.'
        }, status=503)
    
    except Exception as e:
        logger.error(f"An 500 error occurred: {str(e)} at unibot_window_api")
        return JsonResponse({
            'error': 'Internal server error, Try again in sometime. Please contact us grow@unimad.ai if this continues.'
        }, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def unibot_history(request):
    # Extract the section name from the query parameters
    section_name = request.query_params.get('sectionName')

    if not section_name:
        return JsonResponse({"error": "sectionName parameter is required"}, status=400)

    user_profile = request.user.userprofile

    # Fetch history for the specific section for the authenticated user
    section_history = UnibotHistory.objects.filter(user=user_profile, section_name=section_name).order_by('created_at')

    # If no history exists for the section, return an empty array
    if not section_history.exists():
        return JsonResponse({'chat_history': []})
    
     # Get the first message's ID for this section
    first_message = section_history.first()
    first_message_id = first_message.id if first_message else None

    # Serialize the history using the custom ChatHistorySerializer
    serializer = ChatHistorySerializer(section_history, many=True, context={'first_message_id': first_message_id, 'section_name': section_name})
    serialized_data = serializer.data

    # Flatten the list of lists into a single list of messages
    flat_history = [item for sublist in serialized_data for item in sublist]

    # Return the chat history
    return JsonResponse({'chat_history': flat_history})