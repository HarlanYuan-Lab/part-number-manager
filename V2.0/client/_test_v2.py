"""Headless verification of the V2 data layer against the real server."""
import os, sys, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from part_manager import config
from part_manager.db import ConnectionManager
from part_manager.services import ProjectService, PartNumberService
from part_manager.exporter import export_parts_to_excel

ok = True
def check(label, cond, extra=""):
    global ok
    print(("PASS" if cond else "FAIL"), "-", label, extra)
    if not cond:
        ok = False

mgr = ConnectionManager()
try:
    mgr.connect(config.DEFAULT_HOST, config.DEFAULT_PORT, config.DEFAULT_DB,
                config.DEFAULT_USER, config.DEFAULT_PASSWORD)
    check("connect + schema", mgr.connected)

    ps = ProjectService(mgr)

    # cleanup any leftover test project
    existing = ps.get_by_name("ZZ_V2TEST")
    if existing:
        ps.delete(existing.id)

    proj = ps.create("ZZ_V2TEST", {"Assembly":"8","Part":"2","Standard":"9"})
    check("create project", proj is not None, f"id={proj.id}")
    check("project prefixes", proj.prefixes == {"Assembly":"8","Part":"2","Standard":"9"})

    psv = PartNumberService(mgr, proj)

    n1 = psv.create("Bracket", "Assembly")
    check("assembly first = 800001", n1 == "800001", n1)
    n2 = psv.create("Screw", "Part")
    check("part first = 200001", n2 == "200001", n2)
    n3 = psv.create("Washer", "Standard")
    check("standard first = 900001", n3 == "900001", n3)
    n4 = psv.create("Cover", "Assembly")
    check("assembly second = 800002", n4 == "800002", n4)

    peek = psv.peek_number("Assembly")
    check("peek next assembly = 800003", peek == "800003", peek)

    parts = psv.search("Bracket")
    check("search by name finds 1", len(parts) == 1)
    parts = psv.search("800002")
    check("search by number finds cover", len(parts) == 1 and parts[0].part_name == "Cover")
    check("count = 4", psv.count() == 4, psv.count())

    # update basic fields
    psv.update("800001", "Bracket-New", "Steel", "desc updated")
    p = psv.get("800001")
    check("update fields", p.part_name == "Bracket-New" and p.material == "Steel")

    # renumber 800002 -> 800005 (currently free)
    final = psv.update_part("800002", "800005", "Cover", "Al", "x", "Assembly")
    check("renumber to 800005", final == "800005", final)
    # same-number self edit keeps its number (no bump)
    final2 = psv.update_part("800005", "800005", "Cover", "Al", "x", "Assembly")
    check("same-number self edit stays", final2 == "800005", final2)
    # renumber 800001 to an occupied number (800005, a different part) -> bump
    final3 = psv.update_part("800001", "800005", "Bracket-New", "Steel", "z", "Assembly")
    check("conflict bumps to 800006", final3 == "800006", final3)

    # delete one and confirm the monotonic counter never reuses freed numbers
    psv.delete("800006")
    check("count after delete = 3", psv.count() == 3, psv.count())
    n5 = psv.create("NewBracket", "Assembly")
    check("counter never reuses freed numbers", n5 == "800007", n5)

    # export
    allp = psv.search("")
    xlsx = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_v2test.xlsx")
    export_parts_to_excel(allp, xlsx, proj.name)
    check("export writes xlsx", os.path.exists(xlsx) and os.path.getsize(xlsx) > 0)
    if os.path.exists(xlsx):
        os.remove(xlsx)

    # cleanup project
    ps.delete(proj.id)
    check("delete project", ps.get_by_name("ZZ_V2TEST") is None)

    mgr.close()
    print("RESULT:", "ALL OK" if ok else "FAILURES PRESENT")
except Exception:
    traceback.print_exc()
    try:
        mgr.close()
    except Exception:
        pass
    sys.exit(1)

sys.exit(0 if ok else 2)
