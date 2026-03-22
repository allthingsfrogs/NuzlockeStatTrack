import math
import pandas as pd
from pathlib import Path

PROJECT_ROOT_DIR = Path(__file__).parent.parent
TYPES_BY_SPECIES = next(PROJECT_ROOT_DIR.rglob("types_by_species.csv"), None)

# ── Experience formula per growth rate ───────────────────────────────────────
# Formulas from Bulbapedia: https://bulbapedia.bulbagarden.net/wiki/Experience
# Each function returns the total exp required to reach a given level

def _exp_medium_fast(n):
    return n ** 3

def _exp_medium_slow(n):
    return int(6/5 * n**3 - 15 * n**2 + 100 * n - 140)

def _exp_fast(n):
    return int(4 * n**3 / 5)

def _exp_slow(n):
    return int(5 * n**3 / 4)

def _exp_erratic(n):
    if n <= 50:
        return int(n**3 * (100 - n) / 50)
    elif n <= 68:
        return int(n**3 * (150 - n) / 100)
    elif n <= 98:
        return int(n**3 * ((1911 - 10*n) / 3) / 500)
    else:
        return int(n**3 * (160 - n) / 100)

def _exp_fluctuating(n):
    if n <= 15:
        return int(n**3 * (((n + 1) / 3) + 24) / 50)
    elif n <= 35:
        return int(n**3 * (n + 14) / 50)
    else:
        return int(n**3 * ((n / 2) + 32) / 50)

# ── Build lookup tables ───────────────────────────────────────────────────────
def _build_table(formula):
    """Build a 101-entry list where index N = exp required for level N."""
    table = [0] * 101
    for level in range(2, 101):
        table[level] = max(0, formula(level))
    return table

EXP_TABLE = {
    'Medium Fast':  _build_table(_exp_medium_fast),
    'Medium Slow':  _build_table(_exp_medium_slow),
    'Fast':         _build_table(_exp_fast),
    'Slow':         _build_table(_exp_slow),
    'Erratic':      _build_table(_exp_erratic),
    'Fluctuating':  _build_table(_exp_fluctuating),
}

# ── Level lookup ──────────────────────────────────────────────────────────────
def exp_to_level(exp, growth_rate):
    """Convert raw experience points to level using the species growth rate."""
    table = EXP_TABLE.get(growth_rate, EXP_TABLE['Medium Fast'])
    for level in range(100, 0, -1):
        if exp >= table[level]:
            return level
    return 1

# ── Growth rate lookup ────────────────────────────────────────────────────────
def get_growth_rate(species):
    """Look up a species growth rate from types_by_species.csv."""
    try:
        df = pd.read_csv(TYPES_BY_SPECIES)
        matches = df[df['species'] == species]
        if matches.empty:
            return 'Medium Fast'  # safe default
        return matches.iloc[0]['growth_rate']
    except Exception:
        return 'Medium Fast'  # safe default if file missing


# ── Sanity check ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Verify level 100 totals match known values
    expected = {
        'Medium Fast':  1_000_000,
        'Medium Slow':  1_059_860,
        'Fast':           800_000,
        'Slow':         1_250_000,
        'Erratic':        600_000,
        'Fluctuating':  1_640_000,
    }
    for rate, exp in expected.items():
        actual = EXP_TABLE[rate][100]
        status = "OK" if actual == exp else "FAIL"
        print(f"{status} {rate}: expected {exp:,}, got {actual:,}")
