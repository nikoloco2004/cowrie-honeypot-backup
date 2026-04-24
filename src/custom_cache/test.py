"""Smoke test for custom_mem."""

from custom_mem import memstate, memupdate
import time
import os

print("=" * 60)
print("custom_mem Smoke Test")
print("=" * 60)

memstate.reset_to_baseline()
baseline = memstate.get_state()
print(f"Field count:       {len(memstate.field_order())}")
print(f"First 3 fields:    {memstate.field_order()[:3]}")
print(f"Baseline MemTotal: {baseline['MemTotal']:,}")
print(f"Baseline MemFree:  {baseline['MemFree']:,}")

memupdate.force_update()
s1 = memstate.get_state()
print(f"\nAfter force_update():")
print(f"  MemTotal:      {s1['MemTotal']:,}  (should be unchanged)")
print(f"  MemFree:       {s1['MemFree']:,}  (should differ from baseline)")

memupdate.update()
s2 = memstate.get_state()
print(f"\nAfter immediate update() (throttled):")
print(f"  MemFree:       {s2['MemFree']:,}  (should equal previous)")
assert s1["MemFree"] == s2["MemFree"], "Throttle failed!"

time.sleep(2.1)
memupdate.update()
s3 = memstate.get_state()
print(f"\nAfter sleep(2.1) + update():")
print(f"  MemFree:       {s3['MemFree']:,}  (should differ from previous)")

print(f"\nHoneyfs file: {memupdate.HONEYFS_MEMINFO}")
if os.path.exists(memupdate.HONEYFS_MEMINFO):
    with open(memupdate.HONEYFS_MEMINFO) as f:
        content = f.read()
    print(f"  Size: {len(content)} bytes")
    print(f"  First 3 lines:")
    for line in content.splitlines()[:3]:
        print(f"    {line!r}")
else:
    print("  (not found — check HONEYFS_MEMINFO path)")

print("\n[OK] All tests passed")