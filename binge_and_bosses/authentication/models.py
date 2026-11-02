from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.
class User(AbstractUser):
    # Sets email to be unique during signup
    AbstractUser._meta.get_field('email')._unique = True
    pass