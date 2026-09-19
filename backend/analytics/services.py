from metrics.query_engine import execute_metric


def merge_filters(default_filters, runtime_filters):
    merged = []
    merged.extend(default_filters or [])
    merged.extend(runtime_filters or [])
    return merged


def chart_dataset(chart, runtime_filters=None, use_cache=True):
    dimension_ids = list(chart.dimensions.values_list("id", flat=True))
    filters = merge_filters(chart.default_filters, runtime_filters)

    result = execute_metric(
        chart.metric,
        dimension_ids=dimension_ids,
        filters=filters,
        limit=chart.limit,
        use_cache=use_cache,
    )

    return {
        "chart": {
            "id": str(chart.id),
            "name": chart.name,
            "chart_type": chart.chart_type,
            "config": chart.config,
            "sort_order": chart.sort_order,
        },
        "dataset": result,
    }


def dashboard_dataset(dashboard, runtime_filters=None, use_cache=True):
    filters = merge_filters(dashboard.global_filters, runtime_filters)
    items = []

    for item in dashboard.items.select_related("chart", "chart__metric").prefetch_related(
        "chart__dimensions"
    ).all():
        chart_result = chart_dataset(
            item.chart,
            runtime_filters=filters,
            use_cache=use_cache,
        )
        items.append(
            {
                "item_id": str(item.id),
                "position": item.position,
                "title_override": item.title_override,
                "config_override": item.config_override,
                **chart_result,
            }
        )

    return {
        "dashboard": {
            "id": str(dashboard.id),
            "name": dashboard.name,
            "description": dashboard.description,
            "layout": dashboard.layout,
            "global_filters": dashboard.global_filters,
        },
        "items": items,
    }


def drilldown(chart, runtime_filters=None, level=None, use_cache=True):
    dimensions = list(chart.dimensions.order_by("sort_order", "name"))
    if not dimensions:
        return chart_dataset(chart, runtime_filters, use_cache)

    if level is None:
        level = 1

    level = max(1, min(int(level), len(dimensions)))
    selected = dimensions[:level]

    result = execute_metric(
        chart.metric,
        dimension_ids=[dimension.id for dimension in selected],
        filters=merge_filters(chart.default_filters, runtime_filters),
        limit=chart.limit,
        use_cache=use_cache,
    )

    return {
        "chart": {
            "id": str(chart.id),
            "name": chart.name,
            "chart_type": chart.chart_type,
        },
        "drill_level": level,
        "max_level": len(dimensions),
        "dimensions": [
            {
                "id": str(d.id),
                "name": d.name,
                "field": d.field.name,
            }
            for d in selected
        ],
        "dataset": result,
    }
