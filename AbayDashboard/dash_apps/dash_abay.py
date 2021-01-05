import os
import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import copy
import requests
from datetime import datetime, timedelta, time
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

local = False
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
suffix_row = "_row"
suffix_button_id = "_button"
suffix_sparkline_graph = "_sparkline_graph"
suffix_count = "_count"
suffix_ooc_n = "_OOC_number"
suffix_ooc_g = "_OOC_graph"
suffix_indicator = "_indicator"
stopped_interval = 100 # How many data points to include

def populate_ooc(data, ucl, lcl):
    ooc_count = 0
    ret = []
    for i in range(len(data)):
        if data[i] >= ucl or data[i] <= lcl:
            ooc_count += 1
            ret.append(ooc_count / (i + 1))
        else:
            ret.append(ooc_count / (i + 1))
    return ret

def init_df():
    ret = {}
    for col in list(dfp[1:]):
        data = dfp[col]
        stats = data.describe()

        std = stats["std"].tolist()
        ucl = (stats["mean"] + 3 * stats["std"]).tolist()
        lcl = (stats["mean"] - 3 * stats["std"]).tolist()
        usl = (stats["mean"] + stats["std"]).tolist()
        lsl = (stats["mean"] - stats["std"]).tolist()

        ret.update(
            {
                col: {
                    "count": stats["count"].tolist(),
                    "data": data,
                    "mean": stats["mean"].tolist(),
                    "std": std,
                    "ucl": round(ucl, 3),
                    "lcl": round(lcl, 3),
                    "usl": round(usl, 3),
                    "lsl": round(lsl, 3),
                    "min": stats["min"].tolist(),
                    "max": stats["max"].tolist(),
                    "ooc": populate_ooc(data, ucl, lcl),
                }
            }
        )

    return ret

params = list(dfp)
state_dict = init_df()

def main(meters):
    site_lat = df.lat
    site_lon = df.lon
    locations_name = df.name
    locations_id = df.id
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

    alert_options = {
        'River Flows': ['R4', 'R11', 'R20', 'R30'],
        'Abay Management': ['Elevation', 'Oxbow', 'Rafting'],
        'Generation': ['Oxbow', 'French Meadows', 'Ralston']
    }


    layout = dict(
        automargin=True,
        margin=dict(l=40, r=40, b=10, t=40),
        hovermode="closest",
        plot_bgcolor="#F9F9F9",
        paper_bgcolor="#F9F9F9",
        legend=dict(font=dict(size=10), orientation="h"),
        title="Satellite Overview",
        mapbox=dict(
            accesstoken=mapbox_access_token,
            style="light",
            center=dict(lon=-119.05, lat=38.54),
            zoom=16,
        ),
    )

    fig = go.Figure()

    # This is for the large outer Ring
    fig.add_trace(go.Scattermapbox(
            lat=site_lat,
            lon=site_lon,
            mode='text+markers',                # A mode of "text" will just show hover
            marker=go.scattermapbox.Marker(
                size=17,
                color='rgb(255, 0, 0)',
                opacity=0.7
            ),
            text=locations_id,
            textfont=dict(
                family="sans serif",
                size=18,
                color="white"
            ),
            textposition="top center",
            hoverinfo='text'
        ))

    #This is for the small inner right.
    fig.add_trace(go.Scattermapbox(
            lat=site_lat,
            lon=site_lon,
            mode='markers',
            marker=go.scattermapbox.Marker(
                size=8,
                color='rgb(242, 177, 172)',
                opacity=0.7
            ),
            hoverinfo='text',
            text=[i for i in locations_name],
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

    subheader = dbc.Row(className='mb-2 mb-xl-3',
                        children=[
                            dbc.Col(className="col-auto d-none d-sm-block"),
                            html.H3("Dashboard"),
                            dbc.Col(className="col-auto ml-auto text-right nt-n1", children=[
                                        dcc.DatePickerSingle(
                                        id="date-picker",
                                        min_date_allowed=dt(2020, 4, 1),
                                        max_date_allowed=dt(2021, 9, 30),
                                        initial_visible_month=dt(2020, 4, 1),
                                        date=dt(2020, 4, 1).date(),
                                        display_format="MMMM D, YYYY",
                                    )
                            ]

                            )
                        ])

    app.layout = html.Main(
        className='content',
        children=[
            html.Div(className='container-fluid',
                     children=[
            subheader,
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
                                        min_date_allowed=dt(2014, 4, 1),
                                        max_date_allowed=dt(2014, 9, 30),
                                        initial_visible_month=dt(2014, 4, 1),
                                        date=dt(2014, 4, 1).date(),
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
                                                for i in locations_id
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
                                            placeholder="Select map layer",
                                        )
                                    ],
                                ),),width=2),
            dbc.Col(dbc.Row([
                            dbc.Col(dcc.Graph(figure=fig, id="map-graph", className="col s5"), width=6),
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

            html.Div(
                id="top-section-container",
                className="row",
                children=[
                    # Metrics summary
                    html.Div(
                        id="metric-summary-session",
                        className="col-8",
                        children=[
                            html.Div(className="section-banner", children="Process Control Metrics Summary"),
                            html.Div(
                                id="metric-div",
                                children=[
                                    generate_metric_list_header(),
                                    html.Div(
                                        id="metric-rows",
                                        children=[
                                            generate_metric_row_helper(stopped_interval, 1),
                                            generate_metric_row_helper(stopped_interval, 2),
                                            generate_metric_row_helper(stopped_interval, 3),
                                            generate_metric_row_helper(stopped_interval, 4),
                                            generate_metric_row_helper(stopped_interval, 5),
                                            generate_metric_row_helper(stopped_interval, 6),
                                            generate_metric_row_helper(stopped_interval, 7),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),
                    html.Div(
                        id="abay_storage",
                        className="col-4",
                        children=[
                            daq.Tank(
                                id='my-tank',
                                value=5,
                                min=0,
                                max=10,
                                style={'margin-left': '50px'},
                                units = "Elevation",
                                showCurrentValue = True
                            )
                        ]
                    )
                ]
            )]
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


    @app.callback(
        Output(component_id="alarm_modal", component_property="is_open", ),
        [Input(component_id="open_modal", component_property="n_clicks"), Input(component_id="close", component_property="n_clicks")],
        [State(component_id="alarm_modal", component_property="is_open")],
    )
    def toggle_modal(n1, n2, is_open):
        test = is_open
        if n1 or n2:
            return not is_open
        return is_open



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


    @app.callback(Output("map-graph", "figure"), [Input("mapbox_layer_dropdown", "value")])
    def update_mapbox_layer(value):
        current_map = copy.deepcopy(fig)
        if value is None or len(value) == 0:
            current_map.update_layout(
                mapbox_layers=[
                    {}
                ])
            return current_map
        current_map.update_layout(
            mapbox_layers=[
                {
                    "below": 'traces',
                    "sourcetype": "raster",
                    "sourceattribution": "United States Geological Survey",
                    "source": [
                        value[0]
                    ]
                }
            ])
        return current_map


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
                    line=dict(shape="spline", smoothing=2, width=1, color="#fac1b7"),
                    marker=dict(symbol="diamond-open"),
                ),
                dict(
                    type="scatter",
                    mode="lines+markers",
                    name="Oil Produced (bbl)",
                    x=df_meter.index,
                    y=df_meter['Value'],
                    line=dict(shape="spline", smoothing=2, width=1, color="#a9bb95"),
                    marker=dict(symbol="diamond-open"),
                ),
                dict(
                    type="scatter",
                    mode="lines+markers",
                    name="Water Produced (bbl)",
                    x=df_meter.index,
                    y=df_meter['Value'],
                    line=dict(shape="spline", smoothing=2, width=1, color="#92d8d8"),
                    marker=dict(symbol="diamond-open"),
                ),
            ]
            layout_individual["title"] = main_graph_click['points'][0]['text']

        figure = dict(data=data, layout=layout_individual)
        return figure


    # Triggered when type pull down selected. This will then populate the "IDS" of the alert ID options
    @app.callback(
        Output('alert_id', 'options'),
        [Input('alert_type', 'value')])
    def set_alert_options(selected_type):
        return [{'label': i, 'value': i} for i in alert_options[selected_type]]


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


# Build header
def generate_metric_list_header():
    return generate_metric_row(
        "metric_header",
        {"height": "3rem", "margin": "1rem 0", "textAlign": "center"},
        {"id": "m_header_1", "children": html.Div("Parameter")},
        {"id": "m_header_2", "children": html.Div("Count")},
        {"id": "m_header_3", "children": html.Div("Sparkline")},
        {"id": "m_header_4", "children": html.Div("OOC%")},
        {"id": "m_header_5", "children": html.Div("%OOC")},
        {"id": "m_header_6", "children": "Pass/Fail"},
    )


def generate_metric_row_helper(stopped_interval, index):
    item = params[index]

    div_id = item + suffix_row
    button_id = item + suffix_button_id
    sparkline_graph_id = item + suffix_sparkline_graph
    count_id = item + suffix_count
    ooc_percentage_id = item + suffix_ooc_n
    ooc_graph_id = item + suffix_ooc_g
    indicator_id = item + suffix_indicator

    return generate_metric_row(
        div_id,
        None,
        {
            "id": item,
            "className": "metric-row-button-text",
            "children": html.Button(
                id=button_id,
                className="metric-row-button",
                children=item,
                title="Click to visualize live SPC chart",
                n_clicks=0,
            ),
        },
        {"id": count_id, "children": "0"},
        {
            "id": item + "_sparkline",
            "children": dcc.Graph(
                id=sparkline_graph_id,
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
                                "x": state_dict["Batch"]["data"].tolist()[
                                     :stopped_interval
                                     ],
                                "y": state_dict[item]["data"][:stopped_interval],
                                "mode": "lines+markers",
                                "name": item,
                                "line": {"color": "#f4d44d"},
                            }
                        ],
                        "layout": {
                            "uirevision": True,
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
                            "paper_bgcolor": "rgba(0,0,0,0)",
                            "plot_bgcolor": "rgba(0,0,0,0)",
                        },
                    }
                ),
            ),
        },
        {"id": ooc_percentage_id, "children": "0.00%"},
        {
            "id": ooc_graph_id + "_container",
            "children": daq.GraduatedBar(
                id=ooc_graph_id,
                color={"gradient":True,"ranges":{"green":[0,30],"yellow":[30,70],"red":[70,100]}},
                showCurrentValue=True,
                max=100,
                value=50,
            ),
        },
        {
            "id": item + "_pf",
            "children": daq.Indicator(
                id=indicator_id, value=True, color="#91dfd2", size=12
            ),
        },
    )


def generate_metric_row(id, style, col1, col2, col3, col4, col5, col6):
    if style is None:
        style = {"height": "8rem", "width": "100%"}

    return html.Div(
        id=id,
        className="row metric-row",
        style=style,
        children=[
            html.Div(
                id=col1["id"],
                className="col-1",
                style={"margin-right": "2.5rem", "minWidth": "50px"},
                children=col1["children"],
            ),
            html.Div(
                id=col2["id"],
                style={"textAlign": "center"},
                className="col-1",
                children=col2["children"],
            ),
            html.Div(
                id=col3["id"],
                style={"height": "100%"},
                className="col-4",
                children=col3["children"],
            ),
            html.Div(
                id=col4["id"],
                style={},
                className="col-1",
                children=col4["children"],
            ),
            html.Div(
                id=col5["id"],
                style={"height": "100%", "margin-top": "5rem"},
                className="col-3",
                children=col5["children"],
            ),
            html.Div(
                id=col6["id"],
                style={"display": "flex", "justifyContent": "center"},
                className="col-1",
                children=col6["children"],
            ),
        ],
    )
main(None)

if __name__ == '__main__':
    meters = [PiRequest("R4", "Flow"), PiRequest("R11", "Flow"),
              PiRequest("R30", "Flow"), PiRequest("Afterbay", "Elevation"),
              PiRequest("Afterbay", "Elevation Setpoint"),
              PiRequest("Middle Fork", "Power - (with Ralston)")]
    app.run_server(debug=True)
    main(meters)


