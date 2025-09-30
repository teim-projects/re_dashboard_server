from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required


def index_page(request):
  return render(request, 'index.html')


from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib.auth.models import User
from django.db.models import Count
from django.utils.timezone import now
import datetime, json
from collections import defaultdict
from accounts.models import UserProfile, EnergyType, Provider


@login_required
def dashboard(request):
    user = request.user

    if user.is_superuser:
        # --- Customer stats ---
        total_customers = UserProfile.objects.count()
        active_customers = User.objects.filter(is_active=True).count()
        inactive_customers = User.objects.filter(is_active=False).count()

        # --- Energy stats ---
        total_energy = EnergyType.objects.count()
        energy_data = (
            EnergyType.objects.annotate(total=Count("userprofile"))
            .values("name", "total")
        )
        energy_labels = [e["name"] for e in energy_data]
        energy_values = [e["total"] for e in energy_data]

        # --- Provider stats ---
        total_providers = Provider.objects.count()

        # --- User Registrations (last 6 months, grouped by username) ---
        today = now().date()
        six_months_ago = today - datetime.timedelta(days=180)
        users = User.objects.filter(date_joined__gte=six_months_ago)

        months = [
            (today - datetime.timedelta(days=i * 30)).strftime("%b %Y")
            for i in range(6, -1, -1)
        ]

        user_data = defaultdict(lambda: [0] * len(months))
        for u in users:
            month_label = u.date_joined.strftime("%b %Y")
            if month_label in months:
                idx = months.index(month_label)
                user_data[u.username][idx] += 1

        colors = [
            "#36A2EB", "#FF6384", "#4BC0C0", "#9966FF", "#FF9F40",
            "#28a745", "#e83e8c", "#20c997", "#6f42c1", "#fd7e14"
        ]
        datasets = []
        for i, (username, values) in enumerate(user_data.items()):
            datasets.append({
                "label": username,
                "data": values,
                "borderColor": colors[i % len(colors)],
                "backgroundColor": colors[i % len(colors)] + "33",
                "fill": True,
                "tension": 0.3,
                "pointRadius": 5,
                "pointHoverRadius": 8
            })

        context = {
            "total_customers": total_customers,
            "active_customers": active_customers,
            "inactive_customers": inactive_customers,
            "total_energy": total_energy,
            "energy_labels": json.dumps(energy_labels),
            "energy_values": json.dumps(energy_values),
            "total_providers": total_providers,
            "registration_labels": json.dumps(months),
            "registration_datasets": json.dumps(datasets),
        }
        return render(request, "tracking_dashboard.html", context)

    # Normal user dashboard
    return render(request, "wind_dashboard.html")



@login_required
def modify_data(request):
  return render(request,'modify_data.html')

@login_required
def manage_user(request):
   return render(request, 'manageUsers.html')

@login_required
def client_info(request):
   return render(request, 'client_info.html')
 
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.utils.text import slugify
from django.contrib.auth.models import User


 

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.contrib.auth.models import User
from accounts.models import Provider, EnergyType
import datetime

from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.contrib.auth.models import User
from accounts.models import Provider, EnergyType
from datetime import datetime


@login_required
def modify_data(request):
    users = User.objects.filter(is_superuser=False)

    # Fetch all actual tables from DB
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        db_tables = [row[0] for row in cursor.fetchall()]

    # Match pattern: username_provider_energytype
    expected_tables = []
    for table in db_tables:
        parts = table.split('_')
        if len(parts) >= 3:
            username = parts[0]
            provider_slug = '_'.join(parts[1:-1])
            energy_type_slug = parts[-1]

            if Provider.objects.filter(name__iexact=provider_slug.replace('_', ' ')).exists() and \
               EnergyType.objects.filter(name__iexact=energy_type_slug.replace('_', ' ')).exists():
                expected_tables.append({
                    'name': table,
                    'label': f"{username} - {provider_slug.replace('_', ' ').title()} - {energy_type_slug.title()}"
                })

    if request.method == "POST":
        user_id = request.POST.get("user_id")
        table_name = request.POST.get("table_name")
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")

        if not all([user_id, table_name, start_date, end_date]):
            messages.error(request, "❌ All fields are required.")
            return redirect("modify_data")

        try:
            # Validate input dates
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()

            if start_date_obj > end_date_obj:
                messages.error(request, "⚠️ Start date cannot be after End date.")
                return redirect("modify_data")

            # 🔑 Detect correct date column
            with connection.cursor() as cursor:
                cursor.execute(f"SHOW COLUMNS FROM `{table_name}`;")
                columns = [row[0].lower() for row in cursor.fetchall()]

            date_col = None
            for candidate in ["gen_date", "date", "Date"]:
                if candidate.lower() in columns:
                    date_col = candidate
                    break

            if not date_col:
                messages.error(request, "❌ No valid date column found in the selected table.")
                return redirect("modify_data")

            # Perform delete
            with connection.cursor() as cursor:
                delete_sql = f"""
                    DELETE FROM `{table_name}`
                    WHERE uploaded_by = (
                        SELECT username FROM auth_user WHERE id = %s
                    )
                    AND `{date_col}` BETWEEN %s AND %s
                """
                cursor.execute(delete_sql, [user_id, start_date, end_date])
                if cursor.rowcount == 0:
                    messages.warning(request, "⚠️ No records matched the criteria.")
                else:
                    messages.success(request, f"✅ {cursor.rowcount} record(s) deleted successfully.")

        except Exception as e:
            messages.error(request, f"❌ Error: {str(e)}")
        return redirect("modify_data")

    return render(request, "modify_data.html", {
        "users": users,
        "expected_tables": expected_tables
    })

from django.utils.text import slugify
from accounts.models import UserProfile  # already linked to User
from django.contrib.auth.models import User

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.core.files.storage import FileSystemStorage
from django.db import connection
from django.utils.text import slugify
from django.contrib.auth.models import User

import pandas as pd

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.db import connection
from django.shortcuts import render, redirect
from django.utils.text import slugify
from django.contrib.auth.models import User
from accounts.models import EnergyType  # make sure this import is correct

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.utils.text import slugify
from django.db import connection
import pandas as pd

from django.contrib.auth.models import User
from accounts.models import EnergyType


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.utils.text import slugify
from django.db import connection
import pandas as pd
from django.contrib.auth.models import User
from accounts.models import EnergyType

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.utils.text import slugify
from django.db import connection
import pandas as pd
from accounts.models import EnergyType

@login_required
def upload_installation_summary(request):
    energy_types = EnergyType.objects.all()

    if request.method == 'POST':
        energy_type_id = request.POST.get('energy_type')
        file = request.FILES.get('file')

        if not energy_type_id or not file:
            messages.error(request, "All fields are required.")
            return redirect('upload_installation_summary')

        try:
            energy_type = EnergyType.objects.get(id=energy_type_id)
        except EnergyType.DoesNotExist:
            messages.error(request, "Invalid energy type.")
            return redirect('upload_installation_summary')

        fs = FileSystemStorage()
        filename = fs.save(file.name, file)
        file_path = fs.path(filename)

        try:
            # Read only the headers (ignore data rows)
            if filename.endswith('.csv'):
                df = pd.read_csv(file_path, nrows=0)
            else:
                df = pd.read_excel(file_path, nrows=0)

            # Normalize headers
            user_columns = [col.strip().replace(' ', '_').lower() for col in df.columns]

            # Prepend 'customer' (from request.user) and 'energy_type'
            final_columns = ['customer', 'energy_type'] + user_columns

            # Table name based on energy type
            table_name = f"installation_summary_{slugify(energy_type.name)}"

            with connection.cursor() as cursor:
                columns_sql = ", ".join([f"`{col}` TEXT" for col in final_columns])
                cursor.execute(f"CREATE TABLE IF NOT EXISTS `{table_name}` ({columns_sql})")

            messages.success(request, f"✅ Structure created successfully for table `{table_name}`.")

        except Exception as e:
            messages.error(request, f"❌ Upload failed: {str(e)}")

        finally:
            fs.delete(filename)

        return redirect('upload_installation_summary')

    return render(request, 'upload_installation_summary.html', {
        'energy_types': energy_types,
    })

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.utils.text import slugify
from django.db import connection
import pandas as pd

from django.contrib.auth.models import User
from accounts.models import EnergyType


@login_required
def upload_installation_data(request):
    customers = User.objects.filter(is_superuser=False)
    energy_types = EnergyType.objects.all()

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        energy_type_id = request.POST.get('energy_type')
        file = request.FILES.get('file')

        if not user_id or not energy_type_id or not file:
            messages.error(request, "All fields are required.")
            return redirect('upload_installation_data')

        try:
            user = User.objects.get(id=user_id)
            energy_type = EnergyType.objects.get(id=energy_type_id)
        except (User.DoesNotExist, EnergyType.DoesNotExist):
            messages.error(request, "Invalid user or energy type.")
            return redirect('upload_installation_data')

        fs = FileSystemStorage()
        filename = fs.save(file.name, file)
        file_path = fs.path(filename)

        try:
            if filename.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)

            # Add metadata
            df['uploaded_by'] = request.user.username
            df['customer'] = user.username
            df['energy_type'] = energy_type.name
            df.columns = [col.strip().replace(' ', '_').lower() for col in df.columns]

            table_name = f"installation_summary_{slugify(energy_type.name)}"

            # Fetch table columns from database
            with connection.cursor() as cursor:
                cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
                db_columns = [row[0] for row in cursor.fetchall()]

            # Validate that uploaded columns match existing table
            missing_cols = set(db_columns) - set(df.columns)
            if missing_cols:
                messages.error(request, f"Uploaded file is missing columns: {', '.join(missing_cols)}")
                return redirect('upload_installation_data')

            # Reorder columns to match DB order
            df = df[db_columns]

            with connection.cursor() as cursor:
                for _, row in df.iterrows():
                    columns = ", ".join(f"`{col}`" for col in df.columns)
                    placeholders = ", ".join(["%s"] * len(row))
                    values = list(row.values)
                    cursor.execute(f"INSERT INTO `{table_name}` ({columns}) VALUES ({placeholders})", values)

            messages.success(request, f"✅ Data uploaded successfully into `{table_name}`.")
        except Exception as e:
            messages.error(request, f"❌ Upload failed: {str(e)}")
        finally:
            fs.delete(filename)

        return redirect('upload_installation_data')

    return render(request, 'upload_installation_data.html', {
        'customers': customers,
        'energy_types': energy_types,
    })


from django.db import connection
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from accounts.models import EnergyType, User  # Adjust imports to match your project

@login_required
@csrf_exempt
def manage_installation_data(request):
    customers = User.objects.filter(is_superuser=False)
    energy_types = EnergyType.objects.all()
    installation_entries = []

    if request.method == 'POST' and 'delete_entry' in request.POST:
        user_id = request.POST.get('user_id')
        energy_type_id = request.POST.get('energy_type_id')

        try:
            user = User.objects.get(id=user_id)
            energy_type = EnergyType.objects.get(id=energy_type_id)
            table_name = f"installation_summary_{slugify(energy_type.name)}"

            with connection.cursor() as cursor:
                cursor.execute(f"DELETE FROM `{table_name}` WHERE customer = %s", [user.username])
            messages.success(request, f"✅ Installation data for '{user.username}' deleted.")
        except Exception as e:
            messages.error(request, f"⚠️ Failed to delete installation: {str(e)}")

        return redirect('manage_installation_data')

    # List all installations grouped by customer and energy type
    for e_type in energy_types:
        table_name = f"installation_summary_{slugify(e_type.name)}"
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT DISTINCT customer FROM `{table_name}`"
                )
                rows = cursor.fetchall()
                for row in rows:
                    customer_username = row[0]
                    user = User.objects.filter(username=customer_username).first()
                    if user:
                        installation_entries.append({
                            'user': user,
                            'energy_type': e_type,
                        })
        except Exception:
            continue  # skip tables that don't exist or are invalid

    return render(request, 'manage_installation_data.html', {
        'installation_entries': installation_entries,
    })

 

from django.http import HttpResponse
from django.utils.text import slugify
from django.db import connection
import pandas as pd
import io
from accounts.models import EnergyType
from django.contrib.auth.decorators import login_required

@login_required
def download_template(request):
    energy_type_id = request.GET.get('energy_type')

    if not energy_type_id:
        return HttpResponse("❌ Energy Type is required in query params.", status=400)

    try:
        energy_type = EnergyType.objects.get(id=energy_type_id)
    except EnergyType.DoesNotExist:
        return HttpResponse("❌ Invalid Energy Type.", status=400)

    table_name = f"installation_summary_{slugify(energy_type.name)}"

    try:
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
            columns = [row[0] for row in cursor.fetchall()]
    except Exception as e:
        return HttpResponse(f"❌ Table `{table_name}` not found or invalid: {str(e)}", status=500)

    exclude_columns = {'customer', 'energy_type'}
    user_columns = [col for col in columns if col not in exclude_columns]

    if not user_columns:
        return HttpResponse("❌ No user-uploaded columns found in this table.", status=500)

    df = pd.DataFrame(columns=user_columns)

    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)

    response = HttpResponse(
        buffer,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{table_name}_template.xlsx"'
    return response


import os
import re
import traceback
import pandas as pd
import numpy as np

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
import os
import re
import traceback
import pandas as pd
import os
import re
import traceback
import pandas as pd
import numpy as np
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.db import connection
from django.contrib.auth.models import User
from django.utils.timezone import now
from accounts.models import Provider, EnergyType
from .models import UploadMetadata

# --- Column cleaner
def clean_col(col: str) -> str:
    return re.sub(r'\W+', '_', str(col).strip()).lower().strip('_')

# --- Detect meta-info row & robust Excel/HTML detection
def read_file_with_meta_check(file_path, ext):
    def looks_like_meta(row_values):
        text = " ".join(str(v) for v in row_values if pd.notnull(v)).lower()
        return "wec wise report" in text or "date :" in text

    # Check for HTML content
    with open(file_path, "rb") as f:
        header = f.read(8)
        is_html = header.startswith(b'<!DOCTYPE') or header.startswith(b'<html')

    try:
        skip_rows = 0

        if ext == ".csv":
            preview = pd.read_csv(file_path, nrows=1, header=None)
            skip_rows = 1 if looks_like_meta(preview.iloc[0].tolist()) else 0
            df = pd.read_csv(file_path, header=0, skiprows=skip_rows)

        elif ext == ".xls":
            # Try old Excel binary first
            try:
                df = pd.read_excel(file_path, header=0, engine="xlrd")
            except Exception:
                # fallback to HTML table parsing
                df = pd.read_html(file_path)[0]

        elif ext in [".xlsx", ".xlsm"]:
            preview = pd.read_excel(file_path, nrows=1, header=None, engine="openpyxl")
            skip_rows = 1 if looks_like_meta(preview.iloc[0].tolist()) else 0
            df = pd.read_excel(file_path, header=0, skiprows=skip_rows, engine="openpyxl")

        elif ext in [".ods", ".odt"]:
            preview = pd.read_excel(file_path, nrows=1, header=None, engine="odf")
            skip_rows = 1 if looks_like_meta(preview.iloc[0].tolist()) else 0
            df = pd.read_excel(file_path, header=0, skiprows=skip_rows, engine="odf")

        else:
            raise Exception(f"Unsupported file format: {ext}")

    except Exception as e:
        raise Exception(f"Unsupported format or corrupt file: {str(e)}")

    return df

import pandas as pd
from datetime import datetime, date
# --- Normalize date values
def normalize_date(val):
    """
    Convert Excel/CSV date into YYYY-MM-DD string.
    """
    if val is None or str(val).strip().lower() in ["", "nan", "nat"]:
        return None
    try:
        return pd.to_datetime(val).date()
    except Exception:
        return None


# --- Normalize hours values
def normalize_hours(val):
    """
    Convert values like '1 days 00:00:00', '21:30:00', or 24 into float hours.
    """
    if val is None or val == "" or str(val).lower() == "nan":
        return None
    try:
        if isinstance(val, (int, float)):
            return float(val)

        s = str(val).strip()

        # Case: '1 days 00:00:00'
        if "day" in s:
            parts = s.split()
            days = float(parts[0])
            h, m, sec = [float(x) for x in parts[-1].split(":")]
            return days * 24 + h + m/60 + sec/3600

        # Case: '21:30:00'
        if ":" in s:
            h, m, sec = [float(x) for x in s.split(":")]
            return h + m/60 + sec/3600

        # Otherwise, plain number string
        return float(s)
    except:
        return None

# --- Helper: sanitize values for DB ---
def sanitize_value(val):
    """Convert invalid DB values into None (MySQL NULL)."""
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


@login_required
def upload_files(request):
    energy_types = EnergyType.objects.all()
    providers = Provider.objects.all()

    # --- Fetch existing DB tables
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        db_tables = [row[0] for row in cursor.fetchall()]

    expected_tables = []
    for table in db_tables:
        parts = table.split("_")
        if len(parts) >= 3:
            username = parts[0]
            provider_slug = "_".join(parts[1:-1])
            energy_type_slug = parts[-1]
            if Provider.objects.filter(name__iexact=provider_slug.replace("_", " ")).exists() and \
               EnergyType.objects.filter(name__iexact=energy_type_slug.replace("_", " ")).exists():
                expected_tables.append({
                    "name": table,
                    "label": f"{username} - {provider_slug.replace('_',' ').title()} - {energy_type_slug.title()}"
                })

    if request.method == "POST":
        table_name = request.POST.get("provider", "").strip()
        provider_name = request.POST.get("provider_name", "").strip()
        data_file = request.FILES.get("data_file")

        if not table_name or not data_file or not provider_name:
            messages.error(request, "❌ Table, file, and provider are required.")
            return redirect("upload_files")

        fs = FileSystemStorage()
        filename = fs.save(data_file.name, data_file)
        file_path = fs.path(filename)

        try:
            ext = os.path.splitext(filename)[1].lower()
            df = read_file_with_meta_check(file_path, ext)

            # --- Clean column names
            df.columns = [clean_col(c) for c in df.columns]

            # --- Replace invalid values early
            df = df.replace({pd.NaT: None, "": None, "nan": None, "NaN": None})
            df = df.astype(object).where(pd.notnull(df), None)
            df = df.replace({np.nan: None, np.inf: None, -np.inf: None})

            # --- Fetch DB columns
            with connection.cursor() as cursor:
                cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
                table_columns = [col[0].lower() for col in cursor.fetchall()]

            # --- Keep only matching columns
            valid_columns = [col for col in df.columns if col in table_columns]
            df = df[valid_columns]

            if df.shape[1] == 0:
                messages.error(request, "❌ Upload failed: No matching columns between file and table.")
                return redirect("upload_files")

            # --- Normalize date columns
            date_cols = [c for c in df.columns if "date" in c]
            for dc in date_cols:
                df[dc] = df[dc].apply(normalize_date)

            # --- Normalize hours columns
            if "o_hrs" in df.columns:
                df["o_hrs"] = df["o_hrs"].apply(normalize_hours)
            if "l_hrs" in df.columns:
                df["l_hrs"] = df["l_hrs"].apply(normalize_hours)

            # --- Add mandatory fields
            parts = table_name.split("_")
            uploaded_by = parts[0]
            energy_type = parts[-1].replace("_", " ").title()

            if "energy_type" in table_columns:
                df["energy_type"] = energy_type
            if "uploaded_by" in table_columns:
                df["uploaded_by"] = uploaded_by
            if "provider" in table_columns:
                df["provider"] = provider_name

            # --- Prepare SQL insert
            columns = ", ".join(f"`{col}`" for col in df.columns)
            placeholders = ", ".join(["%s"] * len(df.columns))
            insert_sql = f"INSERT INTO `{table_name}` ({columns}) VALUES ({placeholders})"

            # --- Sanitize all values before insert
            values = [tuple(sanitize_value(v) for v in row) for row in df.values]

            # --- Bulk insert
            with connection.cursor() as cursor:
                cursor.executemany(insert_sql, values)
                rows_inserted = cursor.rowcount

            if rows_inserted > 0:
                UploadMetadata.objects.update_or_create(
                    table_name=table_name,
                    defaults={"last_modified": now()}
                )
                messages.success(request, f"✅ Uploaded {rows_inserted} rows to '{table_name}'.")
            else:
                messages.error(request, "❌ Upload failed: No rows inserted. Check file structure.")

        except Exception as e:
            print("🔥 Upload failed:\n", traceback.format_exc())
            messages.error(request, f"❌ Upload failed: {str(e)}")
        finally:
            fs.delete(filename)

        return redirect("upload_files")

    return render(request, "upload_files.html", {
        "expected_tables": expected_tables,
        "providers": providers,
        "energy_types": energy_types,
        "staff_users": User.objects.filter(is_superuser=False),
    })

from django.db import connection, DatabaseError

from django.db import connection, DatabaseError
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from accounts.models import Provider, EnergyType
import re

from django.db import connection, DatabaseError
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
 
from .models import UploadMetadata  # ✅ import this
from django.db.utils import DatabaseError
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.shortcuts import render

from django.shortcuts import render
from django.db import connection, DatabaseError
from django.contrib.auth.decorators import login_required
 
from django.core.paginator import Paginator
from django.db import connection, DatabaseError
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from accounts.models import Provider, EnergyType
from core.models import UploadMetadata

from django.shortcuts import render
from django.db import connection, DatabaseError
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
 

from django.utils.dateparse import parse_date

@login_required
def client_info(request):
    client_data = []

    client_filter = request.GET.get('client', '').lower()
    oem_filter = request.GET.get('oem', '').lower()
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')

    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        all_tables = [row[0] for row in cursor.fetchall()]

    oem_names_set = set()

    for table in all_tables:
        parts = table.split('_')
        if len(parts) >= 3:
            username = parts[0]
            provider_slug = '_'.join(parts[1:-1])
            energy_type_slug = parts[-1]

            provider_name = provider_slug.replace('_', ' ').title()
            energy_type_name = energy_type_slug.replace('_', ' ').title()
            oem_names_set.add(provider_name)

            provider_exists = Provider.objects.filter(name__iexact=provider_name).exists()
            energy_exists = EnergyType.objects.filter(name__iexact=energy_type_name).exists()

            if provider_exists and energy_exists:
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(f"SHOW COLUMNS FROM `{table}`")
                        available_cols = [row[0] for row in cursor.fetchall()]

                    uploaded_by = 'uploaded_by' if 'uploaded_by' in available_cols else None

                    row_uploaded_by = None
                    if uploaded_by:
                        with connection.cursor() as cursor:
                            cursor.execute(f"SELECT `{uploaded_by}` FROM `{table}` LIMIT 1")
                            result = cursor.fetchone()
                            if result:
                                row_uploaded_by = result[0]

                    try:
                        metadata = UploadMetadata.objects.get(table_name=table)
                        last_modified = metadata.last_modified.strftime('%Y-%m-%d')
                    except UploadMetadata.DoesNotExist:
                        last_modified = None

                    client_name = f"{row_uploaded_by}_{energy_type_name}" if row_uploaded_by else "N/A"

                    # Apply filters
                    if client_filter and client_filter not in client_name.lower():
                        continue
                    if oem_filter and oem_filter not in provider_name.lower():
                        continue
                    if from_date and last_modified and last_modified < from_date:
                        continue
                    if to_date and last_modified and last_modified > to_date:
                        continue

                    client_data.append({
                        "client": client_name,
                        "oem": provider_name,
                        "generation": "N/A",
                        "breakdown": "N/A",
                        "last_modified": last_modified or "N/A",
                    })

                except DatabaseError as e:
                    print(f"⚠️ Skipping table `{table}` due to error: {e}")
                    continue

    # Sort data (optional)
    client_data.sort(key=lambda x: x['client'])

    paginator = Paginator(client_data, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'client_info.html', {
        'page_obj': page_obj,
        'unique_oems': sorted(oem_names_set)
    })


from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from core.models import UploadMetadata
from accounts.models import Provider
from django.db import connection

@login_required
def user_generation_info(request):
    user = request.user.username  # logged-in user
    client_data = []

    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        all_tables = [row[0] for row in cursor.fetchall()]

    for table in all_tables:
        if table.startswith(user + "_"):  # ✅ only take current user's tables
            parts = table.split("_")
            if len(parts) >= 3:
                provider_slug = "_".join(parts[1:-1])
                energy_type_slug = parts[-1]

                provider_name = provider_slug.replace("_", " ").title()
                firm_name = user.replace("_", " ").title()

                try:
                    metadata = UploadMetadata.objects.get(table_name=table)
                    last_modified = metadata.last_modified.strftime('%a, %d %b %Y %H:%M:%S GMT')
                except UploadMetadata.DoesNotExist:
                    last_modified = "N/A"

                client_data.append({
                    "provider": provider_name,
                    "firm": firm_name,
                    "last_modified": last_modified
                })

    return render(request, "profile_info_user.html", {
        "client_data": client_data
    })


from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.db.models import Count, Sum


from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.db.models import Count
from django.contrib.auth.models import User
from accounts.models import UserProfile, EnergyType, Provider
import json

import json
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.db.models import Count, DateField
from django.db.models.functions import TruncMonth
from django.contrib.auth.models import User
from accounts.models import UserProfile, EnergyType, Provider


from django.shortcuts import render
from django.contrib.auth.models import User
from django.db.models import Count
from django.utils.timezone import now
import json
import datetime
from collections import Counter
from calendar import month_abbr

from django.shortcuts import render
from django.contrib.auth.models import User
from django.db.models import Count
from django.utils.timezone import now
import datetime
import json
from collections import Counter

from accounts.models import UserProfile, EnergyType, Provider  # make sure imports are correct

from django.shortcuts import render
from django.contrib.auth.models import User
from django.db.models import Count
from django.utils.timezone import now
import datetime
import json
from collections import defaultdict, Counter

from accounts.models import UserProfile, EnergyType, Provider  # ✅ correct imports


def tracking_dashboard(request):
    # --- Customer stats ---
    total_customers = UserProfile.objects.count()
    active_customers = User.objects.filter(is_active=True).count()
    inactive_customers = User.objects.filter(is_active=False).count()

    # --- Energy stats ---
    total_energy = EnergyType.objects.count()   # ✅ only count energy types
    energy_data = (
        EnergyType.objects.annotate(total=Count("userprofile"))
        .values("name", "total")
    )
    energy_labels = [e["name"] for e in energy_data]
    energy_values = [e["total"] for e in energy_data]

    # --- Provider stats ---
    total_providers = Provider.objects.count()

    # --- User Registrations (last 6 months, grouped by username) ---
    today = now().date()
    six_months_ago = today - datetime.timedelta(days=180)
    users = User.objects.filter(date_joined__gte=six_months_ago)

    # labels: last 6 months
    months = [(today - datetime.timedelta(days=i * 30)).strftime("%b %Y") for i in range(6, -1, -1)]

    # dict to hold {username: [0,0,0...]}
    user_data = defaultdict(lambda: [0] * len(months))

    for user in users:
        month_label = user.date_joined.strftime("%b %Y")
        if month_label in months:
            idx = months.index(month_label)
            user_data[user.username][idx] += 1

    # build datasets (one per user)
    colors = [
        "#36A2EB", "#FF6384", "#4BC0C0", "#9966FF", "#FF9F40",
        "#28a745", "#e83e8c", "#20c997", "#6f42c1", "#fd7e14"
    ]
    datasets = []
    for i, (username, values) in enumerate(user_data.items()):
        datasets.append({
            "label": username,
            "data": values,
            "borderColor": colors[i % len(colors)],
            "backgroundColor": colors[i % len(colors)] + "33",  # semi-transparent
            "fill": True,
            "tension": 0.3,
            "pointRadius": 5,
            "pointHoverRadius": 8
        })

    context = {
        "total_customers": total_customers,
        "active_customers": active_customers,
        "inactive_customers": inactive_customers,
        "total_energy": total_energy,
        "energy_labels": json.dumps(energy_labels),
        "energy_values": json.dumps(energy_values),
        "total_providers": total_providers,
        "registration_labels": json.dumps(months),
        "registration_datasets": json.dumps(datasets),  # ✅ send multiple datasets
    }
    return render(request, "tracking_dashboard.html", context)
