from django.shortcuts import render

# Create your views here.

def open_access(request):
    return render(request,'open_access.html')



from django.shortcuts import render

def calculate_bills(params):
    """
    params is a dict of floats taken from the form.
    Returns a dict with all calculated values.
    """

    # ----- Common inputs -----
    total_units = params["total_units"]            # kWh
    contract_demand = params["contract_demand"]    # kVA
    billed_demand = params["billed_demand"]        # kVA used for charges
    demand_rate = params["demand_rate"]            # Rs/kVA

    wheeling_rate = params["wheeling_rate"]        # Rs/kWh
    energy_rate = params["energy_rate"]            # Rs/kWh
    tod_c_rate = params["tod_c_rate"]              # Rs/kWh (usually -3.5)
    tod_d_rate = params["tod_d_rate"]              # Rs/kWh (usually +3.5)
    tod_c_units = params["tod_c_units"]            # kWh in Zone C
    tod_d_units = params["tod_d_units"]            # kWh in Zone D

    fac_rate = params["fac_rate"]                  # Rs/kWh
    duty_percent = params["duty_percent"] / 100.0  # to fraction
    tax_sale_rate = params["tax_sale_rate"]        # Rs/kWh
    incremental_rebate = params["incremental_rebate"]  # Rs (negative)
    prompt_discount = params["prompt_discount"]        # Rs (negative)

    # ----- OA related inputs -----
    oa_percent = params["oa_percent"] / 100.0      # fraction of units on OA
    oa_energy_rate = params["oa_energy_rate"]      # Rs/kWh
    oa_transmission_rate = params["oa_transmission_rate"]  # Rs/kWh
    oa_wheeling_rate = params["oa_wheeling_rate"]  # Rs/kWh
    oa_loss_rate = params["oa_loss_rate"]          # Rs/kWh
    oa_sldc_fixed = params["oa_sldc_fixed"]        # Rs fixed per month

    # =======================
    # 1) ONLY MSEDCL BILL
    # =======================

    demand_charges_only = billed_demand * demand_rate

    wheeling_only = total_units * wheeling_rate
    energy_only = total_units * energy_rate

    tod_c_only = tod_c_units * tod_c_rate
    tod_d_only = tod_d_units * tod_d_rate
    tod_total_only = tod_c_only + tod_d_only

    fac_only = total_units * fac_rate

    duty_base_only = energy_only + wheeling_only + fac_only + tod_total_only

    duty_only = duty_base_only * duty_percent

    tax_sale_only = total_units * tax_sale_rate

    total_only_msedcl = (
        demand_charges_only
        + wheeling_only
        + energy_only
        + tod_total_only
        + fac_only
        + duty_only
        + tax_sale_only
        + incremental_rebate
        + prompt_discount
    )

    unit_rate_only = total_only_msedcl / total_units if total_units else 0

    # =======================
    # 2) AFTER OPEN ACCESS
    # =======================

    oa_units = total_units * oa_percent
    msedcl_units_after = total_units - oa_units

    # scale TOD units in same ratio
    scale = msedcl_units_after / total_units if total_units else 0
    tod_c_units_after = tod_c_units * scale
    tod_d_units_after = tod_d_units * scale

    # MSEDCL portion after OA (same formulas but with reduced units)
    demand_charges_after = demand_charges_only  # usually demand is same
    wheeling_after = msedcl_units_after * wheeling_rate
    energy_after = msedcl_units_after * energy_rate

    tod_c_after = tod_c_units_after * tod_c_rate
    tod_d_after = tod_d_units_after * tod_d_rate
    tod_total_after = tod_c_after + tod_d_after

    fac_after = msedcl_units_after * fac_rate

    duty_base_after = energy_after + wheeling_after + fac_after + tod_total_after

    duty_after = duty_base_after * duty_percent

    tax_sale_after = msedcl_units_after * tax_sale_rate

    total_msedcl_after = (
        demand_charges_after
        + wheeling_after
        + energy_after
        + tod_total_after
        + fac_after
        + duty_after
        + tax_sale_after
        + incremental_rebate * scale
        + prompt_discount * scale
    )

    # OA charges
    oa_energy_cost = oa_units * oa_energy_rate
    oa_transmission = oa_units * oa_transmission_rate
    oa_wheeling = oa_units * oa_wheeling_rate
    oa_losses = oa_units * oa_loss_rate

    total_oa_charges = (
        oa_energy_cost
        + oa_transmission
        + oa_wheeling
        + oa_losses
        + oa_sldc_fixed
    )

    total_after_oa = total_msedcl_after + total_oa_charges
    unit_rate_after = total_after_oa / total_units if total_units else 0

    savings = total_only_msedcl - total_after_oa
    per_unit_saving = savings / total_units if total_units else 0
    monthly_saving = savings
    yearly_saving = savings * 12

    return {
        "total_only_msedcl": round(total_only_msedcl, 2),
        "unit_rate_only": round(unit_rate_only, 2),
        "total_msedcl_after": round(total_msedcl_after, 2),
        "total_oa_charges": round(total_oa_charges, 2),
        "total_after_oa": round(total_after_oa, 2),
        "unit_rate_after": round(unit_rate_after, 2),
        "savings": round(savings, 2),
        "per_unit_saving": round(per_unit_saving, 2),
        "monthly_saving": round(monthly_saving, 2),
        "yearly_saving": round(yearly_saving, 2),
        "oa_units": round(oa_units, 0),
        "msedcl_units_after": round(msedcl_units_after, 0),
    }


def calculator_view(request):
    # Default values loosely based on your Phoenix Studios case
    default_data = {
        "total_units": 50728,
        "contract_demand": 356,
        "billed_demand": 267,
        "demand_rate": 600,
        "wheeling_rate": 0.74,
        "energy_rate": 14.03,
        "tod_c_rate": -3.5,
        "tod_d_rate": 3.5,
        "tod_c_units": 18868,
        "tod_d_units": 21337,
        "fac_rate": 0.50,
        "duty_percent": 21.0,
        "tax_sale_rate": 0.19,
        "incremental_rebate": -9657,
        "prompt_discount": -9085,
        "oa_percent": 58.0,
        "oa_energy_rate": 4.5,       # adjust to your OA energy price
        "oa_transmission_rate": 1.14,
        "oa_wheeling_rate": 0.74,
        "oa_loss_rate": 0.59,
        "oa_sldc_fixed": 15450,
    }

    context = {"input": default_data, "result": None}

    if request.method == "POST":
        # Read form data, convert to float
        data = {}
        for key in default_data.keys():
            value = request.POST.get(key, "")
            try:
                data[key] = float(value)
            except ValueError:
                data[key] = default_data[key]
        context["input"] = data
        context["result"] = calculate_bills(data)

    return render(request, "calculator.html", context)
