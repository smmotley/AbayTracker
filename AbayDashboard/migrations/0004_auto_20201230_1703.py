# Generated by Django 3.0.3 on 2020-12-30 17:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('AbayDashboard', '0003_auto_20201230_0404'),
    ]

    operations = [
        migrations.RenameField(
            model_name='alertprefs',
            old_name='abay_lower',
            new_name='afterbay_hi',
        ),
        migrations.RenameField(
            model_name='alertprefs',
            old_name='abay_upper',
            new_name='afterbay_lo',
        ),
    ]
