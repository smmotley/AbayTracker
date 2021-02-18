from django.core.mail import EmailMessage
from AbayTracker.settings import EMAIL_HOST_USER
import os, sys, platform

if "Linux" in platform.platform(terse=True):
    sys.path.append("/var/www/FireWeather")
os.environ['DJANGO_SETTINGS_MODULE'] = 'AbayTracker.settings'

def send_mail(user_phone, user_email, email_text, email_subject):
    msg = EmailMessage(
        subject=email_subject,
        body=email_text,
        from_email=EMAIL_HOST_USER,
        bcc=[user_email, f"{user_phone}@mms.att.net"],
    )
    #msg.attach_file(file_attachement1)
    msg.send(fail_silently=False)
    print("ALERT SENT")
    return


if __name__ == '__main__':
    send_mail(None, None)