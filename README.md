# CBF-System-Dashboard

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/087b7fe788d4415c8369dc0e365dff4c)](https://app.codacy.com/app/mmphego/CBF-System-Dashboard?utm_source=github.com&utm_medium=referral&utm_content=ska-sa/CBF-System-Dashboard&utm_campaign=Badge_Grade_Settings)
[![Build Status](https://travis-ci.org/ska-sa/CBF-System-Dashboard.svg?branch=master)](https://travis-ci.org/ska-sa/CBF-System-Dashboard)
[![LICENSE](https://img.shields.io/github/license/ska-sa/cbf-system-dashboard.svg?style=flat)](LICENSE)

Simplified Docker based, CBF Sensor dashboard which polls the CBF sensors every x seconds and uses [Dash](https://plot.ly/dash) for its front-end.

![cbfdash](dashboard.png)


## What is Dash

**Dash is a Python framework for building analytical web applications. No JavaScript/HTML required.**

Build on top of Plotly.js, React, and Flask, Dash ties modern UI elements like dropdowns, sliders, and graphs directly to your analytical python code.

To learn more about Dash, read the [extensive announcement letter](https://medium.com/@plotlygraphs/introducing-dash-5ecf7191b503) or [jump in with the user guide](https://plot.ly/dash).

View the [Dash User Guide](https://plot.ly/dash). It's chock-full of examples, pro tips, and guiding principles.

More info visit: [Dash](https://github.com/plotly/dash)

### Usage

#### Build

Build both the front-end and back-end docker images.

```shell
make bootstrap
```

#### Run

```shell
make run
```

## Feedback

Feel free to fork it or send me PR to improve it.
