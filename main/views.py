from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Equipment
from .serializers import EquipmentSerializer

@api_view(['GET'])
def equipment_list_api(request):
    equipments = Equipment.objects.all()  
    serializer = EquipmentSerializer(equipments, many=True)  
    return Response(serializer.data)
