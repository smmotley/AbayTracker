import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import dash
import dash_bootstrap_components as dbc
import plotly.express as px
data_canada = px.data.gapminder().query("country == 'Canada'")
import pandas as pd


app = dash.Dash(
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        external_scripts=["https://code.jquery.com/jquery-3.5.1.min.js",
                          ],
        suppress_callback_exceptions = True
    )
server = app.server



years = [1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002, 2003,
         2004]

data = {'years': years, 'float': [500, 500, 500, 500, 500, 500, 500, 500, 500, 500],
        'level': [100, 150, 190, 400, 500, 10, 430, 420, 240, 250]}
data = {'years': years, 'float': [1175, 1175, 1175, 1175, 1175, 1175, 1175, 1175, 1175, 1175,],
             'level': [1170, 1170, 1170, 1170, 1170, 1170, 1170, 1170, 1170, 1168,]}
df = pd.DataFrame(data=data)

df["new_float"] = df.float - df.level

fig = go.Figure()
fig.add_trace(go.Bar(x=years,
                y=df['level'],
                name='Elevation',
                marker_color='#2c7be5',
                width=0.1,
                ))
fig.add_trace(go.Bar(x=years,
                y=df['new_float'],
                name='China',
                marker_color='#061325',
                width=0.1,
                ))

fig.update_layout(
    title=None,
    xaxis_tickfont_size=14,
    showlegend=False,
    yaxis=dict(
        title=None,
        titlefont_size=16,
        tickfont_size=14,
        showline=False,
        showgrid=False,
        zeroline=False,
        showticklabels=False,
        visible=False,
    ),
    xaxis=dict(
        showline=False,
        showgrid=False,
        zeroline=False,
        showticklabels=False,
        visible=False,  # numbers below
    ),
    legend=None,
    yaxis_range=[1168,1175],
    barmode='relative',
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    bargap=0.05, # gap between bars of adjacent location coordinates.
    bargroupgap=0.05, # gap between bars of the same location coordinate.
)

app.layout = html.Div([
    html.H1('Square Root Slider Graph'),
    dcc.Graph(figure=fig, id='slider-graph', animate=True, style={"backgroundColor": "#1a2d46", 'color': '#ffffff'}),
    dcc.Slider(
        id='slider-updatemode',
        marks={i: '{}'.format(i) for i in range(20)},
        max=20,
        value=2,
        step=1,
        updatemode='drag',
    ),
])


# @app.callback(
#                Output('slider-graph', 'figure'),
#               [Input('slider-updatemode', 'value')])
# def display_value(value):
#
#
#     x = []
#     for i in range(value):
#         x.append(i)
#
#     y = []
#     for i in range(value):
#         y.append(i*i)
#
#     graph = go.Scatter(
#         x=x,
#         y=y,
#         name='Manipulate Graph'
#     )
#     layout = go.Layout(
#         paper_bgcolor='#27293d',
#         plot_bgcolor='rgba(0,0,0,0)',
#         xaxis=dict(range=[min(x), max(x)]),
#         yaxis=dict(range=[min(y), max(y)]),
#         font=dict(color='white'),
#
#     )
#     return {'data': [graph], 'layout': layout}

if __name__ == '__main__':
    app.run_server(debug=True)