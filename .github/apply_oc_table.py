#!/usr/bin/env python3
"""
Raise the top-end CPU/GPU OPP steps on this MT6765 tree from the stock
"C62" bin ceiling up to the real, MediaTek-authored "SB"/"MT6762D" bin
values found elsewhere in this same kernel source.

Why this is safe-ish to do as a straight #define swap:
- Across every bin in mtk_cpufreq_opp_table.h (FY/SB/C65T/C65/C62...),
  the bottom 8 OPP steps (big: <=1750MHz, little: <=1050MHz) are
  byte-for-byte identical. Only the top 8 steps differ per bin.
- So swapping just the top 8 FREQ+VOLT defines of the C62 (our bin)
  table for the SB bin's top 8 FREQ+VOLT defines is a clean,
  self-consistent substitution -- not an invented table.
- For the GPU, segment2 (our GPU segment) tops out at 650000 KHz @
  80000 (0.80V). Segment4 (MT6762D bin) already runs 730000 KHz at
  that exact same 80000 voltage, on the same silicon family. So we
  raise FREQ0 only and leave the proven voltage alone.

This does NOT change which bin/segment your chip is detected as
(leaves _mt_cpufreq_get_cpu_level()/efuse segment logic untouched), so
power-leakage/EEM/PMIC calibration tied to your real bin stays intact.
It only raises the ceiling of the table your own bin already uses.

These are still new, untested operating points for YOUR specific chip.
Treat every step above the old stock ceiling (2001000 Big /
1500000 Little / 650000 GPU) as unverified until you've tested it.
"""
import re
import sys

CPU_OPP = "drivers/misc/mediatek/base/power/cpufreq_v1/src/mach/mt6765/mtk_cpufreq_opp_table.h"
GPU_CORE = "drivers/misc/mediatek/base/power/mt6765/mtk_gpufreq_core.h"

# (old_define_line_regex, new_value) pairs: C62 -> SB, top 8 steps only.
CPU_SWAPS = [
    # Big cluster (L) frequency, C62 top-8 -> SB top-8
    (r"#define CPU_DVFS_FREQ0_L_C62\s+2001000", "#define CPU_DVFS_FREQ0_L_C62    2501000"),
    (r"#define CPU_DVFS_FREQ1_L_C62\s+1961000", "#define CPU_DVFS_FREQ1_L_C62    2397000"),
    (r"#define CPU_DVFS_FREQ2_L_C62\s+1927000", "#define CPU_DVFS_FREQ2_L_C62    2294000"),
    (r"#define CPU_DVFS_FREQ3_L_C62\s+1897000", "#define CPU_DVFS_FREQ3_L_C62    2191000"),
    (r"#define CPU_DVFS_FREQ4_L_C62\s+1868000", "#define CPU_DVFS_FREQ4_L_C62    2103000"),
    (r"#define CPU_DVFS_FREQ5_L_C62\s+1838000", "#define CPU_DVFS_FREQ5_L_C62    2015000"),
    (r"#define CPU_DVFS_FREQ6_L_C62\s+1809000", "#define CPU_DVFS_FREQ6_L_C62    1926000"),
    (r"#define CPU_DVFS_FREQ7_L_C62\s+1779000", "#define CPU_DVFS_FREQ7_L_C62    1838000"),
    # Big cluster (L) voltage, C62 top-8 -> SB top-8 (10uV units)
    (r"#define CPU_DVFS_VOLT0_VPROC_L_C62\s+111875", "#define CPU_DVFS_VOLT0_VPROC_L_C62    112000"),  # literal MAX_VPROC_VOLT, still in-spec
    (r"#define CPU_DVFS_VOLT1_VPROC_L_C62\s+106875", "#define CPU_DVFS_VOLT1_VPROC_L_C62    107500"),
    (r"#define CPU_DVFS_VOLT2_VPROC_L_C62\s+102500", "#define CPU_DVFS_VOLT2_VPROC_L_C62    103125"),
    (r"#define CPU_DVFS_VOLT3_VPROC_L_C62\s+98750",  "#define CPU_DVFS_VOLT3_VPROC_L_C62     98750"),
    (r"#define CPU_DVFS_VOLT4_VPROC_L_C62\s+95000",  "#define CPU_DVFS_VOLT4_VPROC_L_C62     95000"),
    (r"#define CPU_DVFS_VOLT5_VPROC_L_C62\s+91250",  "#define CPU_DVFS_VOLT5_VPROC_L_C62     91250"),
    (r"#define CPU_DVFS_VOLT6_VPROC_L_C62\s+87500",  "#define CPU_DVFS_VOLT6_VPROC_L_C62     87500"),
    (r"#define CPU_DVFS_VOLT7_VPROC_L_C62\s+83750",  "#define CPU_DVFS_VOLT7_VPROC_L_C62     83750"),

    # Little cluster (LL) frequency, C62 top-8 -> SB top-8
    (r"#define CPU_DVFS_FREQ0_LL_C62\s+1500000", "#define CPU_DVFS_FREQ0_LL_C62    1901000"),
    (r"#define CPU_DVFS_FREQ1_LL_C62\s+1429000", "#define CPU_DVFS_FREQ1_LL_C62    1784000"),
    (r"#define CPU_DVFS_FREQ2_LL_C62\s+1367000", "#define CPU_DVFS_FREQ2_LL_C62    1667000"),
    (r"#define CPU_DVFS_FREQ3_LL_C62\s+1314000", "#define CPU_DVFS_FREQ3_LL_C62    1550000"),
    (r"#define CPU_DVFS_FREQ4_LL_C62\s+1261000", "#define CPU_DVFS_FREQ4_LL_C62    1450000"),
    (r"#define CPU_DVFS_FREQ5_LL_C62\s+1208000", "#define CPU_DVFS_FREQ5_LL_C62    1350000"),
    (r"#define CPU_DVFS_FREQ6_LL_C62\s+1155000", "#define CPU_DVFS_FREQ6_LL_C62    1250000"),
    (r"#define CPU_DVFS_FREQ7_LL_C62\s+1102000", "#define CPU_DVFS_FREQ7_LL_C62    1150000"),
    # Little cluster (LL) voltage, C62 top-8 -> SB top-8
    (r"#define CPU_DVFS_VOLT0_VPROC_LL_C62\s+111875", "#define CPU_DVFS_VOLT0_VPROC_LL_C62    112000"),  # literal MAX_VPROC_VOLT, still in-spec
    (r"#define CPU_DVFS_VOLT1_VPROC_LL_C62\s+106875", "#define CPU_DVFS_VOLT1_VPROC_LL_C62    107500"),
    (r"#define CPU_DVFS_VOLT2_VPROC_LL_C62\s+102500", "#define CPU_DVFS_VOLT2_VPROC_LL_C62    103125"),
    (r"#define CPU_DVFS_VOLT3_VPROC_LL_C62\s+98750",  "#define CPU_DVFS_VOLT3_VPROC_LL_C62     98750"),
    (r"#define CPU_DVFS_VOLT4_VPROC_LL_C62\s+95000",  "#define CPU_DVFS_VOLT4_VPROC_LL_C62     95000"),
    (r"#define CPU_DVFS_VOLT5_VPROC_LL_C62\s+91250",  "#define CPU_DVFS_VOLT5_VPROC_LL_C62     91250"),
    (r"#define CPU_DVFS_VOLT6_VPROC_LL_C62\s+87500",  "#define CPU_DVFS_VOLT6_VPROC_LL_C62     87500"),
    (r"#define CPU_DVFS_VOLT7_VPROC_LL_C62\s+83750",  "#define CPU_DVFS_VOLT7_VPROC_LL_C62     83750"),
]

# GPU bump RESTORED: the earlier "730MHz crashes 8 Ball Pool online" data
# point turned out to be a false lead -- the same crash reproduces
# identically at stock 650MHz with zero GPU OC, so it's unrelated to this
# frequency (likely an ad-SDK/app-side issue instead). No real evidence
# 730MHz is unstable on this unit remains; VGPU_MAX_VOLT (0.80V) is still
# the hard ceiling for the whole chip family, so 730MHz runs at the same
# max voltage as 650MHz -- same risk class as before, just not contradicted
# by evidence anymore. Still worth testing in isolation (a GPU benchmark/
# stress app, away from 8 Ball Pool's online+ads path) to get a clean signal.
GPU_SWAPS = [
    (r"#define SEG2_GPU_DVFS_FREQ0\s+\(650000\)", "#define SEG2_GPU_DVFS_FREQ0\t\t\t(680000)"),
]


def apply_swaps(path, swaps):
    if not swaps:
        print(f"Skipping {path}: no swaps defined (GPU OC reverted)")
        return
    with open(path, "r") as f:
        text = f.read()
    for pattern, replacement in swaps:
        new_text, n = re.subn(pattern, replacement, text, count=1)
        if n != 1:
            print(f"ERROR: pattern not found (expected exactly 1 match): {pattern}", file=sys.stderr)
            sys.exit(1)
        text = new_text
    with open(path, "w") as f:
        f.write(text)
    print(f"Patched {path}: {len(swaps)} defines updated")


apply_swaps(CPU_OPP, CPU_SWAPS)
apply_swaps(GPU_CORE, GPU_SWAPS)
print("OC ceiling applied: Big -> 2501MHz @ 1.12V, Little -> 1901MHz @ 1.12V, GPU -> 680MHz (table ceiling only; FKM still controls what you actually run).")
