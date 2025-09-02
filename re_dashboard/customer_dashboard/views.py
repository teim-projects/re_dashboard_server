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

    # --- Find user's wind table:  <username>_*_wind
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        db_tables = [row[0] for row in cursor.fetchall()]
    table_name = next((t for t in db_tables if t.startswith(user + "_") and t.endswith("_wind")), None)
    if not table_name:
        return HttpResponse(f"No wind generation table found for user: {user}", status=404)

    # --- Read schema and build case-insensitive column map
    with connection.cursor() as cursor:
        cursor.execute(f"SHOW COLUMNS FROM `{table_name}`;")
        cols = [r[0] for r in cursor.fetchall()]
    col_map = {c.lower(): c for c in cols}  # lower -> actual case

    # --- Discover columns from common aliases
    wtg_col  = _pick(col_map, "loc_no", "wtg", "wtg_no", "turbine", "turbine_no")
    gen_col  = _pick(col_map, "gen_kwh_day", "generation", "day_generation", "day_gen_kwh", "gen_day_kwh", "kwh")
    date_col = _pick(col_map, "gen_date", "date", "reading_date", "day_date")

    customer_col = _pick(col_map, "customer_name", "customer", "consumer", "client")
    state_col    = _pick(col_map, "state", "state_name", "st")
    site_col     = _pick(col_map, "site", "site_name", "location", "plant", "wind_farm_name", "park", "sitecode", "city", "town", "village")
    provider_col = _pick(col_map, "oem", "provider", "oem_provider", "oem_name", "oemprovider")

    if not wtg_col or not gen_col:
        return HttpResponse(
            f"Required columns not found in `{table_name}` "
            f"(need turbine id & daily generation).", status=500
        )

    # --- Collect filters from GET (multi-select)
    date_from  = request.GET.get("date_from") or None
    date_to    = request.GET.get("date_to") or None
    providers  = request.GET.getlist("provider")
    customers  = request.GET.getlist("customer")
    states     = request.GET.getlist("state")
    sites      = request.GET.getlist("site")
    wtgs       = request.GET.getlist("wtg")

    conditions, params = [], []

    # Date range
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

    # --- Main aggregation (WTG wise)
    query = f"""
        SELECT `{wtg_col}`, SUM(`{gen_col}`) AS total_gen
        FROM `{table_name}`
        {where_clause}
        GROUP BY `{wtg_col}`
        ORDER BY total_gen DESC
    """

    chart_data, table_data, total_generation = [], [], 0
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()

    for wtg, gen in rows:
        gen = int(gen or 0)
        total_generation += gen
        chart_data.append({"wtg": wtg, "generation": gen})
        table_data.append({"wtg_no": wtg, "generation": gen})

    # --- Distincts for filter modals (unfiltered = from entire table)
    def distinct_list(col):
        if not col:
            return []
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT DISTINCT `{col}` FROM `{table_name}` ORDER BY `{col}`;")
            return [r[0] for r in cursor.fetchall() if r[0] not in (None, "")]

    providers_dist = distinct_list(provider_col)
    customers_dist = distinct_list(customer_col)
    states_dist    = distinct_list(state_col)
    sites_dist     = distinct_list(site_col)
    wtgs_dist      = distinct_list(wtg_col)

    context = {
        "chart_data": json.dumps(chart_data),
        "table_data": table_data,
        "total_generation": total_generation,

        # dynamic filter choices
        "providers": providers_dist,
        "customers": customers_dist,
        "states": states_dist,
        "sites": sites_dist,
        "wtgs": wtgs_dist,

        "request": request,  # keep GET sticky
    }
    return render(request, "wind_generation_kwh.html", context)
