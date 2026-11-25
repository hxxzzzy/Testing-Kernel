#!/usr/bin/env python3
"""
I/O scheduler + GPU DVFS responsiveness tweaks, aimed at the stutter
pattern reported on this device (weak eMMC + sluggish GPU ramp-up),
NOT at raw clock ceilings (that's apply_oc_table.py).

1. I/O scheduler: flip the compiled-in default from CFQ (fairness-
   focused, designed with rotational disks in mind, more per-request
   overhead) to deadline (simpler, lower overhead, more predictable
   latency -- generally a better fit for flash/eMMC than CFQ).
   This only changes the DEFAULT; CFQ/noop stay compiled in and
   selectable at runtime via /sys/block/<dev>/queue/scheduler.

2. GPU DVFS margin: GED's governor keeps an extra "margin" of headroom
   before it commits to bumping the GPU to a higher OPP step. Smaller
   margin = it commits to the higher step sooner = less visible lag
   when a scene suddenly gets heavier (e.g. a TikTok video starting to
   decode/composite). Lowering these two defaults makes that reaction
   faster. This is a tradeoff: a smaller margin means less buffer
   against committing to a bump that then isn't needed, so slightly
   less headroom for power efficiency in exchange for responsiveness.
"""
import re
import sys

DEFCONFIG = "arch/arm64/configs/certus_defconfig"
GED_DVFS = "drivers/misc/mediatek/gpu/ged/src/ged_dvfs.c"

with open(DEFCONFIG, "a") as f:
    f.write(
        "\nCONFIG_IOSCHED_DEADLINE=y\nCONFIG_DEFAULT_DEADLINE=y\n"
        "\n# BBR congestion control: better suited than cubic to a lossy/"
        "variable 2.4GHz-only wifi link; requires fq pacing qdisc.\n"
        "CONFIG_TCP_CONG_BBR=y\nCONFIG_NET_SCH_FQ=y\nCONFIG_DEFAULT_BBR=y\n"
        'CONFIG_DEFAULT_TCP_CONG="bbr"\n'
    )
print(f"Appended I/O scheduler + BBR/fq config to {DEFCONFIG}")

with open(GED_DVFS, "r") as f:
    text = f.read()

swaps = [
    (r"#define GED_DVFS_TIMER_BASED_DVFS_MARGIN 30",
     "#define GED_DVFS_TIMER_BASED_DVFS_MARGIN 15"),
    (r"#define DEFAULT_DVFS_MARGIN 100 /\* 10% margin \*/",
     "#define DEFAULT_DVFS_MARGIN 50 /* 5% margin -- tuned faster ramp */"),
]
for pattern, replacement in swaps:
    text, n = re.subn(pattern, replacement, text, count=1)
    if n != 1:
        print(f"ERROR: pattern not found: {pattern}", file=sys.stderr)
        sys.exit(1)

with open(GED_DVFS, "w") as f:
    f.write(text)
print(f"Patched {GED_DVFS}: GPU DVFS margin defaults lowered (30->15, 100->50)")
