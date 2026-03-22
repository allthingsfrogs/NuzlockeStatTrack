import struct
from pathlib import Path
import pandas as pd
import os 
from reader_utils import exp_to_level, get_growth_rate

# ── Constants ─────────────────────────────────────────────────────────────────
# HGSS big block starts at 0x0F700
# Box data starts at offset 0x00 within the big block
# Each box is padded to 0x1000 bytes (4096), with 30 pokemon * 136 bytes = 4080 bytes + 16 padding
# 18 boxes total in vanilla HGSS

BIG_BLOCK_1_OFFSET  = 0x0F700
BIG_BLOCK_2_OFFSET  = 0x4F700
BOX_POKEMON_SIZE    = 136
BOX_CAPACITY        = 30
NUM_BOXES           = 18
BOX_PADDED_SIZE     = 0x1000   # each box padded to 4096 bytes

GAME_SAV = os.getenv("SAV")

PROJECT_ROOT_DIR = Path("..")
#SCRIPT_DIR = Path(__file__).parent.parent / 'resources'

#OUTPUT_TXT = "all_pokemon.txt"
OUTPUT_TXT = PROJECT_ROOT_DIR / "showdown" / "all_pokemon.txt"

ABILITIES = next(PROJECT_ROOT_DIR.rglob("abilities.txt"), None)
ITEMS = next(PROJECT_ROOT_DIR.rglob("items.txt"), None)
LOCATIONS = next(PROJECT_ROOT_DIR.rglob("locations.txt"), None)
MOVES = next(PROJECT_ROOT_DIR.rglob("moves.txt"), None)
SPECIES_ABILITIES = next(PROJECT_ROOT_DIR.rglob("species_abilities.csv"), None)
SPECIES = next(PROJECT_ROOT_DIR.rglob("species.txt"), None)
TYPES_BY_SPECIES = next(PROJECT_ROOT_DIR.rglob("types_by_species.csv"), None)



# ── Lookup tables ─────────────────────────────────────────────────────────────
NATURES = [
    'Hardy', 'Lonely', 'Brave', 'Adamant', 'Naughty',
    'Bold', 'Docile', 'Relaxed', 'Impish', 'Lax',
    'Timid', 'Hasty', 'Serious', 'Jolly', 'Naive',
    'Modest', 'Mild', 'Quiet', 'Bashful', 'Rash',
    'Calm', 'Gentle', 'Sassy', 'Careful', 'Quirky'
]

BLOCK_ORDERS = [
    [0,1,2,3],[0,1,3,2],[0,2,1,3],[0,3,2,1],[0,2,3,1],[0,3,1,2],
    [1,0,2,3],[1,0,3,2],[2,1,0,3],[3,1,2,0],[2,1,3,0],[3,1,0,2],
    [1,2,0,3],[1,3,0,2],[2,0,1,3],[3,0,2,1],[2,3,0,1],[3,2,0,1],
    [1,2,3,0],[1,3,2,0],[2,0,3,1],[2,3,1,0],[3,0,1,2],[3,2,1,0],
]

# ── Data loaders ──────────────────────────────────────────────────────────────
def get_species_name(dex_num):
    try:
        with open(SPECIES, 'r') as f:
            names = [line.strip() for line in f]
        return names[dex_num - 1] if 0 < dex_num <= len(names) else f"Unknown({dex_num})"
    except FileNotFoundError:
        return f"Species({dex_num})"

def get_move_name(move_id):
    if move_id == 0:
        return None
    try:
        with open(MOVES, 'r') as f:
            moves = [line.strip() for line in f]
        return moves[move_id - 1] if 0 < move_id <= len(moves) else f"Move({move_id})"
    except FileNotFoundError:
        return f"Move({move_id})"

def get_item_name(item_id):
    if item_id == 0:
        return None
    try:
        with open(ITEMS, 'r') as f:
            items = [line.strip() for line in f]
        return items[item_id - 1] if 0 < item_id <= len(items) else f"Item({item_id})"
    except FileNotFoundError:
        return f"Item({item_id})"

def get_ability_name(ability_id):
    try:
        with open(ABILITIES, 'r') as f:
            abilities = [line.strip() for line in f]
        return abilities[ability_id] if 0 <= ability_id < len(abilities) else f"Ability({ability_id})"
    except FileNotFoundError:
        return f"Ability({ability_id})"

def get_location_name(location_id):
    try:
        with open(LOCATIONS, 'r') as f:
            locations = [line.strip() for line in f]
        return locations[location_id] if 0 <= location_id < len(locations) else f"Location({location_id})"
    except FileNotFoundError:
        return f"Location({location_id})"
    
def get_type(species):
    df = pd.read_csv(TYPES_BY_SPECIES)
    matches = df[df['species'] == species]

    print(f"Looking for: '{species}'")      # what are you searching for?
    print(f"Matches found: {len(matches)}") # is it finding anything?

    row = df[df['species'] == species].iloc[0]
    type1 = row['type1']
    type2 = row['type2'] if pd.notna(row['type2']) else None
    return type1, type2

# ── Gen IV decryption ─────────────────────────────────────────────────────────
def prng_next(seed):
    return (0x41C64E6D * seed + 0x6073) & 0xFFFFFFFF

def decrypt_block_data(data, seed):
    result = bytearray(data)
    state  = seed
    for i in range(0, 128, 2):
        state = prng_next(state)
        key   = (state >> 16) & 0xFFFF
        word  = struct.unpack_from('<H', result, i)[0]
        struct.pack_into('<H', result, i, word ^ key)
    return bytes(result)

def unshuffle_blocks(data, pv):
    shift      = ((pv & 0x3E000) >> 0xD) % 24
    order      = BLOCK_ORDERS[shift]
    blocks     = [data[i*32:(i+1)*32] for i in range(4)]
    unshuffled = [None] * 4
    for dest, src in enumerate(order):
        unshuffled[dest] = blocks[src]
    return b''.join(unshuffled)

GEN4_CHAR_TABLE = {
    0x010A: '0', 0x010B: '1', 0x010C: '2', 0x010D: '3', 0x010E: '4',
    0x010F: '5', 0x0110: '6', 0x0111: '7', 0x0112: '8', 0x0113: '9',
    0x0121: ' ', 0x0122: '!', 0x0123: '?', 0x0124: '.', 0x0125: '-',
    0x012A: 'A', 0x012B: 'B', 0x012C: 'C', 0x012D: 'D', 0x012E: 'E',
    0x012F: 'F', 0x0130: 'G', 0x0131: 'H', 0x0132: 'I', 0x0133: 'J',
    0x0134: 'K', 0x0135: 'L', 0x0136: 'M', 0x0137: 'N', 0x0138: 'O',
    0x0139: 'P', 0x013A: 'Q', 0x013B: "'", 0x013C: 'R', 0x013D: 'S',
    0x013E: 'T', 0x013F: 'U', 0x0140: 'V', 0x0141: 'W', 0x0142: 'X',
    0x0143: 'Y', 0x0144: 'Z',
    0x0145: 'a', 0x0146: 'b', 0x0147: 'c', 0x0148: 'd', 0x0149: 'e',
    0x014A: 'f', 0x014B: 'g', 0x014C: 'h', 0x014D: 'i', 0x014E: 'j',
    0x014F: 'k', 0x0150: 'l', 0x0151: 'm', 0x0152: 'n', 0x0153: 'o',
    0x0154: 'p', 0x0155: 'q', 0x0156: 'r', 0x0157: 's', 0x0158: 't',
    0x0159: 'u', 0x015A: 'v', 0x015B: 'w', 0x015C: 'x', 0x015D: 'y',
    0x015E: 'z',
}

def decode_nickname(raw_bytes):
    """Decode a Gen IV nickname using the proprietary character table."""
    chars = []
    for i in range(0, len(raw_bytes), 2):
        code = struct.unpack_from('<H', raw_bytes, i)[0]
        if code == 0xFFFF or code == 0x0000:
            break
        chars.append(GEN4_CHAR_TABLE.get(code, ''))
    return ''.join(chars).strip()

# ── Pokemon parsing ───────────────────────────────────────────────────────────
def parse_box_pokemon(raw):
    pv       = struct.unpack_from('<I', raw, 0x00)[0]
    checksum = struct.unpack_from('<H', raw, 0x06)[0]

    if pv == 0 and checksum == 0:
        return None

    encrypted_blocks = raw[0x08:0x88]
    decrypted        = decrypt_block_data(encrypted_blocks, checksum)
    unshuffled       = unshuffle_blocks(decrypted, pv)

    # Block A
    dex_num = struct.unpack_from('<H', unshuffled, 0x00)[0]
    held_item  = struct.unpack_from('<H', unshuffled, 0x02)[0]
    ability_id = unshuffled[0x0D]
    ev_hp      = unshuffled[0x10]
    ev_atk     = unshuffled[0x11]
    ev_def     = unshuffled[0x12]
    ev_spe     = unshuffled[0x13]
    ev_spa     = unshuffled[0x14]
    ev_spd     = unshuffled[0x15]

    # Block B
    move1    = struct.unpack_from('<H', unshuffled, 0x20)[0]
    move2    = struct.unpack_from('<H', unshuffled, 0x22)[0]
    move3    = struct.unpack_from('<H', unshuffled, 0x24)[0]
    move4    = struct.unpack_from('<H', unshuffled, 0x26)[0]
    ivs_data = struct.unpack_from('<I', unshuffled, 0x30)[0]
    iv_hp    = ivs_data & 0x1F
    iv_atk   = (ivs_data >> 5) & 0x1F
    iv_def   = (ivs_data >> 10) & 0x1F
    iv_spe   = (ivs_data >> 15) & 0x1F
    iv_spa   = (ivs_data >> 20) & 0x1F
    iv_spd   = (ivs_data >> 25) & 0x1F
    is_egg       = (ivs_data >> 30) & 0x01
    is_nicknamed = (ivs_data >> 31) & 0x01

    # Block C — nickname
    nickname_raw = unshuffled[0x40:0x56]
    nickname     = decode_nickname(nickname_raw) if is_nicknamed else ""

    # Block D — met location
    location_met_id = struct.unpack_from('<H', unshuffled, 0x60)[0]
    location_met    = get_location_name(location_met_id)

    nature  = NATURES[pv % 25]
    species = get_species_name(dex_num)

    # Level from experience points
    exp             = struct.unpack_from('<I', unshuffled, 0x08)[0]
    growth_rate     = get_growth_rate(species)
    exp_level       = exp_to_level(exp, growth_rate)

    # Pokemon's Typing
    type1, type2 = get_type(species)

    return {
        'species':      species,
        'dex_num':      dex_num,
        'nickname':     nickname,
        'exp_level':    exp_level,
        'type1':        type1,
        'type2':        type2,
        'held_item':    get_item_name(held_item),
        'ability':      get_ability_name(ability_id),
        'nature':       nature,
        'is_egg':       is_egg,
        'location_met': location_met,
        'ev_hp': ev_hp, 'ev_atk': ev_atk, 'ev_def': ev_def,
        'ev_spe': ev_spe, 'ev_spa': ev_spa, 'ev_spd': ev_spd,
        'iv_hp': iv_hp, 'iv_atk': iv_atk, 'iv_def': iv_def,
        'iv_spe': iv_spe, 'iv_spa': iv_spa, 'iv_spd': iv_spd,
        'moves': [get_move_name(m) for m in [move1, move2, move3, move4]],
        'personality_value' : pv,
        'growth_rate' : growth_rate,
    }

# ── Save block selection ──────────────────────────────────────────────────────
def get_latest_big_block(sav_data):
    """Return the most recent big block by comparing save indices in the footer."""
    # Big block footer is at end of each block
    # HGSS big block 1 ends at 0x21A10, big block 2 at 0x61A10
    # Footer save index at footer offset 0x04
    try:
        footer1_offset = BIG_BLOCK_1_OFFSET + (0x21A10 - 0x0F700) - 0x14 + 0x04
        footer2_offset = BIG_BLOCK_2_OFFSET + (0x21A10 - 0x0F700) - 0x14 + 0x04
        idx1 = struct.unpack_from('<I', sav_data, footer1_offset)[0]
        idx2 = struct.unpack_from('<I', sav_data, footer2_offset)[0]
    except struct.error:
        idx1, idx2 = 1, 0  # default to block 1 if file is too small

    if idx1 >= idx2:
        return sav_data[BIG_BLOCK_1_OFFSET:]
    else:
        return sav_data[BIG_BLOCK_2_OFFSET:]

# ── Box reader ────────────────────────────────────────────────────────────────
def read_boxes(sav_path):
    with open(sav_path, 'rb') as f:
        sav_data = f.read()

    block = get_latest_big_block(sav_data)
    boxes = []

    for box_num in range(NUM_BOXES):
        box      = []
        box_base = box_num * BOX_PADDED_SIZE
        for slot in range(BOX_CAPACITY):
            offset = box_base + slot * BOX_POKEMON_SIZE
            raw    = block[offset:offset + BOX_POKEMON_SIZE]
            if len(raw) < BOX_POKEMON_SIZE:
                break
            mon = parse_box_pokemon(raw)
            box.append(mon)
        boxes.append(box)
    return boxes

# ── Output ────────────────────────────────────────────────────────────────────
def format_box_pokemon(p, box_num):
    #nickname = p['nickname']
    species  = p['species']
    lines    = []

    # header = f"{nickname} ({species})" if nickname and nickname != species else species
    header = f"{species}"
    if p['held_item']:
        header += f" @ {p['held_item']}"
    lines.append(f"{header}")
    lines.append(f"{p['nature']} Nature")
    lines.append(f"Ability: {p['ability']}")
    lines.append(
        f"EVs: {p['ev_hp']} HP / {p['ev_atk']} Atk / {p['ev_def']} Def / "
        f"{p['ev_spe']} Spe / {p['ev_spa']} SpA / {p['ev_spd']} SpD"
    )
    lines.append(
        f"IVs: {p['iv_hp']} HP / {p['iv_atk']} Atk / {p['iv_def']} Def / "
        f"{p['iv_spe']} Spe / {p['iv_spa']} SpA / {p['iv_spd']} SpD"
    )
    for move in p['moves']:
        if move:
            lines.append(f"- {move}")
    lines.append("\n")
    return "\n".join(lines)

def print_boxes(boxes):
    for box_num, box in enumerate(boxes):
        occupied = [p for p in box if p is not None and not p['is_egg']]
        if not occupied:
            continue
        print(f"\n=== Box {box_num + 1} ===")
        for p in occupied:
            print(format_box_pokemon(p, box_num + 1))

def export_boxes(boxes):
    with open(OUTPUT_TXT, 'a', encoding='utf-8') as f:
        f.write("\n=== PC BOXES ===\n\n")
        for box_num, box in enumerate(boxes):
            occupied = [p for p in box if p is not None and not p['is_egg']]
            if not occupied:
                continue
            for p in occupied:
                f.write(format_box_pokemon(p, box_num + 1))
    print(f"✅ Box data appended to {OUTPUT_TXT}")

# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    path  = sys.argv[1] if len(sys.argv) > 1 else GAME_SAV
    boxes = read_boxes(path)
    print_boxes(boxes)
    export_boxes(boxes)
