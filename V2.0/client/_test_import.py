"""Verify V1.0 -> server import and server -> V1.0 export against 1000.db."""
import os, sys, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from part_manager import config
from part_manager.db import ConnectionManager
from part_manager.services import ProjectService, PartNumberService
from part_manager import local_transfer

# NOTE (open-source): point this at an existing V1.0 database to test migration.
# Example: V1 = r"E:\YourPath\1000.db"
V1 = r"E:\YourPath\1000.db"
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
    ps = ProjectService(mgr)

    # clean leftovers
    for n in ("ZZ_IMP",):
        ex = ps.get_by_name(n)
        if ex:
            ps.delete(ex.id)

    data = local_transfer.read_v1_db(V1)
    check("read name=1000", data["name"] == "1000", data["name"])
    check("read 6 parts", len(data["parts"]) == 6, len(data["parts"]))
    check("read prefixes", data["prefixes"] == {"Assembly":"8","Part":"2","Standard":"9"})

    proj, count, seqs = local_transfer.import_v1_to_server(mgr, ps, V1,
                                                           project_name="ZZ_IMP")
    check("import count=6", count == 6, count)
    check("import seqs", seqs == {"Assembly":800002,"Part":200003,"Standard":900001}, seqs)
    check("project prefixes", proj.prefixes == {"Assembly":"8","Part":"2","Standard":"9"})

    # numbering must continue from last numbers (no reuse)
    psv = PartNumberService(mgr, proj)
    check("next assembly=800003", psv.create("N","Assembly") == "800003")
    check("next part=200004", psv.create("N","Part") == "200004")
    check("next standard=900002", psv.create("N","Standard") == "900002")

    # duplicate import rejected
    try:
        local_transfer.import_v1_to_server(mgr, ps, V1, project_name="ZZ_IMP")
        check("duplicate import rejected", False)
    except ValueError:
        check("duplicate import rejected", True)

    # export round-trip
    parts = psv.search("")
    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_export_test.db")
    local_transfer.export_project_to_v1(mgr, proj, parts, dest)
    back = local_transfer.read_v1_db(dest)
    check("export name", back["name"] == "ZZ_IMP", back["name"])
    check("export part count=9", len(back["parts"]) == 9, len(back["parts"]))
    check("export seqs advanced", back["seqs"]["Assembly"] == "800003", back["seqs"])
    check("export readable as V1 (tables)", True)
    if os.path.exists(dest):
        os.remove(dest)

    ps.delete(proj.id)
    check("cleanup import project", ps.get_by_name("ZZ_IMP") is None)
    mgr.close()
    print("RESULT:", "ALL OK" if ok else "FAILURES")
except Exception:
    traceback.print_exc()
    try:
        mgr.close()
    except Exception:
        pass
    sys.exit(1)
sys.exit(0 if ok else 2)
