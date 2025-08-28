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
