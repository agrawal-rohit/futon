from bokeh.plotting import figure
from bokeh.models import HoverTool, CustomJS, Range1d
from math import pi, inf


def create_candle_plot(
    asset, fig_width=1000, fig_height=600, colored=True
):
    if colored:
        INCREASING_COLOR = "#4CAF50"
        DECREASING_COLOR = "#F44336"
    else:
        INCREASING_COLOR = "#575757"
        DECREASING_COLOR = "#575757"

    p = figure(
        plot_width=fig_width,
        plot_height=fig_height,
        x_axis_type="datetime",
        y_axis_location="right",
        tools="xpan,xwheel_zoom,reset,save",
        active_drag="xpan",
        active_scroll="xwheel_zoom",
        title="{}/{} | Candlestick plot".format(asset.base_asset, asset.quote_asset),
        toolbar_location="above",
    )

    # Set initial axes
    p.grid.grid_line_alpha = 0.3
    p.x_range.follow = "end"
    p.x_range.range_padding = 0
    x_start = asset._data_source_increasing.data["timestamp"][-50]
    x_end = asset._data_source_increasing.data["timestamp"][-1]
    p.x_range = Range1d(x_start, x_end)

    y_min = inf
    y_max = -inf
    dates = asset.scaling_source.data["timestamp"]
    lows = asset.scaling_source.data["low"]
    highs = asset.scaling_source.data["high"]
    for i in range(0, len(dates)):
        if x_start <= dates[i] and dates[i] <= x_end:
            y_max = max(highs[i], y_max)
            y_min = min(lows[i], y_min)

    pad = (y_max - y_min) * 0.05
    final_y_max = y_max + pad
    final_y_min = y_min - pad
    p.y_range = Range1d(final_y_min, final_y_max)

    bar_width = asset.provider.timeframe_seconds * 1000 * 0.6  # seconds in ms

    p.segment(
        x0="timestamp",
        y0="high",
        x1="timestamp",
        y1="low",
        source=asset._data_source_increasing,
        color=INCREASING_COLOR,
    )
    p.segment(
        x0="timestamp",
        y0="high",
        x1="timestamp",
        y1="low",
        source=asset._data_source_decreasing,
        color=DECREASING_COLOR,
    )

    inc_bar = p.vbar(
        x="timestamp",
        width=bar_width,
        top="open",
        bottom="close",
        fill_color=INCREASING_COLOR,
        line_color=INCREASING_COLOR,
        source=asset._data_source_increasing,
        name="price",
    )
    dec_bar = p.vbar(
        x="timestamp",
        width=bar_width,
        top="open",
        bottom="close",
        fill_color=DECREASING_COLOR,
        line_color=DECREASING_COLOR,
        source=asset._data_source_decreasing,
        name="price",
    )

    p.add_tools(
        HoverTool(
            renderers=[inc_bar, dec_bar],
            tooltips=[
                ("Timestamp", "@timestamp{%F}"),
                ("Open", "@open{$0,0.00000}"),
                ("Close", "@close{$0,0.00000}"),
                ("Volume", "@volume{($ 0.00000 a)}"),
            ],
            formatters={"@timestamp": "datetime"},
        )
    )

    # Kline plot callbacks
    y_range_scaling_callback = CustomJS(
        args={"y_range": p.y_range, "source": asset.scaling_source},
        code="""
        clearTimeout(window._autoscale_timeout);
        
        var Date = source.data.timestamp,
            Low = source.data.low,
            High = source.data.high,
            start = cb_obj.start,
            end = cb_obj.end,
            min = Infinity,
            max = -Infinity;

        for (var i=0; i < Date.length; ++i) {
            if (start <= Date[i] && Date[i] <= end) {
                max = Math.max(High[i], max);
                min = Math.min(Low[i], min);
            }
        }
        var pad = (max - min) * .05;
        window._autoscale_timeout = setTimeout(function() {
            y_range.start = min - pad;
            y_range.end = max + pad;
        });
    """,
    )

    # Finalise the figure
    p.x_range.js_on_change("start", y_range_scaling_callback)

    x_range_callback = CustomJS(
        args={"x_range": p.x_range, "interval": asset.provider.timeframe_seconds},
        code="""            
        var latest_date = cb_obj.data["timestamp"][cb_obj.data["timestamp"].length - 1]

        var new_range_start = new Date(latest_date - interval * 1000 * 50);
        var new_range_end = new Date(latest_date + interval * 1000 * 5);

        x_range.start = new_range_start.getTime()
        x_range.end = new_range_end.getTime()

        x_range.change.emit()
    """,
    )

    asset.scaling_source.js_on_change("streaming", x_range_callback)

    # Volume bar plot
    p2 = figure(
        x_axis_type="datetime",
        y_axis_location="right",
        tools="",
        toolbar_location=None,
        plot_width=fig_width,
        plot_height=200,
        x_range=p.x_range,
    )
    p2.xaxis.major_label_orientation = pi / 4

    p2.vbar(
        x="timestamp",
        width=bar_width,
        top="volume",
        color=INCREASING_COLOR,
        source=asset._data_source_increasing,
        alpha=0.5,
    )
    p2.vbar(
        x="timestamp",
        width=bar_width,
        top="volume",
        color=DECREASING_COLOR,
        source=asset._data_source_decreasing,
        alpha=0.5,
    )

    return p, p2
