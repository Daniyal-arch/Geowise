"""
Test filtering GFW data by loss driver to match PRODES deforestation
"""

import requests

GFW_API_KEY = "8e5b3b69-fa31-4eef-af79-eec9674c7014"
BASE_URL = "https://data-api.globalforestwatch.org"

headers = {
    "x-api-key": GFW_API_KEY,
    "Content-Type": "application/json"
}

print("="*70)
print("🔍 TESTING GFW LOSS DRIVERS FILTER")
print("="*70)

url = f"{BASE_URL}/dataset/gadm__tcl__iso_change/latest/query/json"

# Test 1: See what loss drivers exist
print("\nTest 1: What loss drivers are recorded for Brazil 2019?")
print("-"*70)

sql1 = """
SELECT 
    v20250515.wri_google_tree_cover_loss_drivers__category as driver,
    COUNT(*) as row_count,
    SUM(v20250515.umd_tree_cover_loss__ha) as total_loss_ha
FROM v20250515
WHERE v20250515.iso = 'BRA'
AND v20250515.umd_tree_cover_loss__year = 2019
GROUP BY v20250515.wri_google_tree_cover_loss_drivers__category
ORDER BY total_loss_ha DESC
"""

response1 = requests.post(url, headers=headers, json={"sql": sql1.strip()}, timeout=30)

if response1.status_code == 200:
    data1 = response1.json().get("data", [])
    print(f"\n✅ Found {len(data1)} loss driver categories:")
    print("\nDriver Category | Rows | Loss (ha)")
    print("-" * 70)
    
    for row in data1:
        driver = row.get('driver') or 'NULL/Unknown'
        count = int(row.get('row_count', 0))
        loss = float(row.get('total_loss_ha', 0))
        print(f"{driver:40} | {count:6,} | {loss:15,.2f}")
else:
    print(f"❌ Error: {response1.status_code}")
    print(response1.text[:300])

# Test 2: Filter for commodity-driven deforestation
print("\n" + "="*70)
print("Test 2: Filter by 'Commodity driven deforestation'")
print("-"*70)

sql2 = """
SELECT 
    SUM(v20250515.umd_tree_cover_loss__ha) as total_loss_ha,
    COUNT(*) as row_count
FROM v20250515
WHERE v20250515.iso = 'BRA'
AND v20250515.umd_tree_cover_loss__year = 2019
AND v20250515.wri_google_tree_cover_loss_drivers__category = 'Commodity driven deforestation'
"""

response2 = requests.post(url, headers=headers, json={"sql": sql2.strip()}, timeout=30)

if response2.status_code == 200:
    data2 = response2.json().get("data", [])
    if data2:
        row = data2[0]
        loss = float(row.get('total_loss_ha', 0))
        count = int(row.get('row_count', 0))
        
        print(f"✅ Commodity-driven deforestation only:")
        print(f"   Loss: {loss:,.2f} ha")
        print(f"   Rows: {count:,}")
        
        expected = 1011100
        ratio = loss / expected if expected > 0 else 0
        print(f"\n   Expected (PRODES): {expected:,.0f} ha")
        print(f"   Ratio: {ratio:.2f}x")
        
        if 0.8 < ratio < 1.2:
            print(f"   ✅✅✅ VERY CLOSE! This filter works!")
        elif 0.5 < ratio < 2.0:
            print(f"   ⚠️  Reasonably close")
        else:
            print(f"   ❌ Still quite different")

# Test 3: Exclude certain drivers
print("\n" + "="*70)
print("Test 3: Exclude Wildfires (to isolate human deforestation)")
print("-"*70)

sql3 = """
SELECT 
    SUM(v20250515.umd_tree_cover_loss__ha) as total_loss_ha,
    COUNT(*) as row_count
FROM v20250515
WHERE v20250515.iso = 'BRA'
AND v20250515.umd_tree_cover_loss__year = 2019
AND v20250515.wri_google_tree_cover_loss_drivers__category NOT IN ('Wildfire')
"""

response3 = requests.post(url, headers=headers, json={"sql": sql3.strip()}, timeout=30)

if response3.status_code == 200:
    data3 = response3.json().get("data", [])
    if data3:
        row = data3[0]
        loss = float(row.get('total_loss_ha', 0))
        count = int(row.get('row_count', 0))
        
        print(f"✅ Excluding wildfires:")
        print(f"   Loss: {loss:,.2f} ha")
        print(f"   Rows: {count:,}")
        
        expected = 1011100
        ratio = loss / expected if expected > 0 else 0
        print(f"\n   Expected (PRODES): {expected:,.0f} ha")
        print(f"   Ratio: {ratio:.2f}x")

print("\n" + "="*70)
print("ANALYSIS COMPLETE")
print("="*70)
print("\n💡 KEY INSIGHT:")
print("The GFW dataset includes ALL tree cover loss (wildfires, logging, etc.)")
print("PRODES measures only anthropogenic deforestation.")
print("Filtering by driver category can align the datasets better.")
print("="*70)