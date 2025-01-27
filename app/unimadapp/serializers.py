from rest_framework import serializers
from .models import UnibotHistory

class UnibotHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = UnibotHistory
        fields = ['user_message', 'bot_response'] 

class ChatHistorySerializer(serializers.BaseSerializer):
    def to_representation(self, instance):
        is_first_message = self.context.get('first_message_id') == instance.id
        section_name = self.context.get('section_name')

        # If 'displayed_user_message' is not empty, use it; otherwise, fallback to 'user_message'
        user_message = instance.displayed_user_message if instance.displayed_user_message else instance.user_message

        return [
            {
                'message_id': instance.id,
                'type': 'user',
                'message': user_message,
                'isFirstMessage': is_first_message,
                'sectionName': section_name,                
            },
            {
                'message_id': instance.id,
                'type': 'bot',
                'message': instance.bot_response,
                'isFirstMessage': is_first_message,
                'sectionName': section_name,                
            }
        ]