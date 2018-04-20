
title = "CBF Sensors Dashboard"
metadata = 'charset="UTF-8" http-equiv="refresh" content="5"'
# JS links
js_link = {
    "codepen": 'https://codepen.io/mmphego/pen/KoJoZq.js',
    "jquery": "http://code.jquery.com/jquery-1.10.1.min.js"
}
# CSS links
css_link = 'https://codepen.io/mmphego/pen/KoJoZq.css'

# Style colors
COLORS = [
    {   # NOMINAL
        'background': 'green',
        'color': 'white',
    },
    {
        # WARN
        'background': 'orange',
        'color': 'white',
    },
    {
        # ERROR
        'background': 'red',
        'color': 'white',
    },
    {
        # FAILURE
        'background': 'white',
        'color': 'red',
    },
    {
        # Other
        'background': 'white',
        'color': 'black',
    },
]

refresh_time = 10000