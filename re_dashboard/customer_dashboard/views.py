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

from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
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

    # Logged-in user → match against `customer` column
    customer = request.user.username

    try:
        with connection.cursor() as cursor:
            # Capacity by state (only this customer)
            cursor.execute(f"""
                SELECT state, SUM(capacity_mw) AS total_capacity
                FROM `{table_name}`
                WHERE customer = %s
                GROUP BY state
            """, [customer])
            data["capacity_by_state"] = cursor.fetchall()

            # Land type by state
            cursor.execute(f"""
                SELECT state, land, COUNT(*) AS land_count
                FROM `{table_name}`
                WHERE customer = %s
                GROUP BY state, land
            """, [customer])
            data["land_type_by_state"] = cursor.fetchall()

            # Estimated generation WTG wise
            cursor.execute(f"""
                SELECT wtg_location_no, avg_estimate_gen_kwh
                FROM `{table_name}`
                WHERE customer = %s
            """, [customer])
            data["wtg_generation"] = cursor.fetchall()

            # Power sale by state
            cursor.execute(f"""
                SELECT power_sale_details, state
                FROM `{table_name}`
                WHERE customer = %s
            """, [customer])
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
        "installation_summary_Wind",
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

    # --- Current logged-in user name (match against `customer` column)
    customer = request.user.username

    # --- Data containers
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
            WHERE customer = %s
            GROUP BY category
        """, [customer])
        for row in cursor.fetchall():
            data["power_sale_labels"].append(row[0])
            data["power_sale_counts"].append(row[1])

        # Land
        cursor.execute(f"""
            SELECT land, COUNT(*)
            FROM `{table_name}`
            WHERE customer = %s
            GROUP BY land
        """, [customer])
        for row in cursor.fetchall():
            data["land_labels"].append(row[0])
            data["land_counts"].append(row[1])

        # WTG Locations (top 10 by estimated generation)
        cursor.execute(f"""
            SELECT wtg_location_no, avg_estimate_gen_kwh
            FROM `{table_name}`
            WHERE customer = %s
            ORDER BY avg_estimate_gen_kwh DESC
            LIMIT 10
        """, [customer])
        wtg_locations = cursor.fetchall()

        # OEM Breakup
        cursor.execute(f"""
            SELECT capacity_mw, firm, make, COUNT(*)
            FROM `{table_name}`
            WHERE customer = %s
            GROUP BY capacity_mw, firm, make
        """, [customer])
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

import json
import re
from collections import defaultdict
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required


import json
import re
from collections import defaultdict
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required


def normalize(col):
    """Normalize column name for comparison"""
    return re.sub(r'[^a-z0-9]+', '_', col.lower()).strip('_')


def _pick(col_map, *candidates):
    """Match candidate names against actual columns (case/space/dot insensitive)."""
    for cand in candidates:
        cand_norm = normalize(cand)
        for k, v in col_map.items():
            if normalize(k) == cand_norm:
                return v
    return None


import json
import re
from collections import defaultdict
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required


def normalize(col):
    """Normalize column name for comparison"""
    return re.sub(r'[^a-z0-9]+', '_', col.lower()).strip('_')


def _pick(col_map, *candidates):
    """
    Match candidate names against actual columns (case/space/dot insensitive).
    Returns actual column name if found.
    """
    for cand in candidates:
        cand_norm = normalize(cand)
        for k, v in col_map.items():
            if normalize(k) == cand_norm:
                return v
    return None


@login_required
def wind_generation_kwh(request):
    user = request.user.username.lower()

    # --- Find ALL user's wind tables
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        db_tables = [row[0] for row in cursor.fetchall()]
    table_names = [t for t in db_tables if t.startswith(user + "_") and t.endswith("_wind")]

    if not table_names:
        return render(request, "wind_generation_kwh.html", {
            "chart_data": json.dumps([]),
            "table_data": [],
            "total_generation": 0,
            "providers": [], "customers": [], "states": [], "sites": [], "wtgs": [],
            "selected_providers": [], "selected_customers": [],
            "selected_states": [], "selected_sites": [], "selected_wtgs": [],
            "date_from": None, "date_to": None,
            "no_data": True,
            "no_data_msg": "No wind generation data found for your account."
        })

    # --- Collect filters from GET
    date_from = request.GET.get("date_from") or None
    date_to = request.GET.get("date_to") or None
    providers = request.GET.getlist("provider")
    customers = request.GET.getlist("customer")
    states = request.GET.getlist("state")
    sites = request.GET.getlist("site")
    wtgs = request.GET.getlist("wtg")

    wtg_sum = defaultdict(float)
    distincts = {k: set() for k in ["providers", "customers", "states", "sites", "wtgs"]}

    # Loop over all user tables
    for table_name in table_names:
        print(f"📂 Processing table: {table_name}")

        # --- Read schema
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table_name}`;")
            cols = [r[0] for r in cursor.fetchall()]
        col_map = {normalize(c): c for c in cols}

        # --- Flexible column mapping
        wtg_col = _pick(col_map, "loc_no", "loc no", "wtg", "wtg_no", "wec")
        gen_col = _pick(col_map, "gen_kwh_day", "gen_kwh", "generation", "gen (kwh)", "kwh")
        date_col = _pick(col_map, "gen_date", "date")
        customer_col = _pick(col_map, "customer_name", "customer")
        state_col = _pick(col_map, "state")
        site_col = _pick(col_map, "site", "wind_farm_name")
        provider_col = _pick(col_map, "provider", "oem")

        if not wtg_col or not gen_col:
            print(f"❌ Skipping {table_name}, missing columns")
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

        # --- Aggregate generation
        query = f"""
            SELECT `{wtg_col}`, SUM(`{gen_col}`) AS total_gen
            FROM `{table_name}`
            {where_clause}
            GROUP BY `{wtg_col}`
        """
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        print(f"⚡ {table_name} rows:", len(rows))

        for wtg, gen in rows:
            wtg_sum[str(wtg)] += float(gen or 0)

        # --- Collect distinct values
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

    # --- Final aggregations
    chart_data = [{"wtg": k, "generation": v} for k, v in wtg_sum.items()]
    chart_data.sort(key=lambda x: x["generation"], reverse=True)
    table_data = [{"wtg_no": d["wtg"], "generation": d["generation"]} for d in chart_data]

    total_generation = sum(wtg_sum.values())

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
from datetime import datetime, date  # ✅ keep original classes
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
import json

def _pick(col_map, *candidates):
    """Return actual-cased column name if it matches any candidate"""
    for c in candidates:
        lc = c.lower()
        if lc in col_map:
            return col_map[lc]
    return None

def parse_date_like(v):
    """Parse date/datetime strings or objects into date object (SAFE)"""
    # ✅ DO NOT overwrite 'date' or 'datetime'
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
    return None  # ✅ return None if no format matches

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
        hms_parts = [0, 0, 0]

    hours = days * 24 + hms_parts[0] + hms_parts[1] / 60 + hms_parts[2] / 3600
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
        return render(request, "wind_genration_hovers.html", {
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
        })

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

        # --- Identify columns safely
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

        # --- Build conditions
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

        for d_val, wtg_val, hrs in rows:
            d_obj = parse_date_like(d_val)  # ✅ SAFE
            if not d_obj:
                continue

            year = d_obj.year
            years_set.add(year)

            if not wtg_val:
                continue

            wtg_name = str(wtg_val)
            hour_val = float(hrs or 0)
            wtg_year_hours[(wtg_name, year)] += hour_val
            total_hours += hour_val

        # --- Collect distinct values
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
            wtg_year_hours.setdefault((wtg, year), 0.0)

    # --- Prepare chart & table
    chart_data = [
        {"wtg": k[0], "year": k[1], "hours": round(v, 2)}
        for k, v in sorted(wtg_year_hours.items(), key=lambda x: (x[0][1], x[0][0]))
    ]

    table_data = [
        {"wtg_no": k[0], "year": k[1], "hours": round(v, 2)}
        for k, v in wtg_year_hours.items()
    ]

    years = sorted(years_set)

    context = {
        "chart_data": json.dumps(chart_data),
        "table_data": table_data,
        "years": years,
        "total_hours": round(total_hours, 2),
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

        plf_day_col = _pick(col_map, "plf_day", "plfday", "%plf_day", "plf","%PLFDAY","cf", "plf","PLF_DAY","plf_day", "plantloadfactor", "capacityfactor")

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
    """Return a date object or None."""
    if v is None:
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    formats = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d-%b-%Y", "%d.%m.%Y", "%Y/%m/%d")
    s = str(v).strip()
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue
    # try smart split (Y-M-D or D-M-Y)
    try:
        parts = s.replace("/", "-").replace(".", "-").split("-")
        if len(parts) == 3:
            if len(parts[0]) == 4:  # yyyy-mm-dd
                return datetime(int(parts[0]), int(parts[1]), int(parts[2])).date()
            else:  # dd-mm-yyyy
                return datetime(int(parts[2]), int(parts[1]), int(parts[0])).date()
    except Exception:
        pass
    return None


def parse_hours(value):
    """Convert Operating Hours into float hours. Accepts 'HH:MM:SS', numeric, etc."""
    if value is None or value == "":
        return 0.0
    try:
        if isinstance(value, (int, float)):
            return float(value)
        s = str(value).strip()
        # some spreadsheets show "00:00" or "24:00:00"
        parts = s.split(":")
        if len(parts) == 3:
            h, m, sec = parts
            return float(h) + float(m) / 60.0 + float(sec) / 3600.0
        elif len(parts) == 2:
            h, m = parts
            return float(h) + float(m) / 60.0
        else:
            # try direct float
            return float(s)
    except Exception:
        return 0.0


def safe_float(v):
    """Try to coerce value to float, return 0.0 on failure."""
    try:
        if v is None or v == "":
            return 0.0
        return float(v)
    except Exception:
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

        # --- try to detect columns ---
        date_col = _pick(col_map, "date", "gen date", "reading_date", "day_date", "gen.date", "gen_date")
        site_col = _pick(col_map, "site", "location", "plant", "park")
        wec_col = _pick(col_map, "wec", "wtg", "wecno", "wtgno", "loc no", "locno", "loc. no")
        gen_col = _pick(col_map, "generation", "gen", "genkwh", "gen kwh day", "gen (kwh) day", "gen.(kwh)")
        ma_col = _pick(col_map,  "ma", "machineavailability", "m/c avail.%", "m/c avail", "mc_avail", "m_c_avail", "m/c avail", "m c avail")
        ga_col = _pick(col_map, "ga", "gridavailability", "grid availability", "ga%", "gia", "%ga")
        # operating hours column candidates
        oh_col = _pick(col_map, "O_hrs","Opr_Hrs" ,"ohrs", "operatinghours", "op_hours", "op_hrs", "opr hrs", "Gen Hrs", "GenHrs")
        provider_col = _pick(col_map, "provider", "oem")
        customer_col = _pick(col_map, "customer", "customer name", "client", "customername")
        state_col = _pick(col_map, "state")
        site_filter_col = site_col

        # Suzlon-style columns for GA computation fallback
        gf_col = _pick(col_map, "gf")
        fm_col = _pick(col_map, "fm")
        s_col = _pick(col_map, "s")
        u_col = _pick(col_map, "u")
        nor_col = _pick(col_map, "nor")
        opr_col = _pick(col_map, "opr hrs", "opr_hrs", "oprhrs", "ophrs", "operatinghours", "Opr_Hrs", "Gen Hrs")

        if not date_col:
            # can't process rows without date
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
                                   provider_col, customer_col, state_col, gf_col, fm_col, s_col, u_col, nor_col, opr_col] if c]
        select_clause = ", ".join(f"`{c}`" for c in select_cols)

        query = f"SELECT {select_clause} FROM `{table}` {where_clause}"
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        idx = {col: i for i, col in enumerate(select_cols)}

        def val(row, column_name):
            """Safely get value from row by column name (may be missing)."""
            if not column_name:
                return None
            pos = idx.get(column_name)
            if pos is None:
                return None
            return row[pos]

        for row in rows:
            d = parse_date_like(val(row, date_col))
            if not d:
                continue

            site_val = val(row, site_col) or "Unknown"
            wec_val = val(row, wec_col) or "Unknown"

            # collect distinct filter values
            if provider_col and val(row, provider_col): providers_set.add(val(row, provider_col))
            if customer_col and val(row, customer_col): customers_set.add(val(row, customer_col))
            if state_col and val(row, state_col): states_set.add(val(row, state_col))
            if site_col and val(row, site_col): sites_set.add(val(row, site_col))
            if wec_col and val(row, wec_col): wtgs_set.add(val(row, wec_col))

            # Generation
            gen_val = val(row, gen_col)
            if gen_col and gen_val not in (None, ""):
                try:
                    site_gen[site_val] += float(gen_val)
                except Exception:
                    try:
                        site_gen[site_val] += safe_float(str(gen_val).replace(",", ""))
                    except Exception:
                        pass

            # Machine Availability
            ma_val = val(row, ma_col)
            if ma_col and ma_val not in (None, ""):
                try:
                    ma_by_wec[wec_val].append(float(ma_val))
                except Exception:
                    ma_by_wec[wec_val].append(safe_float(ma_val))

            # Grid Availability: prefer ga_col if present else compute from gf/fm/s/u/nor and opr hrs
            if ga_col and val(row, ga_col) not in (None, ""):
                try:
                    ga_by_wec[wec_val].append(float(val(row, ga_col)))
                except Exception:
                    ga_by_wec[wec_val].append(safe_float(val(row, ga_col)))
            else:
                # fallback compute GA if we have any of gf/fm/s/u/nor/ophrs
                gf_v = safe_float(val(row, gf_col)) if gf_col else 0.0
                fm_v = safe_float(val(row, fm_col)) if fm_col else 0.0
                s_v = safe_float(val(row, s_col)) if s_col else 0.0
                u_v = safe_float(val(row, u_col)) if u_col else 0.0
                nor_v = safe_float(val(row, nor_col)) if nor_col else 0.0

                opr_h_raw = val(row, opr_col) if opr_col else None
                opr_h = parse_hours(opr_h_raw) if opr_h_raw not in (None, "") else 0.0
                if opr_h <= 0:
                    # default to 24 (per your choice)
                    opr_h = 24.0

                unavailable = gf_v + fm_v + s_v + u_v + nor_v
                available_hours = opr_h - unavailable
                if available_hours < 0:
                    available_hours = 0.0
                try:
                    ga_percent = (available_hours / opr_h) * 100.0 if opr_h > 0 else 0.0
                except Exception:
                    ga_percent = 0.0
                ga_by_wec[wec_val].append(ga_percent)

            # Operating Hours (aggregate)
            oh_val = val(row, oh_col)
            if oh_col and oh_val not in (None, ""):
                oh_by_wec[wec_val] += parse_hours(oh_val)
            else:
                # If Opr Hrs column not present, fallback to Gen Hrs or to 0
                # try Gen Hrs column name variants weren't explicitly added; we already used gen_col for kWh.
                # So skip if not present.
                pass

    # --- prepare chart data ---
    site_gen_data = [{"site": k, "generation": v} for k, v in site_gen.items()]
    ma_data = [{"wec": k, "ma": (sum(v) / len(v) if v else 0.0)} for k, v in ma_by_wec.items()]
    ga_data = [{"wec": k, "ga": (sum(v) / len(v) if v else 0.0)} for k, v in ga_by_wec.items()]
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

 

from collections import defaultdict
from datetime import datetime, date
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
import json


def _pick(col_map, *candidates):
    """Return the actual column name if it matches any of the candidates"""
    for c in candidates:
        lc = c.lower()
        if lc in col_map:
            return col_map[lc]
    return None


def parse_date_like(v):
    """Parse various date formats to datetime.date"""
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

from collections import defaultdict
from django.db import connection
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render
import json

@login_required
def wind_Avg_Machine_Availability(request):
    user = request.user.username.lower()

    # --- Get all wind tables for user
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        db_tables = [row[0] for row in cursor.fetchall()]
    table_names = [t for t in db_tables if t.startswith(user + "_") and t.endswith("_wind")]

    if not table_names:
        return render(request, "wind_Avg_Machine_Availability.html", {
            "chart_data": "[]",
            "table_data": [],
            "providers": [], "customers": [], "states": [], "sites": [], "wtgs": [],
            "selected_providers": [], "selected_customers": [], "selected_states": [], "selected_sites": [], "selected_wtgs": [],
            "date_from": None, "date_to": None,
            "no_data": True,
            "no_data_msg": "No wind tables found for your account.",
            "overall_avg_ma": 0,
            "paginator": None,
            "table_page": None
        })

    # --- Get filters from GET parameters
    date_from = request.GET.get("date_from") or None
    date_to = request.GET.get("date_to") or None
    providers = request.GET.getlist("provider")
    customers = request.GET.getlist("customer")
    states = request.GET.getlist("state")
    sites = request.GET.getlist("site")
    wtgs = request.GET.getlist("wtg")

    # --- Containers
    wtg_ma = defaultdict(list)
    distincts = {"providers": set(), "customers": set(), "states": set(), "sites": set(), "wtgs": set()}

    for table_name in table_names:
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table_name}`;")
            cols = [r[0] for r in cursor.fetchall()]
        col_map = {c.lower(): c for c in cols}

        # --- Identify columns
        date_col = _pick(col_map, "date", "gen_date", "reading_date", "day_date")
        wtg_col = _pick(col_map, "wec", "wtg", "loc_no", "turbine")
        ohrs_col = _pick(col_map, "ohrs", "operatinghours", "o_hours")
        loss_col = _pick(col_map, "lhrs", "losshrs", "loss_hours", "l_hrs")
        ma_col = _pick(col_map, "ma", "machineavailability","MC_Avail","m/c avail.%")

        provider_col = _pick(col_map, "provider", "oem")
        customer_col = _pick(col_map, "customer", "consumer", "client")
        state_col = _pick(col_map, "state", "statename")
        site_col = _pick(col_map, "site", "sitename", "plant")

        if not date_col or not wtg_col:
            continue

        # --- Build conditions for query
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

        # --- Expression for MA
        if ma_col:
            expr = f"`{ma_col}`"
        elif ohrs_col and loss_col:
            expr = f"(CASE WHEN `{ohrs_col}` > 0 THEN ((`{ohrs_col}` - `{loss_col}`)/`{ohrs_col}`)*100 ELSE 0 END)"
        else:
            continue

        # --- Query per table
        query = f"""
            SELECT `{wtg_col}`, AVG({expr}) AS avg_ma
            FROM `{table_name}`
            {where_clause}
            GROUP BY `{wtg_col}`
        """

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        for wtg_val, ma in rows:
            if not wtg_val:
                continue
            wtg_ma[str(wtg_val)].append(float(ma or 0))

        # --- Collect distincts for filters
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

    # --- Prepare chart & table data
    chart_data = [{"x": wtg, "y": round(sum(vals) / len(vals), 2)} for wtg, vals in wtg_ma.items()]
    table_data = [{"wtg_no": wtg, "avg_ma": round(sum(vals) / len(vals), 2)} for wtg, vals in wtg_ma.items()]

    # --- Paginate table data
    page = request.GET.get('page', 1)
    paginator = Paginator(table_data, 5)  # 10 rows per page
    try:
        table_page = paginator.page(page)
    except PageNotAnInteger:
        table_page = paginator.page(1)
    except EmptyPage:
        table_page = paginator.page(paginator.num_pages)

    # --- Calculate overall average MA
    all_vals = [val for vals in wtg_ma.values() for val in vals]
    overall_avg_ma = round(sum(all_vals) / len(all_vals), 2) if all_vals else 0

    context = {
        "chart_data": json.dumps(chart_data, default=str),
        "table_data": table_data,
        "table_page": table_page,
        "paginator": paginator,
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
        "no_data": len(chart_data) == 0,
        "no_data_msg": "No Machine Availability data found for the selected filters." if len(chart_data) == 0 else "",
        "overall_avg_ma": overall_avg_ma
    }

    return render(request, "wind_Avg_Machine_Availability.html", context)




from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.db import connection
from django.contrib.auth.models import User
from django.utils.timezone import now

import os
import re
import traceback
import pandas as pd
import numpy as np

import os, re, traceback
import pandas as pd
import numpy as np
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.db import connection
from django.contrib.auth.models import User
from django.utils.timezone import now



from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.db import connection
from django.contrib.auth.models import User
from django.utils.timezone import now

import os
import re
import traceback
import pandas as pd
import numpy as np

import os, re, traceback
import pandas as pd
import numpy as np
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.db import connection
from django.contrib.auth.models import User
from django.utils.timezone import now

import os, re, traceback
import pandas as pd
import numpy as np
from datetime import datetime, date
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.db import connection
from django.utils.timezone import now
from accounts.models import Provider, EnergyType
from core.models import UploadMetadata


# ---------------- HELPERS ---------------- #

def clean_col(col: str) -> str:
    return re.sub(r'\W+', '_', str(col).strip()).lower().strip('_')


def normalize_date(val):
    """Convert any date-like value to proper YYYY-MM-DD date."""
    if val is None or str(val).strip().lower() in ["", "nan", "nat"]:
        return None
    try:
        if isinstance(val, (datetime, pd.Timestamp)):
            return val.date()
        if isinstance(val, date):  # ✅ handle pure date
            return val
        if isinstance(val, (int, float)):
            return (datetime(1899, 12, 30) + pd.to_timedelta(val, unit='D')).date()
        parsed = pd.to_datetime(str(val), errors='coerce')
        if pd.notna(parsed):
            return parsed.date()
        return None
    except Exception:
        return None


def normalize_hours(val):
    """Convert time strings or day-hour formats into float hours."""
    if val is None or str(val).strip().lower() in ["", "nan", "nat"]:
        return 0.0
    try:
        if isinstance(val, (int, float)):
            return float(val)
        s = str(val).strip().replace(".", ":")
        if "day" in s:
            parts = s.split()
            days = float(parts[0])
            h, m, sec = [float(x) for x in parts[-1].split(":")]
            return days * 24 + h + m / 60 + sec / 3600
        if ":" in s:
            parts = s.split(":")
            h, m = float(parts[0]), float(parts[1]) if len(parts) > 1 else 0
            sec = float(parts[2]) if len(parts) > 2 else 0
            return h + m / 60 + sec / 3600
        return float(s)
    except Exception:
        return 0.0


def sanitize_value(val):
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except Exception:
        pass
    if isinstance(val, (np.floating, float)) and (np.isnan(val) or np.isinf(val)):
        return None
    if str(val).strip().lower() in ["nan", "nat", "none", ""]:
        return None
    return val


def detect_header_row(df):
    """Detect first row that looks like a real header, skip meta rows like 'WEC Wise Report'."""
    for i, row in df.iterrows():
        row_values = [str(x).strip().lower() for x in row.values if pd.notna(x)]
        if not row_values:
            continue
        if any("wec wise report" in val for val in row_values):
            continue
        keywords = ["date", "wec", "generation"]
        if any(kw in val for val in row_values for kw in keywords):
            return i
    return 0


def read_excel_multi(file_path, ext):
    """Read multi-sheet Excel, CSV, or HTML-based XLS and skip meta header rows."""
    def find_data_start(df):
        """Return the index where data header starts (e.g. contains DATE/WEC)."""
        for i, row in df.iterrows():
            joined = " ".join(str(x).lower() for x in row if pd.notna(x))
            if "date" in joined and "wec" in joined:
                return i
        return 0

    if ext == ".csv":
        df_preview = pd.read_csv(file_path, header=None)
        start_row = find_data_start(df_preview)
        df = pd.read_csv(file_path, header=start_row)
        return {"main": df}

    # --- Detect HTML disguised as .xls ---
    with open(file_path, "rb") as f:
        start_bytes = f.read(100).lower()
        if b"<html" in start_bytes or b"<table" in start_bytes:
            df_all = pd.read_html(file_path)[0]
            start_row = find_data_start(df_all)
            df = df_all.iloc[start_row:].reset_index(drop=True)
            df.columns = [clean_col(c) for c in df.iloc[0]]
            df = df[1:]  # drop header row from data
            return {"main": df}

    # --- Regular Excel / XLSX ---
    if ext in [".xlsx", ".xlsm"]:
        sheets = pd.read_excel(file_path, sheet_name=None, engine="openpyxl", header=None)
    elif ext == ".xls":
        sheets = pd.read_excel(file_path, sheet_name=None, engine="xlrd", header=None)
    else:
        raise Exception("Unsupported format")

    cleaned_sheets = {}
    for sheet_name, df in sheets.items():
        start_row = find_data_start(df)
        df = pd.read_excel(
            file_path,
            sheet_name=sheet_name,
            engine="openpyxl" if ext != ".xls" else "xlrd",
            header=start_row,
        )
        cleaned_sheets[sheet_name] = df
    return cleaned_sheets

# ---------------- VIEW ---------------- #
# ---------------- VIEW ---------------- #

@login_required
def customer_upload(request):
    username = request.user.username.lower()
    providers = Provider.objects.all()
    energy_types = EnergyType.objects.all()

    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        db_tables = [row[0] for row in cursor.fetchall()]

    user_tables = []
    for table in db_tables:
        if table.startswith(username + "_"):
            parts = table.split("_")
            provider_slug = "_".join(parts[1:-1])
            energy_slug = parts[-1]
            label = f"{username} - {provider_slug.replace('_',' ').title()} - {energy_slug.title()}"
            user_tables.append({"name": table, "label": label})

    if request.method == "POST":
        table_name = request.POST.get("table_name", "").strip()
        provider_name = request.POST.get("provider_name", "").strip()
        energy_type_name = request.POST.get("energy_type", "").title()
        data_file = request.FILES.get("data_file")

        if not table_name or not data_file or not provider_name:
            messages.error(request, "❌ Table, file, and provider are required.")
            return redirect("customer_upload")

        fs = FileSystemStorage()
        filename = fs.save(data_file.name, data_file)
        file_path = fs.path(filename)

        # 🔥 NEW FLAG (Delete breakdown only once)
        breakdown_cleared = False

        try:
            ext = os.path.splitext(filename)[1].lower()
            sheets = read_excel_multi(file_path, ext)
            uploaded_sheets = []

            for sheet_name, df in sheets.items():
                if df.empty:
                    continue

                # Clean column names
                df.columns = [clean_col(c) for c in df.columns]

                # Replace NaN, empty
                df = df.replace({pd.NaT: None, "": None, "nan": None, "NaN": None})
                df = df.astype(object).where(pd.notnull(df), None)
                df = df.replace({np.nan: None, np.inf: None, -np.inf: None})

                # Normalize date/hour columns
                for col in df.columns:
                    if col in ["gen_date", "date", "generation_date"]:
                        df[col] = df[col].apply(normalize_date)
                    elif "hrs" in col or "hour" in col:
                        df[col] = df[col].apply(normalize_hours)

                # Determine target table
                if "breakdown" in sheet_name.lower():
                    target_table = f"{table_name}_breakdowndata"

                    # 🔥 AUTO-DELETE OLD BREAKDOWN DATA
                    if not breakdown_cleared and target_table in db_tables:
                        with connection.cursor() as cursor:
                            cursor.execute(f"DELETE FROM `{target_table}`")
                        breakdown_cleared = True

                else:
                    target_table = table_name

                if target_table not in db_tables:
                    continue

                # Match table columns
                with connection.cursor() as cursor:
                    cursor.execute(f"SHOW COLUMNS FROM `{target_table}`")
                    table_columns = [col[0].lower() for col in cursor.fetchall()]

                valid_columns = [col for col in df.columns if col in table_columns]
                df = df[valid_columns]

                # Add metadata
                if "uploaded_by" in table_columns:
                    df["uploaded_by"] = username
                if "provider" in table_columns:
                    df["provider"] = provider_name
                if "energy_type" in table_columns:
                    df["energy_type"] = energy_type_name

                # Insert rows safely
                columns = ", ".join(f"`{col}`" for col in df.columns)
                placeholders = ", ".join(["%s"] * len(df.columns))
                insert_sql = f"INSERT INTO `{target_table}` ({columns}) VALUES ({placeholders})"
                values = [tuple(sanitize_value(v) for v in row) for row in df.values]

                with connection.cursor() as cursor:
                    cursor.executemany(insert_sql, values)
                    rows_inserted = cursor.rowcount

                if rows_inserted > 0:
                    UploadMetadata.objects.update_or_create(
                        table_name=target_table,
                        defaults={"last_modified": now()},
                    )
                    uploaded_sheets.append(f"{sheet_name} → {rows_inserted} rows")

            if uploaded_sheets:
                messages.success(
                    request,
                    f"✅ Uploaded Successfully: {', '.join(uploaded_sheets)}"
                )
            else:
                messages.error(request, "❌ No sheets uploaded successfully.")

        except Exception as e:
            print("❌ Error:", traceback.format_exc())
            messages.error(request, f"❌ Upload failed: {e}")

        finally:
            fs.delete(filename)

        return redirect("customer_upload")

    return render(request, "customer_upload.html", {
        "user_tables": user_tables,
        "providers": providers,
        "energy_types": energy_types,
    })

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import connection
from datetime import datetime

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import connection
from datetime import datetime

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import connection
from datetime import datetime



@login_required
def wind_wtg_plf(request):
    username = request.user.username.lower()

    # --- Filters
    date_from = request.GET.get("date_from") or None
    date_to = request.GET.get("date_to") or None
    providers = request.GET.getlist("provider")
    customers = request.GET.getlist("customer")
    states = request.GET.getlist("state")
    sites = request.GET.getlist("site")
    wtgs = request.GET.getlist("wtg")

    plf_data = defaultdict(list)
    provider_plf_data = defaultdict(list)   # ✅ new dict for provider-wise data
    distincts = {
        "providers": set(),
        "customers": set(),
        "states": set(),
        "sites": set(),
        "wtgs": set(),
    }

    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES")
        db_tables = [row[0] for row in cursor.fetchall()]
    table_names = [t for t in db_tables if t.startswith(username + "_") and t.endswith("_wind")]

    for table in table_names:
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table}`;")
            cols = [c[0] for c in cursor.fetchall()]
        col_map = {c.lower(): c for c in cols}

        # --- Flexible col picking
        def _pick(cmap, *candidates):
            for cand in candidates:
                if cand.lower() in cmap:
                    return cmap[cand.lower()]
            return None

        wtg_col      = _pick(col_map, "wec", "loc_no", "wtg", "wtg_no", "turbine", "turbineno", "locno")
        plf_col      = _pick(col_map, "cf", "plf","PLF_DAY","%plf_day", "plantloadfactor", "capacityfactor")
        date_col     = _pick(col_map, "date", "gen_date", "reading_date", "day_date")
        customer_col = _pick(col_map, "customername", "customer", "consumer", "client")
        state_col    = _pick(col_map, "state", "statename", "st")
        site_col     = _pick(col_map, "site", "sitename", "location", "plant", "windfarmname", "park", "sitecode", "city", "town", "village")
        provider_col = _pick(col_map, "provider", "oem", "oemprovider", "oem_name")

        if not (wtg_col and plf_col):
            continue

        # --- WHERE filters
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

        # --- Query PLF WTG-wise
        query_wtg = f"""
            SELECT `{wtg_col}`, AVG(`{plf_col}`) as avg_plf
            FROM `{table}`
            {where_clause}
            GROUP BY `{wtg_col}`
        """
        with connection.cursor() as cursor:
            cursor.execute(query_wtg, params)
            rows = cursor.fetchall()
        for wtg, avg_plf in rows:
            if wtg and avg_plf is not None:
                plf_data[str(wtg)].append(float(avg_plf))

        # --- Query PLF Provider-wise
        if provider_col:
            query_provider = f"""
                SELECT `{provider_col}`, AVG(`{plf_col}`) as avg_plf
                FROM `{table}`
                {where_clause}
                GROUP BY `{provider_col}`
            """
            with connection.cursor() as cursor:
                cursor.execute(query_provider, params)
                prov_rows = cursor.fetchall()
            for prov, avg_plf in prov_rows:
                if prov and avg_plf is not None:
                    provider_plf_data[str(prov)].append(float(avg_plf))

        # --- Collect distincts
        def distinct_list(col):
            if not col:
                return []
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT DISTINCT `{col}` FROM `{table}` ORDER BY `{col}`;")
                return [str(r[0]) for r in cursor.fetchall() if r[0]]

        distincts["providers"].update(distinct_list(provider_col))
        distincts["customers"].update(distinct_list(customer_col))
        distincts["states"].update(distinct_list(state_col))
        distincts["sites"].update(distinct_list(site_col))
        distincts["wtgs"].update(distinct_list(wtg_col))

    # --- Final aggregated PLF per WTG
    plf_final = {wtg: sum(vals) / len(vals) for wtg, vals in plf_data.items()}
    plf_chart_data = [{"x": k, "y": round(v, 2)} for k, v in plf_final.items()]
    plf_chart_data.sort(key=lambda x: x["y"], reverse=True)

    # --- Final aggregated PLF per Provider
    provider_final = {prov: sum(vals) / len(vals) for prov, vals in provider_plf_data.items()}
    provider_chart_data = [{"x": k, "y": round(v, 2)} for k, v in provider_final.items()]
    provider_chart_data.sort(key=lambda x: x["y"], reverse=True)

    context = {
        "plf_wtg_data": json.dumps(plf_chart_data),
        "plf_provider_data": json.dumps(provider_chart_data),  # ✅ new dataset
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
    return render(request, "wind_wtg_plf.html", context)

from collections import defaultdict
from datetime import datetime, date, timedelta
from django.db import connection
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render
import json
import re

def _pick(col_map, *candidates):
    """Return the actual column name if it matches any of the candidates"""
    for c in candidates:
        if not c:
            continue
        lc = c.lower()
        if lc in col_map:
            return col_map[lc]
    return None

def parse_date_like(v):
    """Parse various date formats to datetime.date (returns ISO string for SQL)."""
    if v is None:
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, datetime):
        return v.date().isoformat()
    s = str(v).strip()
    if not s:
        return None
    fmts = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d-%b-%Y", "%d %b %Y")
    for fmt in fmts:
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except Exception:
            continue
    # As fallback, try ISO-like or dateutil style by slicing
    try:
        return datetime.fromisoformat(s).date().isoformat()
    except Exception:
        return None

def parse_numeric(v):
    """Safe numeric parsing. Handles numbers, strings like '24' or '24.0', and '1 day 00:00:00' (returns hours)."""
    if v is None:
        return None
    # If already numeric
    try:
        return float(v)
    except Exception:
        pass
    s = str(v).strip()
    if s == "":
        return None
    # handle "1 day 00:00:00" or "0 days 12:00:00"
    m = re.match(r'(?:(\d+)\s*day[s]?\s*)?(\d{1,2}):(\d{2})(?::(\d{2}))?', s)
    if m:
        days = int(m.group(1)) if m.group(1) else 0
        hrs = int(m.group(2))
        mins = int(m.group(3))
        secs = int(m.group(4)) if m.group(4) else 0
        total_hours = days * 24 + hrs + (mins / 60.0) + (secs / 3600.0)
        return float(total_hours)
    # handle values like "24 Hrs", "24.0"
    m2 = re.search(r'[-+]?\d*\.?\d+', s)
    if m2:
        try:
            return float(m2.group(0))
        except:
            return None
    return None

@login_required
def wind_Grid_Availability(request):
    user = request.user.username.lower()

    # --- Get all wind tables for user
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        db_tables = [row[0] for row in cursor.fetchall()]
    table_names = [t for t in db_tables if t.startswith(user + "_") and t.endswith("_wind")]

    if not table_names:
        return render(request, "wind_Grid_Availability.html", {
            "ext_data": [], "int_data": [],
            "ext_json": "[]", "int_json": "[]",
            "overall_ext": 0, "overall_int": 0,
            "providers": [], "customers": [], "states": [], "sites": [], "wtgs": [],
            "selected_providers": [], "selected_customers": [], "selected_states": [], "selected_sites": [], "selected_wtgs": [],
            "date_from": None, "date_to": None,
            "no_data": True,
            "no_data_msg": "No wind tables found for your account.",
            "paginator": None,
            "table_page": None
        })

    # --- Get filters from GET
    raw_date_from = request.GET.get("date_from") or None
    raw_date_to = request.GET.get("date_to") or None
    date_from = parse_date_like(raw_date_from)
    date_to = parse_date_like(raw_date_to)
    providers = request.GET.getlist("provider")
    customers = request.GET.getlist("customer")
    states = request.GET.getlist("state")
    sites = request.GET.getlist("site")
    wtgs = request.GET.getlist("wtg")

    # --- Containers
    ext_avl = defaultdict(list)   # wtg -> list of ext values
    int_avl = defaultdict(list)   # wtg -> list of int values
    # Also collect when we must compute ext/int from GF/FM/S/U + Opr Hrs
    distincts = {"providers": set(), "customers": set(), "states": set(), "sites": set(), "wtgs": set()}

    for table_name in table_names:
        # get columns
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table_name}`;")
            cols = [r[0] for r in cursor.fetchall()]
        col_map = {c.lower(): c for c in cols}

        # --- Identify columns (extended list to match messy names)
        date_col = _pick(col_map, "date", "gen_date", "reading_date", "day_date", "gen. date", "generation date", "gen date")
        wtg_col = _pick(col_map, "wec", "wtg", "loc_no", "loc. no.", "loc no", "turbine", "locno", "loc")
        # direct GA/GIA variants
        ext_col = _pick(col_map, "ga", "externalgridavailability", "ega", "ext_grid", "external grid", "external grid availability", "ga (%)", "ga%")
        int_col = _pick(col_map, "gia", "internalgridavailability", "iga", "int_grid", "internal grid", "internal grid availability", "gia (%)", "gia%")
        # GF / FM / S / U / NOR
        gf_col = _pick(col_map, "gf", "gridfailure", "grid_failure", "grid_failure_hrs")
        fm_col = _pick(col_map, "fm", "forcemajeure", "force_majeure")
        s_col = _pick(col_map, "s", "shutdown", "shut_down")
        u_col = _pick(col_map, "u", "unknown", "unclassified")
        nor_col = _pick(col_map, "nor", "normal")
        # hours fields
        gen_hrs_col = _pick(col_map, "gen hrs", "gen. hrs.", "gen_hrs", "generation hours", "gen hrs.")
        opr_hrs_col = _pick(col_map, "opr hrs", "opr. hrs.", "opr_hrs", "ohrs", "operatinghours", "o_hours", "opr_hrs", "ophrs", "operation hrs")
        # optional: machine availability
        ma_col = _pick(col_map, "ma", "machineavailability", "m/c avail.%", "m/c avail", "mc_avail", "m_c_avail")
        # provider/customer/state/site variants
        provider_col = _pick(col_map, "provider", "oem", "company", "vendor")
        customer_col = _pick(col_map, "customer", "consumer", "client", "customer name", "client name")
        state_col = _pick(col_map, "state", "statename", "state name", "STATE")
        site_col = _pick(col_map, "site", "sitename", "plant", "location", "site name")

        # if missing essential columns skip this table
        if not date_col or not wtg_col:
            # skip table if no date or wtg column
            continue

        # --- Build WHERE conditions and params
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

        # Build SELECT - request all columns we might need (use COALESCE only when averaging in SQL; here we fetch raw rows)
        select_cols = [f"`{wtg_col}`"]
        # include direct availability columns if present
        for c in (ext_col, int_col, gf_col, fm_col, s_col, u_col, nor_col, gen_hrs_col, opr_hrs_col, ma_col):
            if c:
                select_cols.append(f"`{c}`")
        select_clause = ", ".join(select_cols)

        query = f"SELECT {select_clause} FROM `{table_name}` {where_clause}"
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        # column order mapping for this table's SELECT
        # the first selected col is wtg_col, then the ones appended in the same order
        selected_cols = [wtg_col] + [c for c in (ext_col, int_col, gf_col, fm_col, s_col, u_col, nor_col, gen_hrs_col, opr_hrs_col, ma_col) if c]

        for row in rows:
            # row is a tuple aligned to selected_cols
            row_dict = {selected_cols[i]: row[i] for i in range(len(selected_cols))}
            wtg_val = row_dict.get(wtg_col)
            if not wtg_val:
                continue
            wtg_key = str(wtg_val)

            # First try to use direct ext/int if present
            ext_val = None
            int_val = None

            if ext_col and row_dict.get(ext_col) is not None:
                ext_val = parse_numeric(row_dict.get(ext_col))
            if int_col and row_dict.get(int_col) is not None:
                int_val = parse_numeric(row_dict.get(int_col))

            # If direct ext/int not available, try to compute using GF/FM/S/U and Opr Hrs.
            if (ext_val is None or int_val is None):
                # parse GF, FM, S, U, Opr Hrs
                gf = parse_numeric(row_dict.get(gf_col)) if gf_col else None
                fm = parse_numeric(row_dict.get(fm_col)) if fm_col else None
                s_hrs = parse_numeric(row_dict.get(s_col)) if s_col else None
                u_hrs = parse_numeric(row_dict.get(u_col)) if u_col else None
                opr = parse_numeric(row_dict.get(opr_hrs_col)) if opr_hrs_col else None
                # If Opr Hrs is missing but Gen Hrs present, try to use Gen Hrs as fallback (not ideal but better than nothing)
                if opr is None and gen_hrs_col:
                    opr = parse_numeric(row_dict.get(gen_hrs_col))
                # Now compute if opr exists and gf/fm/s/u are numbers
                # compute GIF % = (GF / OPR) *100  => ext availability = 100 - GIF%
                if ext_val is None and gf is not None and opr and opr > 0:
                    try:
                        ext_val = 100.0 - ((gf / opr) * 100.0)
                    except Exception:
                        ext_val = None
                # compute GIA using fm+s+u
                if int_val is None:
                    sum_int_loss = 0.0
                    got_any = False
                    for x in (fm, s_hrs, u_hrs):
                        if x is not None:
                            sum_int_loss += float(x)
                            got_any = True
                    if got_any and opr and opr > 0:
                        try:
                            int_val = 100.0 - ((sum_int_loss / opr) * 100.0)
                        except Exception:
                            int_val = None

            # If both still None and MA present, and MA is percent of machine availability, we can use it as a proxy
            if ext_val is None and ma_col and row_dict.get(ma_col) is not None:
                # Use machine availability as surrogate for internal availability
                ma_v = parse_numeric(row_dict.get(ma_col))
                if ma_v is not None:
                    # assume external ~ ma (best-effort)
                    ext_val = ma_v
            if int_val is None and ma_col and row_dict.get(ma_col) is not None:
                ma_v = parse_numeric(row_dict.get(ma_col))
                if ma_v is not None:
                    int_val = ma_v

            # Final fallback: if still None set to 0 to avoid breaking averages (you can change this)
            if ext_val is None:
                ext_val = 0.0
            if int_val is None:
                int_val = 0.0

            # Append to lists for averaging
            try:
                ext_avl[wtg_key].append(float(ext_val))
            except Exception:
                pass
            try:
                int_avl[wtg_key].append(float(int_val))
            except Exception:
                pass

        # --- Gather distincts for filters (safe even if some cols are None)
        def distinct_list(col):
            if not col:
                return []
            with connection.cursor() as cursor:
                try:
                    cursor.execute(f"SELECT DISTINCT `{col}` FROM `{table_name}` ORDER BY `{col}`;")
                    return [str(r[0]) for r in cursor.fetchall() if r[0] not in (None, "")]
                except Exception:
                    return []
        distincts["providers"].update(distinct_list(provider_col))
        distincts["customers"].update(distinct_list(customer_col))
        distincts["states"].update(distinct_list(state_col))
        distincts["sites"].update(distinct_list(site_col))
        distincts["wtgs"].update(distinct_list(wtg_col))

    # --- Prepare data (average per WTG)
    ext_data = [{"wtg": wtg, "value": round(sum(vals) / len(vals), 2) if vals else 0.0} for wtg, vals in ext_avl.items()]
    int_data = [{"wtg": wtg, "value": round(sum(vals) / len(vals), 2) if vals else 0.0} for wtg, vals in int_avl.items()]

    # --- Overall averages
    all_ext_vals = [v for vals in ext_avl.values() for v in vals]
    all_int_vals = [v for vals in int_avl.values() for v in vals]
    overall_ext = round(sum(all_ext_vals) / len(all_ext_vals), 2) if all_ext_vals else 0.0
    overall_int = round(sum(all_int_vals) / len(all_int_vals), 2) if all_int_vals else 0.0

    # --- Sort results by WTG key (natural)
    ext_data = sorted(ext_data, key=lambda x: x["wtg"])
    int_data = sorted(int_data, key=lambda x: x["wtg"])

    # --- Paginate ext_data for table (example paginating ext_data combined list)
    combined_table = []
    # Make a combined row per WTG to show both ext and int in table if desired
    all_wtgs = sorted(set([r["wtg"] for r in ext_data] + [r["wtg"] for r in int_data]))
    for wtg in all_wtgs:
        ext_val = next((r["value"] for r in ext_data if r["wtg"] == wtg), 0.0)
        int_val = next((r["value"] for r in int_data if r["wtg"] == wtg), 0.0)
        combined_table.append({"wtg": wtg, "ext": ext_val, "int": int_val})

    page = request.GET.get('page', 1)
    paginator = Paginator(combined_table, 10)  # change page size as needed
    try:
        table_page = paginator.page(page)
    except PageNotAnInteger:
        table_page = paginator.page(1)
    except EmptyPage:
        table_page = paginator.page(paginator.num_pages)

    context = {
        "ext_data": ext_data,
        "int_data": int_data,
        "ext_json": json.dumps(ext_data, default=str),
        "int_json": json.dumps(int_data, default=str),
        "overall_ext": overall_ext,
        "overall_int": overall_int,
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
        "date_from": raw_date_from,
        "date_to": raw_date_to,
        "no_data": len(ext_data) == 0 and len(int_data) == 0,
        "no_data_msg": "No Grid Availability data found for the selected filters." if (len(ext_data) == 0 and len(int_data) == 0) else "",
        "paginator": paginator,
        "table_page": table_page
    }

    return render(request, "wind_Grid_Availability.html", context)


from collections import defaultdict
from datetime import datetime
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
import json, re

# ---------- Improved Column Picker ----------
def _normalize(name):
    """Simplify column name for matching"""
    return re.sub(r'[^a-z0-9]', '', name.lower())

def _pick(col_map, *candidates):
    """
    Return the actual-cased column name if it matches any of the candidates.
    Handles dots, spaces, underscores, and case insensitivity.
    """
    normalized_map = {_normalize(k): v for k, v in col_map.items()}
    for c in candidates:
        norm_c = _normalize(c)
        if norm_c in normalized_map:
            return normalized_map[norm_c]
    return None


# ---------- Main View ----------
@login_required
def wind_breakdown_hours(request):
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
            "total_breakdown": 0,
            "providers": [], "customers": [], "states": [], "sites": [], "wtgs": [],
            "selected_providers": [], "selected_customers": [], "selected_states": [],
            "selected_sites": [], "selected_wtgs": [],
            "date_from": None, "date_to": None,
            "no_data": True,
            "no_data_msg": "No wind tables found for your account."
        }
        return render(request, "wind_breakdown_hours.html", context)

    # --- Get filters
    date_from = request.GET.get("date_from") or None
    date_to = request.GET.get("date_to") or None
    providers = request.GET.getlist("provider")
    customers = request.GET.getlist("customer")
    states = request.GET.getlist("state")
    sites = request.GET.getlist("site")
    wtgs = request.GET.getlist("wtg")

    breakdown_hours = defaultdict(float)
    total_breakdown = 0.0
    distincts = {"providers": set(), "customers": set(), "states": set(), "sites": set(), "wtgs": set()}

    for table_name in table_names:
        # --- Read schema
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table_name}`;")
            cols = [r[0] for r in cursor.fetchall()]
        col_map = {c.lower(): c for c in cols}

        # --- Identify columns (robust matching)
        wtg_col = _pick(col_map, "wec", "loc_no", "locno", "wtg", "wtg_no", "turbine", "turbineno")
        date_col = _pick(col_map, "date", "gen_date", "reading_date", "day_date")
        genhrs_col = _pick(col_map, "genhrs", "generationhours", "gen_hours", "gen_hrs", "genhrs.", "genhrs")
        ohrs_col = _pick(col_map, "ohrs", "operatinghours", "o_hours", "o_hrs", "oprhrs", "opr_hrs")
        loss_col = _pick(col_map, "lhrs", "l.hrs", "losshrs", "loss_hours", "l_hrs")
        provider_col = _pick(col_map, "provider", "oem", "oemprovider", "oem_name")
        customer_col = _pick(col_map, "customername", "customer", "consumer", "client")
        state_col = _pick(col_map, "state", "statename", "st")
        site_col = _pick(col_map, "site", "sitename", "location", "plant", "windfarmname", "park", "sitecode", "city", "town", "village")

        if not wtg_col:
            continue

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

        # --- Breakdown Expression
        if loss_col:  
            breakdown_expr = f"`{loss_col}`"
        elif genhrs_col and ohrs_col:  
            breakdown_expr = f"(`{ohrs_col}` - `{genhrs_col}`)"
        else:
            continue  # skip if no suitable breakdown formula

        # --- Query WTG-wise breakdown hours
        query = f"""
            SELECT `{wtg_col}`, SUM({breakdown_expr}) AS breakdown
            FROM `{table_name}`
            {where_clause}
            GROUP BY `{wtg_col}`
        """
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        for wtg, hrs in rows:
            if not wtg:
                continue
            breakdown_hours[str(wtg)] += float(hrs or 0)
            total_breakdown += float(hrs or 0)

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

    # --- Prepare chart & table data
    chart_data = [{"wtg": k, "breakdown": round(v, 2)} for k, v in breakdown_hours.items()]
    chart_data.sort(key=lambda x: x["breakdown"], reverse=True)
    table_data = [{"wtg_no": k, "breakdown": round(v, 2)} for k, v in breakdown_hours.items()]

    context = {
        "chart_data": json.dumps(chart_data),
        "table_data": table_data,
        "total_breakdown": round(total_breakdown, 2),
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
        "no_data_msg": "No breakdown data found for the selected filters." if not chart_data else ""
    }

    return render(request, "wind_breakdown_hours.html", context)






























# views.py
import json
import re
from collections import defaultdict
from datetime import datetime, date
from django.db import connection
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

# -------------------------
# Helpers
# -------------------------
def _normalize_key(s: str):
    return re.sub(r'[\s\._\-()%]', '', (s or "").lower())

def _pick(col_map, *candidates):
    """
    Pick actual column name from col_map by comparing normalized forms.
    col_map: dict mapping original_column_name -> original_column_name
    candidates: possible names to match
    Returns actual original column name or None
    """
    # Create normalized map: norm -> original
    norm_map = { _normalize_key(k): k for k in col_map.keys() }
    for c in candidates:
        if not c:
            continue
        norm = _normalize_key(c)
        if norm in norm_map:
            return norm_map[norm]
    # fallback: try partial match (candidate contained in column)
    for c in candidates:
        if not c:
            continue
        norm = _normalize_key(c)
        for k in col_map.keys():
            if norm in _normalize_key(k):
                return k
    return None

def parse_date_like(value):
    """Return date object or None. Accepts many formats."""
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    s = str(value).strip()
    if not s:
        return None
    fmts = ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d-%b-%Y", "%d %b %Y"]
    for f in fmts:
        try:
            return datetime.strptime(s, f).date()
        except Exception:
            continue
    # try ISO parse
    try:
        return datetime.fromisoformat(s).date()
    except Exception:
        return None

def parse_time_to_hours(v):
    """
    Convert a value representing hours/time to float hours.
    Handles:
     - numeric strings / ints / floats -> returned as float
     - "1 day 02:30:00" -> days*24 + hours + minutes/60 + seconds/3600
     - "02:30" or "2:30" -> hours + minutes/60
     - "hh:mm:ss"
     - "24" -> 24.0
    Returns None if cannot parse.
    """
    if v is None:
        return None
    # if already numeric
    try:
        return float(v)
    except Exception:
        pass
    s = str(v).strip()
    if not s:
        return None

    # pattern: "X day(s) HH:MM:SS" or "X day HH:MM"
    m = re.match(r'(?:(\d+)\s*day[s]?\s*)?(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?$', s, re.IGNORECASE)
    if m:
        days = int(m.group(1)) if m.group(1) else 0
        hrs = int(m.group(2))
        mins = int(m.group(3))
        secs = int(m.group(4)) if m.group(4) else 0
        return days * 24.0 + hrs + mins / 60.0 + secs / 3600.0

    # pattern like "1 day" or "2 days"
    m2 = re.match(r'^(\d+)\s*day[s]?$', s, re.IGNORECASE)
    if m2:
        return float(int(m2.group(1)) * 24)

    # pattern like "HH:MM:SS"
    m3 = re.match(r'^(\d{1,2}):(\d{1,2}):(\d{1,2})$', s)
    if m3:
        hrs = int(m3.group(1))
        mins = int(m3.group(2))
        secs = int(m3.group(3))
        return hrs + mins / 60.0 + secs / 3600.0

    # pattern like "HH:MM"
    m4 = re.match(r'^(\d{1,2}):(\d{1,2})$', s)
    if m4:
        hrs = int(m4.group(1))
        mins = int(m4.group(2))
        return hrs + mins / 60.0

    # fallback: extract first numeric token
    m5 = re.search(r'[-+]?\d*\.?\d+', s)
    if m5:
        try:
            return float(m5.group(0))
        except:
            return None

    return None

# -------------------------
# Main view
# -------------------------
@login_required
def wind_breakdown_log(request):
    """
    Aggregates breakdown records from all user_*_wind tables.
    Supports different column names and computes breakdown hours when L.Hrs missing:
        Breakdown Hrs = Opr Hrs - Gen Hrs
    """
    user = request.user.username.lower()

    # list tables
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        all_tables = [r[0] for r in cursor.fetchall()]

    table_names = [t for t in all_tables if t.startswith(user + "_") and t.endswith("_wind")]

    if not table_names:
        return render(request, "wind_breakdown_log.html", {
            "data": [], "breakdown_data": "[]",
            "providers": [], "customers": [], "states": [], "sites": [], "wtgs": [],
            "no_data": True, "no_data_msg": "No wind tables found for your account.", "total_hours": 0
        })

    # --- Filters from request
    raw_date_from = request.GET.get("date_from") or None
    raw_date_to = request.GET.get("date_to") or None
    date_from = parse_date_like(raw_date_from)
    date_to = parse_date_like(raw_date_to)

    selected_providers = request.GET.getlist("provider")
    selected_customers = request.GET.getlist("customer")
    selected_states = request.GET.getlist("state")
    selected_sites = request.GET.getlist("site")
    selected_wtgs = request.GET.getlist("wtg")

    breakdown_records = []
    providers_set, customers_set, states_set, sites_set, wtgs_set = set(), set(), set(), set(), set()
    total_hours = 0.0

    # Candidate name lists (extend as needed)
    date_candidates = ["date", "gen date", "gen_date", "generation date", "gen. date", "gen. (date)"]
    site_candidates = ["site", "sitename", "plant", "location", "park"]
    wec_candidates = ["wec", "wtg", "loc no", "loc.no", "loc_no", "wecno", "wtgno", "locno", "loc"]
    lhrs_candidates = ["l.hrs", "lhrs", "l_hrs", "loss hours", "loss_hrs", "breakdown hrs", "breakdown_hrs", "bd hrs", "bdhrs", "bd.hrs"]
    gen_hrs_candidates = ["gen hrs", "gen. hrs.", "generation hours", "gen_hours", "gen_hrs", "gen. (kwh) day", "gen (kwh) day"]
    opr_hrs_candidates = ["opr hrs", "opr. hrs.", "ohrs", "operatinghours", "o_hours", "ophrs", "operation hrs", "oper hrs"]
    remarks_candidates = ["remarks", "comment", "reason", "note", "remarks/remarks"]
    provider_candidates = ["provider", "oem", "company", "vendor"]
    customer_candidates = ["customer", "customer name", "client", "consumer", "client name", "customer_name"]
    state_candidates = ["state", "statename", "state name", "STATE"]

    # iterate tables and collect rows
    for table in table_names:
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table}`;")
            cols = [r[0] for r in cursor.fetchall()]
        col_map = {c: c for c in cols}

        # pick actual columns
        date_col = _pick(col_map, *date_candidates)
        if not date_col:
            # can't use table without a date column
            continue

        wec_col = _pick(col_map, *wec_candidates)
        site_col = _pick(col_map, *site_candidates)
        lhrs_col = _pick(col_map, *lhrs_candidates)
        gen_hrs_col = _pick(col_map, *gen_hrs_candidates)
        opr_hrs_col = _pick(col_map, *opr_hrs_candidates)
        remarks_col = _pick(col_map, *remarks_candidates)

        provider_col = _pick(col_map, *provider_candidates)
        customer_col = _pick(col_map, *customer_candidates)
        state_col = _pick(col_map, *state_candidates)

        # build where clause
        conditions, params = [], []
        if date_from:
            # use raw dates as strings; MySQL will parse 'YYYY-MM-DD'
            conditions.append(f"`{date_col}` >= %s"); params.append(date_from.isoformat())
        if date_to:
            conditions.append(f"`{date_col}` <= %s"); params.append(date_to.isoformat())
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

        # prepare columns to select (only those identified)
        select_cols = [c for c in [date_col, site_col, wec_col, lhrs_col, gen_hrs_col, opr_hrs_col,
                                   remarks_col, provider_col, customer_col, state_col] if c]

        if not select_cols:
            continue

        select_clause = ", ".join(f"`{c}`" for c in select_cols)
        query = f"SELECT {select_clause} FROM `{table}` {where_clause}"

        with connection.cursor() as cursor:
            try:
                cursor.execute(query, params)
                rows = cursor.fetchall()
            except Exception:
                rows = []

        # index mapping
        idx = {col: i for i, col in enumerate(select_cols)}

        for row in rows:
            # parse date
            raw_date = row[idx[date_col]]
            d = parse_date_like(raw_date)
            if not d:
                # skip rows without valid date
                continue

            # read values carefully and parse hours
            # L.Hrs direct
            lhrs_val = None
            if lhrs_col and row[idx.get(lhrs_col)] not in (None, ""):
                lhrs_val = parse_time_to_hours(row[idx.get(lhrs_col)])
            # Gen Hrs
            gen_hrs_val = None
            if gen_hrs_col and row[idx.get(gen_hrs_col)] not in (None, ""):
                gen_hrs_val = parse_time_to_hours(row[idx.get(gen_hrs_col)])
            # Opr Hrs
            opr_hrs_val = None
            if opr_hrs_col and row[idx.get(opr_hrs_col)] not in (None, ""):
                opr_hrs_val = parse_time_to_hours(row[idx.get(opr_hrs_col)])

            # If L.Hrs missing but we have Opr & Gen -> compute
            if (lhrs_val is None) and (opr_hrs_val is not None) and (gen_hrs_val is not None):
                # breakdown = opr - gen (ensure non-negative)
                try:
                    calc = float(opr_hrs_val) - float(gen_hrs_val)
                    lhrs_val = calc if calc >= 0 else 0.0
                except Exception:
                    lhrs_val = 0.0

            # Final fallback if still None -> set 0.0
            if lhrs_val is None:
                lhrs_val = 0.0

            # remarks
            remark_val = ""
            if remarks_col and row[idx.get(remarks_col)] not in (None, ""):
                remark_val = str(row[idx.get(remarks_col)]).strip()

            # prepare record
            state_val = row[idx.get(state_col)] if state_col else None
            site_val = row[idx.get(site_col)] if site_col else None
            wtg_val = row[idx.get(wec_col)] if wec_col else None
            prov_val = row[idx.get(provider_col)] if provider_col else None
            cust_val = row[idx.get(customer_col)] if customer_col else None

            rec = {
                "date": d.strftime("%d-%m-%Y"),
                "state": state_val or "",
                "site": site_val or "",
                "wtg": wtg_val or "",
                "provider": prov_val or "",
                "customer": cust_val or "",
                "remark": remark_val or "-",
                "breakdown_hours": round(float(lhrs_val), 3) if isinstance(lhrs_val, (int, float)) else lhrs_val
            }

            breakdown_records.append(rec)

            # collect sets
            if prov_val: providers_set.add(str(prov_val))
            if cust_val: customers_set.add(str(cust_val))
            if state_val: states_set.add(str(state_val))
            if site_val: sites_set.add(str(site_val))
            if wtg_val: wtgs_set.add(str(wtg_val))

            # accumulate total hours
            try:
                total_hours += float(lhrs_val)
            except Exception:
                pass

    # sort by date (string dd-mm-yyyy sorts lexicographically wrong sometimes, so convert)
    def _sort_key(x):
        try:
            return datetime.strptime(x["date"], "%d-%m-%Y")
        except Exception:
            return datetime.min
    breakdown_records = sorted(breakdown_records, key=_sort_key, reverse=False)

    # pagination (optional)
    page = request.GET.get("page", 1)
    paginator = Paginator(breakdown_records, 25)
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    context = {
        "data": page_obj.object_list,
        "breakdown_data": json.dumps(page_obj.object_list, default=str),
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
        "date_from": raw_date_from,
        "date_to": raw_date_to,
        "no_data": False if breakdown_records else True,
        "no_data_msg": "No data found for given filters." if not breakdown_records else "",
        "total_hours": round(total_hours, 3),
        "paginator": paginator,
        "page_obj": page_obj
    }

    return render(request, "wind_breakdown_log.html", context)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from .models import ChargeMaster
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import math

def get_default_charges(energy_type=None, state=None, year=None):
    """
    Fetch charges filtered by energy type, state, and year if provided.
    """
    qs = ChargeMaster.objects.all()

    if energy_type:
        qs = qs.filter(energy_type__iexact=str(energy_type).strip())
    if state:
        qs = qs.filter(state__iexact=str(state).strip())
    if year:
        qs = qs.filter(year=str(year).strip())

    return qs

def _safe_float(v, d=0.0):
    try:
        return float(v) if v not in (None, "", []) else float(d)
    except (ValueError, TypeError):
        return float(d)

# ---------- Core Calculation ----------
def compute_open_access_result(post, defaults):
    """
    Inputs are read from `post` (QueryDict). Defaults come from ChargeMaster.
    Enhanced features:
    - If units_at_generator not provided, compute from approved_capacity_mw + cuf + months
    - Zone-wise inputs accepted but treated as additive to total_units
    - Offer breakdown of each charge component
    """
    warnings = []

    # --- Basic consumer inputs ---
    total_units = _safe_float(post.get("total_units"), 0)  # consumer-side units (kWh)
    # zone wise (optional): A,B,C,D
    zone_a = _safe_float(post.get("zone_a"), 0)
    zone_b = _safe_float(post.get("zone_b"), 0)
    zone_c = _safe_float(post.get("zone_c"), 0)
    zone_d = _safe_float(post.get("zone_d"), 0)
    # if zone inputs provided, use their sum as total if total_units is zero
    zone_sum = zone_a + zone_b + zone_c + zone_d
    if not total_units and zone_sum:
        total_units = zone_sum

    fac = _safe_float(post.get("fac", defaults.get("fac", 0)), 0)
    wheeling = _safe_float(post.get("wheeling", defaults.get("wheeling_charges", 0)), 0)
    duty_tcs = _safe_float(post.get("duty_tcs"), defaults.get("duty_tcs", 0))
    benefit = _safe_float(post.get("benefit"), 0) / 100.0
    demand_charge_rate = _safe_float(post.get("demand_charges"), 0)
    demand_charge_type = post.get("demand_charge_type", "total")
    billed_demand = _safe_float(post.get("billed_demand"), 0)
    contract_demand = _safe_float(post.get("contract_demand"), 0)

    # --- Demand charge calculation ---
    if demand_charge_type == "per_kva":
        kva_basis = billed_demand or contract_demand
        demand_charge_total = demand_charge_rate * (kva_basis or 0)
    else:
        demand_charge_total = demand_charge_rate

    # --- MSEDCL energy cost (consumer side) ---
    # energy charge includes FAC + wheeling (per unit) applied on total units
    msedcl_energy = total_units * (fac + wheeling) * (1 - benefit)
    msedcl_total = demand_charge_total + msedcl_energy + duty_tcs
    msedcl_rate = (msedcl_total / total_units) if total_units else 0

    # ---------- OA parameters ----------
    # generator units: either provided or computed from capacity & CUF
    units_at_generator = _safe_float(post.get("units_at_generator"), 0)
    approved_capacity_mw = _safe_float(post.get("approved_capacity_mw"), 0)
    cuf = _safe_float(post.get("cuf"), 0)  # CUF in percent
    months = int(_safe_float(post.get("months"), 1))

    if not units_at_generator:
        # approximate hours in month as 24 * 30 = 720 per month
        hours = 24 * 30 * months
        # capacity in MW -> convert to kW for kWh calc: MW * 1000 * hours * (cuf/100)
        units_at_generator = approved_capacity_mw * 1000 * hours * (cuf / 100.0)

    # losses and rate components (use defaults if present)
    stu_loss = _safe_float(post.get("stu_loss", defaults.get("stu_loss", 0)), 0) / 100.0
    wheeling_loss = _safe_float(post.get("wheeling_loss", defaults.get("wheeling_loss", 0)), 0) / 100.0

    generator_cost = _safe_float(post.get("generator_cost"), 0)
    sldc = _safe_float(post.get("sldc", defaults.get("sldc_charges", 0)), 0)
    trans = _safe_float(post.get("trans_charge", defaults.get("transmission_charges", 0)), 0)
    css = _safe_float(post.get("css", defaults.get("css", 0)), 0)
    addl = _safe_float(post.get("addl_surcharge", defaults.get("additional_surcharge", 0)), 0)
    msedcl_op = _safe_float(post.get("msedcl_op", defaults.get("msedcl_operating", 0)), 0)
    tax = _safe_float(post.get("sale_tax", defaults.get("tax_on_sale", 0)), 0) / 100.0

    # --- Loss factor & conversion (generator end -> consumer end) ---
    loss_factor = (1 - stu_loss) * (1 - wheeling_loss)
    gen_to_cons = 1 / loss_factor if loss_factor > 0 else 1.0
    # units delivered to consumer (approx)
    delivered_units = units_at_generator * loss_factor

    # OA share percent (how many percent of consumer consumption is OA)
    oa_share_pct = _safe_float(post.get("oa_share_pct", 100), 100)
    oa_frac = max(0.0, min(1.0, oa_share_pct / 100.0))

    # --- OA per-unit rate computation ---
    # apply generator cost + per-unit charges scaled for losses where appropriate
    oa_rate_components = {
        "generator_cost_at_consumer": generator_cost * gen_to_cons,
        "sldc_at_consumer": sldc * gen_to_cons,
        "trans_at_consumer": trans * gen_to_cons,
        "css": css,
        "additional_surcharge": addl,
        "msedcl_operating": msedcl_op,
    }
    oa_rate_before_tax = sum(oa_rate_components.values())
    oa_total_before_tax = oa_rate_before_tax * (delivered_units or 0)
    oa_total = oa_total_before_tax * (1 + tax)
    oa_rate_final = (oa_total / delivered_units) if delivered_units else oa_rate_before_tax * (1 + tax)

    # --- Mixed scenario (blending OA units and MSEDCL units) ---
    msedcl_units = total_units * (1 - oa_frac)
    oa_units = total_units * oa_frac

    # If user provided OA units explicitly (override the above)
    # If oa_units zero but we have delivered_units, use delivered_units min(total_units)
    if oa_units == 0 and delivered_units > 0:
        # treat delivered units as OA up to total_units
        oa_units = min(delivered_units, total_units)
        msedcl_units = total_units - oa_units

    combined_total = (msedcl_units * msedcl_rate) + (oa_units * oa_rate_final)
    blended_rate = (combined_total / total_units) if total_units else 0
    savings_rs = msedcl_total - combined_total
    savings_percent = (savings_rs / msedcl_total * 100.0) if msedcl_total else 0

    # Build a clean result dict
    result = {
        "msedcl_total": round(msedcl_total, 2),
        "oa_total": round(oa_total, 2),
        "msedcl_rate": round(msedcl_rate, 4),
        "oa_rate": round(oa_rate_final, 4),
        "combined_total": round(combined_total, 2),
        "blended_rate": round(blended_rate, 4),
        "savings_rs": round(savings_rs, 2),
        "savings_percent": round(savings_percent, 2),
        "inputs_echo": {
            "oa_share_pct": oa_share_pct,
            "total_units": total_units,
            "units_at_generator": round(units_at_generator, 2),
            "delivered_units": round(delivered_units, 2),
            "approved_capacity_mw": approved_capacity_mw,
            "cuf": cuf,
            "months": months,
            "energy_type": post.get("energy_type")
        },
        "oa_rate_components": {k: round(v, 6) for k, v in oa_rate_components.items()},
        "warnings": warnings,
    }

    return result

# ---------- Views ----------
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render
from .models import OpenAccessCalculation

@login_required
def open_access_calculator(request):
    energy_type = request.POST.get("energy_type") if request.method == "POST" else request.GET.get("energy_type")
    state = request.POST.get("state") if request.method == "POST" else request.GET.get("state")
    year = request.POST.get("year") if request.method == "POST" else request.GET.get("year")

    # ✅ Fetch only default charges filtered by selected energy type, state, and year
    qs = get_default_charges(energy_type=energy_type, state=state, year=year)
    defaults = {c.name.lower().replace(" ", "_"): float(c.value or 0) for c in qs}

    result = None
    saved_list = request.session.get("oa_saved", [])

    if request.method == "POST":
        try:
            result = compute_open_access_result(request.POST, defaults)
            OpenAccessCalculation.objects.create(
                user=request.user,
                energy_type=request.POST.get("energy_type", ""),
                msedcl_total=result["msedcl_total"],
                oa_total=result["oa_total"],
                blended_rate=result["blended_rate"],
                savings=result["savings_rs"]
            )
            if request.POST.get("save_result", "") == "1":
                saved_entry = {
                    "timestamp": str(request.POST.get("save_label", "") or "saved"),
                    "energy_type": request.POST.get("energy_type", ""),
                    "inputs": result["inputs_echo"],
                    "result": {
                        "msedcl_total": result["msedcl_total"],
                        "oa_total": result["oa_total"],
                        "combined_total": result["combined_total"],
                        "savings_rs": result["savings_rs"],
                        "savings_percent": result["savings_percent"],
                    },
                }
                saved_list.append(saved_entry)
                request.session["oa_saved"] = saved_list
                messages.success(request, "Calculation saved to session (temporary).")
        except Exception as e:
            result = {"error": str(e)}

    context = {
        "defaults": defaults,
        "result": result,
        "saved_list": saved_list,
    }
    return render(request, "open_access_calculator.html", context)

def open_access_pdf(request):
    """
    Generate PDF report; accepts query params or reads from GET as before.
    """
    msedcl_total = request.GET.get("msedcl_total", "0")
    oa_total = request.GET.get("oa_total", "0")
    msedcl_rate = request.GET.get("msedcl_rate", "0")
    oa_rate = request.GET.get("oa_rate", "0")
    savings_rs = request.GET.get("savings_rs", "0")
    savings_percent = request.GET.get("savings_percent", "0")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "inline; filename=open_access_report.pdf"

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    y = height - 80

    p.setFont("Helvetica-Bold", 16)
    p.drawString(80, y, "Open Access Cost Comparison Report")
    y -= 30

    p.setFont("Helvetica", 12)
    p.drawString(50, y, f"MSEDCL Total: ₹{msedcl_total}")
    y -= 18
    p.drawString(50, y, f"OA Total: ₹{oa_total}")
    y -= 18
    p.drawString(50, y, f"Unit Rate (MSEDCL): ₹{msedcl_rate}")
    y -= 18
    p.drawString(50, y, f"Unit Rate (Open Access): ₹{oa_rate}")
    y -= 18
    p.drawString(50, y, f"Savings: ₹{savings_rs} ({savings_percent}%)")
    y -= 30

    p.setFont("Helvetica-Oblique", 10)
    p.drawString(50, y, "Generated from Redashboard | © TEIM")
    p.showPage()
    p.save()
    return response

# Charge master views (kept mostly the same)
def charge_master_list(request):
    charges = ChargeMaster.objects.all()
    return render(request, "charge_master_list.html", {"charges": charges})

def charge_master_add(request):
    if request.method == "POST":
        name = request.POST.get("name")
        value = request.POST.get("value")
        unit = request.POST.get("unit")
        year = request.POST.get("year")
        energy_type = request.POST.get("energy_type")
        state = request.POST.get("state")

        ChargeMaster.objects.create(
            name=name,
            value=value,
            unit=unit,
            year=year,
            energy_type=energy_type,
            state=state
        )
        messages.success(request, f"Charge '{name}' added successfully!")
        return redirect("charge_master_list")

    return render(request, "charge_master_form.html", {"title": "Add Charge"})

def charge_master_edit(request, pk):
    charge = get_object_or_404(ChargeMaster, pk=pk)
    if request.method == "POST":
        charge.name = request.POST.get("name")
        charge.value = request.POST.get("value")
        charge.unit = request.POST.get("unit")
        charge.year = request.POST.get("year")
        charge.energy_type = request.POST.get("energy_type")
        charge.state = request.POST.get("state")  # ✅ Add this
        charge.save()
        messages.success(request, f"Charge '{charge.name}' updated successfully!")
        return redirect("charge_master_list")
    return render(request, "charge_master_form.html", {"title": "Edit Charge", "charge": charge})

def charge_master_delete(request, pk):
    charge = get_object_or_404(ChargeMaster, pk=pk)
    charge.delete()
    messages.warning(request, f"Charge '{charge.name}' deleted.")
    return redirect("charge_master_list")







@login_required
def open_access_history(request):
    """
    Show logged-in user's Open Access calculation history.
    """
    calculations = OpenAccessCalculation.objects.filter(user=request.user).order_by('-calc_date')

    # Optional: totals and summary
    total_savings = sum(c.savings for c in calculations)
    total_msedcl = sum(c.msedcl_total for c in calculations)
    total_oa = sum(c.oa_total for c in calculations)

    context = {
        "calculations": calculations,
        "total_savings": total_savings,
        "total_msedcl": total_msedcl,
        "total_oa": total_oa,
    }
    return render(request, "open_access_history.html", context)


@login_required
def delete_calculation(request, calc_id):
    """
    Delete a specific Open Access calculation belonging to the logged-in user.
    """
    calc = get_object_or_404(OpenAccessCalculation, id=calc_id, user=request.user)
    calc.delete()
    messages.success(request, "Calculation deleted successfully.")
    return redirect("open_access_history")








import json
import re
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db import connection
import json
import re
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db import connection


@login_required
def dashboard_breakdown(request):
    user = request.user.username.lower()

    # --- Find user's latest table
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        db_tables = [row[0] for row in cursor.fetchall()]
    table_names = [t for t in db_tables if t.startswith(user + "_") and t.endswith("_wind")]

    if not table_names:
        return render(request, "dashboard_breakdown.html", {"error": "No data table found for this user."})

    table_name = sorted(table_names)[-1]

    # --- Get table columns
    with connection.cursor() as cursor:
        cursor.execute(f"SHOW COLUMNS FROM `{table_name}`;")
        cols = [r[0] for r in cursor.fetchall()]
    col_map = {c.lower(): c for c in cols}

    def _pick(col_map, *candidates):
        def normalize(s):
            return s.lower().replace(" ", "").replace(".", "").replace("_", "").replace("(", "").replace(")", "")
        norm_map = {normalize(k): k for k in col_map.keys()}
        for c in candidates:
            nc = normalize(c)
            if nc in norm_map:
                return norm_map[nc]
        return None

    # --- Auto map required columns
    col_oem = _pick(col_map, "oem", "provider", "manufacturer", "make", "client")
    col_customer = _pick(col_map, "customer name", "customer", "client")
    col_state = _pick(col_map, "state")
    col_site = _pick(col_map, "site", "location")
    col_wtg = _pick(col_map, "wtg", "loc no", "loc_no", "turbine", "wec")
    col_date = _pick(col_map, "date", "reading date", "entry date", "gen date", "generation date")

    # --- Handle breakdown columns (Suzlon vs WindWorld)
    col_gf = _pick(col_map, "gf", "grid failure")
    col_fm = _pick(col_map, "fm", "force majeure")
    col_s = _pick(col_map, "s", "schedule", "scheduled services", "gs", "grid shutdown")
    col_u = _pick(col_map, "u", "unscheduled services", "unscheduled", "uptime", "avail")

    if not any([col_gf, col_fm, col_s, col_u]):
        has_breakdown = False
    else:
        has_breakdown = True

    # --- Filters
    f_provider = request.GET.get("provider")
    f_customer = request.GET.get("customer")
    f_state = request.GET.get("state")
    f_site = request.GET.get("site")
    f_wtg = request.GET.get("wtg")
    f_date_from = request.GET.get("date_from")
    f_date_to = request.GET.get("date_to")

    filters = []
    params = []
    if f_provider and col_oem:
        filters.append(f"`{col_oem}` = %s")
        params.append(f_provider)
    if f_customer and col_customer:
        filters.append(f"`{col_customer}` = %s")
        params.append(f_customer)
    if f_state and col_state:
        filters.append(f"`{col_state}` = %s")
        params.append(f_state)
    if f_site and col_site:
        filters.append(f"`{col_site}` = %s")
        params.append(f_site)
    if f_wtg and col_wtg:
        filters.append(f"`{col_wtg}` = %s")
        params.append(f_wtg)
    if f_date_from and f_date_to and col_date:
        filters.append(f"`{col_date}` BETWEEN %s AND %s")
        params.extend([f_date_from, f_date_to])

    where_clause = "WHERE " + " AND ".join(filters) if filters else ""

    # --- Distincts for dropdown filters
    with connection.cursor() as cursor:
        distincts = {}
        for name, col in [
            ("providers", col_oem),
            ("customers", col_customer),
            ("states", col_state),
            ("sites", col_site),
            ("wtgs", col_wtg),
        ]:
            if col:
                cursor.execute(f"SELECT DISTINCT `{col}` FROM `{table_name}` ORDER BY `{col}`;")
                distincts[name] = [r[0] for r in cursor.fetchall() if r[0]]
            else:
                distincts[name] = []

    # --- Data aggregation
    with connection.cursor() as cursor:
        if has_breakdown:
            # ✅ Suzlon-style data
            cursor.execute(f"""
                SELECT `{col_oem}`, `{col_wtg}`,
                       SUM(`{col_gf}`), SUM(`{col_fm}`), SUM(`{col_s}`), SUM(`{col_u}`)
                FROM `{table_name}` {where_clause}
                GROUP BY `{col_oem}`, `{col_wtg}`;
            """, params)
            treemap_data = [
                {"oem": r[0] or "Unknown", "wtg": r[1],
                 "gf": r[2] or 0, "fm": r[3] or 0, "s": r[4] or 0, "u": r[5] or 0}
                for r in cursor.fetchall()
            ]

            cursor.execute(f"""
                SELECT SUM(`{col_gf}`), SUM(`{col_fm}`), SUM(`{col_s}`), SUM(`{col_u}`)
                FROM `{table_name}` {where_clause};
            """, params)
            totals = cursor.fetchone()
            summary = {
                "total_gf": totals[0] or 0,
                "total_fm": totals[1] or 0,
                "total_s": totals[2] or 0,
                "total_u": totals[3] or 0,
            }

        else:
            # --- WindWorld-style data with remarks ---
            col_remarks = _pick(col_map, "remarks", "remark", "observation", "comments", "remark(s)")
            treemap_data = []
            summary = {"total_gf": 0, "total_fm": 0, "total_s": 0, "total_u": 0}

            if col_remarks:
                def extract_hours(text):
                    if not text:
                        return 0
                    text = str(text).lower()
                    total = 0.0
                    for h, m in re.findall(r'(\d{1,2})[:](\d{1,2})\s*hrs?', text):
                        total += int(h) + int(m) / 60.0
                    if total == 0:
                        for h in re.findall(r'(\d{1,3})\s*hrs?\b', text):
                            total += int(h)
                    return round(total, 2)

                read_oem_col = col_oem or col_customer or list(col_map.keys())[0]
                select_col_for_label = col_customer if col_customer else read_oem_col

                cursor.execute(f"""
                    SELECT `{select_col_for_label}`, `{col_wtg}`, `{col_remarks}`
                    FROM `{table_name}` {where_clause};
                """, params)
                rows = cursor.fetchall()

                # --- Build raw list
                for label, wtg_val, remarks in rows:
                    gf = fm = s = u = 0.0
                    if remarks:
                        rtext = str(remarks).lower()

                        # Grid Failure / Breakdown
                        if any(k in rtext for k in ["bd", "breakdown", "grid feeding error", "gf"]):
                            hrs = extract_hours(rtext)
                            gf += hrs if hrs else 1
                            summary["total_gf"] += hrs if hrs else 1

                        # Force Majeure
                        if any(k in rtext for k in ["fm", "force majeure"]):
                            hrs = extract_hours(rtext)
                            fm += hrs if hrs else 1
                            summary["total_fm"] += hrs if hrs else 1

                        # Scheduled / Grid Shutdown
                        if any(k in rtext for k in ["gs", "shutdown", "grid shutdown", "schedule", "s"]):
                            hrs = extract_hours(rtext)
                            s += hrs if hrs else 1
                            summary["total_s"] += hrs if hrs else 1

                        # Unscheduled / Maintenance
                        if any(k in rtext for k in ["pm", "maintenance", "visual maintenance", "preventive maintenance"]):
                            hrs = extract_hours(rtext)
                            u += hrs if hrs else 1
                            summary["total_u"] += hrs if hrs else 1

                    treemap_data.append({
                        "oem": label or "Unknown",
                        "wtg": wtg_val,
                        "gf": round(gf, 2),
                        "fm": round(fm, 2),
                        "s": round(s, 2),
                        "u": round(u, 2),
                    })

                # ✅ Aggregate by WTG to avoid duplicate treemap blocks
                agg_map = {}
                for entry in treemap_data:
                    key = (entry["oem"], entry["wtg"])
                    if key not in agg_map:
                        agg_map[key] = entry
                    else:
                        agg_map[key]["gf"] += entry["gf"]
                        agg_map[key]["fm"] += entry["fm"]
                        agg_map[key]["s"] += entry["s"]
                        agg_map[key]["u"] += entry["u"]

                treemap_data = list(agg_map.values())

            else:
                # --- Simple fallback (if no remarks)
                cursor.execute(f"""
                    SELECT `{col_customer}`, `{col_wtg}`, SUM(`generation`)
                    FROM `{table_name}` {where_clause}
                    GROUP BY `{col_customer}`, `{col_wtg}`;
                """, params)
                treemap_data = [
                    {"oem": r[0] or "Unknown", "wtg": r[1],
                     "gf": 0, "fm": 0, "s": 0, "u": 0, "generation": r[2] or 0}
                    for r in cursor.fetchall()
                ]
                summary = {"total_gf": 0, "total_fm": 0, "total_s": 0, "total_u": 0}

    # --- Context for template
    context = {
        "table_name": table_name,
        "treemap_data": json.dumps(treemap_data),
        "donut_data": json.dumps(treemap_data),
        "summary": summary,
        **distincts,
        "filters": {
            "provider": f_provider,
            "customer": f_customer,
            "state": f_state,
            "site": f_site,
            "wtg": f_wtg,
            "date_from": f_date_from,
            "date_to": f_date_to,
        },
    }

    return render(request, "dashboard_breakdown.html", context)














from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import connection
from datetime import datetime

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import connection
from datetime import datetime

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import connection
from datetime import datetime

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import connection
  # ✅ safer import


@login_required
def Modifydata(request):
    user = request.user

    # --- Fetch all tables belonging to this user ---
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
              AND table_name LIKE %s
        """, [f"{user.username}_%"])
        tables = [row[0] for row in cursor.fetchall()]

    expected_tables = [{'name': t, 'label': t.replace('_', ' - ')} for t in tables]

    if request.method == "POST":
        table_name = request.POST.get('table_name')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        # --- Validation checks ---
        if not all([table_name, start_date, end_date]):
            messages.error(request, "⚠️ All fields are required.")
            return redirect('Modifydata')

        if table_name not in tables:
            messages.error(request, "❌ Invalid table selected.")
            return redirect('Modifydata')

        try:
            # --- Convert date strings to datetime.date objects ---
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()

            if start_dt > end_dt:
                messages.error(request, "⚠️ Start date cannot be after end date.")
                return redirect('Modifydata')

            # --- Detect date column name dynamically ---
            with connection.cursor() as cursor:
                cursor.execute(f"SHOW COLUMNS FROM `{table_name}`;")
                columns = [row[0].lower() for row in cursor.fetchall()]

            date_col = None
            for candidate in ["tdate", "gen_date", "date"]:
                if candidate.lower() in columns:
                    date_col = candidate
                    break

            if not date_col:
                messages.error(request, "❌ No valid date column found in the selected table.")
                return redirect('Modifydata')

            # --- Perform delete operation ---
            with connection.cursor() as cursor:
                query = f"""
                    DELETE FROM `{table_name}`
                    WHERE `{date_col}` BETWEEN %s AND %s
                """
                cursor.execute(query, [start_date, end_date])
                rows_deleted = cursor.rowcount

            # --- Feedback message ---
            if rows_deleted > 0:
                messages.success(
                    request,
                    f"✅ Deleted {rows_deleted} rows from {table_name} "
                    f"between {start_date} and {end_date}."
                )
            else:
                messages.warning(
                    request,
                    f"⚠️ No rows found in {table_name} between {start_date} and {end_date}."
                )

            return redirect('Modifydata')

        except Exception as e:
            messages.error(request, f"❌ Error occurred: {str(e)}")
            return redirect('Modifydata')

    return render(request, 'Modifydata.html', {
        'expected_tables': expected_tables,
    })





from datetime import date, timedelta, datetime
from django.utils.timezone import now

def auto_reset_completed_tasks(username=None):
    """
    Automatically reset completed monthly/quarterly/yearly checkpoints 
    when a new period starts.
    """
    from datetime import date
    today = date.today()

    with connection.cursor() as cursor:
        # Example: reset Monthly checkpoints older than 30 days
        cursor.execute(f"""
            UPDATE preventive_maintenance_with_wtg
            SET status='Pending', completed_on=NULL
            WHERE checkpoints_period='Monthly'
            AND status='Completed'
            AND completed_on IS NOT NULL
            AND completed_on <= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            {f"AND username='{username}'" if username else ""}
        """)

        # Quarterly reset example (older than 90 days)
        cursor.execute(f"""
            UPDATE preventive_maintenance_with_wtg
            SET status='Pending', completed_on=NULL
            WHERE checkpoints_period='Quarterly'
            AND status='Completed'
            AND completed_on IS NOT NULL
            AND completed_on <= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
            {f"AND username='{username}'" if username else ""}
        """)

        # Yearly reset example (older than 365 days)
        cursor.execute(f"""
            UPDATE preventive_maintenance_with_wtg
            SET status='Pending', completed_on=NULL
            WHERE checkpoints_period='Yearly'
            AND status='Completed'
            AND completed_on IS NOT NULL
            AND completed_on <= DATE_SUB(CURDATE(), INTERVAL 365 DAY)
            {f"AND username='{username}'" if username else ""}
        """)

    print(f"🔁 Auto-reset executed for {username or 'all users'} ✅")




PM_TABLE_NAME = "preventive_maintenance_data"
PM_WTG_TABLE = "preventive_maintenance_with_wtg"

def ensure_wtg_table():
    """Ensure WTG table exists and unique constraint is correctly applied."""
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        tables = [r[0] for r in cursor.fetchall()]

        if PM_WTG_TABLE not in tables:
            cursor.execute(f"""
                CREATE TABLE `{PM_WTG_TABLE}` (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    username TEXT,
                    wtg_no TEXT,
                    site TEXT,
                    state TEXT,
                    energy_type TEXT,
                    mw TEXT,
                    checkpoints_period TEXT,
                    category TEXT,
                    sub_category TEXT,
                    duration TEXT,
                    status TEXT DEFAULT 'Pending',
                    remarks TEXT,
                    completed_on DATE,
                    FOREIGN KEY (user_id) REFERENCES auth_user(id) ON DELETE CASCADE
                );
            """)

        # 🧹 Drop any old conflicting constraints
        for idx in ["unique_wtg_checkpoint", "unique_wtg_checkpoint_per_unit", "unique_wtg_checkpoint_final"]:
            try:
                cursor.execute(f"ALTER TABLE `{PM_WTG_TABLE}` DROP INDEX {idx};")
            except Exception:
                pass

        # 🔍 Remove internal duplicates automatically (same WTG + same checkpoint)
        try:
            cursor.execute(f"""
                DELETE t1 FROM `{PM_WTG_TABLE}` t1
                JOIN `{PM_WTG_TABLE}` t2
                ON t1.id > t2.id
                AND t1.username = t2.username
                AND t1.wtg_no = t2.wtg_no
                AND t1.category = t2.category
                AND t1.sub_category = t2.sub_category
                AND t1.duration = t2.duration
                AND t1.checkpoints_period = t2.checkpoints_period
                AND t1.mw = t2.mw;
            """)
        except Exception:
            pass

        # ✅ Add the final unique key
        try:
            cursor.execute(f"""
                ALTER TABLE `{PM_WTG_TABLE}`
                ADD UNIQUE KEY unique_wtg_checkpoint_final
                (`username`(50), `wtg_no`(50), `category`(100),
                 `sub_category`(100), `duration`(50),
                 `checkpoints_period`(50), `mw`(50));
            """)
        except Exception:
            pass

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import connection

PM_TABLE_NAME = "preventive_maintenance_data"
PM_WTG_TABLE = "preventive_maintenance_with_wtg"


@login_required
def my_preventive_maintenance(request):
    """
    User-side page: view, upload, and manage user's own preventive maintenance records.
    Also allows registering WTGs to create per-WTG checklists.
    """
    user = request.user
    username = user.username
    ensure_wtg_table()
    auto_reset_completed_tasks(request.user.username)

    # ------------------ REGISTER WTG ------------------ #
    if request.method == "POST" and request.POST.get("register_wtg") == "1":
        wtg_no = request.POST.get("wtg_no", "").strip()
        site = request.POST.get("site", "").strip()
        state = request.POST.get("state", "").strip()

        if not wtg_no or not site or not state:
            messages.error(request, "Please fill all WTG details.")
            return redirect("my_preventive_maintenance")

        try:
            # Fetch all user checkpoints from PM table
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    SELECT energy_type, mw, checkpoints_period, category, sub_category, duration
                    FROM `{PM_TABLE_NAME}`
                    WHERE username = %s
                """, [username])
                rows = cursor.fetchall()

            if not rows:
                messages.warning(request, "No maintenance checkpoints found to copy.")
                return redirect("my_preventive_maintenance")

            # Insert each checkpoint — silently ignore duplicates
            with connection.cursor() as cursor:
                for r in rows:
                    energy_type, mw, period, category, sub_category, duration = r
                    cursor.execute(f"""
                        INSERT IGNORE INTO `{PM_WTG_TABLE}`
                        (user_id, username, wtg_no, site, state, energy_type, mw, checkpoints_period,
                         category, sub_category, duration, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Pending')
                    """, [user.id, username, wtg_no, site, state,
                          energy_type, mw, period, category, sub_category, duration])

            messages.success(request, f"✅ WTG '{wtg_no}' registered successfully.")
        except Exception as e:
            messages.error(request, f"❌ Error registering WTG: {e}")

        return redirect("my_preventive_maintenance")

    # ------------------ FETCH USER RECORDS ------------------ #
    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT id, category, sub_category, duration, checkpoints_period, mw, description, energy_type
            FROM `{PM_TABLE_NAME}`
            WHERE username = %s
            ORDER BY id DESC
        """, [username])
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
    records = [dict(zip(columns, r)) for r in rows]

    # ------------------ DELETE RECORD ------------------ #
    if request.method == "POST" and request.POST.get("delete_id"):
        delete_id = request.POST.get("delete_id")
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"DELETE FROM `{PM_TABLE_NAME}` WHERE id=%s AND username=%s", [delete_id, username])
            messages.success(request, f"🗑️ Record {delete_id} deleted successfully.")
        except Exception as e:
            messages.error(request, f"❌ Delete failed: {e}")
        return redirect("my_preventive_maintenance")

    # ------------------ EDIT RECORD ------------------ #
    if request.method == "POST" and request.POST.get("edit_id"):
        edit_id = request.POST.get("edit_id")
        cat = request.POST.get("edit_category")
        subcat = request.POST.get("edit_sub_category")
        dur = request.POST.get("edit_duration")
        desc = request.POST.get("edit_description")
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    UPDATE `{PM_TABLE_NAME}`
                    SET category=%s, sub_category=%s, duration=%s, description=%s
                    WHERE id=%s AND username=%s
                """, [cat, subcat, dur, desc, edit_id, username])
            messages.success(request, f"✅ Record {edit_id} updated successfully.")
        except Exception as e:
            messages.error(request, f"❌ Update failed: {e}")
        return redirect("my_preventive_maintenance")

    return render(request, "my_preventive_maintenance.html", {"records": records})











from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import connection
from datetime import date

PM_WTG_TABLE = "preventive_maintenance_with_wtg"

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import connection
from datetime import date

PM_WTG_TABLE = "preventive_maintenance_with_wtg"

def ensure_wtg_table():
    """Ensure the preventive_maintenance_with_wtg table exists and has required columns."""
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        tables = [r[0] for r in cursor.fetchall()]

        if PM_WTG_TABLE not in tables:
            cursor.execute(f"""
                CREATE TABLE `{PM_WTG_TABLE}` (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    username TEXT,
                    wtg_no TEXT,
                    site TEXT,
                    state TEXT,
                    energy_type TEXT,
                    mw TEXT,
                    checkpoints_period TEXT,
                    category TEXT,
                    sub_category TEXT,
                    duration TEXT,
                    status TEXT DEFAULT 'Pending',
                    remarks TEXT,
                    completed_on DATE,
                    FOREIGN KEY (user_id) REFERENCES auth_user(id) ON DELETE CASCADE
                );
            """)

        # 🧹 Drop any old constraints that might conflict
        for idx in ["unique_wtg_checkpoint", "unique_wtg_checkpoint_per_unit"]:
            try:
                cursor.execute(f"ALTER TABLE `{PM_WTG_TABLE}` DROP INDEX {idx};")
            except Exception:
                pass

        # ✅ Add final unique key per WTG + period + MW
        try:
            cursor.execute(f"""
                ALTER TABLE `{PM_WTG_TABLE}`
                ADD UNIQUE KEY unique_wtg_checkpoint_final
                (`username`(50), `wtg_no`(50), `category`(100), 
                 `sub_category`(100), `duration`(50),
                 `checkpoints_period`(50), `mw`(50));
            """)
        except Exception:
            pass

@login_required
def user_completed_maintenance(request):
    """User dashboard — view and complete WTG-wise preventive maintenance."""
    ensure_wtg_table()
    user = request.user
    username = user.username

    # ---------- Filters ----------
    energy_types, mw_list, periods, sites, wtgs = [], [], [], [], []
    selected_energy = request.GET.get("energy_type")
    selected_mw = request.GET.get("mw")
    selected_period = request.GET.get("period")
    selected_site = request.GET.get("site")
    selected_wtg = request.GET.get("wtg_no")

    with connection.cursor() as cursor:
        # 1️⃣ Energy Type
        cursor.execute(f"SELECT DISTINCT energy_type FROM `{PM_WTG_TABLE}` WHERE username=%s", [username])
        energy_types = [r[0] for r in cursor.fetchall() if r[0]]

        # 2️⃣ MW
        if selected_energy:
            cursor.execute(f"""
                SELECT DISTINCT mw FROM `{PM_WTG_TABLE}` WHERE username=%s AND energy_type=%s
            """, [username, selected_energy])
            mw_list = [r[0] for r in cursor.fetchall() if r[0]]

        # 3️⃣ Period
        if selected_mw:
            cursor.execute(f"""
                SELECT DISTINCT checkpoints_period FROM `{PM_WTG_TABLE}`
                WHERE username=%s AND energy_type=%s AND mw=%s
            """, [username, selected_energy, selected_mw])
            periods = [r[0] for r in cursor.fetchall() if r[0]]

        # 4️⃣ Site (after selecting Period)
        if selected_period:
            cursor.execute(f"""
                SELECT DISTINCT site FROM `{PM_WTG_TABLE}`
                WHERE username=%s AND energy_type=%s AND mw=%s AND checkpoints_period=%s
            """, [username, selected_energy, selected_mw, selected_period])
            sites = [r[0] for r in cursor.fetchall() if r[0]]

        # 5️⃣ WTG (after selecting Site)
        if selected_site:
            cursor.execute(f"""
                SELECT DISTINCT wtg_no FROM `{PM_WTG_TABLE}`
                WHERE username=%s AND energy_type=%s AND mw=%s AND checkpoints_period=%s AND site=%s
            """, [username, selected_energy, selected_mw, selected_period, selected_site])
            wtgs = [r[0] for r in cursor.fetchall() if r[0]]

    # ---------- Fetch filtered tasks ----------
    records = []
    if selected_energy and selected_mw and selected_period and selected_site and selected_wtg:
        query = f"""
            SELECT id, category, sub_category, duration, site, wtg_no, status, remarks, completed_on
            FROM `{PM_WTG_TABLE}`
            WHERE username=%s AND energy_type=%s AND mw=%s 
            AND checkpoints_period=%s AND site=%s AND wtg_no=%s
        """
        params = [username, selected_energy, selected_mw, selected_period, selected_site, selected_wtg]

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            columns = [col[0] for col in cursor.description]
            records = [dict(zip(columns, r)) for r in rows]

    # ---------- Handle task completion ----------
    if request.method == "POST" and request.POST.get("complete_id"):
        complete_id = request.POST.get("complete_id")
        remarks = request.POST.get("remarks", "").strip()

        ensure_wtg_table()
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    UPDATE `{PM_WTG_TABLE}`
                    SET status='Completed', remarks=%s, completed_on=%s
                    WHERE id=%s AND username=%s
                """, [remarks, date.today(), complete_id, username])
            messages.success(request, "✅ Task marked as completed successfully.")
        except Exception as e:
            if "Unknown column" in str(e):
                ensure_wtg_table()
                with connection.cursor() as cursor:
                    cursor.execute(f"""
                        UPDATE `{PM_WTG_TABLE}`
                        SET status='Completed', remarks=%s, completed_on=%s
                        WHERE id=%s AND username=%s
                    """, [remarks, date.today(), complete_id, username])
                messages.success(request, "✅ Task marked as completed successfully (after schema fix).")
            else:
                messages.error(request, f"❌ Error updating task: {e}")

        return redirect("user_completed_maintenance")

    # ---------- Render ----------
    return render(request, "user_completed_maintenance.html", {
        "energy_types": energy_types,
        "mw_list": mw_list,
        "periods": periods,
        "sites": sites,
        "wtgs": wtgs,
        "records": records,
        "selected_energy": selected_energy,
        "selected_mw": selected_mw,
        "selected_period": selected_period,
        "selected_site": selected_site,
        "selected_wtg": selected_wtg,
    })







from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db import connection
from datetime import date

PM_WTG_TABLE = "preventive_maintenance_with_wtg"  # 🔧 replace with your actual table name


@login_required
def user_pm_report_dashboard(request):
    """User Preventive Maintenance Dashboard with ApexCharts and exportable reports."""
    user = request.user
    username = user.username

    # ✅ Ensure preventive maintenance table exists
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        tables = [r[0] for r in cursor.fetchall()]
    if PM_WTG_TABLE not in tables:
        return render(request, "user_pm_report_dashboard.html", {
            "error": "No preventive maintenance data found."
        })

    # ✅ Fetch overall completed / pending counts
    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT 
                SUM(CASE WHEN status='Completed' THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN status!='Completed' THEN 1 ELSE 0 END) AS pending
            FROM `{PM_WTG_TABLE}`
            WHERE username=%s
        """, [username])
        row = cursor.fetchone()
        completed = row[0] or 0
        pending = row[1] or 0

    total = completed + pending
    completion_rate = round((completed / total) * 100, 1) if total > 0 else 0

    # ✅ WTG-wise completion stats
    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT wtg_no,
                   SUM(CASE WHEN status='Completed' THEN 1 ELSE 0 END) AS completed,
                   SUM(CASE WHEN status!='Completed' THEN 1 ELSE 0 END) AS pending
            FROM `{PM_WTG_TABLE}`
            WHERE username=%s
            GROUP BY wtg_no
        """, [username])
        wtg_stats = cursor.fetchall()

    wtg_labels = [r[0] for r in wtg_stats]
    wtg_completed = [r[1] for r in wtg_stats]
    wtg_pending = [r[2] for r in wtg_stats]

    # ✅ Time trend (by date)
    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT DATE(completed_on), COUNT(*)
            FROM `{PM_WTG_TABLE}`
            WHERE username=%s AND status='Completed' AND completed_on IS NOT NULL
            GROUP BY DATE(completed_on)
            ORDER BY DATE(completed_on)
        """, [username])
        trend_rows = cursor.fetchall()

    trend_dates = [str(r[0]) for r in trend_rows]
    trend_counts = [r[1] for r in trend_rows]

    # ✅ Fetch records for tabs (explicit columns)
    with connection.cursor() as cursor:
        # --- Completed ---
        cursor.execute(f"""
            SELECT wtg_no, site, category, status, completed_on, remarks
            FROM `{PM_WTG_TABLE}`
            WHERE username=%s AND status='Completed'
            ORDER BY completed_on DESC
        """, [username])
        completed_records = [
            dict(zip([c[0] for c in cursor.description], r)) for r in cursor.fetchall()
        ]

        # --- Pending ---
        cursor.execute(f"""
            SELECT wtg_no, site, category, status
            FROM `{PM_WTG_TABLE}`
            WHERE username=%s AND (status!='Completed' OR status IS NULL)
        """, [username])
        pending_records = [
            dict(zip([c[0] for c in cursor.description], r)) for r in cursor.fetchall()
        ]

        # --- All Records ---
        cursor.execute(f"""
            SELECT wtg_no, site, category, status, completed_on
            FROM `{PM_WTG_TABLE}`
            WHERE username=%s
        """, [username])
        all_records = [
            dict(zip([c[0] for c in cursor.description], r)) for r in cursor.fetchall()
        ]

    # ✅ Render final dashboard
    return render(request, "user_pm_report_dashboard.html", {
        "completed": completed,
        "pending": pending,
        "completion_rate": completion_rate,
        "wtg_labels": wtg_labels,
        "wtg_completed": wtg_completed,
        "wtg_pending": wtg_pending,
        "trend_dates": trend_dates,
        "trend_counts": trend_counts,
        "completed_records": completed_records,
        "pending_records": pending_records,
        "all_records": all_records,
    })





import pandas as pd
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from .ml_utils import BreakdownMLAnalyzer
import pandas as pd
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.mail import send_mail
from .ml_utils import BreakdownMLAnalyzer

import pandas as pd
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
from .ml_utils import BreakdownMLAnalyzer


import pandas as pd
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
from .ml_utils import BreakdownMLAnalyzer
import pandas as pd
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
from .ml_utils import BreakdownMLAnalyzer
import pandas as pd
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
from .ml_utils import BreakdownMLAnalyzer
from core.models import UploadMetadata
import pandas as pd
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
from .ml_utils import BreakdownMLAnalyzer


from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
import pandas as pd
from .ml_utils import BreakdownMLAnalyzer


@login_required
def breakdown_analysis(request):

    username = request.user.username.lower().strip()
    table_name = None

    # -----------------------------------------------
    # 1️⃣ FETCH ALL TABLES
    # -----------------------------------------------
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        all_rows = cursor.fetchall()

    all_tables = [str(r[0]).strip().lower() for r in all_rows]

    # Filter only this user's breakdown tables
    user_break_tables = [
        t for t in all_tables
        if t.startswith(username + "_") and "breakdowndata" in t
    ]

    if not user_break_tables:
        return render(request, "breakdown_analysis.html", {
            "alerts": [],
            "chart_data": {},
            "error_msg": f"No breakdown table found for user '{username}'.",
            "btype": "repetitive"
        })

    table_name = sorted(user_break_tables)[-1]  # Latest table

    # -----------------------------------------------
    # 2️⃣ LOAD TABLE DATA
    # -----------------------------------------------
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT * FROM `{table_name}`")
        rows = cursor.fetchall()
        cols = [c[0] for c in cursor.description]

    if not rows:
        return render(request, "breakdown_analysis.html", {
            "alerts": [],
            "chart_data": {},
            "error_msg": f"Table '{table_name}' has no data.",
            "btype": "repetitive"
        })

    df = pd.DataFrame(rows, columns=cols)

    # Normalize columns
    df.columns = (
        df.columns
        .str.replace(".", "", regex=False)
        .str.replace(" ", "_")
        .str.lower()
    )

    # -----------------------------------------------
    # 3️⃣ AUTO-DETECT DATE & WTG COLUMNS
    # -----------------------------------------------
    date_cols = [c for c in df.columns if "date" in c or "dt" in c]
    date_col = date_cols[0] if date_cols else None

    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

    wtg_cols = [c for c in df.columns if "loc" in c or "wtg" in c or "wec" in c or "machine" in c]
    wtg_col = wtg_cols[0] if wtg_cols else None

    # -----------------------------------------------
    # 4️⃣ GET FILTERS (Including NEW Breakdown Type)
    # -----------------------------------------------
    btype = request.GET.get("btype", "repetitive")  # NEW
    severity_filter = request.GET.get("severity", "")
    wtg_filter = request.GET.get("wtg", "")
    date_from = request.GET.get("from", "")
    date_to = request.GET.get("to", "")

    # -----------------------------------------------
    # 5️⃣ APPLY FILTERS
    # -----------------------------------------------
    if wtg_filter and wtg_col:
        df = df[df[wtg_col] == wtg_filter]

    if date_from and date_col:
        df = df[df[date_col] >= date_from]

    if date_to and date_col:
        df = df[df[date_col] <= date_to]

    if df.empty:
        return render(request, "breakdown_analysis.html", {
            "alerts": [],
            "chart_data": {},
            "error_msg": "No data for selected filters.",
            "btype": btype
        })

    # -----------------------------------------------
    # 6️⃣ EXTENDED BREAKDOWN MODE (EMPTY DASHBOARD)
    # -----------------------------------------------
    if btype == "extended":
        return render(request, "breakdown_analysis.html", {
            "alerts": [],
            "chart_data": {},
            "error_msg": None,
            "severity_filter": severity_filter,
            "wtg_filter": wtg_filter,
            "date_from": date_from,
            "date_to": date_to,
            "total_alerts": 0,
            "affected_wtgs": 0,
            "repetition_rate": 0,
            "most_repetitive_wtg": None,
            "most_repetitions": 0,
            "dynamic_table": table_name,
            "btype": btype
        })

    # -----------------------------------------------
    # 7️⃣ REPETITIVE BREAKDOWN MODE (NORMAL ML MODEL)
    # -----------------------------------------------
    analyzer = BreakdownMLAnalyzer(similarity_threshold=0.60, days_window=8)
    analyzer.load_dataframe(df)
    alerts = analyzer.detect_repetitions()

    if severity_filter:
        alerts = [a for a in alerts if a["severity"] == severity_filter]

    # Chart + KPIs
    chart_data = {}
    for a in alerts:
        machine = str(a.get("machine", "Unknown"))
        chart_data[machine] = chart_data.get(machine, 0) + 1

    total_alerts = len(alerts)
    affected_wtgs = len(chart_data)
    repetition_rate = round((total_alerts / affected_wtgs) * 100, 2) if affected_wtgs else 0

    most_repetitive_wtg = None
    most_repetitions = 0
    if chart_data:
        most_repetitive_wtg, most_repetitions = max(chart_data.items(), key=lambda x: x[1])

    # -----------------------------------------------
    # 8️⃣ RENDER REPETITIVE BREAKDOWN DASHBOARD
    # -----------------------------------------------
    return render(request, "breakdown_analysis.html", {
        "alerts": alerts,
        "chart_data": chart_data,
        "error_msg": None,

        "severity_filter": severity_filter,
        "wtg_filter": wtg_filter,
        "date_from": date_from,
        "date_to": date_to,

        "total_alerts": total_alerts,
        "affected_wtgs": affected_wtgs,
        "repetition_rate": repetition_rate,

        "most_repetitive_wtg": most_repetitive_wtg,
        "most_repetitions": most_repetitions,

        "dynamic_table": table_name,
        "btype": btype  # NEW
    })
