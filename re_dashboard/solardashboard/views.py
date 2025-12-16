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








# --------------------------------------------------------------------------
# 🔥 NEW: Solar Summary Dashboard (KPIs + Monthly Chart + GF/FM/S/U Pie)
# --------------------------------------------------------------------------
from django.http import JsonResponse
from django.db import connection
from datetime import datetime
from collections import defaultdict
from decimal import Decimal

def _pick(col_map, *names):
    for n in names:
        if n and n.lower() in col_map:
            return col_map[n.lower()]
    return None

def _num(v):
    if v is None:
        return 0
    try:
        return float(Decimal(str(v).replace(",", "")))
    except:
        return 0

def _parse_date(v):
    try:
        return datetime.strptime(str(v), "%Y-%m-%d").date()
    except:
        try:
            return datetime.fromisoformat(str(v)).date()
        except:
            return None


def _parse_time_to_minutes(v):
    if not v:
        return 0
    v = str(v)
    if ":" not in v:
        return _num(v)
    try:
        h, m, s = v.split(":")
        return int(h) * 60 + int(m) + int(s) / 60
    except:
        return 0

@login_required
def summary_dashboard(request):
    return render(request, "solar_summary_dashboard.html")
from django.http import JsonResponse
from django.db import connection
from datetime import datetime
from collections import defaultdict
from decimal import Decimal
from django.contrib.auth.decorators import login_required

# views.py (or appropriate file)
from django.http import JsonResponse
from django.db import connection
from datetime import datetime
from collections import defaultdict
from decimal import Decimal
from django.contrib.auth.decorators import login_required

# helpers (reuse from your project)
def _pick(col_map, *names):
    for n in names:
        if n and n.lower() in col_map:
            return col_map[n.lower()]
    return None

def _num(v):
    if v is None:
        return 0
    try:
        return float(Decimal(str(v).replace(",", "")))
    except:
        return 0

def _parse_date(v):
    if not v:
        return None
    if isinstance(v, datetime):
        return v
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except:
            pass
    try:
        return datetime.fromisoformat(s)
    except:
        return None

def _parse_time_to_minutes(v):
    if not v:
        return 0
    s = str(v)
    if ":" not in s:
        return _num(s)
    try:
        h,m,s_ = s.split(":")
        return int(h)*60 + int(m) + int(float(s_)/60)
    except:
        return 0

@login_required
def api_solar_summary_dashboard(request):
    site = request.GET.get("site")
    year_filter = request.GET.get("year")
    quarter = request.GET.get("quarter")
    month_filter = request.GET.get("month")

    year_filter_int = int(year_filter) if year_filter else None
    qmap = {"Q1":[1,2,3], "Q2":[4,5,6], "Q3":[7,8,9], "Q4":[10,11,12]}
    allowed_months = qmap.get(quarter) if quarter else None
    if month_filter:
        allowed_months = [int(month_filter)]

    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        tables = [r[0] for r in cursor.fetchall()]

    solar_tables = [
        t for t in tables
        if "solar" in t.lower()
        or t.lower().endswith("_solar")
        or "_solar_" in t.lower()
        or t.lower().startswith("solar_")
    ]

    monthly = defaultdict(lambda: defaultdict(float))
    sites, years = set(), set()

    plf_vals = []
    grid_vals = []
    avail_vals = []
    gen_daily_vals, op_daily_vals = [], []

    gf_total = fm_total = s_total = u_total = 0

    for table in solar_tables:
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table}`;")
            cols = [c[0] for c in cursor.fetchall()]

        col_map = {c.lower(): c for c in cols}
        date_col = _pick(col_map, "date", "reading_date", "generation_date", "timestamp")
        site_col = _pick(col_map, "site", "plant", "sitename", "location")

        gen_col  = _pick(col_map, "generation_hours", "gen_hours", "gen")
        op_col   = _pick(col_map, "operating_hours", "op_hours", "op")

        plf_col   = _pick(col_map, "daily_plf", "plf")
        grid_col  = _pick(col_map, "grid_ok", "grid_status")
        avail_col = _pick(col_map, "plant_availability", "availability")

        gf_col = _pick(col_map, "gf")
        fm_col = _pick(col_map, "fm")
        s_col  = _pick(col_map, "s")
        u_col  = _pick(col_map, "u")

        if not date_col:
            continue

        where = []
        params = []

        if site and site_col:
            where.append(f"`{site_col}`=%s")
            params.append(site)

        if year_filter_int:
            where.append(f"(YEAR(`{date_col}`)=%s OR YEAR(STR_TO_DATE(`{date_col}`, '%Y-%m-%d'))=%s)")
            params.extend([year_filter_int, year_filter_int])

        where_sql = "WHERE " + " AND ".join(where) if where else ""

        query = f"""
            SELECT
                `{date_col}` AS dt,
                `{site_col}` AS site,
                `{gen_col}` AS gen,
                `{op_col}` AS op,
                `{plf_col}` AS plf,
                `{grid_col}` AS grid_ok,
                `{avail_col}` AS avail,
                `{gf_col}` AS gf,
                `{fm_col}` AS fm,
                `{s_col}` AS s,
                `{u_col}` AS u
            FROM `{table}` {where_sql}
        """

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            desc = [d[0].lower() for d in cursor.description]

        for r in rows:
            row = dict(zip(desc, r))
            dt = _parse_date(row['dt'])
            if not dt:
                continue

            y, m = dt.year, dt.month
            if allowed_months and m not in allowed_months:
                continue

            years.add(y)
            sites.add(str(row.get("site", "Unknown")))

            # generation + operating
            gen = _num(row.get("gen"))
            op  = _num(row.get("op"))
            monthly[y][m] += gen
            monthly[y][m + 100] += op
            gen_daily_vals.append(gen)
            op_daily_vals.append(op)

            # plf, grid ok, availability
            if row.get("plf"):   plf_vals.append(_num(row["plf"]))
            if row.get("grid_ok"): grid_vals.append(_num(row["grid_ok"]))
            if row.get("avail"): avail_vals.append(_num(row["avail"]))

            # downtime
            gf_total += _parse_time_to_minutes(row.get("gf"))
            fm_total += _parse_time_to_minutes(row.get("fm"))
            s_total  += _parse_time_to_minutes(row.get("s"))
            u_total  += _parse_time_to_minutes(row.get("u"))

    # Monthly output
    monthly_out = {}
    for y in years:
        arr = []
        for m in range(1, 13):
            arr.append({
                "m": m,
                "gen": round(monthly[y].get(m, 0.0), 3),
                "op":  round(monthly[y].get(m + 100, 0.0), 3)
            })
        monthly_out[y] = arr

    # KPI final values
    plf_daily = round(sum(plf_vals)/len(plf_vals), 2) if plf_vals else 0
    grid_ok_percent = round(sum(grid_vals)/len(grid_vals), 2) if grid_vals else 0
    plant_avail = round(sum(avail_vals)/len(avail_vals), 2) if avail_vals else 0

    # Downtime Pie
    total_dt = gf_total + fm_total + s_total + u_total
    pie = []
    if total_dt > 0:
        pie = [
            {"label": "GF", "value": round(gf_total/total_dt*100, 2)},
            {"label": "FM", "value": round(fm_total/total_dt*100, 2)},
            {"label": "S", "value":  round(s_total/total_dt*100, 2)},
            {"label": "U", "value":  round(u_total/total_dt*100, 2)}
        ]

    return JsonResponse({
        "status": "ok",
        "years": sorted(list(years)),
        "sites": sorted(list(sites)),
        "monthly_by_year": monthly_out,
        "kpis": {
            "plf_daily": plf_daily,
            "grid_ok": grid_ok_percent,
            "plant_availability": plant_avail,
        },
        "pie": pie
    })





# solardashboard/views.py  (append or integrate into existing file)
import math
import calendar
from collections import defaultdict, OrderedDict
from datetime import datetime
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render

# ---------------- Helpers ----------------
def _pick(col_map, *candidates):
    """Return actual DB column name from col_map for first matching candidate (case-insensitive)."""
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
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y", "%d-%b-%y", "%d-%b-%Y", "%Y-%m-%d %H:%M:%S"):
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
        except Exception:
            return 0.0

def _time_to_minutes(v):
    """If downtime fields are like 'hh:mm:ss' convert to minutes, else numeric fallback."""
    if v is None:
        return 0.0
    s = str(v).strip()
    if ":" in s:
        parts = s.split(":")
        try:
            h = float(parts[0]); m = float(parts[1]); sec = float(parts[2]) if len(parts) > 2 else 0.0
            return h*60 + m + sec/60.0
        except Exception:
            return _num(s)
    else:
        return _num(s)




import calendar
import re
from collections import defaultdict
from datetime import datetime
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required


# --- Helper Functions (Missing in Original Snippet) ---

def _pick(d, *keys):
    """Picks the first key present in the dictionary d."""
    for k in keys:
        if k in d:
            return d[k]
    return None

def _parse_date(val):
    """Attempts to parse various date formats from the database."""
    if not val:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, str):
        # MySQL/PostgreSQL datetime/date formats
        try:
            return datetime.strptime(val.split(" ")[0], "%Y-%m-%d").date()
        except ValueError:
            # Fallback for other formats if needed
            pass
    return None

def _num(val):
    """Converts a value to a float, returning 0.0 on failure."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0

def _time_to_minutes(val):
    """Converts a value (assumed minutes or hours/minutes) to total minutes."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        # Assume it's already in minutes if a simple number
        return float(val)
    if isinstance(val, str):
        # Try to parse HH:MM or similar formats if present, but for simplicity,
        # we'll assume the column *should* be in minutes as implied by the field names.
        return _num(val)
    return 0.0


# ---------------- Page view ----------------
@login_required
def generation_report(request):
    """Render the generation report page (template below)."""
    return render(request, "generation_report.html", {})


# ---------------- API ----------------
# ---------------- API ----------------
@login_required
def api_generation_report(request):
    """
    Returns:
      - pivot_rows
      - monthly_by_year
      - yearly_trend (with correct PLF logic)
      - kpis
      - downtime_pie
    """

    site_filter = request.GET.get("site")
    year_filter = request.GET.get("year")
    quarter = request.GET.get("quarter")
    month_filter = request.GET.get("month")
    day_filter = request.GET.get("day")

    qmap = {
        "Q1":[1,2,3], 
        "Q2":[4,5,6], 
        "Q3":[7,8,9], 
        "Q4":[10,11,12]
    }

    allowed_months = None
    if quarter in qmap:
        allowed_months = qmap[quarter]
    if month_filter:
        allowed_months = [int(month_filter)]

    # find solar tables
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        db_tables = [r[0] for r in cursor.fetchall()]

    solar_tables = [
        t for t in db_tables
        if re.search(r"solar|generation|_gen", t.lower())
    ]

    # containers
    distinct_sites = set()
    years_set = set()

    monthly_by_year = defaultdict(lambda: defaultdict(float))
    yearly_sum = defaultdict(float)
    pivot_map = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    all_daily_vals = []

    # NEW containers for Power BI PLF formula
    plf_yearly_generation = defaultdict(float)       # SUM(Yearly Generation)
    plf_total_day_generation = defaultdict(float)    # SUM(Total Day Generation)

    gf_total = fm_total = s_total = u_total = 0.0

    # helpers
    def pick(col_map, *names):
        for n in names:
            key = n.lower()
            if key in col_map:
                return col_map[key]
        for n in names:
            for k,orig in col_map.items():
                if n.lower() in k.lower():
                    return orig
        return None

    def num(x):
        if x is None: return 0
        try: return float(str(x).replace(",",""))
        except: return 0

    def parse_dt(x):
        if not x: return None
        try:
            if isinstance(x, datetime):
                return x.date()
            return datetime.fromisoformat(str(x)).date()
        except:
            pass
        for f in ("%Y-%m-%d","%d-%m-%Y","%Y/%m/%d"):
            try: return datetime.strptime(str(x), f).date()
            except: pass
        return None

    for table in solar_tables:
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"SHOW COLUMNS FROM `{table}`;")
                cols = [c[0] for c in cursor.fetchall()]
        except:
            continue

        col_map = {c.lower():c for c in cols}

        date_col = pick(col_map, "date","reading_date","generation_date","dt")
        site_col = pick(col_map, "site","sitename","sitecode")
        daily_col = pick(col_map, "daily_generation","daily","generation")
        yearly_gen_col = pick(col_map, "yearly","yearly_generation","year_gen")

        gf_col = pick(col_map, "gf","grid_failure")
        fm_col = pick(col_map, "fm","forced_maintenance")
        s_col  = pick(col_map, "s","stoppage")
        u_col  = pick(col_map, "u","unplanned")

        if not date_col or not daily_col:
            continue

        where = []
        params = []

        if site_filter and site_col:
            where.append(f"`{site_col}`=%s")
            params.append(site_filter)

        if year_filter:
            where.append(f"YEAR(`{date_col}`)=%s")
            params.append(year_filter)

        if month_filter:
            where.append(f"MONTH(`{date_col}`)=%s")
            params.append(month_filter)

        if day_filter:
            where.append(f"DAY(`{date_col}`)=%s")
            params.append(day_filter)

        where_sql = "WHERE "+ " AND ".join(where) if where else ""

        sel = [
            f"`{date_col}` AS dt",
            f"`{daily_col}` AS daily"
        ]
        if site_col: sel.append(f"`{site_col}` AS site")
        if yearly_gen_col: sel.append(f"`{yearly_gen_col}` AS yearly")

        if gf_col: sel.append(f"`{gf_col}` AS gf")
        if fm_col: sel.append(f"`{fm_col}` AS fm")
        if s_col: sel.append(f"`{s_col}` AS s")
        if u_col: sel.append(f"`{u_col}` AS u")

        query = f"""
            SELECT {", ".join(sel)}
            FROM `{table}`
            {where_sql}
            ORDER BY `{date_col}` ASC
        """

        try:
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                fetched = cursor.fetchall()
                desc = [d[0].lower() for d in cursor.description]
        except:
            continue

        for row in fetched:
            rec = dict(zip(desc, row))

            dt = parse_dt(rec.get("dt"))
            if not dt: continue

            y = dt.year
            m = dt.month

            if allowed_months and m not in allowed_months:
                continue

            years_set.add(y)

            daily_v = num(rec.get("daily"))
            yearly_v = num(rec.get("yearly"))

            # For Power BI PLF formula
            plf_yearly_generation[y] += yearly_v
            plf_total_day_generation[y] += daily_v

            monthly_by_year[y][m] += daily_v
            yearly_sum[y] += daily_v
            pivot_map[y][((m-1)//3)+1][m] += daily_v
            all_daily_vals.append(daily_v)

            # site unique list
            if site_col:
                distinct_sites.add(str(rec.get("site")))

            # downtime (optional)
            gf_total += num(rec.get("gf"))
            fm_total += num(rec.get("fm"))
            s_total += num(rec.get("s"))
            u_total += num(rec.get("u"))

    # monthly output
    month_names = [calendar.month_name[i] for i in range(1,13)]
    monthly_out = {}
    for y in sorted(monthly_by_year.keys()):
        arr = []
        for mm in range(1,13):
            if allowed_months and mm not in allowed_months:
                continue
            arr.append({
                "m":mm,
                "month_name": month_names[mm-1],
                "gen": round(monthly_by_year[y].get(mm,0),3),
                "trend":0   # optional
            })
        # simple MA-3 trend
        gens = [x["gen"] for x in arr]
        for i in range(len(arr)):
            window = gens[max(0,i-1):min(len(arr),i+2)]
            arr[i]["trend"] = round(sum(window)/len(window),3) if window else 0
        monthly_out[y] = arr

    # pivot rows
    pivot_rows = []
    for y in sorted(pivot_map.keys()):
        for q in sorted(pivot_map[y].keys()):
            q_total = round(sum(pivot_map[y][q].values()),3)
            pivot_rows.append({
                "type":"quarter",
                "year":y,
                "quarter":f"Qtr {q}",
                "quarter_total":q_total
            })
            for mm in sorted(pivot_map[y][q].keys()):
                pivot_rows.append({
                    "type":"month",
                    "year":y,
                    "quarter":f"Qtr {q}",
                    "month":month_names[mm-1],
                    "total_daily_generation": round(pivot_map[y][q][mm],3)
                })

    # YEARLY TREND (Power BI logic)
    yearly_trend = []
    for y in sorted(yearly_sum.keys()):
        # PLF = SUM(Yearly Gen) / SUM(Total Day Gen) * 100
        plf_val = 0
        if plf_total_day_generation[y] > 0:
            plf_val = (plf_yearly_generation[y] / plf_total_day_generation[y]) * 100
        
        yearly_trend.append({
            "year": y,
            "yearly_sum": round(yearly_sum[y],3),
            "plf_yearly": round(plf_val,3)
        })

    # KPIs
    daily_avg = round(sum(all_daily_vals)/len(all_daily_vals),2) if all_daily_vals else 0
    monthly_avg = round(sum(yearly_sum.values())/12,2) if yearly_sum else 0
    yearly_avg = round(sum(yearly_sum.values())/len(yearly_sum),2) if yearly_sum else 0

    return JsonResponse({
        "status":"ok",
        "years":sorted(list(years_set)),
        "sites":sorted(list(distinct_sites)),
        "kpis":{
            "daily_avg":daily_avg,
            "monthly_avg":monthly_avg,
            "yearly_avg":yearly_avg
        },
        "pivot_rows":pivot_rows,
        "monthly_by_year":monthly_out,
        "yearly_trend":yearly_trend
    })



from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db import connection
from django.http import JsonResponse

@login_required
def overall_breakdown_analysis(request):
    return render(request, "overall_breakdown_analysis.html")

from django.http import JsonResponse
from django.db import connection
from django.contrib.auth.decorators import login_required
from collections import defaultdict
from datetime import datetime
from decimal import Decimal

# ---------------- HELPERS ---------------- #

def _pick(col_map, *names):
    for n in names:
        if n and n.lower() in col_map:
            return col_map[n.lower()]
    return None

def _num(v):
    if v is None:
        return 0.0
    try:
        return float(Decimal(str(v).replace(",", "")))
    except:
        return 0.0

def _parse_date(v):
    if not v:
        return None
    if isinstance(v, datetime):
        return v.date()
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).date()
        except:
            pass
    try:
        return datetime.fromisoformat(s).date()
    except:
        return None

def _parse_time_to_minutes(v):
    if not v:
        return 0.0
    s = str(v).strip()
    if ":" in s:
        try:
            h, m, sec = s.split(":")
            return float(h) * 60 + float(m) + float(sec) / 60
        except:
            return _num(s)
    return _num(s)

# ---------------- API ---------------- #

@login_required
def api_overall_breakdown_analysis(request):

    year_filter = request.GET.get("year")
    quarter = request.GET.get("quarter")
    day_filter = request.GET.get("day")

    qmap = {
        "Q1": [1,2,3],
        "Q2": [4,5,6],
        "Q3": [7,8,9],
        "Q4": [10,11,12]
    }
    allowed_months = qmap.get(quarter)

    # ---- discover solar tables dynamically ----
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        tables = [r[0] for r in cursor.fetchall()]

    solar_tables = [t for t in tables if "solar" in t.lower()]

    # ---- accumulators ----
    gf_min = fm_min = s_min = u_min = 0.0
    generation_hours_total = 0.0

    breakdown_counter = defaultdict(int)
    weather_counter = defaultdict(int)
    years_set = set()

    # ---- process each table ----
    for table in solar_tables:

        try:
            with connection.cursor() as cursor:
                cursor.execute(f"SHOW COLUMNS FROM `{table}`;")
                cols = [c[0] for c in cursor.fetchall()]
        except:
            continue

        col_map = {c.lower(): c for c in cols}

        date_col = _pick(col_map, "date", "reading_date", "generation_date")
        genh_col = _pick(col_map, "generation hours", "generation_hours", "gen_hours")

        gf_col = _pick(col_map, "gf")
        fm_col = _pick(col_map, "fm")
        s_col  = _pick(col_map, "s")
        u_col  = _pick(col_map, "u")

        weather_col = _pick(col_map, "weather condition", "weather_condition")
        bd_col = _pick(col_map, "breakdown details", "breakdown_details")

        if not date_col or not genh_col:
            continue

        where = []
        params = []

        if year_filter:
            where.append(f"YEAR(`{date_col}`)=%s")
            params.append(year_filter)

        if day_filter:
            where.append(f"DAY(`{date_col}`)=%s")
            params.append(day_filter)

        where_sql = "WHERE " + " AND ".join(where) if where else ""

        select_cols = [
            f"`{date_col}` AS dt",
            f"`{genh_col}` AS genh"
        ]

        if gf_col: select_cols.append(f"`{gf_col}` AS gf")
        if fm_col: select_cols.append(f"`{fm_col}` AS fm")
        if s_col:  select_cols.append(f"`{s_col}` AS s")
        if u_col:  select_cols.append(f"`{u_col}` AS u")
        if weather_col: select_cols.append(f"`{weather_col}` AS weather")
        if bd_col: select_cols.append(f"`{bd_col}` AS bd")

        query = f"""
            SELECT {", ".join(select_cols)}
            FROM `{table}`
            {where_sql}
        """

        try:
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()
                desc = [d[0].lower() for d in cursor.description]
        except:
            continue

        for r in rows:
            row = dict(zip(desc, r))

            dt = _parse_date(row.get("dt"))
            if not dt:
                continue

            if allowed_months and dt.month not in allowed_months:
                continue

            years_set.add(dt.year)

            # ---- downtime (minutes) ----
            gf_min += _parse_time_to_minutes(row.get("gf"))
            fm_min += _parse_time_to_minutes(row.get("fm"))
            s_min  += _parse_time_to_minutes(row.get("s"))
            u_min  += _parse_time_to_minutes(row.get("u"))

            # ---- generation hours (hours) ----
            generation_hours_total += _num(row.get("genh"))

            # ---- breakdown details ----
            if row.get("bd"):
                breakdown_counter[str(row["bd"]).strip()] += 1

            # ---- weather condition ----
            if row.get("weather"):
                weather_counter[str(row["weather"]).strip()] += 1

    # ================= KPI FIX =================
    # Convert minutes → hours BEFORE dividing
    breakdown_hours = (gf_min + fm_min + s_min + u_min) / 60

    # Extra safety: downtime cannot exceed generation hours
    breakdown_hours = min(breakdown_hours, generation_hours_total)

    gt_breakdown_percentage = round(
        (breakdown_hours / generation_hours_total * 100)
        if generation_hours_total else 0,
        2
    )



    print("---- GT BREAKDOWN DEBUG ----")
    print("GF minutes:", gf_min)
    print("FM minutes:", fm_min)
    print("S  minutes:", s_min)
    print("U  minutes:", u_min)
    print("TOTAL downtime minutes:", gf_min + fm_min + s_min + u_min)
    print("TOTAL downtime hours:", (gf_min + fm_min + s_min + u_min) / 60)
    print("TOTAL generation hours:", generation_hours_total)
    print("GT Breakdown %:", gt_breakdown_percentage)
    print("-----------------------------")

    return JsonResponse({
        "status": "ok",

        "kpis": {
            "gt_breakdown_percentage": gt_breakdown_percentage
        },

        "filters": {
            "years": sorted(list(years_set))
        },

        "breakdown_table": [
            {"label": k, "count": v}
            for k, v in sorted(
                breakdown_counter.items(),
                key=lambda x: -x[1]
            )
        ],

        "weather_table": [
            {"condition": k, "count": v}
            for k, v in sorted(
                weather_counter.items(),
                key=lambda x: -x[1]
            )
        ],

        "weather_chart": [
            {"condition": k, "count": v}
            for k, v in sorted(
                weather_counter.items(),
                key=lambda x: -x[1]
            )
        ]
    })
