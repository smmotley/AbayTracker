# Generated by Django 3.0.3 on 2020-12-28 23:19

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('AbayDashboard', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Issued_Alarms',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('alarm_trigger', models.TextField(null=True)),
                ('alarm_setpoint', models.IntegerField(null=True)),
                ('trigger_value', models.IntegerField(null=True)),
                ('tigger_time', models.DateTimeField(null=True)),
                ('alarm_sent', models.BooleanField(null=True)),
                ('alarm_still_active', models.BooleanField(null=True)),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]