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

@login_required
def wind_installation_summary2(request):
    table_name = "installation_summary_wind"

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

    return render(request, "wind_installation_summary2.html", {
        "data": json.dumps(data),
        "wtg_locations": wtg_locations,
        "oem_breakup": oem_breakup
    })
import json
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required

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


def _pick(col_map, *candidates):
    """Return the actual-cased column name from SHOW COLUMNS that matches any candidate (case-insensitive)."""
    for cand in candidates:
        lc = cand.lower()
        if lc in col_map:
            return col_map[lc]
    return None


@login_required
def wind_generation_kwh(request):
    user = request.user.username.lower()

    # --- Find ALL user's wind tables: <username>_*_wind
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        db_tables = [row[0] for row in cursor.fetchall()]
    table_names = [t for t in db_tables if t.startswith(user + "_") and t.endswith("_wind")]
    if not table_names:
        return HttpResponse(f"No wind generation table found for user: {user}", status=404)

    # --- Collect filters from GET (multi-select)
    date_from  = request.GET.get("date_from") or None
    date_to    = request.GET.get("date_to") or None
    providers  = request.GET.getlist("provider")
    customers  = request.GET.getlist("customer")
    states     = request.GET.getlist("state")
    sites      = request.GET.getlist("site")
    wtgs       = request.GET.getlist("wtg")

    # Global aggregations
    wtg_sum = defaultdict(int)  # {wtg: total_gen}
    total_generation = 0

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

        # --- Column discovery
        wtg_col      = _pick(col_map, "wec", "loc_no", "wtg", "wtg_no", "turbine", "turbine_no")
        gen_col      = _pick(col_map, "generation", "gen", "gen_kwh", "kwh", "energy", "units")
        date_col     = _pick(col_map, "date", "gen_date", "reading_date", "day_date")
        customer_col = _pick(col_map, "customer_name", "customer", "consumer", "client")
        state_col    = _pick(col_map, "state", "state_name", "st")
        site_col     = _pick(col_map, "site", "site_name", "location", "plant", "wind_farm_name", "park", "sitecode", "city", "town", "village")
        provider_col = _pick(col_map, "provider", "oem", "oem_provider", "oem_name", "oemprovider")

        if not wtg_col or not gen_col:
            # Skip tables missing core columns
            continue

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

        # --- Aggregate WTG wise for this table
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
    chart_data = [{"wtg": k, "generation": v} for k, v in wtg_sum.items()]
    # Order by generation desc for treemap consistency
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
    if not table_names:
        return HttpResponse(f"No wind generation table found for user: {user}", status=404)

    # --- Collect filters from GET (multi-select)
    date_from = request.GET.get("date_from") or None
    date_to = request.GET.get("date_to") or None
    providers = request.GET.getlist("provider")
    customers = request.GET.getlist("customer")
    states = request.GET.getlist("state")
    sites = request.GET.getlist("site")
    wtgs = request.GET.getlist("wtg")

    # Global aggregations
    wtg_sum = defaultdict(int)  # {wtg: total_hours}
    total_hours = 0

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
        wtg_col = _pick(col_map, "wec", "loc_no", "wtg", "wtg_no", "turbine", "turbineno", "locno")
        hours_col = _pick(col_map, "genhrs", "ohrs", "generationhours", "gen_hours", "gen_hrs")
        date_col = _pick(col_map, "date", "gen_date", "reading_date", "day_date")
        customer_col = _pick(col_map, "customername", "customer", "consumer", "client")
        state_col = _pick(col_map, "state", "statename", "st")
        site_col = _pick(col_map, "site", "sitename", "location", "plant", "windfarmname", "park", "sitecode", "city", "town", "village")
        provider_col = _pick(col_map, "provider", "oem", "oemprovider", "oem_name")

 
        if not wtg_col or not hours_col:
            continue  # skip tables missing core columns

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

        # --- Aggregate WTG wise for this table
        query = f"""
            SELECT `{wtg_col}`, SUM(`{hours_col}`) AS total_hours
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
    }

    return render(request, "wind_genration_hovers.html", context)
