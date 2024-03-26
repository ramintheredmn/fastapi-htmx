import plotly.graph_objects as go
from datetime import datetime


def make_chart(x_data, y_data):
    
    fig = go.Figure(data=go.Scatter(x=x_data, y=y_data))

    # Update layout for the chart to take the full area
    fig.update_layout(
        margin=dict(l=8, r=10, t=10, b=4), # Set margins to 0
        xaxis={'type': 'date'}
        
    )
    fig.update_xaxes(calendar='jalali')

    html = fig.to_html(
        include_plotlyjs=False,
        full_html=False,
    )

    return html
