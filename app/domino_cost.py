import os
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List

import pandas as pd
import plotly.express as px
import requests 
import solara as sl
import re
import concurrent.futures 

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

class TokenExpiredException(Exception):
    pass


def get_token() -> str:
    orgs_res = requests.get(auth_url.value)  
    token = orgs_res.content.decode('utf-8')
    if token == "<ANONYMOUS>":
        raise TokenExpiredException("Your token has expired. Please redeploy your Domino Cost App.")
    return token
 
auth_header = { 
    'X-Authorization': get_token()
}


# For interacting with the different scopes
breakdown_options = ["Projects", "User", "Organization"]
breakdown_to_param = {
    "Projects": "dominodatalab.com/project-name",
    "User": "dominodatalab.com/starting-user-username",
    "Organization": "dominodatalab.com/organization-name",
}


# For granular aggregations
window_options = ["Last 14 days", "Last week", "Today"]
window_to_param = {
    "Last 14 days": "14d",
    "Last week": "lastweek",
    "Today": "today",
}
window_choice = sl.reactive(window_options[0])



def format_datetime(dt_str: str) -> str:
    datetime_object = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%SZ")
    return datetime_object.strftime("%m/%d %I:%M %p")

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


def get_aggregated_allocations():
    params = {
        "window": window_to_param[window_choice.value],
        "aggregate": (
            "label:dominodatalab.com/workload-type,"
            "label:dominodatalab.com/project-id,"
            "label:dominodatalab.com/project-name,"
            "label:dominodatalab.com/starting-user-username,"
            "label:dominodatalab.com/organization-name"
        ),
        "accumulate": True,
    }

    
    res = requests.get(allocations_url.value, params=params, headers=auth_header)  
    
    res.raise_for_status() 
    alloc_data = res.json()["data"]
   
    filtered = filter(lambda costData: costData["name"] != "__idle__", alloc_data)

    return list(filtered)



def get_top_level_cost() -> Dict[str, float]:
    params = {
        "window": window_to_param[window_choice.value],
        "accumulate": True,
    }

    res = requests.get(assets_url.value, params=params, headers=auth_header) 
    
    res.raise_for_status() 
    data = res.json()["data"]
    
    accumulated_data = dict()

    for cost_record in data:
        cost_type = cost_record["type"]
        accumulated_data[cost_type] = accumulated_data.get(cost_type, 0) + cost_record["totalCost"]

    overAllCost = {cost_data: round(accumulated_data[cost_data], 2) for cost_data in accumulated_data}
     
    return overAllCost


def get_daily_cost() -> pd.DataFrame:
    window = window_to_param[window_choice.value]
    params = {
        "window": window,
        "aggregate": (
            "label:dominodatalab.com/organization-name"
        ),
    }

    res = requests.get(allocations_url.value, params=params, headers=auth_header) 
    
    res.raise_for_status() 
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
            daily_costs[start][cost_type] += sum(aloc.get(cost_key,0) for cost_key in cost_keys)

    # Cumulative sum over the daily costs
    cumulative_daily_costs = pd.DataFrame(daily_costs).T.sort_index()

    
    cumulative_daily_costs["CPU"] = (round(cumulative_daily_costs["CPU"].cumsum(),2) if "CPU" in cumulative_daily_costs else 0)
    cumulative_daily_costs["GPU"] = (round(cumulative_daily_costs["GPU"].cumsum(),2) if "GPU" in cumulative_daily_costs else 0)
    cumulative_daily_costs["Storage"] = (round(cumulative_daily_costs["Storage"].cumsum(),2) if "Storage" in cumulative_daily_costs else 0)


    # Unless we are looking at today granularity, rollup values to the day level
    # (they are returned at the 5min level)
    if window != "today":
        cumulative_daily_costs.index = cumulative_daily_costs.index.map(to_date)
        cumulative_daily_costs = cumulative_daily_costs.groupby(level=0).max()

    return cumulative_daily_costs



def get_execution_cost_table(aggregated_allocations: List) -> pd.DataFrame:

    exec_data = []

    cpu_cost_key = ["cpuCost", "gpuCost"]
    gpu_cost_key = ["cpuCostAdjustment", "gpuCostAdjustment"]
    storage_cost_keys = ["pvCost", "ramCost", "pvCostAdjustment", "ramCostAdjustment"]

    data = [costData for costData in aggregated_allocations if not costData["name"].startswith("__")]
    
    for costData in data:
        workload_type, project_id, project_name, username, organization = costData["name"].split("/")
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



def graph_breakdown(name: str, labels: List, values: List):
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
        "yAxis": {"type": "category", "data": list(labels)},
        "series": [
            {
                "type": "bar",
                "data": list(map(lambda n: round(n, 2), values)),
                "stack": "y",
                "name": name,
            },
        ]
    }
    sl.FigureEcharts(option)


def get_cost_per_breakdown(aggregated_allocations: List):
    
    project_names = dict()
    project_data = dict()
    user_breakdown = dict()
    organization_breakdown = dict()
    
    for costData in aggregated_allocations:
        workload_type, project_id, project_name, username, organization = costData["name"].split("/")
        if not project_name.startswith("__"):
            project_data[project_id] = project_data.get(project_id, 0) + costData["totalCost"]
            project_names[project_id] = project_name

        if not username.startswith("__"):
            user_breakdown[username] = user_breakdown.get(username, 0) + costData["totalCost"]

        if not organization.startswith("__"):
            organization_breakdown[organization] = organization_breakdown.get(organization, 0) + costData["totalCost"]
    
    graph_breakdown("Projects", project_names.values(), project_data.values())
    graph_breakdown("User", user_breakdown.keys(), user_breakdown.values())
    graph_breakdown("Organization", organization_breakdown.keys(), organization_breakdown.values())


def SingleCost(name: str, cost: float) -> None:
    with sl.Column():
        cost_ = f"## ${cost}" if name == "Total" else f"#### ${cost}"
        sl.Markdown(cost_)
        name_ = f"### {name}" if name == "Total" else name
        sl.Markdown(name_)



def TopLevelCosts(costs: Dict) -> None:
    with sl.Row(justify="space-around"):
        SingleCost("Total", round(sum(list(costs.values())), 2))
        for name, cost in costs.items():
            SingleCost(name, cost)   

def DailyCostBreakdown(daily_cost: pd.DataFrame) -> None:
    if not daily_cost.empty:
        fig = px.bar(
            daily_cost,
            labels={
                "index": "Date",
                "value": "Cost ($)",
            },
            color_discrete_sequence=px.colors.qualitative.D3,
        )

        x0=daily_cost.index.min()
        x1=daily_cost.index.max()

        if window_to_param[window_choice.value] != "today" :
            x0= add_day(daily_cost.index.min(), -1)
            x1= add_day(daily_cost.index.max(), 1)

        sl.FigurePlotly(fig)

def CostBreakdown(aggregated_allocations: List) -> None:
    with sl.Columns([1, 1, 1]):
        get_cost_per_breakdown(aggregated_allocations)

def Executions(aggregated_allocations: List) -> None:
    execution_cost = get_execution_cost_table(aggregated_allocations)
    sl.DataFrame(execution_cost)          
            

@sl.component()
def Page() -> None:
    try:
        with concurrent.futures.ThreadPoolExecutor() as ex:
            futures = dict()
            futures["daily_cost"] = ex.submit(get_daily_cost)
            futures["top_level_cost"] = ex.submit(get_top_level_cost)
            futures["aggregated_allocations"] = ex.submit(get_aggregated_allocations)

            sl.Title("Cost Analysis")
            sl.Markdown(
                "# Domino Cost Management Report",
                style="display: inline-block; margin: 0 auto;",
            )

            with sl.Card():
                with sl.Column(style="width:15%"):
                    with sl.Row():
                        sl.Select(label="Window", value=window_choice, values=window_options)
                        
            concurrent.futures.wait(futures.values())
            with sl.Column():
                with sl.Card():
                    TopLevelCosts(futures["top_level_cost"].result())
                with sl.Card("Overall Cost (Cumulative)"):
                    DailyCostBreakdown(futures["daily_cost"].result())
                with sl.Card("Cost Usage"):
                    CostBreakdown(futures["aggregated_allocations"].result())
                with sl.Card("Executions"):
                    Executions(futures["aggregated_allocations"].result())
                    
    except Exception as err:
        sl.Error(f"{err}")
    

Page()