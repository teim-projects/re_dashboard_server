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
