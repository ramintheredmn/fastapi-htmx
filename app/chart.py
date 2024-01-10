import plotly.graph_objects as go
import datetime
def make_chart(x_data: list[int], y_data: list[int]):
    x_datetime = [datetime.datetime.fromtimestamp(x) for x in x_data]
    fig = go.Figure(data=go.Scatter(x=x_datetime, y=y_data))
    fig.update_xaxes(calendar='jalali')
    html = fig.to_html(
        include_plotlyjs=False,
        full_html=False,
    )

    return html
