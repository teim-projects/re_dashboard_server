from django.shortcuts import render

def wind_dashboard(request):
    return render(request, 'wind_dashboard.html')  # Wind Dashboard

from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.db.utils import ProgrammingError

@login_required
def wind_summary1(request):
    table_name = "installation_summary_wind"
    data = {
        "capacity_by_state": [],
        "land_type_by_state": [],
        "wtg_generation": [],
        "power_sale": [],
    }
    table_exists = True  # flag for SweetAlert

    try:
        with connection.cursor() as cursor:
            # Capacity by state
            cursor.execute(f"""
                SELECT state, SUM(capacity_mw) AS total_capacity
                FROM `{table_name}`
                GROUP BY state
            """)
            data["capacity_by_state"] = cursor.fetchall()

            # Land type by state
            cursor.execute(f"""
                SELECT state, land, COUNT(*) AS land_count
                FROM `{table_name}`
                GROUP BY state, land
            """)
            data["land_type_by_state"] = cursor.fetchall()

            # Estimated generation WTG wise
            cursor.execute(f"""
                SELECT wtg_location_no, avg_estimate_gen_kwh
                FROM `{table_name}`
            """)
            data["wtg_generation"] = cursor.fetchall()

            # Power sale by state
            cursor.execute(f"""
                SELECT power_sale_details, state
                FROM `{table_name}`
            """)
            data["power_sale"] = cursor.fetchall()

    except ProgrammingError:
        # Table not found → just return empty tables, no error
        table_exists = False

    return render(request, "wind_summary1.html", {
        "data": data,
        "table_exists": table_exists,
        "table_name": table_name
    })

import json
from django.shortcuts import render
from django.db import connection
from django.db.utils import ProgrammingError
from django.contrib.auth.decorators import login_required
import json
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required


@login_required
def wind_installation_summary2(request):
    table_name = "installation_summary_wind"

    # --- Check if table exists
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        db_tables = [row[0] for row in cursor.fetchall()]
    if table_name not in db_tables:
        return render(request, "wind_installation_summary2.html", {
            "data": json.dumps({
                "power_sale_labels": [],
                "power_sale_counts": [],
                "land_labels": [],
                "land_counts": [],
            }),
            "wtg_locations": [],
            "oem_breakup": [],
            "no_data": True,
            "no_data_msg": "No installation summary data available."
        })

    # --- Normal flow if table exists
    data = {
        "power_sale_labels": [],
        "power_sale_counts": [],
        "land_labels": [],
        "land_counts": [],
    }
    wtg_locations = []
    oem_breakup = []

    with connection.cursor() as cursor:
        # Power Sale
        cursor.execute(f"""
            SELECT 
                CASE 
                    WHEN power_sale_details = 'Private PPA' THEN 'Captive'
                    WHEN power_sale_details IN ('SECI', 'State Grid') THEN 'Sale FB'
                    ELSE 'Other'
                END AS category,
                COUNT(*) AS cnt
            FROM `{table_name}`
            GROUP BY category
        """)
        for row in cursor.fetchall():
            data["power_sale_labels"].append(row[0])
            data["power_sale_counts"].append(row[1])

        # Land
        cursor.execute(f"SELECT land, COUNT(*) FROM `{table_name}` GROUP BY land")
        for row in cursor.fetchall():
            data["land_labels"].append(row[0])
            data["land_counts"].append(row[1])

        # ✅ Table 1: WTG Locations
        cursor.execute(f"""
            SELECT wtg_location_no, avg_estimate_gen_kwh
            FROM `{table_name}`
            ORDER BY avg_estimate_gen_kwh DESC
            LIMIT 10
        """)
        wtg_locations = cursor.fetchall()

        # ✅ Table 2: OEM Breakup
        cursor.execute(f"""
            SELECT capacity_mw, firm, make, COUNT(*)
            FROM `{table_name}`
            GROUP BY capacity_mw, firm, make
        """)
        oem_breakup = cursor.fetchall()

    # ✅ Handle case: table exists but no rows
    no_data = (
        len(data["power_sale_labels"]) == 0 and
        len(data["land_labels"]) == 0 and
        len(wtg_locations) == 0 and
        len(oem_breakup) == 0
    )

    return render(request, "wind_installation_summary2.html", {
        "data": json.dumps(data),
        "wtg_locations": wtg_locations,
        "oem_breakup": oem_breakup,
        "no_data": no_data,
        "no_data_msg": "No installation summary records found." if no_data else ""
    })

import json
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
import json
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from accounts.models import Provider, EnergyType

import json
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
import json
from collections import defaultdict
from django.http import HttpResponse
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
import re
import json
from collections import defaultdict
from django.http import HttpResponse
from django.db import connection
from django.contrib.auth.decorators import login_required


def _pick(col_map, *candidates):
    """Return the actual-cased column name from SHOW COLUMNS that matches any candidate (case-insensitive)."""
    for cand in candidates:
        lc = cand.lower()
        if lc in col_map:
            return col_map[lc]
    return None


def normalize(col):
    """
    Normalize column name for comparison:
    - lowercase
    - replace non-alphanumeric with _
    - strip _
    """
    return re.sub(r'[^a-z0-9]+', '_', col.lower()).strip('_')


@login_required
def wind_generation_kwh(request):
    user = request.user.username.lower()

    # --- Find ALL user's wind tables: <username>_*_wind
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        db_tables = [row[0] for row in cursor.fetchall()]
    table_names = [t for t in db_tables if t.startswith(user + "_") and t.endswith("_wind")]
    if not table_names:
      context = {
        "chart_data": json.dumps([]),
        "table_data": [],
        "total_generation": 0,
        "providers": [],
        "customers": [],
        "states": [],
        "sites": [],
        "wtgs": [],
        "selected_providers": [],
        "selected_customers": [],
        "selected_states": [],
        "selected_sites": [],
        "selected_wtgs": [],
        "date_from": None,
        "date_to": None,
        "no_data": True,   # 👈 flag for SweetAlert
        "no_data_msg": "No wind generation data found for your account."
       }
      return render(request, "wind_generation_kwh.html", context)

    # --- Collect filters from GET (multi-select)
    date_from  = request.GET.get("date_from") or None
    date_to    = request.GET.get("date_to") or None
    providers  = request.GET.getlist("provider")
    customers  = request.GET.getlist("customer")
    states     = request.GET.getlist("state")
    sites      = request.GET.getlist("site")
    wtgs       = request.GET.getlist("wtg")

    # Global aggregations
    wtg_sum = defaultdict(int)
    total_generation = 0

    # Distinct values for filters
    distincts = {k: set() for k in ["providers","customers","states","sites","wtgs"]}

    for table_name in table_names:
        # --- Read schema
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table_name}`;")
            cols = [r[0] for r in cursor.fetchall()]

        # Map normalized → original
        col_map = {normalize(c): c for c in cols}

        # --- Explicit mapping
        wtg_col      = col_map.get("loc_no") or col_map.get("wec") or col_map.get("wtg_no")
        gen_col      = col_map.get("gen_kwh_day") or col_map.get("gen_kwh") or col_map.get("generation")  # 👈 main fix
        date_col     = col_map.get("gen_date") or col_map.get("date")
        customer_col = col_map.get("customer_name") or col_map.get("customer")
        state_col    = col_map.get("state")
        site_col     = col_map.get("site") or col_map.get("wind_farm_name")
        provider_col = col_map.get("provider") or col_map.get("oem")

        if not wtg_col or not gen_col:
            continue

        # --- Build conditions
        conditions, params = [], []

        if date_col:
            if date_from and date_to:
                conditions.append(f"`{date_col}` BETWEEN %s AND %s")
                params += [date_from, date_to]
            elif date_from:
                conditions.append(f"`{date_col}` >= %s")
                params.append(date_from)
            elif date_to:
                conditions.append(f"`{date_col}` <= %s")
                params.append(date_to)

        def add_in(col, values):
            values = [v for v in values if v not in (None, "", "null")]
            if col and values:
                placeholders = ",".join(["%s"] * len(values))
                conditions.append(f"`{col}` IN ({placeholders})")
                params.extend(values)

        add_in(provider_col, providers)
        add_in(customer_col, customers)
        add_in(state_col, states)
        add_in(site_col, sites)
        add_in(wtg_col, wtgs)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # --- Aggregate daily gen
        query = f"""
            SELECT `{wtg_col}`, SUM(`{gen_col}`) AS total_gen
            FROM `{table_name}`
            {where_clause}
            GROUP BY `{wtg_col}`
        """
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        for wtg, gen in rows:
            gen = int(gen or 0)
            wtg_key = str(wtg)
            wtg_sum[wtg_key] += gen
            total_generation += gen

        # --- Distincts
        def distinct_list(col):
            if not col: return []
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT DISTINCT `{col}` FROM `{table_name}` ORDER BY `{col}`;")
                return [str(r[0]) for r in cursor.fetchall() if r[0] not in (None, "")]
        distincts["providers"].update(distinct_list(provider_col))
        distincts["customers"].update(distinct_list(customer_col))
        distincts["states"].update(distinct_list(state_col))
        distincts["sites"].update(distinct_list(site_col))
        distincts["wtgs"].update(distinct_list(wtg_col))

    # --- Chart data
    chart_data = [{"wtg": k, "generation": v} for k, v in wtg_sum.items()]
    chart_data.sort(key=lambda x: x["generation"], reverse=True)
    table_data = [{"wtg_no": d["wtg"], "generation": d["generation"]} for d in chart_data]

    context = {
        "chart_data": json.dumps(chart_data),
        "table_data": table_data,
        "total_generation": total_generation,
        "providers": sorted(distincts["providers"]),
        "customers": sorted(distincts["customers"]),
        "states": sorted(distincts["states"]),
        "sites": sorted(distincts["sites"]),
        "wtgs": sorted(distincts["wtgs"]),
        "selected_providers": providers,
        "selected_customers": customers,
        "selected_states": states,
        "selected_sites": sites,
        "selected_wtgs": wtgs,
        "date_from": date_from,
        "date_to": date_to,
    }
    return render(request, "wind_generation_kwh.html", context)
from collections import defaultdict
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import HttpResponse
from django.shortcuts import render
import json

def _pick(col_map, *candidates):
    """
    Return the actual-cased column name from SHOW COLUMNS
    that matches any candidate (case-insensitive, ignores spaces, dots, underscores).
    """
    def normalize(name):
        return name.lower().replace(" ", "").replace(".", "").replace("_", "")
    
    normalized = {normalize(c): c for c in col_map.values()}
    
    for cand in candidates:
        key = normalize(cand)
        if key in normalized:
            return normalized[key]
    return None


@login_required
def wind_generation_hours(request):
    user = request.user.username.lower()

    # --- Find ALL user's wind tables: <username>_*_wind
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        db_tables = [row[0] for row in cursor.fetchall()]
    table_names = [t for t in db_tables if t.startswith(user + "_") and t.endswith("_wind")]

    # ✅ If no table found → show blank chart + SweetAlert
    if not table_names:
        context = {
            "chart_data": json.dumps([]),
            "table_data": [],
            "total_hours": 0,
            "providers": [],
            "customers": [],
            "states": [],
            "sites": [],
            "wtgs": [],
            "selected_providers": [],
            "selected_customers": [],
            "selected_states": [],
            "selected_sites": [],
            "selected_wtgs": [],
            "date_from": None,
            "date_to": None,
            "no_data": True,   # 👈 for SweetAlert
            "no_data_msg": "No wind generation tables found for your account."
        }
        return render(request, "wind_genration_hovers.html", context)

    # --- Collect filters from GET (multi-select)
    date_from = request.GET.get("date_from") or None
    date_to = request.GET.get("date_to") or None
    providers = request.GET.getlist("provider")
    customers = request.GET.getlist("customer")
    states = request.GET.getlist("state")
    sites = request.GET.getlist("site")
    wtgs = request.GET.getlist("wtg")

    # Global aggregations
    wtg_sum = defaultdict(float)  # {wtg: total_hours}
    total_hours = 0.0

    # Distinct values for filters (merged across tables)
    distincts = {
        "providers": set(),
        "customers": set(),
        "states": set(),
        "sites": set(),
        "wtgs": set(),
    }

    for table_name in table_names:
        # --- Read schema
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table_name}`;")
            cols = [r[0] for r in cursor.fetchall()]
        col_map = {c.lower(): c for c in cols}

        # Detect columns
        wtg_col     = _pick(col_map, "wec", "loc_no", "wtg", "wtg_no", "turbine", "turbineno", "locno")
        genhrs_col  = _pick(col_map, "genhrs", "generationhours", "gen_hours", "gen_hrs")
        ohrs_col    = _pick(col_map, "ohrs", "operatinghours", "o_hours", "o_hrs")
        loss_col    = _pick(col_map, "lhrs", "l.hrs", "losshrs", "loss_hours", "l_hrs")
        date_col    = _pick(col_map, "date", "gen_date", "reading_date", "day_date")
        customer_col= _pick(col_map, "customername", "customer", "consumer", "client")
        state_col   = _pick(col_map, "state", "statename", "st")
        site_col    = _pick(col_map, "site", "sitename", "location", "plant", "windfarmname", "park", "sitecode", "city", "town", "village")
        provider_col= _pick(col_map, "provider", "oem", "oemprovider", "oem_name")

        if not wtg_col:
            continue  # skip if no turbine column

        # --- Build conditions for this table
        conditions, params = [], []

        if date_col:
            if date_from and date_to:
                conditions.append(f"`{date_col}` BETWEEN %s AND %s")
                params += [date_from, date_to]
            elif date_from:
                conditions.append(f"`{date_col}` >= %s")
                params += [date_from]
            elif date_to:
                conditions.append(f"`{date_col}` <= %s")
                params += [date_to]

        def add_in(col, values):
            values = [v for v in values if v not in (None, "", "null")]
            if col and values:
                placeholders = ",".join(["%s"] * len(values))
                conditions.append(f"`{col}` IN ({placeholders})")
                params.extend(values)

        add_in(provider_col, providers)
        add_in(customer_col, customers)
        add_in(state_col, states)
        add_in(site_col, sites)
        add_in(wtg_col, wtgs)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # --- Decide how to compute Generation Hours
        if ohrs_col and loss_col:
            gen_expr = f"(`{ohrs_col}` - `{loss_col}`)"   # Net Gen Hours = O.Hrs - L.Hrs
        elif genhrs_col:
            gen_expr = f"`{genhrs_col}`"
        elif ohrs_col:
            gen_expr = f"`{ohrs_col}`"
        else:
            continue  # skip if no usable column

        # --- Aggregate WTG wise for this table
        query = f"""
            SELECT `{wtg_col}`, SUM({gen_expr}) AS total_hours
            FROM `{table_name}`
            {where_clause}
            GROUP BY `{wtg_col}`
        """
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        for wtg, hrs in rows:
            hrs = float(hrs or 0)
            wtg_key = str(wtg)
            wtg_sum[wtg_key] += hrs
            total_hours += hrs

        # --- Collect distincts (from whole table, not filtered)
        def distinct_list(col):
            if not col:
                return []
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT DISTINCT `{col}` FROM `{table_name}` ORDER BY `{col}`;")
                return [str(r[0]) for r in cursor.fetchall() if r[0] not in (None, "")]

        distincts["providers"].update(distinct_list(provider_col))
        distincts["customers"].update(distinct_list(customer_col))
        distincts["states"].update(distinct_list(state_col))
        distincts["sites"].update(distinct_list(site_col))
        distincts["wtgs"].update(distinct_list(wtg_col))

    # --- Build chart/table data from merged sums
    chart_data = [{"wtg": k, "hours": v} for k, v in wtg_sum.items()]
    chart_data.sort(key=lambda x: x["hours"], reverse=True)

    table_data = [{"wtg_no": d["wtg"], "hours": d["hours"]} for d in chart_data]

    # ✅ If table exists but no rows → also send SweetAlert
    no_data = (len(chart_data) == 0)

    context = {
        "chart_data": json.dumps(chart_data),
        "table_data": table_data,
        "total_hours": total_hours,
        "providers": sorted(distincts["providers"]),
        "customers": sorted(distincts["customers"]),
        "states": sorted(distincts["states"]),
        "sites": sorted(distincts["sites"]),
        "wtgs": sorted(distincts["wtgs"]),
        "selected_providers": providers,
        "selected_customers": customers,
        "selected_states": states,
        "selected_sites": sites,
        "selected_wtgs": wtgs,
        "date_from": date_from,
        "date_to": date_to,
        "no_data": no_data,
        "no_data_msg": "No wind generation hours available for the selected filters." if no_data else ""
    }

    return render(request, "wind_genration_hovers.html", context)



import json
from collections import defaultdict
from django.http import HttpResponse
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
import json
from collections import defaultdict
from django.http import HttpResponse
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required


def _pick(col_map, *candidates):
    """Return actual-cased column name if it matches any of the candidates"""
    for c in candidates:
        lc = c.lower()
        if lc in col_map:
            return col_map[lc]
    return None


@login_required
def wind_avg_genration(request):
    user = request.user.username.lower()

    # --- Find ALL user's wind tables: <username>_*_wind
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        db_tables = [row[0] for row in cursor.fetchall()]
    table_names = [t for t in db_tables if t.startswith(user + "_") and t.endswith("_wind")]
    if not table_names:
     context = {
        "chart_data": json.dumps([]),
        "table_data": [],
        "total_generation": 0,
        "providers": [],
        "customers": [],
        "states": [],
        "sites": [],
        "wtgs": [],
        "selected_providers": [],
        "selected_customers": [],
        "selected_states": [],
        "selected_sites": [],
        "selected_wtgs": [],
        "date_from": None,
        "date_to": None,
        "no_data": True,   # 👈 flag for SweetAlert
        "no_data_msg": "No wind generation data found for your account."
       }
     return render(request, "wind_avg_genration.html", context)

    # --- Collect filters from GET
    date_from = request.GET.get("date_from") or None
    date_to = request.GET.get("date_to") or None
    providers = request.GET.getlist("provider")
    customers = request.GET.getlist("customer")
    states = request.GET.getlist("state")
    sites = request.GET.getlist("site")
    wtgs = request.GET.getlist("wtg")

    # Global aggregations
    gen_avg = defaultdict(list)   # WTG → list of generation hours averages
    op_avg = defaultdict(list)    # WTG → list of operating hours averages
    distincts = {
        "providers": set(),
        "customers": set(),
        "states": set(),
        "sites": set(),
        "wtgs": set(),
    }

    for table_name in table_names:
        # --- Read schema
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table_name}`;")
            cols = [r[0] for r in cursor.fetchall()]
        col_map = {c.lower(): c for c in cols}

        # ✅ Fixed candidate lists
        wtg_col = _pick(col_map, "wec", "loc_no", "wtg", "wtg_no", "turbine", "turbineno", "locno")
        gen_col = _pick(col_map, "genhrs", "generationhours", "gen_hours", "gen_hrs","O_hrs")
        op_col = _pick(col_map, "O_hrs","Opr_Hrs" ,"ohrs", "operatinghours", "op_hours", "op_hrs")
        date_col = _pick(col_map, "date", "gen_date", "reading_date", "day_date")
        customer_col = _pick(col_map, "customername", "customer", "consumer", "client")
        state_col = _pick(col_map, "state", "statename", "st")
        site_col = _pick(col_map, "site", "sitename", "location", "plant", "windfarmname", "park", "sitecode", "city", "town", "village")
        provider_col = _pick(col_map, "provider", "oem", "oemprovider", "oem_name")

        if not wtg_col:
            continue  # skip tables without WTG

        # --- Build conditions
        conditions, params = [], []

        if date_col:
            if date_from and date_to:
                conditions.append(f"`{date_col}` BETWEEN %s AND %s")
                params += [date_from, date_to]
            elif date_from:
                conditions.append(f"`{date_col}` >= %s")
                params += [date_from]
            elif date_to:
                conditions.append(f"`{date_col}` <= %s")
                params += [date_to]

        def add_in(col, values):
            nonlocal conditions, params
            values = [v for v in values if v not in (None, "", "null")]
            if col and values:
                placeholders = ",".join(["%s"] * len(values))
                conditions.append(f"`{col}` IN ({placeholders})")
                params.extend(values)

        add_in(provider_col, providers)
        add_in(customer_col, customers)
        add_in(state_col, states)
        add_in(site_col, sites)
        add_in(wtg_col, wtgs)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # --- Generation Hours
        if gen_col:
            query = f"""
                SELECT `{wtg_col}`, AVG(`{gen_col}`) AS avg_gen
                FROM `{table_name}`
                {where_clause}
                GROUP BY `{wtg_col}`
            """
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()
            for wtg, avg in rows:
                gen_avg[str(wtg)].append(float(avg or 0))

        # --- Operating Hours
        if op_col:
            query = f"""
                SELECT `{wtg_col}`, AVG(`{op_col}`) AS avg_op
                FROM `{table_name}`
                {where_clause}
                GROUP BY `{wtg_col}`
            """
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()
            for wtg, avg in rows:
                op_avg[str(wtg)].append(float(avg or 0))

        # --- Collect distincts (from whole table, not filtered)
        def distinct_list(col):
            if not col:
                return []
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT DISTINCT `{col}` FROM `{table_name}` ORDER BY `{col}`;")
                return [str(r[0]) for r in cursor.fetchall() if r[0] not in (None, "")]

        distincts["providers"].update(distinct_list(provider_col))
        distincts["customers"].update(distinct_list(customer_col))
        distincts["states"].update(distinct_list(state_col))
        distincts["sites"].update(distinct_list(site_col))
        distincts["wtgs"].update(distinct_list(wtg_col))

    # --- Merge averages
    # --- Merge averages (skip None / empty WTG)
    gen_final = {wtg: sum(vals) / len(vals) for wtg, vals in gen_avg.items() if wtg and wtg.lower() != "none"}
    op_final = {wtg: sum(vals) / len(vals) for wtg, vals in op_avg.items() if wtg and wtg.lower() != "none"}


    gen_chart_data = [{"wtg": k, "hours": v} for k, v in gen_final.items()]
    op_chart_data = [{"wtg": k, "hours": v} for k, v in op_final.items()]

    gen_chart_data.sort(key=lambda x: x["hours"], reverse=True)
    op_chart_data.sort(key=lambda x: x["hours"], reverse=True)

    context = {
        "gen_chart_data": json.dumps(gen_chart_data),
        "op_chart_data": json.dumps(op_chart_data),
        "overall_gen_avg": round(sum(d["hours"] for d in gen_chart_data) / len(gen_chart_data), 2) if gen_chart_data else 0,
        "overall_op_avg": round(sum(d["hours"] for d in op_chart_data) / len(op_chart_data), 2) if op_chart_data else 0,
        "providers": sorted(distincts["providers"]),
        "customers": sorted(distincts["customers"]),
        "states": sorted(distincts["states"]),
        "sites": sorted(distincts["sites"]),
        "wtgs": sorted(distincts["wtgs"]),
        "selected_providers": providers,
        "selected_customers": customers,
        "selected_states": states,
        "selected_sites": sites,
        "selected_wtgs": wtgs,
        "date_from": date_from,
        "date_to": date_to,
    }

    return render(request, "wind_avg_genration.html", context)




import json
from collections import defaultdict
from datetime import datetime, date
from django.http import HttpResponse
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required


def _pick(col_map, *candidates):
    """Return actual-cased column name if it matches any of the candidates."""
    for c in candidates:
        lc = c.lower()
        if lc in col_map:
            return col_map[lc]
    return None


@login_required
def wind_Grid_Availability_and_Machine(request):
    user = request.user.username.lower()

    # --- Find ALL user's tables ending with _wind
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        db_tables = [row[0] for row in cursor.fetchall()]
    table_names = [t for t in db_tables if t.startswith(user + "_") and t.endswith("_wind")]

    if not table_names:
      context = {
        "grid_chart_data": json.dumps([]),  # empty dataset = blank chart
        "providers": [],
        "customers": [],
        "states": [],
        "sites": [],
        "wtgs": [],
        "selected_providers": [],
        "selected_customers": [],
        "selected_states": [],
        "selected_sites": [],
        "selected_wtgs": [],
        "date_from": None,
        "date_to": None,
        "no_data": True,
        "no_data_msg": "No wind tables found for your account."
          }
      return render(request, "wind_Grid_Availability_and_Machine.html", context)

    # Filters from GET
    date_from = request.GET.get("date_from") or None
    date_to = request.GET.get("date_to") or None
    providers = request.GET.getlist("provider")
    customers = request.GET.getlist("customer")
    states = request.GET.getlist("state")
    sites = request.GET.getlist("site")
    wtgs = request.GET.getlist("wtg")

    # Aggregation by year
    year_failure_hours = defaultdict(list)
    distincts = {
        "providers": set(),
        "customers": set(),
        "states": set(),
        "sites": set(),
        "wtgs": set(),
    }

    def parse_date_like(v):
        """Handle str, date, datetime; return a datetime.date or None."""
        if isinstance(v, date):
            return v if not isinstance(v, datetime) else v.date()
        if isinstance(v, (int, float)) or v is None:
            return None
        s = str(v).strip()
        for fmt in ("%d-%b-%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y"):
            try:
                return datetime.strptime(s, fmt).date()
            except Exception:
                continue
        return None

    def to_hours_from_gf_value(raw):
        """
        Interpret GF column as **hours** if plausible.
        If someone stored minutes (0..1440), convert to hours.
        Never treat GF column as % (that caused the 0.24% issue).
        """
        try:
            val = float(raw)
        except Exception:
            return 0.0
        if 0 <= val <= 24:
            return val  # already hours/day
        if 24 < val <= 1440:
            return val / 60.0  # minutes -> hours
        # Any other outlier: best effort, assume it's already hours
        return val

    for table_name in table_names:
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table_name}`;")
            cols = [r[0] for r in cursor.fetchall()]
        col_map = {c.lower(): c for c in cols}

        # Identify columns dynamically
        date_col = _pick(col_map, "date", "gen_date", "reading_date", "day_date", "DATE", "Gen. Date")
        gf_col = _pick(col_map, "gf", "g.F", "GF", "grid_failure", "gridfailure")
        ga_col = _pick(col_map, "GA", "grid_availability")
        gia_col = _pick(col_map, "GIA", "grid_indicator_availability")
        remarks_col = _pick(col_map, "REMARKS", "remarks", "comment")

        wtg_col = _pick(col_map, "wec", "loc_no", "wtg", "wtg_no", "turbine", "turbineno", "locno")
        customer_col = _pick(col_map, "customername", "customer", "consumer", "client")
        state_col = _pick(col_map, "state", "statename", "st")
        site_col = _pick(col_map, "site", "sitename", "location", "plant", "windfarmname", "park", "sitecode", "city", "town", "village")
        provider_col = _pick(col_map, "provider", "oem", "oemprovider", "oem_name")

        if not date_col:
            continue

        # Build conditions
        conditions, params = [], []

        if date_from and date_to:
            conditions.append(f"`{date_col}` BETWEEN %s AND %s")
            params.extend([date_from, date_to])
        elif date_from:
            conditions.append(f"`{date_col}` >= %s")
            params.append(date_from)
        elif date_to:
            conditions.append(f"`{date_col}` <= %s")
            params.append(date_to)

        def add_in(col, values):
            vv = [v for v in values if v not in (None, "", "null")]
            if col and vv:
                placeholders = ",".join(["%s"] * len(vv))
                conditions.append(f"`{col}` IN ({placeholders})")
                params.extend(vv)

        add_in(provider_col, providers)
        add_in(customer_col, customers)
        add_in(state_col, states)
        add_in(site_col, sites)
        add_in(wtg_col, wtgs)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Query all relevant columns
        selected_cols = [date_col]
        if gf_col: selected_cols.append(gf_col)
        if ga_col: selected_cols.append(ga_col)
        if gia_col: selected_cols.append(gia_col)
        if remarks_col: selected_cols.append(remarks_col)

        col_str = ", ".join(f"`{c}`" for c in selected_cols)
        query = f"SELECT {col_str} FROM `{table_name}` {where_clause}"

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        # map for faster index lookup
        idx = {c: i for i, c in enumerate(selected_cols)}

        for row in rows:
            d = parse_date_like(row[idx[date_col]])
            if not d:
                continue
            year = d.year

            # --- Compute Grid Failure **hours/day**
            hours = 0.0
            try:
                if gf_col:
                    # Treat GF column as hours (convert minutes if needed)
                    hours = to_hours_from_gf_value(row[idx[gf_col]])
                else:
                    # No GF column → derive from availability percentage(s)
                    if ga_col and row[idx[ga_col]] not in (None, ""):
                        ga = float(row[idx[ga_col]])
                        ga = max(0.0, min(100.0, ga))
                        hours = (100.0 - ga) * 24.0 / 100.0
                    elif gia_col and row[idx[gia_col]] not in (None, ""):
                        gia = float(row[idx[gia_col]])
                        gia = max(0.0, min(100.0, gia))
                        hours = (100.0 - gia) * 24.0 / 100.0
                    else:
                        hours = 0.0
            except Exception:
                hours = 0.0

            year_failure_hours[year].append(hours)

        # Collect distincts (for filters)
        def distinct_list(col):
            if not col:
                return []
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT DISTINCT `{col}` FROM `{table_name}` ORDER BY `{col}`;")
                return [str(r[0]) for r in cursor.fetchall() if r[0] not in (None, "")]
        distincts["providers"].update(distinct_list(provider_col))
        distincts["customers"].update(distinct_list(customer_col))
        distincts["states"].update(distinct_list(state_col))
        distincts["sites"].update(distinct_list(site_col))
        distincts["wtgs"].update(distinct_list(wtg_col))

    # Aggregate: average grid failure **hours/day** per year
    final_data = []
    for y in sorted(year_failure_hours.keys()):
        vals = year_failure_hours[y]
        avg_hours = round(sum(vals) / len(vals), 2) if vals else 0.0
        final_data.append({"year": str(y), "avg_failure": avg_hours})

    context = {
        "grid_chart_data": json.dumps(final_data),
        "providers": sorted(distincts["providers"]) if distincts["providers"] else [],
        "customers": sorted(distincts["customers"]) if distincts["customers"] else [],
        "states": sorted(distincts["states"]) if distincts["states"] else [],
        "sites": sorted(distincts["sites"]) if distincts["sites"] else [],
        "wtgs": sorted(distincts["wtgs"]) if distincts["wtgs"] else [],
        "selected_providers": providers or [],
        "selected_customers": customers or [],
        "selected_states": states or [],
        "selected_sites": sites or [],
        "selected_wtgs": wtgs or [],
        "date_from": date_from,
        "date_to": date_to,
    }
    return render(request, "wind_Grid_Availability_and_Machine.html", context)
