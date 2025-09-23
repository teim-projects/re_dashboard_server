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

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db import connection
import json

@login_required
def wind_installation_summary2(request):
    # --- List of possible table names
    possible_tables = [
        "installation_summary_wind",
        "installation_summary_windmil",
        "installation_summary_W",
        "installation_summary_Wind"
        "installation_summary_WIND"
    ]

    # --- Get existing tables from database
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        db_tables = [row[0] for row in cursor.fetchall()]

    # --- Find first table that exists
    table_name = next((t for t in possible_tables if t in db_tables), None)

    # --- If no table exists, return empty response
    if not table_name:
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

        # WTG Locations (top 10 by estimated generation)
        cursor.execute(f"""
            SELECT wtg_location_no, avg_estimate_gen_kwh
            FROM `{table_name}`
            ORDER BY avg_estimate_gen_kwh DESC
            LIMIT 10
        """)
        wtg_locations = cursor.fetchall()

        # OEM Breakup
        cursor.execute(f"""
            SELECT capacity_mw, firm, make, COUNT(*)
            FROM `{table_name}`
            GROUP BY capacity_mw, firm, make
        """)
        oem_breakup = cursor.fetchall()

    # --- Handle case: table exists but no rows
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
from datetime import datetime, date
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
import json

def _pick(col_map, *candidates):
    """Return actual-cased column name if it matches any of the candidates"""
    for c in candidates:
        lc = c.lower()
        if lc in col_map:
            return col_map[lc]
    return None

def parse_date_like(v):
    """Parse date/datetime strings or objects into date object"""
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if v is None:
        return None
    s = str(v).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d-%b-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except:
            continue
    return None

def parse_hours(val):
    """Convert numeric or hh:mm:ss style strings to float hours"""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    if " " in s:
        parts = s.split(" ")
        try:
            days = int(parts[0])
        except:
            days = 0
        hms = parts[1] if len(parts) > 1 else "0:0:0"
    else:
        days = 0
        hms = s
    try:
        hms_parts = [int(p) for p in hms.split(":")]
    except:
        hms_parts = [0,0,0]
    hours = days*24 + hms_parts[0] + hms_parts[1]/60 + hms_parts[2]/3600
    return hours

@login_required
def wind_generation_hours(request):
    user = request.user.username.lower()

    # --- Get all user's wind tables
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        db_tables = [row[0] for row in cursor.fetchall()]
    table_names = [t for t in db_tables if t.startswith(user + "_") and t.endswith("_wind")]

    if not table_names:
        context = {
            "chart_data": json.dumps([]),
            "table_data": [],
            "years": [],
            "total_hours": 0,
            "providers": [], "customers": [], "states": [], "sites": [], "wtgs": [],
            "selected_providers": [], "selected_customers": [], "selected_states": [],
            "selected_sites": [], "selected_wtgs": [],
            "date_from": None, "date_to": None,
            "no_data": True,
            "no_data_msg": "No wind tables found for your account."
        }
        return render(request, "wind_genration_hovers.html", context)

    # --- Get filters
    date_from = request.GET.get("date_from") or None
    date_to = request.GET.get("date_to") or None
    providers = request.GET.getlist("provider")
    customers = request.GET.getlist("customer")
    states = request.GET.getlist("state")
    sites = request.GET.getlist("site")
    wtgs = request.GET.getlist("wtg")

    # --- Containers
    wtg_year_hours = defaultdict(float)
    total_hours = 0.0
    distincts = {"providers": set(), "customers": set(), "states": set(), "sites": set(), "wtgs": set()}
    years_set = set()

    for table_name in table_names:
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table_name}`;")
            cols = [r[0] for r in cursor.fetchall()]
        col_map = {c.lower(): c for c in cols}

        # --- Identify columns
        date_col = _pick(col_map, "date", "gen_date", "reading_date", "day_date")
        wtg_col = _pick(col_map, "wec", "loc_no", "wtg", "wtg_no", "turbine", "turbineno", "locno")
        genhrs_col = _pick(col_map, "genhrs", "generationhours", "gen_hours", "gen_hrs", "generation", "o_hrs")
        ohrs_col = _pick(col_map, "ohrs", "operatinghours", "o_hours", "o_hrs")
        loss_col = _pick(col_map, "lhrs", "l.hrs", "losshrs", "loss_hours", "l_hrs")
        provider_col = _pick(col_map, "provider", "oem", "oemprovider", "oem_name")
        customer_col = _pick(col_map, "customername", "customer", "consumer", "client")
        state_col = _pick(col_map, "state", "statename", "st")
        site_col = _pick(col_map, "site", "sitename", "location", "plant", "windfarmname", "park", "sitecode", "city", "town", "village")

        if not date_col or not wtg_col:
            continue

        # --- Conditions
        conditions, params = [], []
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
            nonlocal conditions, params
            values = [v for v in values if v not in (None, "", "null")]
            if col and values:
                placeholders = ",".join(["%s"]*len(values))
                conditions.append(f"`{col}` IN ({placeholders})")
                params.extend(values)

        add_in(provider_col, providers)
        add_in(customer_col, customers)
        add_in(state_col, states)
        add_in(site_col, sites)
        add_in(wtg_col, wtgs)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # --- Choose generation expression
        if ohrs_col and loss_col:
            gen_expr = f"(`{ohrs_col}` - `{loss_col}`)"
        elif genhrs_col:
            gen_expr = f"`{genhrs_col}`"
        elif ohrs_col:
            gen_expr = f"`{ohrs_col}`"
        else:
            continue

        # --- Query
        query = f"""
            SELECT `{date_col}`, `{wtg_col}`, SUM({gen_expr}) AS hours
            FROM `{table_name}`
            {where_clause}
            GROUP BY `{date_col}`, `{wtg_col}`
        """
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        for d_str, wtg_val, hrs in rows:
            d = parse_date_like(d_str)
            if not d:
                continue
            year = d.year
            years_set.add(year)
            if not wtg_val:
                continue
            wtg = str(wtg_val)
            wtg_year_hours[(wtg, year)] += float(hrs or 0)
            total_hours += float(hrs or 0)

        # --- Collect distincts
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

    # --- Ensure each WTG has all years
    for wtg in distincts["wtgs"]:
        for year in years_set:
            key = (wtg, year)
            if key not in wtg_year_hours:
                wtg_year_hours[key] = 0.0

    # --- Prepare chart & table data
    chart_data = [{"wtg": k[0], "year": k[1], "hours": round(v,2)} for k,v in sorted(wtg_year_hours.items(), key=lambda x: (x[0][1], x[0][0]))]
    table_data = [{"wtg_no": k[0], "year": k[1], "hours": round(v,2)} for k,v in wtg_year_hours.items()]
    years = sorted(years_set)

    context = {
        "chart_data": json.dumps(chart_data),
        "table_data": table_data,
        "years": years,
        "total_hours": round(total_hours,2),
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
        "no_data": not bool(chart_data),
        "no_data_msg": "No generation data found for the selected filters." if not chart_data else ""
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




from collections import defaultdict
from datetime import datetime, date
from django.http import HttpResponse
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
import json


def _pick(col_map, *candidates):
    """Find actual column name from possible variants with normalization."""
    def normalize(name):
        return (
            name.lower()
            .replace(".", "")
            .replace("%", "")
            .replace(" ", "")
            .replace("_", "")
            .strip()
        )
    for c in candidates:
        norm_c = normalize(c)
        for actual in col_map:
            if normalize(actual) == norm_c:
                return col_map[actual]
    return None

def parse_date_like(v):
    if isinstance(v, date):
        return v
    if isinstance(v, datetime):
        return v.date()

    # Add more date formats including dd-mm-yyyy
    formats = (
        "%Y-%m-%d",   # 2022-01-01
        "%d/%m/%Y",   # 01/01/2022
        "%d-%m-%Y",   # 01-01-2022
        "%d-%b-%Y",   # 01-Jan-2022
        "%d.%m.%Y",   # 01.01.2022
    )

    for fmt in formats:
        try:
            return datetime.strptime(str(v).strip(), fmt).date()
        except Exception:
            continue

    # Fallback: try to split manually
    try:
        parts = str(v).replace("/", "-").replace(".", "-").split("-")
        if len(parts) == 3:
            if len(parts[0]) == 4:  # yyyy-mm-dd
                return datetime(int(parts[0]), int(parts[1]), int(parts[2])).date()
            else:  # dd-mm-yyyy
                return datetime(int(parts[2]), int(parts[1]), int(parts[0])).date()
    except Exception:
        pass

    return None


def to_hours(value):
    try:
        val = float(value)
        if 0 <= val <= 24:
            return val
        if 24 < val <= 1440:
            return val / 60.0
    except:
        return 0.0
    return 0.0


@login_required
def wind_Grid_Availability_and_Machine(request):
    user = request.user.username.lower()

    # Get all tables ending with _wind for this user
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        tables = [row[0] for row in cursor.fetchall()]
    table_names = [t for t in tables if t.startswith(user + "_") and t.endswith("_wind")]

    if not table_names:
        context = {
            "grid_chart_data": json.dumps([]),
            "availability_chart_data": json.dumps([]),
            "plf_yearly_data": json.dumps([]),
            "plf_monthly_data": json.dumps({}),
            "providers": [], "customers": [], "states": [],
            "sites": [], "wtgs": [],
            "selected_providers": [], "selected_customers": [],
            "selected_states": [], "selected_sites": [],
            "selected_wtgs": [],
            "date_from": None, "date_to": None,
            "no_data": True,
            "no_data_msg": "No wind tables found for your account."
        }
        return render(request, "wind_Grid_Availability_and_Machine.html", context)

    # Filters
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    providers = request.GET.getlist("provider")
    customers = request.GET.getlist("customer")
    states = request.GET.getlist("state")
    sites = request.GET.getlist("site")
    wtgs = request.GET.getlist("wtg")

    # Data accumulators
    year_failure_hours = defaultdict(list)
    month_failure_hours = defaultdict(list)
    year_plf = defaultdict(list)
    month_plf = defaultdict(list)
    distincts = {
        "providers": set(),
        "customers": set(),
        "states": set(),
        "sites": set(),
        "wtgs": set(),
    }

    # Process each table
    for table in table_names:
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table}`")
            cols = [row[0] for row in cursor.fetchall()]
        col_map = {c: c for c in cols}  # keep actual case

        # --- Column mappings (support multiple formats) ---
        date_col = _pick(col_map, "date", "gen_date", "reading_date", "day_date", "gen. date")

        gf_col = _pick(col_map, "gf", "gridfailure", "grid failure", "failure hours")
        ga_col = _pick(col_map, "ga", "gridavailability", "grid availability", "ga%")
        gia_col = _pick(col_map, "gia", "gridinternalavailability", "grid indicator availability", "gia%")

        wtg_col = _pick(col_map, "wec", "wecno", "wecnumber", "wtg", "wtgno", "wtg number", "locno", "section")
        customer_col = _pick(col_map, "customer", "customername", "consumer", "client", "clientname", "customer name")
        state_col = _pick(col_map, "state", "statename", "st")
        site_col = _pick(col_map, "site", "sitename", "location", "plant", "windfarmname",
                         "park", "sitecode", "city", "town", "village")
        provider_col = _pick(col_map, "provider", "oem", "oemprovider", "oemname", "oem_name")

        gen_col = _pick(col_map, "generation", "gen", "genkwh", "g", "generation(kwh)")
        gen_hrs_col = _pick(col_map, "genhrs", "gen hrs", "genhours", "generation hours")
        opr_hrs_col = _pick(col_map, "ophrs", "opr hrs", "operating hours", "machine hrs")

        plf_day_col = _pick(col_map, "plf_day", "plfday", "%plf day", "plf")

        if not date_col:
            continue

        # Build filters
        conditions, params = [], []
        if date_from:
            conditions.append(f"`{date_col}` >= %s")
            params.append(date_from)
        if date_to:
            conditions.append(f"`{date_col}` <= %s")
            params.append(date_to)
        if providers and provider_col:
            placeholders = ",".join(["%s"] * len(providers))
            conditions.append(f"`{provider_col}` IN ({placeholders})")
            params.extend(providers)
        if customers and customer_col:
            placeholders = ",".join(["%s"] * len(customers))
            conditions.append(f"`{customer_col}` IN ({placeholders})")
            params.extend(customers)
        if states and state_col:
            placeholders = ",".join(["%s"] * len(states))
            conditions.append(f"`{state_col}` IN ({placeholders})")
            params.extend(states)
        if sites and site_col:
            placeholders = ",".join(["%s"] * len(sites))
            conditions.append(f"`{site_col}` IN ({placeholders})")
            params.extend(sites)
        if wtgs and wtg_col:
            placeholders = ",".join(["%s"] * len(wtgs))
            conditions.append(f"`{wtg_col}` IN ({placeholders})")
            params.extend(wtgs)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Select only needed columns
        select_cols = [date_col]
        for col in [gf_col, ga_col, gia_col, plf_day_col, gen_hrs_col, opr_hrs_col, gen_col]:
            if col:
                select_cols.append(col)

        select_clause = ", ".join(f"`{col}`" for col in select_cols)
        query = f"SELECT {select_clause} FROM `{table}` {where_clause}"

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        idx = {col: i for i, col in enumerate(select_cols)}

        for row in rows:
            d = parse_date_like(row[idx[date_col]])
            if not d:
                continue
            year = d.year
            month = d.strftime("%Y-%m")

            # --- Grid failure calc ---
            hours = 0.0
            if gf_col and row[idx.get(gf_col)] not in (None, ""):
                hours = to_hours(row[idx[gf_col]])
            elif ga_col and row[idx.get(ga_col)] not in (None, ""):
                try:
                    ga = float(row[idx[ga_col]])
                    ga = max(0.0, min(100.0, ga))
                    hours = (100.0 - ga) * 24.0 / 100.0
                except:
                    pass
            elif gia_col and row[idx.get(gia_col)] not in (None, ""):
                try:
                    gia = float(row[idx[gia_col]])
                    gia = max(0.0, min(100.0, gia))
                    hours = (100.0 - gia) * 24.0 / 100.0
                except:
                    pass

            year_failure_hours[year].append(hours)
            month_failure_hours[month].append(hours)

            # --- PLF ---
            plf_val = None
            if plf_day_col and row[idx.get(plf_day_col)] not in (None, ""):
                try:
                    plf_val = float(row[idx[plf_day_col]])
                except:
                    plf_val = None

            if plf_val is not None:
                year_plf[year].append(plf_val)
                month_plf[month].append(plf_val)

        # Collect distinct values for filters
        def get_distinct(col):
            if not col:
                return []
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT DISTINCT `{col}` FROM `{table}`")
                return [str(r[0]) for r in cursor.fetchall() if r[0] not in (None, "")]
        distincts["providers"].update(get_distinct(provider_col))
        distincts["customers"].update(get_distinct(customer_col))
        distincts["states"].update(get_distinct(state_col))
        distincts["sites"].update(get_distinct(site_col))
        distincts["wtgs"].update(get_distinct(wtg_col))

    # Prepare final chart data
    grid_chart_data = []
    for year in sorted(year_failure_hours.keys()):
        hours_list = year_failure_hours[year]
        avg_failure = round(sum(hours_list) / len(hours_list), 2) if hours_list else 0.0
        grid_chart_data.append({"year": year, "avg_failure": avg_failure})

    availability_chart_data = []
    for month in sorted(month_failure_hours.keys()):
        hours_list = month_failure_hours[month]
        avg_failure = round(sum(hours_list) / len(hours_list), 2) if hours_list else 0.0
        avg_availability = round(100.0 - avg_failure, 2)
        avg_machine = min(100.0, avg_availability + 2.0)
        availability_chart_data.append({
            "month": month,
            "grid_availability": avg_availability,
            "machine_availability": avg_machine
        })

    # PLF (Yearly)
    plf_yearly_data = []
    for year in sorted(year_plf.keys()):
        vals = year_plf[year]
        avg_plf = round(sum(vals) / len(vals), 2) if vals else 0.0
        plf_yearly_data.append({"year": year, "avg_plf": avg_plf})

    # PLF (Monthly per year)
    plf_monthly_data = defaultdict(list)
    for month, vals in month_plf.items():
        avg_plf = round(sum(vals) / len(vals), 2) if vals else 0.0
        year = month.split("-")[0]
        plf_monthly_data[year].append({"month": month, "avg_plf": avg_plf})

    context = {
        "grid_chart_data": json.dumps(grid_chart_data),
        "availability_chart_data": json.dumps(availability_chart_data),
        "plf_yearly_data": json.dumps(plf_yearly_data),
        "plf_monthly_data": json.dumps(plf_monthly_data),
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
        "no_data": False,
    }
    return render(request, "wind_Grid_Availability_and_Machine.html", context)

from collections import defaultdict
from datetime import datetime, date
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
import json


def _pick(col_map, *candidates):
    """Find actual column name from possible variants with normalization."""
    def normalize(name):
        return (
            name.lower()
            .replace(".", "")
            .replace("%", "")
            .replace(" ", "")
            .replace("_", "")
            .strip()
        )
    for c in candidates:
        norm_c = normalize(c)
        for actual in col_map:
            if normalize(actual) == norm_c:
                return col_map[actual]
    return None


def parse_date_like(v):
    if isinstance(v, date):
        return v
    if isinstance(v, datetime):
        return v.date()
    formats = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d-%b-%Y", "%d.%m.%Y")
    for fmt in formats:
        try:
            return datetime.strptime(str(v).strip(), fmt).date()
        except Exception:
            continue
    try:
        parts = str(v).replace("/", "-").replace(".", "-").split("-")
        if len(parts) == 3:
            if len(parts[0]) == 4:
                return datetime(int(parts[0]), int(parts[1]), int(parts[2])).date()
            else:
                return datetime(int(parts[2]), int(parts[1]), int(parts[0])).date()
    except Exception:
        pass
    return None


def parse_hours(value):
    """Convert Operating Hours into float hours."""
    if not value:
        return 0.0
    try:
        if isinstance(value, (int, float)):
            return float(value)
        parts = str(value).split(":")
        if len(parts) == 3:
            h, m, s = map(int, parts)
            return h + m/60 + s/3600
        elif len(parts) == 2:
            h, m = map(int, parts)
            return h + m/60
        elif len(parts) == 1:
            return float(parts[0])
    except:
        return 0.0
    return 0.0


@login_required
def wind_drill_down(request):
    user = request.user.username.lower()

    # --- find all wind tables for this user ---
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        tables = [row[0] for row in cursor.fetchall()]
    table_names = [t for t in tables if t.startswith(user + "_") and t.endswith("_wind")]

    if not table_names:
        return render(request, "wind_drill_down.html", {
            "site_gen_data": "[]",
            "ma_data": "[]",
            "ga_data": "[]",
            "oh_data": "[]",
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
            "no_data": True,
            "no_data_msg": "No wind tables found for your account."
        })

    # --- filters from GET ---
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    selected_providers = request.GET.getlist("provider")
    selected_customers = request.GET.getlist("customer")
    selected_states = request.GET.getlist("state")
    selected_sites = request.GET.getlist("site")
    selected_wtgs = request.GET.getlist("wtg")

    # --- aggregators ---
    site_gen = defaultdict(float)
    ma_by_wec = defaultdict(list)
    ga_by_wec = defaultdict(list)
    oh_by_wec = defaultdict(float)

    # --- distinct filter values ---
    providers_set, customers_set, states_set, sites_set, wtgs_set = set(), set(), set(), set(), set()

    for table in table_names:
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table}`")
            cols = [row[0] for row in cursor.fetchall()]
        col_map = {c: c for c in cols}

        date_col = _pick(col_map, "date", "gen date", "reading_date", "day_date")
        site_col = _pick(col_map, "site", "location", "plant", "park")
        wec_col = _pick(col_map, "wec", "wtg", "wecno", "wtgno", "loc no")
        gen_col = _pick(col_map, "generation", "gen", "genkwh", "gen kwh day")
        ma_col = _pick(col_map, "ma", "machineavailability", "machine availability", "ma%", "m/c avail%")
        ga_col = _pick(col_map, "ga", "gridavailability", "grid availability", "ga%", "gia")
        
        oh_col = _pick(col_map, "o.hrs", "ophrs", "operating hours", "machine hrs", "gen hrs", "opr hrs")

        provider_col = _pick(col_map, "provider", "oem")
        customer_col = _pick(col_map, "customer", "customer name", "client")
        state_col = _pick(col_map, "state")
        site_filter_col = site_col

        if not date_col:
            continue

        # --- build WHERE clause ---
        conditions, params = [], []
        if date_from:
            conditions.append(f"`{date_col}` >= %s")
            params.append(date_from)
        if date_to:
            conditions.append(f"`{date_col}` <= %s")
            params.append(date_to)
        if selected_providers and provider_col:
            placeholders = ",".join(["%s"] * len(selected_providers))
            conditions.append(f"`{provider_col}` IN ({placeholders})")
            params.extend(selected_providers)
        if selected_customers and customer_col:
            placeholders = ",".join(["%s"] * len(selected_customers))
            conditions.append(f"`{customer_col}` IN ({placeholders})")
            params.extend(selected_customers)
        if selected_states and state_col:
            placeholders = ",".join(["%s"] * len(selected_states))
            conditions.append(f"`{state_col}` IN ({placeholders})")
            params.extend(selected_states)
        if selected_sites and site_filter_col:
            placeholders = ",".join(["%s"] * len(selected_sites))
            conditions.append(f"`{site_filter_col}` IN ({placeholders})")
            params.extend(selected_sites)
        if selected_wtgs and wec_col:
            placeholders = ",".join(["%s"] * len(selected_wtgs))
            conditions.append(f"`{wec_col}` IN ({placeholders})")
            params.extend(selected_wtgs)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        select_cols = [c for c in [date_col, site_col, wec_col, gen_col, ma_col, ga_col, oh_col,
                                   provider_col, customer_col, state_col] if c]
        select_clause = ", ".join(f"`{c}`" for c in select_cols)

        query = f"SELECT {select_clause} FROM `{table}` {where_clause}"
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        idx = {col: i for i, col in enumerate(select_cols)}

        for row in rows:
            d = parse_date_like(row[idx[date_col]])
            if not d:
                continue

            site_val = row[idx.get(site_col)] if site_col else "Unknown"
            wec_val = row[idx.get(wec_col)] if wec_col else "Unknown"

            # collect distinct filter values
            if provider_col and row[idx.get(provider_col)]: providers_set.add(row[idx[provider_col]])
            if customer_col and row[idx.get(customer_col)]: customers_set.add(row[idx[customer_col]])
            if state_col and row[idx.get(state_col)]: states_set.add(row[idx[state_col]])
            if site_col and row[idx.get(site_col)]: sites_set.add(row[idx[site_col]])
            if wec_col and row[idx.get(wec_col)]: wtgs_set.add(row[idx[wec_col]])

            # Generation
            if gen_col and row[idx.get(gen_col)] not in (None, ""):
                try:
                    site_gen[site_val] += float(row[idx[gen_col]])
                except:
                    pass

            # Machine Availability
            if ma_col and row[idx.get(ma_col)] not in (None, ""):
                try:
                    ma_by_wec[wec_val].append(float(row[idx[ma_col]]))
                except:
                    pass

            # Grid Availability
            if ga_col and row[idx.get(ga_col)] not in (None, ""):
                try:
                    ga_by_wec[wec_val].append(float(row[idx[ga_col]]))
                except:
                    pass

            # Operating Hours
            if oh_col and row[idx.get(oh_col)] not in (None, ""):
                oh_by_wec[wec_val] += parse_hours(row[idx[oh_col]])

    # --- prepare chart data ---
    site_gen_data = [{"site": k, "generation": v} for k, v in site_gen.items()]
    ma_data = [{"wec": k, "ma": sum(v)/len(v)} for k, v in ma_by_wec.items() if v]
    ga_data = [{"wec": k, "ga": sum(v)/len(v)} for k, v in ga_by_wec.items() if v]
    oh_data = [{"wec": k, "hours": v} for k, v in oh_by_wec.items()]

    context = {
        "site_gen_data": json.dumps(site_gen_data),
        "ma_data": json.dumps(ma_data),
        "ga_data": json.dumps(ga_data),
        "oh_data": json.dumps(oh_data),
        "providers": sorted(providers_set),
        "customers": sorted(customers_set),
        "states": sorted(states_set),
        "sites": sorted(sites_set),
        "wtgs": sorted(wtgs_set),
        "selected_providers": selected_providers,
        "selected_customers": selected_customers,
        "selected_states": selected_states,
        "selected_sites": selected_sites,
        "selected_wtgs": selected_wtgs,
        "date_from": date_from,
        "date_to": date_to,
        "no_data": False,
    }
    return render(request, "wind_drill_down.html", context)


import json
from django.db import connection
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


# Helper: pick column name matching any in candidates
def _pick(col_map, *candidates):
    for c in candidates:
        c_norm = c.lower().replace(" ", "").replace("_", "").replace(".", "")
        for k, v in col_map.items():
            if k.lower().replace(" ", "").replace("_", "").replace(".", "") == c_norm:
                return v
    return None


# Helper: parse date-like values
def parse_date_like(value):
    import datetime
    if not value:
        return None
    if isinstance(value, datetime.date):
        return value
    try:
        return datetime.datetime.strptime(str(value), "%Y-%m-%d").date()
    except Exception:
        try:
            return datetime.datetime.strptime(str(value), "%d-%m-%Y").date()
        except Exception:
            return None


@login_required
def wind_breakdown_log(request):
    user = request.user.username.lower()

    # --- find all wind tables for this user ---
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        tables = [row[0] for row in cursor.fetchall()]
    table_names = [t for t in tables if t.startswith(user + "_") and t.endswith("_wind")]

    if not table_names:
        return render(request, "wind_breakdown_log.html", {
            "breakdown_data": "[]",
            "providers": [], "customers": [], "states": [], "sites": [], "wtgs": [],
            "selected_providers": [], "selected_customers": [], "selected_states": [],
            "selected_sites": [], "selected_wtgs": [],
            "no_data": True,
            "no_data_msg": "No wind tables found for your account."
        })

    # --- filters ---
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    selected_providers = request.GET.getlist("provider")
    selected_customers = request.GET.getlist("customer")
    selected_states = request.GET.getlist("state")
    selected_sites = request.GET.getlist("site")
    selected_wtgs = request.GET.getlist("wtg")

    breakdown_records = []
    providers_set, customers_set, states_set, sites_set, wtgs_set = set(), set(), set(), set(), set()

    for table in table_names:
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table}`")
            cols = [row[0] for row in cursor.fetchall()]
        col_map = {c: c for c in cols}

        date_col = _pick(col_map, "date", "gen date", "reading_date", "day_date")
        site_col = _pick(col_map, "site", "location", "plant", "park")
        wec_col = _pick(col_map, "wec", "wtg", "wecno", "wtgno")
        lhrs_col = _pick(col_map, "l.hrs","l_hrs", "lhours", "loss hours", "lhrs", "lhour")
        remarks_col = _pick(col_map, "remarks", "comment", "reason", "note")

        provider_col = _pick(col_map, "provider", "oem")
        customer_col = _pick(col_map, "customer", "customer name", "client")
        state_col = _pick(col_map, "state")

        if not date_col:
            continue

        # --- build WHERE ---
        conditions, params = [], []
        if date_from:
            conditions.append(f"`{date_col}` >= %s")
            params.append(date_from)
        if date_to:
            conditions.append(f"`{date_col}` <= %s")
            params.append(date_to)
        if selected_providers and provider_col:
            placeholders = ",".join(["%s"] * len(selected_providers))
            conditions.append(f"`{provider_col}` IN ({placeholders})")
            params.extend(selected_providers)
        if selected_customers and customer_col:
            placeholders = ",".join(["%s"] * len(selected_customers))
            conditions.append(f"`{customer_col}` IN ({placeholders})")
            params.extend(selected_customers)
        if selected_states and state_col:
            placeholders = ",".join(["%s"] * len(selected_states))
            conditions.append(f"`{state_col}` IN ({placeholders})")
            params.extend(selected_states)
        if selected_sites and site_col:
            placeholders = ",".join(["%s"] * len(selected_sites))
            conditions.append(f"`{site_col}` IN ({placeholders})")
            params.extend(selected_sites)
        if selected_wtgs and wec_col:
            placeholders = ",".join(["%s"] * len(selected_wtgs))
            conditions.append(f"`{wec_col}` IN ({placeholders})")
            params.extend(selected_wtgs)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        select_cols = [c for c in [date_col, site_col, wec_col, lhrs_col, remarks_col,
                                   provider_col, customer_col, state_col] if c]
        query = f"SELECT {', '.join('`'+c+'`' for c in select_cols)} FROM `{table}` {where_clause}"

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        idx = {col: i for i, col in enumerate(select_cols)}

        for row in rows:
            d = parse_date_like(row[idx[date_col]])
            if not d:
                continue

            lhrs = str(row[idx.get(lhrs_col)]) if lhrs_col and row[idx.get(lhrs_col)] is not None else ""
            remarks = str(row[idx.get(remarks_col)]).strip() if remarks_col and row[idx.get(remarks_col)] else ""

            # ✅ Always include row. If empty, default to "0"
            if not lhrs and not remarks:
                remarks = "0"

            record = {
                "state": row[idx.get(state_col)] if state_col else "Unknown",
                "site": row[idx.get(site_col)] if site_col else "Unknown",
                "wec": row[idx.get(wec_col)] if wec_col else "Unknown",
                "date": d.strftime("%d-%m-%Y"),
                "remarks": remarks
            }
            breakdown_records.append(record)

            # Collect distinct filter values
            if provider_col and row[idx.get(provider_col)]:
                providers_set.add(row[idx[provider_col]])
            if customer_col and row[idx.get(customer_col)]:
                customers_set.add(row[idx[customer_col]])
            if state_col and row[idx.get(state_col)]:
                states_set.add(row[idx[state_col]])
            if site_col and row[idx.get(site_col)]:
                sites_set.add(row[idx[site_col]])
            if wec_col and row[idx.get(wec_col)]:
                wtgs_set.add(row[idx[wec_col]])

    # Debug print
    print("📊 Breakdown records:", breakdown_records)

    # Sort by date
    breakdown_records = sorted(breakdown_records, key=lambda x: x["date"])

    context = {
        "breakdown_data": json.dumps(breakdown_records),
        "providers": sorted(providers_set),
        "customers": sorted(customers_set),
        "states": sorted(states_set),
        "sites": sorted(sites_set),
        "wtgs": sorted(wtgs_set),
        "selected_providers": selected_providers,
        "selected_customers": selected_customers,
        "selected_states": selected_states,
        "selected_sites": selected_sites,
        "selected_wtgs": selected_wtgs,
        "date_from": date_from,
        "date_to": date_to,
        "no_data": False if breakdown_records else True,
        "no_data_msg": "No data found for given filters." if not breakdown_records else "",
    }
    return render(request, "wind_breakdown_log.html", context)
