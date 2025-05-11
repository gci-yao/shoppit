# core/views.py

from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail
from django.conf import settings

from .models import CustomUser
from .serializers import RegisterSerializer, CustomUserSerializer


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token = get_tokens_for_user(user)

        return Response({
            "message": "Compte créé avec succès",
            "token": token,
        }, status=status.HTTP_201_CREATED)

    return Response({
        "message": "Échec de la création du compte",
        "errors": serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])  # Utile si ce endpoint est accessible sans token
def send_welcome_email(request):
    try:
        email = request.data.get('email')
        username = request.data.get('username')

        if not email or not username:
            return Response({'error': 'Email et username sont requis'}, status=400)

        subject = 'Bienvenue sur notre plateforme !'
        message = f"""
Bonjour {username},

Merci pour votre inscription sur notre site !

Vous pouvez dès maintenant découvrir nos produits en cliquant sur ce lien :
{settings.FRONTEND_URL}/products

L'équipe de MyShop
        """.strip()

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )

        return Response({'status': 'Email envoyé avec succès'}, status=200)

    except Exception as e:
        return Response({'error': f'Erreur lors de l\'envoi de l\'email : {str(e)}'}, status=500)


class UserUpdateView(generics.RetrieveUpdateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user  # Renvoie l'utilisateur connecté
