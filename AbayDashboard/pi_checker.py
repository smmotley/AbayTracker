import os
from datetime import datetime, timedelta
import pandas as pd
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AbayTracker.settings')
django.setup()
from django.db import connection, IntegrityError
from django.db.models import Q
from AbayDashboard.models import AlertPrefs, Profile, User, Issued_Alarms
import requests
from timeloop import Timeloop
from scipy import stats
import numpy as np
from mailer import send_mail

t1 = Timeloop()

class PiRequest:
    #
    # https://flows.pcwa.net/piwebapi/assetdatabases/D0vXCmerKddk-VtN6YtBmF5A8lsCue2JtEm2KAZ4UNRKIwQlVTSU5FU1NQSTJcT1BT/elements
    def __init__(self, db, meter_name, attribute):
        self.db = db                    # Database (e.g. "Energy Marketing," "OPS")
        self.meter_name = meter_name    # R4, Afterbay, Ralston
        self.attribute = attribute      # Flow, Elevation, Lat, Lon, Storage, Elevation Setpoint, Gate 1 Position, Generation
        self.baseURL = 'https://flows.pcwa.net/piwebapi/attributes'
        self.meter_element_type = self.meter_element_type()  # Gauging Stations, Reservoirs, Generation Units
        self.url = self.url()

    def url(self):
        try:
            if self.db == "Energy_Marketing":
                response = requests.get(
                    url="https://flows.pcwa.net/piwebapi/attributes",
                    params={
                        "path": f"\\\\BUSINESSPI2\\{self.db}\\Misc Tags|{self.attribute}",
                        },
                )
            else:
                response = requests.get(
                    url="https://flows.pcwa.net/piwebapi/attributes",
                    params={"path": f"\\\\BUSINESSPI2\\{self.db}\\{self.meter_element_type}\\{self.meter_name}|{self.attribute}",
                            },
                )
            j = response.json()
            url_flow = j['Links']['InterpolatedData']
            return url_flow

        except requests.exceptions.RequestException:
            print('HTTP Request failed')
            return None

    def meter_element_type(self):
        if not self.meter_name:
            return None
        if self.attribute == "Flow":
            return "Gauging Stations"
        if "Afterbay" in self.meter_name:
            return "Reservoirs"
        if "Middle Fork" in self.meter_name:
            return "Generation Units"


@t1.job(interval=timedelta(minutes=1))
def main():
    meters = [PiRequest("OPS", "R4", "Flow"), PiRequest("OPS", "R11", "Flow"),
              PiRequest("OPS", "R30", "Flow"), PiRequest("OPS", "Afterbay", "Elevation"),
              PiRequest("OPS", "Afterbay", "Elevation Setpoint"),
              PiRequest("OPS", "Middle Fork", "Power - (with Ralston)"),
              PiRequest("Energy_Marketing", None, "ADS_MDFK_and_RA"),
              PiRequest("Energy_Marketing", None, "ADS_Oxbow"),
              PiRequest("Energy_Marketing", None, "Oxbow_Forecast")]
    df_all = pd.DataFrame()
    for meter in meters:
        # Now that we have the url for the PI data, this request is for the actual data. We will
        # download data from the beginning of the water year to the current date. (We can't download data
        # past today's date, if we do we'll get an error.
        try:
            response = requests.get(
                url=meter.url,
                params={"startTime": (datetime.utcnow() + timedelta(hours=-1)).strftime("%Y-%m-%dT%H:00:00-00:00"),
                        "endTime": datetime.utcnow().strftime("%Y-%m-%dT%H:00:00-00:00"),
                        "interval": "1m",
                        },
            )
            print('Response HTTP Status Code: {status_code}'.format(status_code=response.status_code))
            j = response.json()

            # We only want the "Items" object.
            df_meter = pd.DataFrame.from_dict((j["Items"]))

            # Convert the Timestamp to a pandas datetime object and convert to Pacific time.
            df_meter.index = pd.to_datetime(df_meter.Timestamp)
            df_meter.index.names = ['index']

            # Remove any outliers or data spikes
            df_meter = drop_numerical_outliers(df_meter, meter, z_thresh=3)

            # Rename the column (this was needed if we wanted to merge all the Value columns into a dataframe)
            renamed_col = (f"{meter.meter_name}_{meter.attribute}").replace(' ', '_')
            df_meter.rename(columns={"Value": f"{renamed_col}"}, inplace=True)

            # Check to see if a new alarm needed.
            alarm_checker(meter, df_meter, renamed_col)

            # This part is not longer needed.
            # if df_all.empty:
            #     df_all = df_meter
            # else:
            #     df_all = pd.merge(df_all, df_meter[["Timestamp", renamed_col]], on="Timestamp", how='outer')

        except requests.exceptions.RequestException:
            print('HTTP Request failed')
            return None

    # Email / Text any alerts that may be needed.
    send_alerts()
    return


def alarm_checker(meter, df, column_name):
    # For flows and abay elevation, we have two alarms;
    # 1) For high values and 2) For low values. We need to check both.
    if meter.attribute == "Flow" or meter.attribute == "Elevation":
        # Using Q() operators allows us to create dynamic names.
        hi_Q = Q(**{f"{meter.meter_name.lower()}_hi__lt": df[column_name].values.max()})
        lo_Q = Q(**{f"{meter.meter_name.lower()}_lo__gt": df[column_name].values.min()})
        alert_hi = AlertPrefs.objects.filter(hi_Q)
        alert_lo = AlertPrefs.objects.filter(lo_Q)

        # ############### RESET ALARMS IF NEEDED ##############
        # Check for case were an alarm was issued for a given meter, but now the value is below the alert threshold.
        # This will reset the alarm, so that if the threshold is met again, it will go off.
        alarm_active_hi = Issued_Alarms.objects.filter(alarm_still_active=True,
                                                       alarm_trigger=f"{meter.meter_name.lower()}_hi")
        alarm_active_lo = Issued_Alarms.objects.filter(alarm_still_active=True,
                                                       alarm_trigger=f"{meter.meter_name.lower()}_lo")
        # Check all active alarms
        if alarm_active_hi.exists():
            # Loop through all active alarms
            for active_alarm in alarm_active_hi:
                # If the an alarm is active, but it is now not exceeding the threshold, reset the alarm.
                if not AlertPrefs.objects.filter(hi_Q, user_id=active_alarm.user_id).exists():
                    Issued_Alarms.objects.filter(id=active_alarm.id).update(alarm_still_active=False)

        # Check all active alarms
        if alarm_active_lo.exists():
            # Loop through all active alarms
            for active_alarm in alarm_active_lo:
                # If the an alarm is active, but it is now not exceeding the threshold, reset the alarm.
                if not AlertPrefs.objects.filter(lo_Q, user_id=active_alarm.user_id).exists():
                    Issued_Alarms.objects.filter(id=active_alarm.id).update(alarm_still_active=False)
        # ################## END RESET ###############

        if alert_hi.exists():
            update_alertDB(users=alert_hi,
                           alarm_trigger=f"{meter.meter_name.lower()}_hi",
                           trigger_value=df[column_name].values.max()
                           )

        if alert_lo.exists():
            update_alertDB(users=alert_lo,
                           alarm_trigger=f"{meter.meter_name.lower()}_lo",
                           trigger_value=df[column_name].values.min()
                           )

    # If the elevation setpoint changes, this code will alert all users. It's a simplified version of the other
    # alerts since there's no hi/lo and there's no threshold to hit; just a change > 0.5' in an hour.
    if meter.attribute == "Elevation Setpoint":
        # The float level will be the latest value obtained in the dataset.
        abay_float = df["Afterbay_Elevation_Setpoint"].iloc[-1]

        # Set initial value
        abay_float_changed = False

        # Check to see if the float has changed. If so, alert user.
        if abs(abay_float - df["Afterbay_Elevation_Setpoint"].iloc[0]) > 0.5:
            abay_float_changed = True

        #  If the float changed in the last hour, first check if the alarm is already active.
        alarm_active = Issued_Alarms.objects.filter(alarm_still_active=True,
                                                    alarm_trigger="Abay_Float_Change")

        # This is more basic than resetting the flow alarms. Here, we're just saying if the Abay float hasn't
        # changed, but there are still alarms that are active, reset all the alarms. That way, if the abay float
        # changes again, all users will be notified.
        if alarm_active.exists() and not abay_float_changed:
            alarm_active.update(alarm_still_active=False)

        # If the float has changed, we want to alert all users; so the users param will include everyone that has
        # set up an alert profile (basically everyone).
        if abay_float_changed:
            update_alertDB(users=AlertPrefs.objects.all(),
                           alarm_trigger="Afterbay_Float",
                           trigger_value=int(abay_float))

    return


def update_alertDB(users, alarm_trigger, trigger_value):
    """
    Purpose: Add alerts to the Issued Alarms table in the database. The goal here is to only add alerts to the
            database IF certain fields are unique together: user_id, name of alarm (e.g. r4_hi),
            alarm_setpoint (e.g. the value put into r4_hi to trigger alarm), alarm_still_active.
            This means that an alert for the same event could only be reissued IF the user changed the
            alarm setpoint in their AlertPrefs during the event (which a user might want to do).
    :param users (QuerySet): A queryset containing data from AlertPrefs where are values exceeded by the alarm_trigger.
                             If a user's threshold for an alert is met, the queryset will contain all the threshold
                             data from AlertPrefs for the user.
    :param alarm_trigger: The column name in AlertPrefs that triggered the alert (e.g. r4_hi, afterbay_lo)
    :param trigger_value: The value that exceeded the threshold
    :return:
    """
    for user in users:
        # Users don't have a setpoint for the Afterbay_Float alarm, since it is triggered on a change.
        if alarm_trigger == "Afterbay_Float":
            alarm_setpoint = trigger_value
        # Other values (like r4_hi) do have a threshold value for triggering an alarm.
        else:
            alarm_setpoint = getattr(user, alarm_trigger)
        obj, created = Issued_Alarms.objects.get_or_create(
            user_id=user.user_id,
            alarm_trigger=alarm_trigger,
            alarm_setpoint=alarm_setpoint,  # unique in case someone changes
            alarm_still_active=True,
            defaults={
                'trigger_time': datetime.utcnow(),
                'trigger_value': trigger_value,
                'alarm_sent': False,
                'seen_on_website': False,
            },
        )
    return

def send_alerts():
    need_to_send = Issued_Alarms.objects.filter(alarm_sent=False)
    if need_to_send.exists():
        for alert in need_to_send:
            user_profile = Profile.objects.get(user__id=alert.user_id)
            user_phone = user_profile.phone_number
            user_email = user_profile.user.email
            pretty_name = (alert.alarm_trigger.split('_')[0]).upper()
            email_body = f"{alert.alarm_trigger} triggered this alert \n" \
                         f"Current Value: {alert.trigger_value} \n" \
                         f"Your threshold: {alert.alarm_setpoint}"
            email_subject = f"PCWA Alarm For {pretty_name}"
            send_mail(user_phone, user_email, email_body, email_subject)
            Issued_Alarms.objects.filter(id=alert.id).update(alarm_sent=True)
    return


def drop_numerical_outliers(df, meter, z_thresh):
    # Constrains will contain `True` or `False` depending on if it is a value below the threshold.
    # 1) For each column, first it computes the Z-score of each value in the column,
    #   relative to the column mean and standard deviation.
    # 2) Then is takes the absolute of Z-score because the direction does not matter,
    #   only if it is below the threshold.
    # 3) all(axis=1) ensures that for each row, all column satisfy the constraint.

    # Note: The z-score will return NAN if all values are exactly the same. Therefore,
    #       if all values are the same, return the original dataframe and consider the data valid, otherwise the
    #       data won't pass the z-score test and the data will be QC'ed out.
    u = df["Value"].to_numpy()
    if (u[0] == u).all(0):
        return df

    orig_size = df.shape[0]
    constrains = df.select_dtypes(include=[np.number]) \
        .apply(lambda x: np.abs(stats.zscore(x)) < z_thresh, result_type='reduce') \
        .all(axis=1)
    # Drop (inplace) values set to be rejected
    df.drop(df.index[~constrains], inplace=True)

    if df.shape[0] != orig_size:
        print(f"A total of {orig_size - df.shape[0]} data spikes detected in {meter.meter_name}. "
              f" The data have been removed")
    return df


if __name__ == "__main__":
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AbayTracker.settings')
    main()
    t1.start(block=True)
