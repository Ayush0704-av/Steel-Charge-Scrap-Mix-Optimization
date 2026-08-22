import pandas as pd
from pulp import LpProblem, LpVariable, LpMinimize, lpSum, LpStatus, value

scrap = pd.read_csv("../data/scrap_inventory.csv")
target = pd.read_csv("../data/target_spec.csv").set_index("element")
elements = ["C", "Mn", "Si", "Cu", "Cr", "Ni", "S", "P"]

FURNACE_CAPACITY = 100
MIN_CHARGE = 80

m = LpProblem("Baseline_Sensitivity", LpMinimize)
xv = {row.scrap_id: LpVariable(f"x_{row.scrap_id}", lowBound=0, upBound=row.availability_tons)
      for row in scrap.itertuples()}

m += lpSum(xv[row.scrap_id] * row.cost_per_ton for row in scrap.itertuples())

tw = lpSum(xv[row.scrap_id] for row in scrap.itertuples())
m += tw <= FURNACE_CAPACITY, "Max_Capacity"
m += tw >= MIN_CHARGE, "Min_Charge"

constraint_names = {}
for el in elements:
    el_col = f"{el}_pct"
    weighted_el = lpSum(
        xv[row.scrap_id] * (getattr(row, el_col) / 100) * (row.recovery_rate_pct / 100)
        for row in scrap.itertuples()
    )
    min_pct = target.loc[el, "min_pct"] / 100
    max_pct = target.loc[el, "max_pct"] / 100
    cname_min = f"{el}_min"
    cname_max = f"{el}_max"
    m += weighted_el >= min_pct * tw, cname_min
    m += weighted_el <= max_pct * tw, cname_max

m.solve()
print("Status:", LpStatus[m.status])
print("Total Cost:", value(m.objective))

print("\n--- Shadow Prices (Sensitivity) ---")
rows = []
for name, c in m.constraints.items():
    rows.append({
        "constraint": name,
        "shadow_price": c.pi,
        "slack": c.slack
    })

sens_df = pd.DataFrame(rows)
sens_df.to_csv("../data/sensitivity_analysis.csv", index=False)
print(sens_df.to_string(index=False))
print("\nExported: sensitivity_analysis.csv")