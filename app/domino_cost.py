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
breakdown_options = ["Execution Type", "Top Projects", "User", "Organization"]
breakdown_to_param = {
    # "Execution Type": "dominodatalab_com_workload_type",
    "Top Projects": "dominodatalab_com_project_name",
    "User": "dominodatalab_com_starting_user_username",
    "Organization": "dominodatalab_com_organization_name",
}
#breakdown_choice = sl.reactive(breakdown_options[0])


# For granular aggregations
window_options = ["Last 30 days", "Last 15 days", "Last week", "Today"]
window_to_param = {
    "Last 30 days": "30d",
    "Last 15 days": "15d",
    "Last week": "lastweek",
    "Today": "today",
}
window_choice = sl.reactive(window_options[0])

# TODO: This should be replaced with real values
EXECUTION_COST_MAX = os.getenv("DOMINO_EXECUTION_COST_MAX", None)
PROJECT_MAX_SPEND = os.getenv("DOMINO_PROJECT_MAX_SPEND", 8)
ORG_MAX_SPEND = os.getenv("DOMINO_ORG_MAX_SPEND", 500)

BREAKDOWN_SPEND_MAP = {"Top Projects": PROJECT_MAX_SPEND, "Organization": ORG_MAX_SPEND}
# If the user changes the global filter by clicking on a bar in the breakdown chart
# (lefthand chart), we want to change the breakdown to something else
GLOBAL_FILTER_CHANGE_MAP = {
    "Organization": "Top Projects",
    "Top Projects": "User",
    "User": "Top Projects",
    "Execution Type": "User",
}

def get_all_organizations() -> List[str]:
    params = {
        "window": "30d",
        "aggregate": "label:dominodatalab_com_organization_name",
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



def _format_datetime(dt_str: str) -> str:
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
        "aggregate": "category",
        "accumulate": True,
    }
    set_filter(params)

    res = requests.get(assets_url.value, params=params, headers=get_headers())
    
    data = res.json()["data"]
    
    return {costData["type"]: round(costData["totalCost"], 2) for costData in data}

def _to_date(date_string: str) -> str:
    """Converts minute-level date string to day level

    ex:
       _to_date(2023-04-28T15:05:00Z) -> 2023-04-28
    """
    dt = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%SZ")
    return dt.strftime("%Y-%m-%d")


def _add_day(date: str, days: int) -> str:
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
    df = pd.DataFrame(daily_costs).T.sort_index()

    
    df["CPU"] = (df["CPU"].cumsum() if "CPU" in df else 0)
    df["GPU"] = (df["GPU"].cumsum() if "GPU" in df else 0)
    df["Storage"] = (df["Storage"].cumsum() if "Storage" in df else 0)

    # Unless we are looking at today granularity, rollup values to the day level
    # (they are returned at the 5min level)
    if window != "today":
        df.index = df.index.map(_to_date)
        df = df.groupby(level=0).max()

    return df



def get_execution_cost_table() -> pd.DataFrame:
    # TODO: Break down further by execution id
    # label:dominodatalab_com_execution_id
    params = {
        "window": window_to_param[window_choice.value],
        "aggregate": (
            "label:dominodatalab_com_workload_id,"  
            "label:dominodatalab_com_workload_type,"
            "label:dominodatalab_com_starting_user_username,"
            "label:dominodatalab_com_project_id"
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
        workload_id, workload_type, username, project_id = costData["name"].split("/")
        cpu_cost = round(sum([costData.get(k,0) for k in cpu_cost_key]), 2)
        gpu_cost = round(sum([costData.get(k,0) for k in gpu_cost_key]), 2)
        compute_cost = round(cpu_cost + gpu_cost, 2)
        storage_cost = round(sum([costData.get(k,0) for k in storage_cost_keys]), 2)
        # waste = f"{((1-costData['totalEfficiency'])*100)}%" TODO: CHECK WHERE SHOULD WE GET THIS VALUE
        exec_data.append({
            "TYPE": workload_type,
            "USER": username,
            "START": costData["window"]["start"],
            "END": costData["window"]["end"],
            "CPU_COST": f"${cpu_cost}",
            "GPU_COST": f"${gpu_cost}",
            "COMPUTE_COST": f"${compute_cost}",
            # "COMPUTE_WASTE": waste,
            "STORAGE_COST": f"${storage_cost}",
            "WORKLOAD_ID": workload_id,
            "PROJECT_ID": project_id,

        })
    df = pd.DataFrame(exec_data)
    if all(windowKey in df for windowKey in ("START", "END")):
        df["START"] = df["START"].apply(_format_datetime)
        df["END"] = df["END"].apply(_format_datetime)
    return df

@sl.component()
def Executions() -> None:
    df = get_execution_cost_table()
    sl.DataFrame(df)

@sl.component()
def DailyCostBreakdown() -> None:
    df = get_daily_cost()
    if not df.empty:
        fig = px.bar(
            df,
            labels={
                "index": "Date",
                "value": "Cost ($)",
            },
            title="Overall Cost (Cumulative)",
            color_discrete_sequence=px.colors.qualitative.D3,
        )


        x0=df.index.min()
        x1=df.index.max()

        if window_to_param[window_choice.value] != "today" :
            x0= _add_day(df.index.min(), -1)
            x1= _add_day(df.index.max(), 1)
        
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
    # with sl.Columns([2, 1, 1, 1]):
    with sl.Row(justify="space-around"):
        # with sl.Card():
        SingleCost("Total", round(sum(list(costs.values())), 2))
        for name, cost in costs.items():
            # with sl.Card():
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
    # with sl.Row(gap="1px", justify="space-around"):
    with sl.Card("Cost Usage"):
        with sl.Columns([1, 1, 1]):
            for name, breakdown_choice_ in breakdown_to_param.items():
                # with sl.Card(f"Cost Usage - {name}", margin=10):
                # sl.Select(label="", value=breakdown_choice, values=breakdown_options)
                costs = get_cost_per_breakdown(breakdown_choice_)
                cost_values = list(costs.values())
                max_spend = BREAKDOWN_SPEND_MAP.get(name, 1e1000)
                overflow_values = [v - max_spend for v in cost_values]
                overflow_values = [max(v, 0) for v in overflow_values]
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
                        {
                            "type": "bar",
                            "data": overflow_values,
                            "stack": "y",
                            "color": "red",
                            "name": name,
                        },
                    ],
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