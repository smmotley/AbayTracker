from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from AbayDashboard.models import Profile, AlertPrefs
from phonenumber_field.modelfields import PhoneNumberField

class NewUserForm(UserCreationForm):
    # required = True means you can't fill out form without this.
    username = forms.CharField(required=False, max_length=30,
                             widget=forms.TextInput(attrs={'placeholder': 'Username'}))
    email = forms.EmailField(required=False,
                             widget=forms.TextInput(attrs={'placeholder':'Valid Email'}))
    first_name = forms.CharField(label="First Name", required=False,
                                 widget=forms.TextInput(attrs={'placeholder':'First Name'}))
    last_name = forms.CharField(label="Last Name", required=False,
                                widget=forms.TextInput(attrs={'placeholder': 'Last Name'}))

    def __str__(self):
        return f"{self.username}"

    def get_object(self, queryset=None):
        return self.request.user

    class Meta:
        model = User    # The basic django model we are using as our template here.
        fields = ("username", "first_name", "last_name", "email", "password1", "password2") # So, same as before, but now we're including email

    # When it gets saved, commit the data to the database
    def save(self, commit=True):
        user = super(NewUserForm, self).save(commit=False)  # Don't commit it yet until we modify the data.
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    error_messages =  {'Incorrect Format': ('Value outside of bounds.')}

    alert_sTime = forms.TimeField(label="Alerts OK After", required=False,
                                 widget=forms.TextInput(attrs={'placeholder': 'Alert Start Time',
                                                               'class':'timepicker'}))
    alert_eTime = forms.FloatField(label="Stop Alerts After", required=False,
                                widget=forms.TextInput(attrs={'placeholder': 'Alert End Time',
                                                       'class':'timepicker'}))
    alert = forms.BooleanField(label="Turn Alerts On", required=False,
                                widget=forms.TextInput(attrs={'placeholder': 'Alerts On?',
                                                              'type':'checkbox'}))

    class Meta:
        model = Profile
        fields = ("alert_sTime", "alert_eTime", "alert", "phone_number") # So, same as before, but now we're including email


class AlertForm(forms.ModelForm):
    error_messages = {'Incorrect Format': ('The phone number was entered incorrectly.')}
    class Meta:
        model = AlertPrefs
        fields = ("afterbay_hi", "afterbay_lo", "oxbow_deviation",
                  "r4_lo", "r4_hi", "r11_lo", "r11_hi", "r30_lo", "r30_hi")

    # Order the field so that when it shows up in the template, it displays with the lower value on the left.
    field_order = ["afterbay_lo", "afterbay_hi", "oxbow_deviation",
                  "r4_lo", "r4_hi", "r11_lo", "r11_hi", "r30_lo", "r30_hi"]

    def __init__(self, *args, **kwargs):
        super(AlertForm, self).__init__(*args, **kwargs)
        # Make all of the fields sow that they are not required
        for field in self.fields:
            self.fields[field].required = False