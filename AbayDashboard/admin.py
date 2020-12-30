from django.contrib import admin
from .models import Profile, AlertPrefs

# Register your models here.
class UserAdmin(admin.ModelAdmin):
    fields = ["first_name",
              "last_name",
              "email",
              ""]


admin.site.register(Profile)
admin.site.register(AlertPrefs)
