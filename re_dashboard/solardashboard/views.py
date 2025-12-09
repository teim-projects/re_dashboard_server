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





# views.py
import math
from collections import defaultdict
from datetime import datetime
from django.http import JsonResponse
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required

import math
from collections import defaultdict
from datetime import datetime
from django.http import JsonResponse
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required

# ---------- Helper utilities (reusable) ----------
def _pick(col_map, *candidates):
    """Pick first candidate present in col_map (case-insensitive)."""
    for cand in candidates:
        if cand and cand.lower() in col_map:
            return col_map[cand.lower()]
    return None

def _parse_date(v):
    """Try common date formats, return datetime.date or None."""
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%b-%y", "%d-%b-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue
    # fallback: try to parse ISO
    try:
        return datetime.fromisoformat(s).date()
    except Exception:
        return None

def _clean_num(v):
    """Return float cleaned from strings/None; safe 0 fallback."""
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(",", "").strip()
    try:
        return float(s)
    except Exception:
        return 0.0
# views.py (append / add)
import math
import calendar
from collections import defaultdict
from datetime import datetime
from django.http import JsonResponse
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
from decimal import Decimal

# -----------------------
# Helper utils (auto-detect columns + clean parsing)
# -----------------------
def _pick(cmap, *candidates):
    """Return actual column name from column map for first match (case-insensitive)."""
    for cand in candidates:
        if cand is None:
            continue
        if cand.lower() in cmap:
            return cmap[cand.lower()]
    return None

def _parse_date(v):
    if v is None:
        return None
    if isinstance(v, datetime):
        return v
    # try common date strings
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(str(v), fmt)
        except Exception:
            pass
    # fallback: try parse via fromisoformat
    try:
        return datetime.fromisoformat(str(v))
    except Exception:
        return None

def _clean_num(v):
    if v is None:
        return 0.0
    if isinstance(v, (float, int)):
        return float(v)
    try:
        return float(Decimal(str(v)))
    except Exception:
        try:
            s = str(v).replace(",", "").strip()
            return float(s)
        except Exception:
            return 0.0

# -----------------------
# Page view
import math
from datetime import datetime
from collections import defaultdict
from django.http import JsonResponse
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required

# ---------------- helpers ---------------- #
def _pick(col_map, *candidates):
    """Return real column name from col_map by trying candidate variants (case-insensitive)."""
    for cand in candidates:
        if cand and cand.lower() in col_map:
            return col_map[cand.lower()]
    return None

def _parse_date(val):
    if not val:
        return None
    if isinstance(val, (datetime,)):
        return val
    # try common string formats
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%b-%Y", "%d-%B-%Y"):
        try:
            return datetime.strptime(str(val), fmt)
        except Exception:
            pass
    # try SQL timestamp fallback
    try:
        return datetime.fromisoformat(str(val))
    except Exception:
        return None

def _clean_num(v):
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        try:
            # remove commas
            return float(str(v).replace(",", ""))
        except Exception:
            return None

# ---------------- page view ---------------- #
@login_required
def generation_operating(request):
    # this page renders the template; filters handled in API
    return render(request, "generation_operating.html")

# ---------------- API ---------------- #
@login_required
def api_generation_operating(request):
    """
    Returns JSON:
    {
      "years": [2023,2024],
      "sites": ["S1","S2"],
      "kpis": {"generation_daily_avg":..., "operating_daily_avg":...},
      "monthly_by_year": {
         "2023": [{"m":1,"gen":..., "op":...}, ... 12],
         "2024": [...]
      },
      "comparison": {"generation_total":..., "operating_total":...}
    }
    """
    site_filter = request.GET.get("site")
    year_filter = request.GET.get("year")
    month_filter = request.GET.get("month")
    day_filter = request.GET.get("day")

    # fetch DB tables
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        db_tables = [r[0] for r in cursor.fetchall()]

    # pick candidate solar tables by heuristic
    candidate_tables = []
    for t in db_tables:
        tl = t.lower()
        if 'solar' in tl or tl.endswith('_solar') or '_solar_' in tl:
            candidate_tables.append(t)

    distinct_sites = set()
    rows = []  # unified rows with keys: date, site, gen_hours, op_hours

    for table in candidate_tables:
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table}`;")
            cols = [c[0] for c in cursor.fetchall()]
        col_map = {c.lower(): c for c in cols}

        date_col = _pick(col_map, "date", "reading_date", "gen_date", "timestamp")
        site_col = _pick(col_map, "site", "location", "sitename", "plant", "sitecode", "location_name")

        # possible names for generation and operating hours
        gen_col = _pick(col_map,
                        "generation_hours", "gen_hours", "gen_hour", "generation",
                        "daily_generation", "daily generation", "generation_kwh", "daily_gen")
        op_col = _pick(col_map,
                       "operating_hours", "op_hours", "op_hour", "operating",
                       "operation_hours", "operating_hours_decimal", "operating_hour")

        # if we don't have at least date + one of gen/op, skip
        if not date_col or (not gen_col and not op_col):
            continue

        # build where clauses
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

        sel_cols = []
        sel_cols.append(f"`{date_col}` as dt")
        sel_cols.append(f"`{site_col}` as site") if site_col else sel_cols.append("NULL as site")
        sel_cols.append(f"`{gen_col}` as gen") if gen_col else sel_cols.append("NULL as gen")
        sel_cols.append(f"`{op_col}` as op") if op_col else sel_cols.append("NULL as op")

        query = f"SELECT {', '.join(sel_cols)} FROM `{table}` {where} ORDER BY `{date_col}` ASC"
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                fetched = cursor.fetchall()
                desc = [d[0].lower() for d in cursor.description]
        except Exception:
            # skip tables that error
            continue

        for row in fetched:
            rec = dict(zip(desc, row))
            dt = _parse_date(rec.get("dt"))
            if not dt:
                continue
            site = rec.get("site") or "Unknown"
            gen = _clean_num(rec.get("gen"))
            op = _clean_num(rec.get("op"))
            distinct_sites.add(str(site))
            rows.append({"date": dt, "site": str(site), "gen": gen, "op": op})

    if not rows:
        return JsonResponse({
            "years": [],
            "sites": sorted(list(distinct_sites)),
            "kpis": {"generation_daily_avg": 0, "operating_daily_avg": 0},
            "monthly_by_year": {},
            "comparison": {"generation_total": 0, "operating_total": 0}
        })

    # apply site_filter again if not applied in SQL (defensive)
    if site_filter:
        rows = [r for r in rows if r["site"] == site_filter]

    # KPI calculations - daily average (mean of day's gen/op where available)
    gen_values = [r["gen"] for r in rows if r["gen"] is not None]
    op_values = [r["op"] for r in rows if r["op"] is not None]
    generation_daily_avg = round(sum(gen_values)/len(gen_values), 2) if gen_values else 0
    operating_daily_avg = round(sum(op_values)/len(op_values), 2) if op_values else 0

    # monthly-by-year aggregation: compute average per month per year for both metrics
    monthly_by_year = defaultdict(lambda: {m: {"gen_vals": [], "op_vals": []} for m in range(1,13)})
    totals = {"gen": 0.0, "op": 0.0}

    for r in rows:
        y = r["date"].year
        m = r["date"].month
        if r["gen"] is not None:
            monthly_by_year[y][m]["gen_vals"].append(r["gen"])
            totals["gen"] += (r["gen"] or 0)
        if r["op"] is not None:
            monthly_by_year[y][m]["op_vals"].append(r["op"])
            totals["op"] += (r["op"] or 0)

    # build nice structure
    result_monthly = {}
    for y, months in monthly_by_year.items():
        lst = []
        for m in range(1,13):
            gen_vals = months[m]["gen_vals"]
            op_vals = months[m]["op_vals"]
            gen_avg = round(sum(gen_vals)/len(gen_vals), 3) if gen_vals else None
            op_avg  = round(sum(op_vals)/len(op_vals), 3) if op_vals else None
            lst.append({"m": m, "gen": gen_avg, "op": op_avg})
        result_monthly[y] = lst

    years = sorted(result_monthly.keys())

    return JsonResponse({
        "years": years,
        "sites": sorted(list(distinct_sites)),
        "kpis": {
            "generation_daily_avg": generation_daily_avg,
            "operating_daily_avg": operating_daily_avg
        },
        "monthly_by_year": result_monthly,
        "comparison": {
            "generation_total": round(totals["gen"], 2),
            "operating_total": round(totals["op"], 2)
        }
    })



# --- WEATHER & BREAKDOWN DASHBOARD PAGE ---
from django.shortcuts import render
from django.http import JsonResponse
from django.db import connection

# --- WEATHER + BREAKDOWN DASHBOARD API ---

from django.http import JsonResponse
from django.db import connection
from django.contrib.auth.decorators import login_required
from collections import defaultdict
from datetime import datetime
from decimal import Decimal

# ----------------------------
# Helper functions
# ----------------------------
def _pick(col_map, *candidates):
    for cand in candidates:
        if cand and cand.lower() in col_map:
            return col_map[cand.lower()]
    return None

def _parse_date(v):
    if isinstance(v, datetime):
        return v.date()
    s = str(v)
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d-%b-%y", "%d-%b-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except:
            pass
    return None

def _num(v):
    if v is None:
        return 0
    try:
        return float(Decimal(str(v).replace(",", "")))
    except:
        return 0


# ---------------------------------------------------
# PAGE VIEW
# ---------------------------------------------------
def solar_weather_breakdown_dashboard(request):
    return render(request, "solar_weather_breakdown_dashboard.html")


# ---------------------------------------------------
# FINAL API (Weather + Breakdown)
# ---------------------------------------------------
@login_required
def api_weather_breakdown(request):

    site = request.GET.get("site")
    year = request.GET.get("year")
    month = request.GET.get("month")
    day = request.GET.get("day")

    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES")
        tables = [r[0] for r in cursor.fetchall()]

    rows = []
    all_sites = set()
    all_years = set()

    for table in tables:
        if "solar" not in table.lower():
            continue

        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table}`")
            cols = [c[0] for c in cursor.fetchall()]
        col_map = {c.lower(): c for c in cols}

        date_col = _pick(col_map, "date", "reading_date", "day")
        site_col = _pick(col_map, "site", "sitename", "location")
        gen_col = _pick(col_map, "generation_hours", "generation", "daily_generation")
        weather_col = _pick(col_map, "weather_condition", "weather")
        breakdown_col = _pick(col_map, "breakdown_details", "breakdown")

        if not date_col:
            continue

        # Build SQL filter
        conditions = []
        params = []

        if site and site_col:
            conditions.append(f"`{site_col}`=%s")
            params.append(site)

        if year:
            conditions.append(f"YEAR(`{date_col}`)=%s")
            params.append(year)

        if month:
            conditions.append(f"MONTH(`{date_col}`)=%s")
            params.append(month)

        if day:
            conditions.append(f"DAY(`{date_col}`)=%s")
            params.append(day)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        q = f"""
            SELECT 
                `{date_col}` AS dt,
                `{site_col}` AS site,
                `{gen_col}` AS gen,
                `{weather_col}` AS weather,
                `{breakdown_col}` AS breakdown
            FROM `{table}`
            {where};
        """

        try:
            with connection.cursor() as cursor:
                cursor.execute(q, params)
                fetched = cursor.fetchall()
                desc = [d[0].lower() for d in cursor.description]
        except:
            continue

        for row in fetched:
            r = dict(zip(desc, row))

            date_val = _parse_date(r.get("dt"))
            if not date_val:
                continue

            rows.append({
                "date": date_val,
                "site": r.get("site") or "Unknown",
                "gen": _num(r.get("gen")),
                "weather": r.get("weather") or "Unknown",
                "breakdown": r.get("breakdown") or None,
            })

            all_sites.add(r.get("site"))
            all_years.add(date_val.year)

    # -----------------------------------
    # AGGREGATE
    # -----------------------------------
    weather_sum = defaultdict(float)
    breakdown_count = defaultdict(int)

    for r in rows:
        weather_sum[r["weather"]] += r["gen"]
        if r["breakdown"]:
            breakdown_count[r["breakdown"]] += 1

    # Sort & Limit
    weather_list = sorted(
        [{"label": k, "value": v} for k, v in weather_sum.items()],
        key=lambda x: x["value"],
        reverse=True
    )[:15]

    breakdown_list = sorted(
        [{"label": k, "count": v} for k, v in breakdown_count.items()],
        key=lambda x: x["count"],
        reverse=True
    )[:15]

    return JsonResponse({
        "sites": sorted(all_sites),
        "years": sorted(all_years),
        "weather_data": weather_list,
        "breakdown_data": breakdown_list,
    })

# ----------------------- IMPORTS -----------------------
from django.shortcuts import render
from django.http import JsonResponse
from django.db import connection
from django.contrib.auth.decorators import login_required
from datetime import datetime
from decimal import Decimal


# ----------------------- HELPERS -----------------------
def _pick(col_map, *candidates):
    """Return first matching column name from DB table."""
    for cand in candidates:
        if cand and cand.lower() in col_map:
            return col_map[cand.lower()]
    return None


def _parse_date(v):
    """Safe date parsing; returns None if invalid."""
    if v is None:
        return None

    if isinstance(v, datetime):
        return v.date()

    s = str(v).strip()

    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%b-%y", "%d-%b-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except:
            pass

    return None


def _num(v):
    if v is None:
        return 0
    try:
        return float(Decimal(str(v).replace(",", "")))
    except:
        return 0


from django.shortcuts import render
from django.http import JsonResponse
from django.db import connection
from django.contrib.auth.decorators import login_required
from datetime import datetime
from decimal import Decimal

# ---------- helpers ----------
def _pick(col_map, *candidates):
    for cand in candidates:
        if cand and cand.lower() in col_map:
            return col_map[cand.lower()]
    return None

def _parse_date(v):
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d",
                "%d-%b-%y", "%d-%b-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass
    return None

def _num(v):
    if v is None:
        return 0.0
    try:
        return float(Decimal(str(v).replace(",", "")))
    except Exception:
        return 0.0


# ---------- PAGE VIEW ----------
@login_required
def brekdown_genration_whether_dashboard(request):
    return render(request, "brekdown_genration_whether_dashboard.html")


# ---------- API VIEW ----------
@login_required
def api_brekdown_genration_whether_dashboard(request):
    year = request.GET.get("year")
    month = request.GET.get("month")
    day = request.GET.get("day")

    # list tables
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        tables = [r[0] for r in cursor.fetchall()]

    solar_tables = [t for t in tables if "solar" in t.lower()]
    rows = []

    for table in solar_tables:
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table}`")
            cols = [c[0] for c in cursor.fetchall()]
        col_map = {c.lower(): c for c in cols}

        date_col    = _pick(col_map, "date", "reading_date", "generation_date", "day")
        gen_col     = _pick(col_map, "generation", "daily_generation",
                            "generation_kwh", "daily generation")
        gh_col      = _pick(col_map, "generation_hours", "gen_hours", "generation_hours_decimal")
        weather_col = _pick(col_map, "weather_condition", "weather")

        if not date_col or not gen_col:
            continue

        conditions = []
        params = []

        if year:
            conditions.append(f"YEAR(`{date_col}`)=%s")
            params.append(year)
        if month:
            conditions.append(f"MONTH(`{date_col}`)=%s")
            params.append(month)
        if day:
            conditions.append(f"DAY(`{date_col}`)=%s")
            params.append(day)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        query = f"""
            SELECT `{date_col}`, `{gen_col}`, `{gh_col}`, `{weather_col}`
            FROM `{table}`
            {where}
            ORDER BY `{date_col}`
        """

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            fetched = cursor.fetchall()

        for dt_raw, gen, gh, weather in fetched:
            dt = _parse_date(dt_raw)
            if not dt:
                continue

            rows.append({
                "date": dt,
                "gen": _num(gen),
                "gh": _num(gh),
                "weather": weather or "Unknown",
            })

    if not rows:
        return JsonResponse({"status": "no_data"})

    # -------- line data (daily for now; front-end will aggregate by year) --------
    line_data = []
    for r in rows:
        try:
            dt_str = r["date"].strftime("%Y-%m-%d")
        except Exception:
            continue
        line_data.append({
            "date": dt_str,
            "gen": r["gen"],
            "gh": r["gh"],
        })

    # -------- weather aggregation (e.g. Rainy, Cloudy, Good Radiation) --------
    weather_map = {}
    for r in rows:
        weather_map.setdefault(r["weather"], 0.0)
        weather_map[r["weather"]] += r["gen"]

    weather_data = [
        {"weather": k, "generation": v}
        for k, v in weather_map.items()
    ]

    # -------- KPI --------
    avg_gen = round(sum(r["gen"] for r in rows) / len(rows), 2)
    avg_gh  = round(sum(r["gh"]  for r in rows) / len(rows), 2)

    return JsonResponse({
        "status": "ok",
        "line": line_data,
        "weather": weather_data,
        "kpi": {
            "avg_gen": avg_gen,
            "avg_gh": avg_gh
        }
    })














 

# views.py (add or replace the api_generation_by_day view)
import math
from datetime import datetime
from collections import defaultdict
from decimal import Decimal
import calendar

from django.http import JsonResponse
from django.db import connection
from django.contrib.auth.decorators import login_required

# ---------- small helpers ----------
def _pick(col_map, *candidates):
    for c in candidates:
        if c and c.lower() in col_map:
            return col_map[c.lower()]
    return None

def _parse_date(v):
    if v is None:
        return None
    if isinstance(v, datetime):
        return v
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y", "%d/%m/%Y", "%d-%b-%y", "%d-%b-%Y"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None

def _num(v):
    if v is None:
        return 0.0
    try:
        return float(Decimal(str(v).replace(",", "")))
    except Exception:
        try:
            return float(v)
        except Exception:
            return 0.0

# ---------- Forecast helpers ----------
def simple_exponential_smoothing(series, alpha=0.25):
    """Return fitted (list) and last level. series: list of floats (historic)."""
    if not series:
        return [], 0.0
    fitted = [series[0]]
    level = series[0]
    for t in range(1, len(series)):
        level = alpha * series[t] + (1 - alpha) * level
        fitted.append(level)
    return fitted, level

def forecast_ses(last_level, h):
    """Return list of h forecasts from SES last level (simple constant forecast)."""
    return [last_level for _ in range(h)]

# ---------- API view ----------


import calendar
from datetime import datetime
from django.shortcuts import render

@login_required
def solar_generation_by_day(request):
    import calendar
    from django.db import connection

    years_set = set()
    months_set = set()
    days_set = set()

    # 1️⃣ Fetch all table names
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        tables = [row[0] for row in cursor.fetchall()]

    # 2️⃣ Filter solar tables only
    solar_tables = [t for t in tables if "solar" in t.lower()]

    # 3️⃣ Read date column and extract year/month/day
    for table in solar_tables:
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table}`;")
            cols = [c[0] for c in cursor.fetchall()]

        # find date column
        col_map = {c.lower(): c for c in cols}
        date_col = None
        for possible in ["date", "reading_date", "generation_date"]:
            if possible in col_map:
                date_col = col_map[possible]
                break

        if not date_col:
            continue

        # fetch dates
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT `{date_col}` FROM `{table}`;")
            dates = cursor.fetchall()

        for d in dates:
            dt = _parse_date(d[0])
            if dt:
                years_set.add(dt.year)
                months_set.add(dt.month)
                days_set.add(dt.day)

    # 4️⃣ Prepare dropdown lists  
    years = sorted(years_set)
    months = sorted(months_set)
    days = sorted(days_set)

    # convert months → (num, "MonthName")
    month_list = [(m, calendar.month_name[m]) for m in months]

    return render(request, "solar_generation_by_day.html", {
        "years": years,
        "months": month_list,
        "days": days,
    })


@login_required
def api_generation_by_day(request):
    """
    Returns JSON:
    {
      status: "ok"/"no_data",
      days: [1,2,3...],
      gen_series: [sum gen by day],
      gh_series: [avg gen-hours by day],
      forecast_days: H,
      forecast_gen: { start_day, forecast: [...], upper: [...], lower: [...] },
      forecast_gh: {...}
    }
    Query params:
      year, month, day (filters, optional)
      forecast_days (optional, default 10)
    """
    year = request.GET.get("year")
    month = request.GET.get("month")
    day_filter = request.GET.get("day")
    h = int(request.GET.get("forecast_days") or 10)  # default 10

    # find tables
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        tables = [r[0] for r in cursor.fetchall()]

    solar_tables = [t for t in tables if "solar" in t.lower()]

    agg_by_day = {}  # day -> {gen_sum, gh_sum, count}
    for table in solar_tables:
        with connection.cursor() as cursor:
            try:
                cursor.execute(f"SHOW COLUMNS FROM `{table}`")
                cols = [c[0] for c in cursor.fetchall()]
            except Exception:
                continue
        col_map = {c.lower(): c for c in cols}

        date_col = _pick(col_map, "date", "reading_date", "generation_date", "day")
        gen_col  = _pick(col_map, "daily_generation", "generation", "generation_kwh", "daily_gen", "daily generation")
        gh_col   = _pick(col_map, "generation_hours", "gen_hours", "generation_hours_decimal", "generation_hours")

        if not date_col or not gen_col:
            continue

        conditions = []
        params = []
        if year:
            conditions.append(f"YEAR(`{date_col}`)=%s"); params.append(year)
        if month:
            conditions.append(f"MONTH(`{date_col}`)=%s"); params.append(month)
        if day_filter:
            conditions.append(f"DAY(`{date_col}`)=%s"); params.append(day_filter)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        query = f"SELECT `{date_col}`, `{gen_col}`, {f'`{gh_col}`' if gh_col else 'NULL'} FROM `{table}` {where} ORDER BY `{date_col}`"
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                fetched = cursor.fetchall()
        except Exception:
            fetched = []

        for dt_raw, gen_raw, gh_raw in fetched:
            dt = _parse_date(dt_raw)
            if not dt:
                continue
            d = dt.day
            gen_v = _num(gen_raw)
            gh_v = _num(gh_raw)

            if d not in agg_by_day:
                agg_by_day[d] = {"gen": 0.0, "gh": 0.0, "count": 0}
            agg_by_day[d]["gen"] += gen_v
            if gh_col:
                agg_by_day[d]["gh"] += gh_v
            agg_by_day[d]["count"] += 1

    if not agg_by_day:
        return JsonResponse({"status": "no_data", "rows": []})

    # produce ordered lists for days present (1..max_day)
    days_sorted = sorted(agg_by_day.keys())
    max_day = max(days_sorted)

    gen_series = []
    gh_series = []
    days = []
    for d in range(1, max_day + 1):
        rec = agg_by_day.get(d)
        if rec:
            days.append(d)
            gen_series.append(round(rec["gen"], 3))
            # average gh for that day (if count available)
            gh_avg = (rec["gh"] / rec["count"]) if rec["count"] else 0.0
            gh_series.append(round(gh_avg, 3))
        else:
            # keep zeros for missing day so chart X aligns 1..max_day
            days.append(d)
            gen_series.append(0.0)
            gh_series.append(0.0)

    # ---------- Forecast generation series ----------
    # Build forecast using SES on historical gen_series (use last contiguous positive stretch)
    hist_gen = [v for v in gen_series if v is not None]
    # if all zeros, forecast zeros
    if sum(hist_gen) == 0:
        fcast = [0.0] * h
        upper = [0.0] * h
        lower = [0.0] * h
    else:
        # Use SES
        fitted, last_level = simple_exponential_smoothing(hist_gen, alpha=0.25)
        residuals = [hist_gen[i] - fitted[i] for i in range(len(fitted))] if fitted else []
        # sample std of residuals
        if len(residuals) >= 2:
            mean_res = sum(residuals) / len(residuals)
            var = sum((r - mean_res) ** 2 for r in residuals) / (len(residuals) - 1)
            resid_std = math.sqrt(max(var, 0.0))
        else:
            resid_std = max( (abs(hist_gen[-1]) * 0.05) if hist_gen else 1.0, 1.0 )

        fcast = forecast_ses(last_level, h)
        # 95% z
        z = 1.96
        upper = []
        lower = []
        for i in range(1, h+1):
            # widening factor: sqrt(i) to make cone open
            widen = math.sqrt(i)
            margin = z * resid_std * widen
            upper.append(round(fcast[i-1] + margin, 3))
            lower.append(round(max(fcast[i-1] - margin, 0.0), 3))

    # ---------- Forecast for gen-hours series (same approach but on gh_series) ----------
    hist_gh = [v for v in gh_series if v is not None]
    if sum(hist_gh) == 0:
        fcast_gh = [0.0]*h; upper_gh=[0.0]*h; lower_gh=[0.0]*h
    else:
        fitted_gh, last_level_gh = simple_exponential_smoothing(hist_gh, alpha=0.25)
        residuals_gh = [hist_gh[i] - fitted_gh[i] for i in range(len(fitted_gh))] if fitted_gh else []
        if len(residuals_gh) >= 2:
            mean_r = sum(residuals_gh)/len(residuals_gh)
            var_gh = sum((r-mean_r)**2 for r in residuals_gh) / max(len(residuals_gh)-1,1)
            std_gh = math.sqrt(max(var_gh,0.0))
        else:
            std_gh = max((abs(hist_gh[-1])*0.02) if hist_gh else 0.5, 0.5)
        fcast_gh = forecast_ses(last_level_gh, h)
        z = 1.96
        upper_gh=[]; lower_gh=[]
        for i in range(1,h+1):
            widen = math.sqrt(i)
            margin = z * std_gh * widen
            upper_gh.append(round(fcast_gh[i-1] + margin,3))
            lower_gh.append(round(max(fcast_gh[i-1] - margin,0.0),3))

    response = {
        "status": "ok",
        "days": days,
        "gen_series": gen_series,
        "gh_series": gh_series,
        "forecast_days": h,
        "forecast_gen": {
            "start_day": max_day + 1,
            "forecast": [round(x,3) for x in fcast],
            "upper": upper,
            "lower": lower
        },
        "forecast_gh": {
            "start_day": max_day + 1,
            "forecast": [round(x,3) for x in fcast_gh],
            "upper": upper_gh,
            "lower": lower_gh
        }
    }

    return JsonResponse(response, safe=True)


 # solardashboard/views.py  (append or place near other dashboard views)

import math
from datetime import datetime
from collections import defaultdict
from decimal import Decimal

from django.shortcuts import render
from django.http import JsonResponse
from django.db import connection
from django.contrib.auth.decorators import login_required

# ---------------- Helpers (re-usable) ----------------
def _pick(col_map, *candidates):
    """Return the actual column name from DB for first matching candidate (case-insensitive)."""
    for cand in candidates:
        if cand and cand.lower() in col_map:
            return col_map[cand.lower()]
    return None

def _parse_date(v):
    """Return datetime.date or None."""
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y", "%d/%m/%Y", "%d-%b-%y", "%d-%b-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass
    try:
        return datetime.fromisoformat(s).date()
    except Exception:
        return None

def _num(v):
    if v is None:
        return 0.0
    try:
        return float(Decimal(str(v).replace(",", "")))
    except Exception:
        try:
            return float(v)
        except:
            return 0.0
# ---------------- REQUIRED IMPORTS ----------------
from django.http import JsonResponse
from django.db import connection
from django.contrib.auth.decorators import login_required
from collections import defaultdict
from datetime import datetime
from decimal import Decimal


# ---------------- UTILITIES ----------------
def _pick(col_map, *names):
    """Find matching column name ignoring case."""
    for n in names:
        if n.lower() in col_map:
            return col_map[n.lower()]
    return None

def _parse_date(v):
    if not v:
        return None
    try:
        return datetime.strptime(str(v), "%Y-%m-%d")
    except:
        try:
            return datetime.fromisoformat(str(v))
        except:
            return None

def _num(v):
    try:
        return float(Decimal(str(v)))
    except:
        return None


# ---------------- PAGE VIEW ----------------
@login_required
def trend_analysis(request):
    return render(request, "trend_analysis.html", {})


# ---------------- API ----------------
@login_required
def api_trend_analysis(request):

    # Filters
    site = request.GET.get("site")
    year_filter = request.GET.get("year")
    month_filter = request.GET.get("month")
    day_filter = request.GET.get("day")

    # Get tables
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        tables = [r[0] for r in cursor.fetchall()]

    solar_tables = [
        t for t in tables
        if "solar" in t.lower()
        or t.lower().endswith("_solar")
        or "_solar_" in t.lower()
    ]

    # Containers
    gen_month_year = defaultdict(lambda: defaultdict(list))
    availability_year = defaultdict(list)
    plf_month_year = defaultdict(lambda: defaultdict(list))
    radiation_points = []

    all_sites = set()

    # ---------------- PROCESS EACH TABLE ----------------
    for table in solar_tables:
        # Fetch columns
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"SHOW COLUMNS FROM `{table}`;")
                cols = [c[0] for c in cursor.fetchall()]
        except:
            continue

        col_map = {c.lower(): c for c in cols}

        # Detect columns
        date_col = _pick(col_map, "date", "reading_date", "generation_date")

        daily_gen_col = _pick(
            col_map,
            "daily_generation",
            "generation",
            "total_generation",
            "generation_kwh",
        )

        plant_avail_col = _pick(
            col_map,
            "plant_availability",
            "plant_avail",
            "grid_ok"
        )

        plf_col = _pick(
            col_map,
            "daily_plf",
            "plf",
            "monthly_plf",
            "yearly_plf"
        )

        # Radiation columns (corrected)
        radiation_col = _pick(
            col_map,
            "horizontal_radiation_in_kwh_m2",
            "tilted_radiation_in_kwh_m2"
        )

        site_col = _pick(col_map, "site", "location")

        if not date_col:
            continue

        # Build filters
        conditions, params = [], []

        if site and site_col:
            conditions.append(f"`{site_col}`=%s")
            params.append(site)

        if year_filter:
            conditions.append(f"YEAR(`{date_col}`)=%s")
            params.append(year_filter)

        if month_filter:
            conditions.append(f"MONTH(`{date_col}`)=%s")
            params.append(month_filter)

        if day_filter:
            conditions.append(f"DAY(`{date_col}`)=%s")
            params.append(day_filter)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        select = [
            f"`{date_col}` as dt",
            f"`{daily_gen_col}` as daily_gen" if daily_gen_col else "NULL as daily_gen",
            f"`{plant_avail_col}` as avail" if plant_avail_col else "NULL as avail",
            f"`{radiation_col}` as radiation" if radiation_col else "NULL as radiation",
            f"`{plf_col}` as plf" if plf_col else "NULL as plf",
            f"`{site_col}` as site" if site_col else "NULL as site",
        ]

        query = f"SELECT {','.join(select)} FROM `{table}` {where} ORDER BY `{date_col}`"

        try:
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()
                desc = [d[0].lower() for d in cursor.description]
        except:
            continue

        # Process rows
        for r in rows:
            row = dict(zip(desc, r))
            dt = _parse_date(row.get("dt"))
            if not dt:
                continue

            y, m = dt.year, dt.month

            gen = _num(row.get("daily_gen"))
            avail = _num(row.get("avail"))
            plf = _num(row.get("plf"))
            rad = _num(row.get("radiation"))
            site_value = row.get("site")

            if site_value:
                all_sites.add(site_value)

            if gen is not None:
                gen_month_year[y][m].append(gen)

            if avail is not None:
                availability_year[y].append(avail)

            if rad is not None and gen is not None:
                radiation_points.append({
                    "radiation": rad,
                    "generation": gen
                })

            if plf is not None:
                plf_month_year[y][m].append(plf)

    # ---------------- BUILD FINAL OUTPUT ----------------

    years = sorted(set(gen_month_year.keys()) | set(availability_year.keys()) | set(plf_month_year.keys()))

    # Yearly Generation Trend
    gen_trend = {}
    for y in years:
        arr = []
        for m in range(1, 13):
            vals = gen_month_year[y].get(m, [])
            arr.append(round(sum(vals)/len(vals), 3) if vals else None)
        gen_trend[y] = arr

    # Plant availability
    availability = [
        round(sum(availability_year[y]) / len(availability_year[y]), 3)
        if availability_year[y] else None
        for y in years
    ]

    # PLF chart
    plf_chart = {}
    for y in years:
        arr = []
        for m in range(1, 13):
            vals = plf_month_year[y].get(m, [])
            arr.append(round(sum(vals)/len(vals), 3) if vals else None)
        plf_chart[y] = arr

    # Month names
    month_names = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

    return JsonResponse({
        "status": "ok",
        "years": years,
        "month_names": month_names,
        "gen_trend": gen_trend,
        "availability": availability,
        "plf_chart": plf_chart,
        "radiation_points": radiation_points,
        "years_ordered": years,
        "sites": sorted(all_sites),
    })
