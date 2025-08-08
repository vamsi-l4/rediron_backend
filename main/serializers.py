from rest_framework import serializers
from .models import Equipment
from .models import ContactMessage

class EquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipment
        fields= '__all__'

class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = '__all__'      