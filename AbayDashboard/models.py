from django.db import models
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models.signals import post_save
# Create your models here.

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    alert_ok_time_start = models.DateTimeField(null=True, blank=True)
    alert_ok_time_end = models.DateTimeField(null=True, blank=True)
    phone_number = models.CharField(blank=True, null=True, max_length=15)
    phone_carrier = models.CharField(blank=True, null=True, max_length=30)
    alarm_on = models.BooleanField(null=True)

    def __str__(self):
        return f'{self.user.first_name}'


class AlertPrefs(models.Model):
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    afterbay_hi = models.FloatField(null=True)
    afterbay_lo = models.FloatField(null=True)
    oxbow_deviation = models.FloatField(null=True)
    r4_hi = models.IntegerField(null=True)
    r4_lo = models.IntegerField(null=True)
    r30_hi = models.IntegerField(null=True)
    r30_lo = models.IntegerField(null=True)
    r11_hi = models.IntegerField(null=True)
    r11_lo = models.IntegerField(null=True)
    error_messages = {'Incorrect Format': ('Value outside of bounds')}

    def __str__(self):
        return f'{self.user.first_name}'


class Issued_Alarms(models.Model):
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    alarm_trigger = models.TextField(null=True)
    alarm_setpoint = models.FloatField(null=True)
    trigger_value = models.FloatField(null=True)
    trigger_time = models.DateTimeField(null=True)
    alarm_sent = models.BooleanField(null=True)
    alarm_still_active = models.BooleanField(null=True)
    seen_on_website = models.BooleanField(null=True)


# Whenever there is a post_save in the User model, run the following code
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()