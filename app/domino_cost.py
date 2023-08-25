import os
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List

import pandas as pd
import plotly.express as px
import requests
import solara as sl
import re

# For hitting the API
api_proxy = os.environ["DOMINO_API_PROXY"]

def get_domino_namespace() -> str:
    api_host = os.environ["DOMINO_API_HOST"]
    pattern = re.compile("(https?://)((.*\.)*)(?P<ns>.*?):(\d*)\/?(.*)")
    match = pattern.match(api_host)
    return match.group("ns")

namespace = get_domino_namespace()

base_url = f"http://domino-cost.{namespace}:9000"
assets_url = sl.reactive(f"{base_url}/asset")
allocations_url = sl.reactive(f"{base_url}/allocation")

auth_url = sl.reactive(f"{api_proxy}/account/auth/service/authenticate")

def get_token() -> str:
    orgs_res = requests.get(auth_url.value)
    return orgs_res.content.decode('utf-8')

def get_headers() -> Dict[str, str]: 
    headers = { 
        'X-Authorization': get_token()
    }
    return headers


# For interacting with the different scopes
breakdown_options = ["Top Projects", "User", "Organization"]
breakdown_to_param = {
    "Top Projects": "dominodatalab.com/project-name",
    "User": "dominodatalab.com/starting-user-username",
    "Organization": "dominodatalab.com/organization-name",
}


# For granular aggregations
window_options = ["Last 30 days", "Last 15 days", "Last week", "Today"]
window_to_param = {
    "Last 30 days": "30d",
    "Last 15 days": "15d",
    "Last week": "lastweek",
    "Today": "today",
}
window_choice = sl.reactive(window_options[0])


GLOBAL_FILTER_CHANGE_MAP = {
    "Organization": "Top Projects",
    "Top Projects": "User",
    "User": "Top Projects",
    "Execution Type": "User",
}

def get_all_organizations() -> List[str]:
    params = {
        "window": "30d",
        "aggregate": "label:dominodatalab.com/organization-name",
        "accumulate": True,
    }
    orgs_res = requests.get(allocations_url.value, params=params, headers=get_headers())
    orgs = orgs_res.json()["data"]
    return [org["name"] for org in orgs if not org["name"].startswith("__")]


ALL_ORGS = [""] + get_all_organizations()
filtered_label = sl.reactive("")
filtered_value = sl.reactive("")


def set_global_filters(click_data: Dict) -> None:
    filtered_label.set(click_data["seriesName"])  # The chart they clicked
    filtered_value.set(click_data["name"])  # The bar within the chart they clicked


def clear_filters() -> None:
    filtered_label.set("")
    filtered_value.set("")


def set_filter(params: Dict) -> None:
    if filtered_value.value and filtered_label.value:
        param_label = breakdown_to_param[filtered_label.value]
        params["filter"] = f'label[{param_label}]:"{filtered_value.value}"'



def format_datetime(dt_str: str) -> str:
    datetime_object = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%SZ")
    return datetime_object.strftime("%m/%d %I:%M %p")


def get_cost_per_breakdown(breakdown_for: str) -> Dict[str, float]:
    params = {
        "window": window_to_param[window_choice.value],
        "aggregate": f"label:{breakdown_for}",
        "accumulate": True,
    }
    set_filter(params)
    res = requests.get(allocations_url.value, params=params, headers=get_headers())
    
    data = res.json()["data"]
    return {costData["name"]: round(costData["totalCost"], 2) for costData in data if not costData["name"].startswith("__")}
    

def get_overall_cost() -> Dict[str, float]:
    params = {
        "window": window_to_param[window_choice.value],
        "accumulate": True,
    }
    set_filter(params)

    res = requests.get(assets_url.value, params=params, headers=get_headers())
        
    data = res.json()["data"]
    
    return {costData["type"]: round(costData["totalCost"], 2) for costData in data}

def to_date(date_string: str) -> str:
    """Converts minute-level date string to day level

    ex:
       to_date(2023-04-28T15:05:00Z) -> 2023-04-28
    """
    dt = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%SZ")
    return dt.strftime("%Y-%m-%d")


def add_day(date: str, days: int) -> str:
    dt = datetime.strptime(date, "%Y-%m-%d")
    dt_new = dt + timedelta(days=days)
    return dt_new.strftime("%Y-%m-%d")


def get_daily_cost() -> pd.DataFrame:
    window = window_to_param[window_choice.value]
    params = {
        "window": window,
    }
    set_filter(params)

    res = requests.get(allocations_url.value, params=params, headers=get_headers())
    data = res.json()["data"]

    # May not have all historical days
    alocs = [day for day in data if day]
    
    # Route returns data non-cumulatively. We make it cumulative by summing over the
    # returned windows (could be days, hours, weeks etc)
    daily_costs = defaultdict(dict)

    cpu_costs = ["cpuCost", "cpuCostAdjustment"]
    gpu_costs = ["gpuCost", "gpuCostAdjustment"]
    storage_costs = ["pvCost", "pvCostAdjustment", "ramCost", "ramCostAdjustment"]

    costs = {"CPU": cpu_costs, "GPU": gpu_costs, "Storage": storage_costs}

    # Gets the overall cost per day
    for aloc in alocs:
        start = aloc["window"]["start"]
        for cost_type, cost_keys in costs.items():
            if cost_type not in daily_costs[start]:
                daily_costs[start][cost_type] = 0.0
            daily_costs[start][cost_type] += round(
                sum(aloc.get(cost_key,0) for cost_key in cost_keys), 2
            )

    # Cumulative sum over the daily costs
    cumulative_daily_costs = pd.DataFrame(daily_costs).T.sort_index()

    
    cumulative_daily_costs["CPU"] = (cumulative_daily_costs["CPU"].cumsum() if "CPU" in cumulative_daily_costs else 0)
    cumulative_daily_costs["GPU"] = (cumulative_daily_costs["GPU"].cumsum() if "GPU" in cumulative_daily_costs else 0)
    cumulative_daily_costs["Storage"] = (cumulative_daily_costs["Storage"].cumsum() if "Storage" in cumulative_daily_costs else 0)

    # Unless we are looking at today granularity, rollup values to the day level
    # (they are returned at the 5min level)
    if window != "today":
        cumulative_daily_costs.index = cumulative_daily_costs.index.map(to_date)
        cumulative_daily_costs = cumulative_daily_costs.groupby(level=0).max()

    return cumulative_daily_costs



def get_execution_cost_table() -> pd.DataFrame:
    params = {
        "window": window_to_param[window_choice.value],
        "aggregate": (
            "label:dominodatalab.com/workload-type,"
            "label:dominodatalab.com/starting-user-username,"
            "label:dominodatalab.com/project-id"
        ),
        "accumulate": True,
    }
    set_filter(params)

    
    res = requests.get(allocations_url.value, params=params, headers=get_headers())
    aloc_data = res.json()["data"]
    
    exec_data = []

    cpu_cost_key = ["cpuCost", "gpuCost"]
    gpu_cost_key = ["cpuCostAdjustment", "gpuCostAdjustment"]
    storage_cost_keys = ["pvCost", "ramCost", "pvCostAdjustment", "ramCostAdjustment"]

    data = [costData for costData in aloc_data if not costData["name"].startswith("__")]
    
    for costData in data:
        workload_type, username, project_id = costData["name"].split("/")
        cpu_cost = round(sum([costData.get(k,0) for k in cpu_cost_key]), 2)
        gpu_cost = round(sum([costData.get(k,0) for k in gpu_cost_key]), 2)
        compute_cost = round(cpu_cost + gpu_cost, 2)
        storage_cost = round(sum([costData.get(k,0) for k in storage_cost_keys]), 2)
        exec_data.append({
            "TYPE": workload_type,
            "USER": username,
            "START": costData["window"]["start"],
            "END": costData["window"]["end"],
            "CPU_COST": f"${cpu_cost}",
            "GPU_COST": f"${gpu_cost}",
            "COMPUTE_COST": f"${compute_cost}",
            "STORAGE_COST": f"${storage_cost}",
            "PROJECT_ID": project_id,

        })
    execution_costs = pd.DataFrame(exec_data)
    if all(windowKey in execution_costs for windowKey in ("START", "END")):
        execution_costs["START"] = execution_costs["START"].apply(format_datetime)
        execution_costs["END"] = execution_costs["END"].apply(format_datetime)
    return execution_costs

@sl.component()
def Executions() -> None:
    execution_cost = get_execution_cost_table()
    sl.DataFrame(execution_cost)

@sl.component()
def DailyCostBreakdown() -> None:
    daily_cost = get_daily_cost()
    if not daily_cost.empty:
        fig = px.bar(
            daily_cost,
            labels={
                "index": "Date",
                "value": "Cost ($)",
            },
            title="Overall Cost (Cumulative)",
            color_discrete_sequence=px.colors.qualitative.D3,
        )

        x0=daily_cost.index.min()
        x1=daily_cost.index.max()

        if window_to_param[window_choice.value] != "today" :
            x0= add_day(daily_cost.index.min(), -1)
            x1= add_day(daily_cost.index.max(), 1)
        
        sl.FigurePlotly(fig)
    

@sl.component()
def SingleCost(name: str, cost: float) -> None:
    with sl.Column():
        cost_ = f"## ${cost}" if name == "Total" else f"#### ${cost}"
        sl.Markdown(cost_)
        name_ = f"### {name}" if name == "Total" else name
        sl.Markdown(name_)


@sl.component()
def TopLevelCosts() -> None:
    costs = get_overall_cost()
    with sl.Row(justify="space-around"):
        SingleCost("Total", round(sum(list(costs.values())), 2))
        for name, cost in costs.items():
            SingleCost(name, cost)


@sl.component()
def OverallCosts() -> None:
    with sl.Column():
        with sl.Card():
            TopLevelCosts()
        with sl.Card():
            DailyCostBreakdown()
    
    
@sl.component()
def CostBreakdown() -> None:
    with sl.Card("Cost Usage"):
        with sl.Columns([1, 1, 1]):
            for name, breakdown_choice_ in breakdown_to_param.items():
                costs = get_cost_per_breakdown(breakdown_choice_)
                cost_values = list(costs.values())
                option = {
                    "title": {"text": name},
                    "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
                    "legend": {},
                    "grid": {
                        "left": "3%",
                        "right": "4%",
                        "bottom": "3%",
                        "containLabel": True,
                    },
                    "xAxis": {"type": "value", "boundaryGap": [0, 0.01]},
                    "yAxis": {"type": "category", "data": list(costs.keys())},
                    "series": [
                        {
                            "type": "bar",
                            "data": cost_values,
                            "stack": "y",
                            "name": name,
                        },
                    ]
                }
                sl.FigureEcharts(option, on_click=set_global_filters)


@sl.component()
def Page() -> None:
    sl.Title("Cost Analysis")
    sl.Markdown(
        "# Domino Cost Management Report",
        style="display: inline-block; margin: 0 auto;",
    )
    with sl.Column(style="width:15%"):
        with sl.Row():
            sl.Select(label="Window", value=window_choice, values=window_options)
            if filtered_label.value and filtered_value.value:
                sl.Button(
                    f"{filtered_label.value}: {filtered_value.value} x",
                    on_click=clear_filters,
                )
    with sl.Column():
        OverallCosts()
        CostBreakdown()
        with sl.Card("Executions"):
            Executions()
            
