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
else:
    app = DjangoDash('dash_django', suppress_callback_exceptions=True, add_bootstrap_links=True)
    df = pd.read_csv(staticfiles_storage.path("data/pcwa_locations.csv"))  # make sure this is in the static dir

main_dir = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..'))
mapbox_access_token = "pk.eyJ1Ijoic21vdGxleSIsImEiOiJuZUVuMnBBIn0.xce7KmFLzFd9PZay3DjvAA"

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

modal = html.Div(
    [
        dbc.Button("Open modal", id="open_modal"),
        dbc.Modal(
            html.Div(id="alarm_modal_content",
            children=[
                dbc.ModalHeader("Change Alarm Values", id='modal_header_text'),
                dbc.ModalBody(id="modal_body", children=[
                    html.Div(
                        className="div-for-dropdown",
                        children=[
                            dcc.Dropdown(
                                id="alert_type",
                                options=[
                                    {"label": i, "value": i}
                                    for i in alert_options.keys()
                                ],
                                value="River Flows",
                                placeholder="Select alarm for",
                            )
                        ]
                    ),
                    html.Div(
                        className="div-for-dropdown",
                        children=[
                            dcc.Dropdown(
                                id="alert_id",
                                options=[
                                ],
                                placeholder="Select alarm for",
                            )
                        ]
                    ),
                    html.Div(
                        className="alarm_input",
                        children=[
                            dbc.Input(id="alarmInputHi", placeholder="Upper Limit", type="text")
                        ]
                    ),
                    html.Div(
                        className="alarm_input",
                        children=[
                            dbc.Input(id="alarmInputLow", placeholder="Lower Limit", type="text")
                        ]
                    )
                ]),
                dbc.ModalFooter(
                    dbc.Button("Close", id="close", className="ml-auto")
                ),
            ]),
            id="alarm_modal",
            centered=True
        ),
    ]
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
                                        placeholder="Select alarm for",
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

    ],
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





if __name__ == '__main__':
    app.run_server(debug=True)
