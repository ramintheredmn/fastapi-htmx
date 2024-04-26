import plotly.graph_objects as go

def make_chart(x_data, y_data):
    
    fig = go.Figure(data=go.Scatter(x=x_data, y=y_data))

    # Update layout for the chart to take the full area
    fig.update_layout(
        margin=dict(l=8, r=10, t=10, b=4), # Set margins to 0
        xaxis={'type': 'date'} ,
        template = "plotly_white"
        
    )
    config = {'scrollZoom': True}
    # set datetime to Iranian datetime
    fig.update_xaxes(calendar='jalali')

    html = fig.to_html(
        include_plotlyjs=False,
        full_html=False,
        config=config
    )

    return html

def make_chart_radar_hr (hr_mean_1 , hr_mean_2 , hr_mean_3 , hr_mean_4 , hr_mean_5 , hr_quantile , hr_min) :
    categories = ['00:8','8:12','12:16','16:20', '20:24']

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=[hr_mean_1 , hr_mean_2 , hr_mean_3 , hr_mean_4 , hr_mean_5],
        theta=categories,
        fill='toself',
        name='Heart Rate' , 
        hovertemplate='Mean Heart Rate: %{r}<br>Day Hours: %{theta}'
    ))

    fig.update_layout(
    polar=dict(
        radialaxis=dict(
        visible=True,
        range=[hr_min, hr_quantile]
        )),
    showlegend=False,

    )

    html = fig.to_html(
    include_plotlyjs=False,
    full_html=False
    )
    return html
def make_chart_radar_step (step_mean_1 , step_mean_2 , step_mean_3 , step_mean_4 , step_mean_5 , step_quantile , step_min) :
    categories = ['00:8','8:12','12:16','16:20', '20:24']

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=[step_mean_1 , step_mean_2 , step_mean_3 , step_mean_4 , step_mean_5],
        theta=categories,
        fill='toself',
        name='Steps' , 
        hovertemplate='Mean Number Of Steps: %{r}<br>Day Hours: %{theta}' ,
        line=dict(color='red')
    ))

    fig.update_layout(
    polar=dict(
        radialaxis=dict(
        visible=True,
        range=[step_min, step_quantile]
        )),
    showlegend=False
    )
    html = fig.to_html(
    include_plotlyjs=False,
    full_html=False
    )
    return html
