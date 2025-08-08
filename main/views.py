from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Equipment, ContactMessage
from rest_framework import status, viewsets as ViewSets
from django.core.mail import send_mail
from django.conf import settings
from .serializers import EquipmentSerializer, ContactMessageSerializer

class ContactMessageViewSet(ViewSets.ModelViewSet):
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer

@api_view(['GET'])
def equipment_list_api(request):
    equipments = Equipment.objects.all()
    serializer = EquipmentSerializer(equipments, many=True)
    return Response(serializer.data)

@api_view(['POST'])
def contact_message_api(request):
    serializer = ContactMessageSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()

        # Send HTML email to admin
        subject = f"📬 New Contact Message from {serializer.validated_data['name']}"
        message_plain = f"Name: {serializer.validated_data['name']}\nEmail: {serializer.validated_data['email']}\nSubject: {serializer.validated_data['subject']}\n\nMessage:\n{serializer.validated_data['message']}"
        message_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f9f9f9;">
            <h2 style="color: #c0392b;">New Contact Message</h2>
            <p><strong>Name:</strong> {serializer.validated_data['name']}</p>
            <p><strong>Email:</strong> {serializer.validated_data['email']}</p>
            <p><strong>Subject:</strong> {serializer.validated_data['subject']}</p>
            <p><strong>Message:</strong><br>{serializer.validated_data['message']}</p>
        </body>
        </html>
        """
        send_mail(
            subject,
            message_plain,
            settings.EMAIL_HOST_USER,
            ['kvamsim7@gmail.com'],  
            html_message=message_html
        )

       
        auto_subject = "✅ We received your message at RedIron Gym!"
        auto_message_plain = f"Hi {serializer.validated_data['name']},\n\nThanks for contacting us! We have received your message and will get back to you shortly.\n\n- RedIron Gym Team"
        auto_message_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #fff;">
            <h2 style="color: #27ae60;">Thank You for Contacting RedIron Gym!</h2>
            <p>Hi {serializer.validated_data['name']},</p>
            <p>We have received your message and our team will reach out to you soon.</p>
            <p style="margin-top: 20px;">💪 Stay strong,<br><strong>RedIron Gym Team</strong></p>
        </body>
        </html>
        """
        send_mail(
            auto_subject,
            auto_message_plain,
            settings.EMAIL_HOST_USER,
            [serializer.validated_data['email']],
            html_message=auto_message_html
        )

        return Response({"success": "Message sent successfully"}, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
