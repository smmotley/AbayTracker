import dash
from dash.dependencies import Output, Input
import dash_core_components as dcc
import dash_html_components as html
import plotly
import random
import plotly.graph_objs as go
from collections import deque
import pandas_datareader.data as web
import datetime

X = deque(maxlen=100)
X.append(1)
Y = deque(maxlen=20)
Y.append(1)
app = dash.Dash()

#app = DjangoDash('DashTutorial')
#df = df.drop("Symbol", axis=1)

# The contents of each element in the html is called children
app.layout = html.Div(children=[
    dcc.Graph(id='live-graph', animate=True),
    dcc.Interval(
        id="graph-update",
        interval=1000,
        n_intervals=0
    )
])

# Says, when you get any input from id "input", return the following (from function) to
# the div with an id of "output-graph"
@app.callback(
    Output(component_id='live-graph', component_property='figure'),
    [Input(component_id='graph-update', component_property='n_intervals')]
)
def update_graph(somevalue):
    X.append(X[-1] + 1)
    Y.append(Y[-1] + Y[-1] * random.uniform(-0.1, 0.1))

    data = go.Scatter(
        x=list(X),
        y=list(Y),
        name='Scatter',
        mode='lines+markers'
    )

    return {'data': [data], 'layout': go.Layout(xaxis=dict(range=[min(X), max(X)]),
                                                yaxis=dict(range=[min(Y), max(Y)]), )}


external_css = ["https://cdnjs.cloudflare.com/ajax/libs/materialize/0.100.2/css/materialize.min.css"]
for css in external_css:
    app.css.append_css({"external_url": css})

external_js = ['https://cdnjs.cloudflare.com/ajax/libs/materialize/0.100.2/js/materialize.min.js']
for js in external_css:
    app.scripts.append_script({'external_url': js})


if __name__ == '__main__':
    app.run_server(debug=True)
