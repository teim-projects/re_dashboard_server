from django.shortcuts import render

# Create your views here.
def solar_dashboard(request):
    return render(request, 'solar_dashboard.html')  # Solar Dashboard
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required

from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required

from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
from django.db.utils import ProgrammingError

@login_required
def solar_summary1(request):
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
        # Table not found
        table_exists = False

    return render(request, "solar_summary1.html", {
        "data": data,
        "table_exists": table_exists,
        "table_name": table_name
    })



import json
from django.shortcuts import render
from django.db import connection
@login_required
def solar_installation_summary2(request):
    table_name = "installation_summary_wind"   # 👈 Change if needed

    data = {}

    with connection.cursor() as cursor:
        # Power Sale summary
        cursor.execute(f"""
            SELECT power_sale_details, COUNT(*) AS cnt
            FROM `{table_name}`
            GROUP BY power_sale_details
        """)
        power_sale_data = cursor.fetchall()

        # Land summary
        cursor.execute(f"""
            SELECT land, COUNT(*) AS cnt
            FROM `{table_name}`
            GROUP BY land
        """)
        land_data = cursor.fetchall()

    # Prepare for Chart.js
    power_sale_labels = [row[0] for row in power_sale_data]
    power_sale_values = [row[1] for row in power_sale_data]

    land_labels = [row[0] for row in land_data]
    land_values = [row[1] for row in land_data]

    context = {
        "power_sale_labels": json.dumps(power_sale_labels),
        "power_sale_values": json.dumps(power_sale_values),
        "land_labels": json.dumps(land_labels),
        "land_values": json.dumps(land_values),
    }
    return render(request, "solar_installation_summary2.html", context)













# views.py
import json
from collections import defaultdict
from datetime import datetime, date
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render

# -------- helpers --------
def _clean_num(x):
    if x is None:
        return 0.0
    s = str(x).strip()
    s = s.replace(",", "")
    s = s.replace("%", "")
    try:
        return float(s)
    except:
        return 0.0

def _parse_date(val):
    # DB may already return date/datetime object
    if isinstance(val, (date, datetime)):
        return val
    if not val:
        return None
    s = str(val).strip()
    # try common formats
    for fmt in ("%d-%b-%y", "%d-%b-%Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except:
            pass
    # fallback: try dd-MMM-yy like "01-Apr-24"
    try:
        return datetime.strptime(s, "%d-%b-%y").date()
    except:
        return None

def _pick(col_map, *candidates):
    for cand in candidates:
        if cand.lower() in col_map:
            return col_map[cand.lower()]
    return None

# -------- page view --------
@login_required
def solar_dashboard_genration(request):
    # just render template, data will be fetched from /api/solar-data/
    return render(request, "solar_dashboard_genration.html", {})

# -------- API endpoint --------
@login_required
def api_solar_data(request):
    """
    GET params:
      site (string)
      year (numeric: 2024)
      month (numeric: 1-12)
      day (numeric: 1-31)
      max_rows (optional)
    Returns JSON:
      {
        sites: [...],
        years: [...],
        kpis: {daily, monthly, yearly},
        treemap: [{name: "2024", value: 12345}, ...],
        monthly: [{month: "January", value: 1234}, ...],
        table_rows: [{date, site, daily_gen, monthly_gen, yearly_gen}, ...]
      }
    """
    user = request.user.username.lower()

    site_filter = request.GET.get("site")
    year_filter = request.GET.get("year")
    month_filter = request.GET.get("month")
    day_filter = request.GET.get("day")
    max_rows = int(request.GET.get("max_rows") or 1000)

    # collect all tables with 'solar' in name (flexible)
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        db_tables = [r[0] for r in cursor.fetchall()]

    solar_tables = [t for t in db_tables if "solar" in t.lower() or t.lower().endswith("_solar") or "_solar_" in t.lower()]

    distinct_sites = set()
    treemap_sum = defaultdict(float)   # year -> sum daily
    monthly_sum = defaultdict(float)   # monthname -> sum daily
    kpi_daily = 0.0
    kpi_monthly = 0.0
    kpi_yearly = 0.0
    rows_out = []

    for table in solar_tables:
        # show columns
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table}`;")
            cols = [c[0] for c in cursor.fetchall()]
        col_map = {c.lower(): c for c in cols}

        # flexible column selection based on your provided formats
        date_col = _pick(col_map, "date", "day", "day_date", "reading_date")
        site_col = _pick(col_map, "site", "location", "sitename", "plant", "sitecode")
        daily_col = _pick(col_map, "daily generation", "daily_generation", "daily_gen", "daily", "dailygeneration", "daily_generation_kwh", "daily_kwh", "generation")
        monthly_col = _pick(col_map, "monthly generation", "monthly_generation", "monthly_gen", "monthlygeneration")
        yearly_col = _pick(col_map, "yearly generation", "yearly_generation", "yearly_gen", "yearlygeneration")

        # require date + daily_gen at minimum
        if not (date_col and daily_col):
            continue

        # build where clause & params
        conditions = []
        params = []

        if site_filter and site_col:
            conditions.append(f"`{site_col}` = %s")
            params.append(site_filter)

        if year_filter and date_col:
            conditions.append(f"YEAR(`{date_col}`) = %s")
            params.append(year_filter)

        if month_filter and date_col:
            conditions.append(f"MONTH(`{date_col}`) = %s")
            params.append(month_filter)

        if day_filter and date_col:
            conditions.append(f"DAY(`{date_col}`) = %s")
            params.append(day_filter)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        select_cols = [f"`{date_col}` as dt", f"`{daily_col}` as daily"]
        if site_col:
            select_cols.append(f"`{site_col}` as site")
        if monthly_col:
            select_cols.append(f"`{monthly_col}` as monthly")
        if yearly_col:
            select_cols.append(f"`{yearly_col}` as yearly")

        query = f"SELECT {', '.join(select_cols)} FROM `{table}` {where} ORDER BY `{date_col}` ASC LIMIT %s"
        params.append(max_rows)

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            fetched = cursor.fetchall()
            # cursor.description column names mapping
            desc = [d[0].lower() for d in cursor.description]

        for row in fetched:
            # map by desc
            rowd = dict(zip(desc, row))
            dt_raw = rowd.get("dt")
            site_val = rowd.get("site") or "Unknown"
            daily_raw = rowd.get("daily")
            monthly_raw = rowd.get("monthly") if "monthly" in rowd else None
            yearly_raw = rowd.get("yearly") if "yearly" in rowd else None

            # parse date
            dt = _parse_date(dt_raw)
            if dt is None:
                # skip if date can't be parsed
                continue

            distinct_sites.add(str(site_val))

            dval = _clean_num(daily_raw)
            mval = _clean_num(monthly_raw)
            yval = _clean_num(yearly_raw)

            kpi_daily += dval
            kpi_monthly += mval
            kpi_yearly += yval

            # treemap by year
            treemap_sum[str(dt.year)] += dval

            # monthly bar (month name)
            month_name = dt.strftime("%B")
            monthly_sum[month_name] += dval

            rows_out.append({
                "date": dt.strftime("%Y-%m-%d"),
                "site": str(site_val),
                "daily_generation": round(dval, 2),
                "monthly_generation": round(mval, 2),
                "yearly_generation": round(yval, 2),
            })

    # build JSON lists
    treemap_list = [{"name": k, "value": v} for k, v in treemap_sum.items()]
    # sort by year ascending
    treemap_list.sort(key=lambda x: int(x["name"]))

    # order months Jan..Dec
    month_order = [datetime(2000, m, 1).strftime("%B") for m in range(1, 13)]
    monthly_list = [{"month": m, "value": monthly_sum.get(m, 0.0)} for m in month_order if monthly_sum.get(m, 0.0) > 0 or m in monthly_sum]

    # years list for UI
    years_list = sorted(list({int(x["name"]) for x in treemap_list})) if treemap_list else []

    response = {
        "sites": sorted(list(distinct_sites)),
        "years": years_list,
        "kpis": {
            "daily": round(kpi_daily, 2),
            "monthly": round(kpi_monthly, 2),
            "yearly": round(kpi_yearly, 2),
        },
        "treemap": treemap_list,
        "monthly": monthly_list,
        "table_rows": rows_out[:2000],  # limit to 2k rows in response
    }

    return JsonResponse(response, safe=True)



import math
from datetime import datetime
from django.http import JsonResponse
from django.shortcuts import render
from django.db import connection


# ------------------------------
# PAGE VIEW
# ------------------------------

def solar_plf_dashboard(request):
    return render(request, "plf_dashboard.html")


# ------------------------------  
# SOLAR PLF API (FINAL VERSION)  
# ------------------------------

@login_required
def api_solar_plf(request):
    site_filter = request.GET.get("site")
    year_filter = request.GET.get("year")
    month_filter = request.GET.get("month")
    day_filter = request.GET.get("day")

    # Get all solar tables like your reference logic
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        db_tables = [r[0] for r in cursor.fetchall()]

    solar_tables = [
        t for t in db_tables
        if "solar" in t.lower() or t.lower().endswith("_solar") or "_solar_" in t.lower()
    ]

    # Storage
    distinct_sites = set()
    filtered_rows = []

    for table in solar_tables:

        # Read columns
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table}`;")
            cols = [c[0] for c in cursor.fetchall()]
        col_map = {c.lower(): c for c in cols}

        # Auto detect columns
        date_col = _pick(col_map, "date", "reading_date")
        site_col = _pick(col_map, "site", "location", "sitename", "plant", "sitecode")

        daily_plf_col = _pick(col_map, "daily_plf", "daily plf", "plf_daily")
        monthly_plf_col = _pick(col_map, "monthly_plf", "monthly plf", "plf_monthly")
        yearly_plf_col = _pick(col_map, "yearly_plf", "yearly plf", "plf_yearly")

        # Must have date + at least one PLF column
        if not date_col or not daily_plf_col:
            continue

        # Build WHERE filters
        conditions = []
        params = []

        if site_filter and site_col:
            conditions.append(f"`{site_col}` = %s")
            params.append(site_filter)

        if year_filter:
            conditions.append(f"YEAR(`{date_col}`) = %s")
            params.append(year_filter)

        if month_filter:
            conditions.append(f"MONTH(`{date_col}`) = %s")
            params.append(month_filter)

        if day_filter:
            conditions.append(f"DAY(`{date_col}`) = %s")
            params.append(day_filter)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        query = f"""
            SELECT `{date_col}` as dt,
                   `{daily_plf_col}` as daily_plf,
                   `{monthly_plf_col}` as monthly_plf,
                   `{yearly_plf_col}` as yearly_plf,
                   `{site_col}` as site
            FROM `{table}`
            {where}
            ORDER BY `{date_col}` ASC
        """

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            fetched = cursor.fetchall()
            desc = [d[0].lower() for d in cursor.description]

        for row in fetched:
            d = dict(zip(desc, row))

            dt = _parse_date(d["dt"])
            if not dt:
                continue

            site = d["site"] or "Unknown"
            distinct_sites.add(str(site))

            filtered_rows.append({
                "date": dt,
                "site": site,
                "daily_plf": _clean_num(d["daily_plf"]),
                "monthly_plf": _clean_num(d["monthly_plf"]),
                "yearly_plf": _clean_num(d["yearly_plf"]),
            })

    # ------------------------------
    # RETURN EMPTY DATA IF NO MATCH
    # ------------------------------
    if not filtered_rows:
        return JsonResponse({
            "kpis": {"daily": 0, "monthly": 0, "yearly": 0},
            "plf_quarterly": [],
            "plf_yearly_chart": [],
            "plf_monthly_chart": [],
            "years": [],
            "sites": list(distinct_sites),
        })

    # ------------------------------
    # KPI CALCULATIONS
    # ------------------------------
    kpi_daily = sum(r["daily_plf"] for r in filtered_rows) / len(filtered_rows)
    kpi_monthly = sum(r["monthly_plf"] for r in filtered_rows) / len(filtered_rows)
    kpi_yearly = sum(r["yearly_plf"] for r in filtered_rows) / len(filtered_rows)

    # ------------------------------
    # QUARTERLY PLF
    # ------------------------------
    quarter_map = {1: [], 2: [], 3: [], 4: []}

    for r in filtered_rows:
        q = (r["date"].month - 1) // 3 + 1
        quarter_map[q].append(r["daily_plf"])

    plf_quarterly = [
        {"quarter": f"Qtr {q}", "value": round(sum(vals)/len(vals), 4) if vals else 0}
        for q, vals in quarter_map.items()
    ]

    # ------------------------------
    # YEARLY PLF
    # ------------------------------
    yearly_map = {}

    for r in filtered_rows:
        y = r["date"].year
        yearly_map.setdefault(y, []).append(r["daily_plf"])

    plf_yearly_chart = [
        {"year": y, "value": round(sum(v)/len(v), 4)}
        for y, v in yearly_map.items()
    ]

    # ------------------------------
    # MONTHLY PLF
    # ------------------------------
    monthly_map = {m: [] for m in range(1, 13)}

    for r in filtered_rows:
        monthly_map[r["date"].month].append(r["daily_plf"])

    month_names = [
        "January","February","March","April","May","June",
        "July","August","September","October","November","December"
    ]

    plf_monthly_chart = [
        {
            "month": month_names[m-1],
            "value": round(sum(vals)/len(vals), 4) if vals else 0
        }
        for m, vals in monthly_map.items()
    ]

    # ------------------------------
    # SEND JSON RESPONSE
    # ------------------------------
    years = sorted(list({r["date"].year for r in filtered_rows}))

    return JsonResponse({
        "kpis": {
            "daily": round(kpi_daily, 2),
            "monthly": round(kpi_monthly, 2),
            "yearly": round(kpi_yearly, 2),
        },
        "plf_quarterly": plf_quarterly,
        "plf_yearly_chart": plf_yearly_chart,
        "plf_monthly_chart": plf_monthly_chart,
        "years": years,
        "sites": sorted(list(distinct_sites)),
    })
