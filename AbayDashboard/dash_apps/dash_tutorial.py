import os
import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import copy
import requests
from datetime import datetime, timedelta, time
import pytz
import numpy as np
from django.contrib.staticfiles.storage import staticfiles_storage

from dash.dependencies import Input, Output, State
from plotly import graph_objs as go
from plotly.graph_objs import *
from datetime import datetime as dt
from django_plotly_dash import DjangoDash
import dash_bootstrap_components as dbc
from htexpr import compile
import dash_daq as daq

# ###To run the app on it's own (not in Django), you would do:
# app = dash.Dash()
# ###Then at the bottom you would do the following:
# if __name__ == '__main__':
#    app.run_server(debug=True)
### Then you'd just run python from the terminal > python dash_first.py
# app = DjangoDash('UberExample')

# app = dash.Dash(
#     __name__, meta_tags=[{"name": "viewport", "content": "width=device-width" }],
#     external_stylesheets=["https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/css/materialize.min.css"],
#     external_scripts=["https://code.jquery.com/jquery-3.5.1.min.js",
#                       'https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/js/materialize.min.js',
#                       ]
# )
#
# # app = dash.Dash()

class PiRequest:
    #
    # https://flows.pcwa.net/piwebapi/assetdatabases/D0vXCmerKddk-VtN6YtBmF5A8lsCue2JtEm2KAZ4UNRKIwQlVTSU5FU1NQSTJcT1BT/elements
    def __init__(self, meter_name, attribute):
        self.meter_name = meter_name  # R4, Afterbay, Ralston
        self.attribute = attribute  # Flow, Elevation, Lat, Lon, Storage, Elevation Setpoint, Gate 1 Position, Generation
        self.baseURL = 'https://flows.pcwa.net/piwebapi/attributes'
        self.meter_element_type = self.meter_element_type()  # Gauging Stations, Reservoirs, Generation Units
        self.url = self.url()

    def url(self):
        try:
            response = requests.get(
                url="https://flows.pcwa.net/piwebapi/attributes",
                params={"path": f"\\\\BUSINESSPI2\\OPS\\{self.meter_element_type}\\{self.meter_name}|{self.attribute}",
                        },
            )
            j = response.json()
            url_flow = j['Links']['InterpolatedData']
            return url_flow

        except requests.exceptions.RequestException:
            print('HTTP Request failed')
            return None

    def meter_element_type(self):
        if self.attribute == "Flow":
            return "Gauging Stations"
        if "Afterbay" in self.meter_name:
            return "Reservoirs"
        if "Middle Fork" in self.meter_name:
            return "Generation Units"

local = True
if local:
    app = dash.Dash(
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        external_scripts=["https://code.jquery.com/jquery-3.5.1.min.js",
                          ],
        suppress_callback_exceptions = True
    )
    server = app.server
    df = pd.read_csv("pcwa_locations.csv")
    dfp = pd.read_csv("spc_data.csv")
else:
    app = DjangoDash('dash_django', suppress_callback_exceptions=True, add_bootstrap_links=True)
    df = pd.read_csv(staticfiles_storage.path("data/pcwa_locations.csv"))  # make sure this is in the static dir
    dfp = pd.read_csv(staticfiles_storage.path("data/spc_data.csv"))

main_dir = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..'))
mapbox_access_token = "pk.eyJ1Ijoic21vdGxleSIsImEiOiJuZUVuMnBBIn0.xce7KmFLzFd9PZay3DjvAA"

def main(meters):
    meters = [PiRequest("R4", "Flow"), PiRequest("R11", "Flow"),
              PiRequest("R30", "Flow"), PiRequest("Afterbay", "Elevation"),
              PiRequest("Afterbay", "Elevation Setpoint"),
              PiRequest("Middle Fork", "Power - (with Ralston)")]
    df_all = pd.DataFrame()
    for meter in meters:
        # Now that we have the url for the PI data, this request is for the actual data. We will
        # download data from the beginning of the water year to the current date. (We can't download data
        # past today's date, if we do we'll get an error.
        try:
            response = requests.get(
                url=meter.url,
                params={"startTime": (datetime.utcnow() + timedelta(hours=-24)).strftime("%Y-%m-%dT%H:00:00-00:00"),
                        "endTime": datetime.utcnow().strftime("%Y-%m-%dT%H:00:00-00:00"),
                        "interval": "1h",
                        },
            )
            print('Response HTTP Status Code: {status_code}'.format(status_code=response.status_code))
            j = response.json()

            # We only want the "Items" object.
            df_meter = pd.DataFrame.from_dict((j["Items"]))

            # Convert the Timestamp to a pandas datetime object and convert to Pacific time.
            df_meter.Timestamp = pd.to_datetime(df_meter.Timestamp).dt.tz_convert('US/Pacific')
            df_meter.index = df_meter.Timestamp
            df_meter.index.names = ['index']

            # Rename the column (this was needed if we wanted to merge all the Value columns into a dataframe)
            renamed_col = (f"{meter.meter_name}_{meter.attribute}").replace(' ', '_')
            df_meter.rename(columns={"Value": f"{renamed_col}"}, inplace=True)

            if df_all.empty:
                df_all = df_meter
            else:
                df_all = pd.merge(df_all, df_meter[["Timestamp", renamed_col]], on="Timestamp", how='outer')

        except requests.exceptions.RequestException:
            print('HTTP Request failed')
            return None


    locations_types = df.type.unique()
    mapbox_layers = {
        "SWE": "https://idpgis.ncep.noaa.gov/arcgis/services/NWS_Observations/NOHRSC_Snow_Analysis/"
                "MapServer/WmsServer?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image/"
                "png&TRANSPARENT=true&LAYERS=1&WIDTH=256&HEIGHT=256&CRS=EPSG:3857&STYLES=&BBOX={bbox-epsg-3857}",
        "RADAR": "https://mesonet.agron.iastate.edu/cache/tile.py/1.0.0/nexrad-n0q-900913/{z}/{x}/{y}.png",
        "SAT_TILES": "https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}",
        "PRECIP_24": "https://mesonet.agron.iastate.edu/cache/tile.py/1.0.0/q2-p24h-900913/{z}/{x}/{y}.png",
        "PRECIP_48": "https://mesonet.agron.iastate.edu/cache/tile.py/1.0.0/q2-p48h-900913/{z}/{x}/{y}.png",
        "PRECIP_72": "https://mesonet.agron.iastate.edu/cache/tile.py/1.0.0/q2-p72h-900913/{z}/{x}/{y}.png",
    }

    map_meter_options = {
        'River Flows': ['R4', 'R11', 'R20', 'R30'],
        'Abay Management': ['Elevation', 'Oxbow', 'Rafting'],
        'Generation': ['Oxbow', 'French Meadows', 'Ralston']
    }

# Layout for line graph plot.
    layout = dict(
        margin=dict(l=40, r=40, b=40, t=40),
        hovermode="closest",
        plot_bgcolor="#343a40",    # This hard codes the background. theme="plotly_dark" works if this line is removed.
        paper_bgcolor="#343a40",
        legend=dict(font=dict(size=10), orientation="h"),
    )


    top_row_cards = dbc.Row([
        dbc.Col(
            dbc.Card([
            dbc.CardHeader(f"Abay - "
                           f"Float: {round(df_all['Afterbay_Elevation_Setpoint'].values.max(),1)}"
                           f" Updated: {(df_all['Timestamp'].iloc[-1]).strftime('%b %d, %H:%M %p')}"),
            dbc.CardBody(
                dbc.Row([
                    dbc.Col(
                        daq.Tank(
                            id='my-tank2',
                            className='dark-theme-control',
                            value=round(df_all["Afterbay_Elevation"].iloc[-1], 1),
                            height=75,
                            min=1165,
                            max=df_all["Afterbay_Elevation_Setpoint"].values.max(),
                            color='#2376f3',
                            style={"width":"100%"},
                            units="Elevation",
                            showCurrentValue=True
                        )
                        ,width=4,
                    ),
                    dbc.Col(
                        dcc.Graph(
                            className="sparkline_graph",
                            style={"width": "100%", "height": "95%"},
                            config={
                                "staticPlot": False,
                                "editable": False,
                                "displayModeBar": False,
                            },
                            figure={
                                    "data": [
                                        {
                                            "x": df_all['Timestamp'][-10:],
                                            "y": df_all['Afterbay_Elevation'][-10:],
                                            "type": "bar",
                                            "name": "Elevation",
                                            "marker":{"color":'#2c7be5'},
                                            "hovertemplate": "%{x|%b-%d, %H:%M %p} %{y}",
                                            #"width":"1.5",
                                        },
                                        {
                                            "x": df_all['Timestamp'][-10:],
                                            "y": df_all['Afterbay_Elevation_Setpoint'][-10:] - df_all["Afterbay_Elevation"][-10:],
                                            "type": "bar",
                                            "name": "Space",
                                            "marker": {"color": '#061325'},
                                            "hovertemplate": "%{x|%b-%d, %H:%M %p} %{y}",
                                            #"width": "1.5",
                                        },

                                    ],
                                    "layout": {
                                        "margin": dict(l=0, r=0, t=4, b=4, pad=0),
                                        "title": None,
                                        "showlegend":False,
                                        "yaxis":dict(
                                            title=None,
                                            titlefont_size=16,
                                            tickfont_size=14,
                                            showline=False,
                                            showgrid=False,
                                            zeroline=False,
                                            showticklabels=False,
                                            visible=False,
                                            range=[1168,df_all["Afterbay_Elevation_Setpoint"].values.max()]
                                            ),
                                        "xaxis":dict(
                                            showline=False,
                                            showgrid=False,
                                            zeroline=False,
                                            showticklabels=False,
                                            visible=False,  # numbers below
                                        ),
                                        "legend": None,
                                        "hovermode":"closest",
                                        "barmode": 'relative',
                                        "paper_bgcolor":'rgba(0,0,0,0)',
                                        "plot_bgcolor":"rgba(0,0,0,0)",
                                        #"bargap": 0.05, # gap between bars of adjacent location coordinates.
                                        #"bargroupgap":0.05, # gap between bars of the same location coordinate.,
                                        "autosize": True,
                                    },
                                }
                        ), width=8, className='sparkline', style={"display":"flex", "padding-left":"0"}
                    )
                ],style={"flex-grow": "1"}),
            )
            ], color="dark", inverse=True), width=3, lg=3, md=3, xs=12
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("MF+RA Gen vs Scheduled"),
                dbc.CardBody(dbc.Row([
                    dbc.Col(
                        daq.Gauge(
                            style={"top" : "-20px", "position": "absolute"},
                            color={"gradient": True,
                                   "ranges":
                                            {"blue": [0, 80],
                                             "green": [80, 160],
                                             "yellow": [160, 220]}},
                            value=int(df_all["Middle_Fork_Power_-_(with_Ralston)"].iloc[-1]),
                            max=220,
                            min=0,
                            units="MW",
                            size=75,
                            showCurrentValue=True,
                        )
                        , width=4,
                    ),
                    dbc.Col(
                        dcc.Graph(
                            className="sparkline_graph",
                            style={"width": "100%", "height": "95%"},
                            config={
                                "staticPlot": False,
                                "editable": False,
                                "displayModeBar": False,
                            },
                            figure=go.Figure(
                                {
                                    "data": [
                                        {
                                            "x": df_all["Timestamp"],
                                            "y": df_all["Middle_Fork_Power_-_(with_Ralston)"],
                                            "mode": "lines+markers",
                                            "name": "R4 Flow (CFS)",
                                            "line": {"color": "#f4d44d"},
                                        }
                                    ],
                                    "layout": {
                                        "margin": dict(l=0, r=0, t=4, b=4, pad=0),
                                        "xaxis": dict(
                                            showline=False,
                                            showgrid=False,
                                            zeroline=False,
                                            showticklabels=False,
                                        ),
                                        "yaxis": dict(
                                            showline=False,
                                            showgrid=False,
                                            zeroline=False,
                                            showticklabels=False,
                                        ),
                                        "autosize": True,
                                        "paper_bgcolor": "rgba(0,0,0,0)",
                                        "plot_bgcolor": "rgba(0,0,0,0)",
                                    },
                                }
                            ),
                        ), width=8, className='sparkline', style={"display":"flex"}
                    )
                ]))
            ], color="dark", inverse=True), width=3, lg=3, md=3, xs=12
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("R4 Flow"),
                dbc.CardBody(dbc.Row([
                    dbc.Col(
                        daq.LEDDisplay(
                            size=30,
                            value=int(df_all["R4_Flow"].iloc[-1]),
                            color="#FF5E5E",
                            backgroundColor="#343a40"
                        ),
                    width=4),
                    dbc.Col(
                        dcc.Graph(
                            className="sparkline_graph",
                            style={"width": "100%", "height": "95%"},
                            config={
                                "staticPlot": False,
                                "editable": False,
                                "displayModeBar": False,
                            },
                            figure=go.Figure(
                                {
                                    "data": [
                                        {
                                            "x": df_all["Timestamp"],
                                            "y": df_all["R4_Flow"],
                                            "mode": "lines+markers",
                                            "name": "R4 Flow",
                                            "line": {"color": "#f4d44d"},
                                        }
                                    ],
                                    "layout": {
                                        "margin": dict(l=0, r=0, t=4, b=4, pad=0),
                                        "xaxis": dict(
                                            showline=False,
                                            showgrid=False,
                                            zeroline=False,
                                            showticklabels=False,
                                        ),
                                        "yaxis": dict(
                                            showline=False,
                                            showgrid=False,
                                            zeroline=False,
                                            showticklabels=False,
                                        ),
                                        "autosize": True,
                                        "paper_bgcolor": "rgba(0,0,0,0)",
                                        "plot_bgcolor": "rgba(0,0,0,0)",
                                    },
                                }
                            ),
                        ), width=8, className='sparkline', style={"display": "flex"}
                    )
                ]))
            ], color="dark", inverse=True), width=3, lg=3, md=3, xs=12
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("R30 Flow"),
                dbc.CardBody(dbc.Row([
                    dbc.Col(
                        daq.LEDDisplay(
                            size=30,
                            value=int(df_all["R30_Flow"].iloc[-1]),
                            color="#FF5E5E",
                            backgroundColor="#343a40"
                        ), width=4,
                    ),
                    dbc.Col(
                        dcc.Graph(
                            className="sparkline_graph",
                            style={"width": "100%", "height": "95%"},
                            config={
                                "staticPlot": False,
                                "editable": False,
                                "displayModeBar": False,
                            },
                            figure=go.Figure(
                                {
                                    "data": [
                                        {
                                            "x": df_all["Timestamp"],
                                            "y": df_all["R30_Flow"],
                                            "mode": "lines+markers",
                                            "name": "something",
                                            "line": {"color": "#f4d44d"},
                                        }
                                    ],
                                    "layout": {
                                        "margin": dict(l=0, r=0, t=4, b=4, pad=0),
                                        "xaxis": dict(
                                            showline=False,
                                            showgrid=False,
                                            zeroline=False,
                                            showticklabels=False,
                                        ),
                                        "yaxis": dict(
                                            showline=False,
                                            showgrid=False,
                                            zeroline=False,
                                            showticklabels=False,
                                        ),
                                        "autosize": True,
                                        "paper_bgcolor": "rgba(0,0,0,0)",
                                        "plot_bgcolor": "rgba(0,0,0,0)",
                                    },
                                }
                            ),
                        ), width=8, className='sparkline', style={"display": "flex"}
                    )
                ]))
            ], color="dark", inverse=True), width=3, lg=3, md=3, xs=12
        )
        #dbc.Col(dbc.Card(card_content, color="dark", inverse=True)),
        #dbc.Col(dbc.Card(card_content, color="dark", inverse=True)),
        #dbc.Col(dbc.Card(card_content, color="dark", inverse=True)),
        ],
        className='top-cards'
    )


    app.layout = html.Main(
        className='content',
        children=[
            html.Div(className='container-fluid',
                     children=[
                         top_row_cards
                     ]),
            html.Div(className='container-fluid',
                     children=[
            dbc.Row([
                dbc.Col((html.H2("PCWA - STATION DATA"),
                                html.P(
                                    """Select a station to display current flows or reservoir levels."""
                                ),
                                html.Div(
                                    className="div-for-dropdown",
                                    children=[
                                        dcc.DatePickerSingle(
                                            id="date-picker",
                                            min_date_allowed=dt(2018, 4, 1),
                                            max_date_allowed=dt.now().date(),
                                            initial_visible_month=dt.now().date(),
                                            date=dt.now().date(),
                                            display_format="MMMM D, YYYY",
                                        )
                                    ],
                                ),
                                # Change to side-by-side for mobile layout
                                    html.Div(
                                        className="div-for-dropdown",
                                        children=[
                                            # Dropdown for locations on map
                                            dcc.Dropdown(
                                                id="alert-dropdown",
                                                options=[
                                                    {"label": i, "value": i}
                                                    for i in locations_types
                                                ],
                                                placeholder="Select meter",
                                            )
                                        ],
                                    ),
                                    html.Div(
                                        className="div-for-dropdown",
                                        children=[
                                            # Dropdown to select times
                                            dcc.Dropdown(
                                                id="mapbox_layer_dropdown",
                                                options=[
                                                    {
                                                        "label": key,
                                                        "value": value,
                                                    }
                                                    for key, value in mapbox_layers.items()
                                                ],
                                                multi=True,
                                                placeholder="Add a Map Layer",
                                            )
                                        ],
                                    ),),width=2),
                dbc.Col(dbc.Row([
                    dbc.Col(dcc.Graph(id="map-graph", className="col s5"), width=6),
                    dbc.Col(dcc.Loading(
                                id='loading_graph',
                                parent_className='loading_wrapper col s5',
                                children=[html.Div([dcc.Graph(id="histogram")])],
                                type="circle",
                                ), width=6
                            )
                        ]),width=10),
            ])
                     ]
                    ),
            html.Div(id='dummy-output'),
        ]
    )


    def produce_individual(api_well_num):
        try:
            point = df.iloc[api_well_num]
        except:
            return None

        try:
            response = requests.get(
                url="https://flows.pcwa.net/piwebapi/attributes",
                params={"path": f"\\\\BUSINESSPI2\\OPS\\Gauging Stations\\{point['id']}|Flow",
                    },
                )
            j = response.json()
            url_flow = j['Links']['InterpolatedData']

        except requests.exceptions.RequestException:
            print('HTTP Request failed')
            return None

        # Now that we have the url for the PI data, this request is for the actual data. We will
        # download data from the beginning of the water year to the current date. (We can't download data
        # past today's date, if we do we'll get an error.
        try:
            response = requests.get(
                url=url_flow,
                params={"startTime": (datetime.now() + timedelta(days=-3)).strftime("%Y-%m-%dT%H:00:00-07:00"),
                        "endTime": datetime.now().strftime("%Y-%m-%dT%H:00:00-07:00"),
                        "interval": "1h",
                        },
            )
            print('Response HTTP Status Code: {status_code}'.format(status_code=response.status_code))
            j = response.json()

            # We only want the "Items" object.
            df_meter = pd.DataFrame.from_dict((j["Items"]))

            # Convert the Timestamp to a pandas datetime object and convert to Pacific time.
            df_meter.index = pd.to_datetime(df_meter.Timestamp)
            #df_meter.index = df.index.tz_convert('US/Pacific')
        except requests.exceptions.RequestException:
            print('HTTP Request failed')
            return None
        return df_meter


    @app.callback(Output("loading_output", "children"), [Input("map-graph", "hoverData")])
    def input_triggers_spinner(value):
        return


    @app.callback(
        Output(component_id="modal_header_text", component_property="children", ),
        [Input(component_id="open_modal", component_property="n_clicks"), Input(component_id="close", component_property="n_clicks")],
        [State(component_id="alert-dropdown", component_property="value")],
    )
    def show_meter_in_modal(n1, n2, value):
        if n1 or n2:
            return html.H5(f"Change Alarm Values For: {value}", className="modal-title")
        return html.H5(f"Change Alarm Values For: {value}", className="modal-title")


    #This callback does two things:
    # 1: Call back for adding / removing mapbox layer
    # 2: Callback for changing marker display.
    @app.callback(
        Output(component_id="map-graph", component_property="figure", ),
        [Input(component_id="alert-dropdown", component_property="value"),
         Input("mapbox_layer_dropdown", "value")],
    )
    def map_markers(marker_type_val, mapbox_overlay):
        fig = go.Figure()

        # MARKER SECTION
        if marker_type_val is None:
            markers = df.loc[df['type'] == 'Flow']
        else:
            markers = df.loc[df['type'] == marker_type_val]

        # This is for the large outer Ring
        fig.add_trace(go.Scattermapbox(
            lat=markers.lat,
            lon=markers.lon,
            mode='text+markers',  # A mode of "text" will just show hover
            marker=go.scattermapbox.Marker(
                size=17,
                color='rgb(255, 0, 0)',
                opacity=0.7
            ),
            text=markers.id,
            textfont=dict(
                family="sans serif",
                size=18,
                color="white"
            ),
            textposition="top center",
            hoverinfo='text'
        ))

        # This is for the small inner right.
        fig.add_trace(go.Scattermapbox(
            lat=markers.lat,
            lon=markers.lon,
            mode='markers',
            marker=go.scattermapbox.Marker(
                size=8,
                color='rgb(242, 177, 172)',
                opacity=0.7
            ),
            hoverinfo='text',
            text=[i for i in markers.name],
        ))

        fig.update_layout(
            title='Meter Locations',
            hovermode='closest',
            margin=dict(l=10, r=10, b=10, t=40),
            plot_bgcolor="#F9F9F9",
            paper_bgcolor="#F9F9F9",
            showlegend=False,
            mapbox=dict(
                accesstoken=mapbox_access_token,
                bearing=0,
                center=dict(
                    lat=39,
                    lon=-120.5
                ),
                pitch=0,
                zoom=9,
                style='dark'
            ),
        )

        # MAPBOX OVERLAY SECTION
        if mapbox_overlay is None or len(mapbox_overlay) == 0:
            fig.update_layout(
                mapbox_layers=[
                    {}
                ])
            return fig
        fig.update_layout(
            mapbox_layers=[
                {
                    "below": 'traces',
                    "sourcetype": "raster",
                    "sourceattribution": "United States Geological Survey",
                    "source": [
                        mapbox_overlay[0]
                    ]
                }
            ])

        return fig


    # app.clientside_callback(
    # """
    # function(meter){
    #     $('#myModal').modal('toggle');
    #     }
    #     """,
    #     Output(component_id="modal_body", component_property="children", ),
    #     [Input(component_id="open_modal", component_property="n_clicks"), Input(component_id="close", component_property="n_clicks")],
    # )

    app.clientside_callback(
        """
        function(alarmHi, alarmLo, div_id){
            console.log(div_id, alarmHi, alarmLo)
            if(div_id=="R4"){
                console.log("INSIDE")
                $("#id_r4_hi").val(alarmHi)
                $("#id_r4_lo").val(alarmLo)
            }
            if(div_id=="Abay"){
                $("#id_abay_upper").val(alarmHi)
                $("#id_abay_lower").val(alarmLo)
            }
        }
        """,
        Output(component_id='dummy-output', component_property='children'),
        [Input("alarmInputHi", "value"),
        Input("alarmInputLow", "value"),
        Input("alert_id", "value")])


    # Main graph -> individual graph
    @app.callback(Output("histogram", "figure"), [Input("map-graph", "clickData")])
    def make_individual_figure(main_graph_click):

        layout_individual = copy.deepcopy(layout)

        if main_graph_click is None:
            main_graph_click = {
                "points": [
                    {"curveNumber": 4, "pointNumber": 1, "text": "MF AR Above Interbay"}
                ]
            }

        chosen = [point["pointNumber"] for point in main_graph_click["points"]]
        df_meter = produce_individual(chosen[0])

        if df_meter is None:
            annotation = dict(
                text="No data available",
                x=0.5,
                y=0.5,
                align="center",
                showarrow=False,
                xref="paper",
                yref="paper",
            )
            layout_individual["annotations"] = [annotation]
            data = []
        else:
            data = [
                dict(
                    type="scatter",
                    mode="lines+markers",
                    name="Gas Produced (mcf)",
                    x=df_meter.index,
                    y=df_meter['Value'],
                    line=dict(shape="spline", smoothing=1, width=1, color="#1254b0"),
                    marker=dict(symbol="diamond-open"),
                )
            ]
            layout_individual["title"] = main_graph_click['points'][0]['text']
            layout_individual["template"] = "plotly_dark"

        figure = go.Figure(data=data, layout=layout_individual)
        return figure


    # Triggered when type pull down selected. This will then populate the "IDS" of the alert ID options
    @app.callback(
        Output('alert_id', 'options'),
        [Input('alert_type', 'value')])
    def set_alert_options(selected_type):
        return [{'label': i, 'value': i} for i in map_meter_options[selected_type]]


    # Triggered from "def set_alert_options" since it will send over all the options for a given type. The default
    # value will be the first value in the list (e.g. [0]['value']
    @app.callback(
        Output('alert_id', 'value'),
        [Input('alert_id', 'options')])
    def set_alert_value(available_options):
        return available_options[0]['value']


def getpidata(meters):
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
            #df_meter = drop_numerical_outliers(df_meter, meter, z_thresh=3)

            # Rename the column (this was needed if we wanted to merge all the Value columns into a dataframe)
            renamed_col = (f"{meter.meter_name}_{meter.attribute}").replace(' ', '_')
            df_meter.rename(columns={"Value": f"{renamed_col}"}, inplace=True)

            if df_all.empty:
                df_all = df_meter
            else:
                df_all = pd.merge(df_all, df_meter[["Timestamp", renamed_col]], on="Timestamp", how='outer')

        except requests.exceptions.RequestException:
            print('HTTP Request failed')
            return df_all


main(None)

if __name__ == '__main__':
    meters = [PiRequest("R4", "Flow"), PiRequest("R11", "Flow"),
              PiRequest("R30", "Flow"), PiRequest("Afterbay", "Elevation"),
              PiRequest("Afterbay", "Elevation Setpoint"),
              PiRequest("Middle Fork", "Power - (with Ralston)")]
    app.run_server(debug=True)
    main(meters)


