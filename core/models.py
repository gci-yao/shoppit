from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    city = models.CharField(max_length=100,blank=1,null=1)
    state = models.CharField(max_length=100, blank=1, null=1)
    address = models.TextField(blank=1,null=1)
    phone = models.CharField(max_length=15,blank=1,null=1)

    class Meta:
        swappable = 'AUTH_USER_MODEL'
    def __str__(self):
        return self.username