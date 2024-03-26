import plotly.graph_objects as go


def make_chart(
    x_data,
    y_data,
):
    fig = go.Figure(data=go.Scatter(x=x_data, y=y_data))


    html = fig.to_html(
        include_plotlyjs=False,
        full_html=False,
    )

    return html
