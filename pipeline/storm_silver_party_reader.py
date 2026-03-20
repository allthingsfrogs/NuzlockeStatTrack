import struct
from pathlib import Path
import pandas as pd
import os 

# ── Constants ─────────────────────────────────────────────────────────────────
# HGSS small block starts at 0x00000
# Party count at 0x9C, party data at 0xA0
# Each party pokemon is 236 bytes (136 box data + 100 battle stats)
# Second save block is at offset + 0x40000, we pick the one with higher save index

SMALL_BLOCK_1_OFFSET  = 0x00000
SMALL_BLOCK_2_OFFSET  = 0x40000
SAVE_INDEX_OFFSET     = 0xC0F4   # within small block footer
PARTY_COUNT_OFFSET    = 0x009C
PARTY_DATA_OFFSET     = 0x00A0
PARTY_POKEMON_SIZE    = 236
PARTY_SIZE            = 6
BOX_POKEMON_SIZE      = 136

OUTPUT_TXT = "all_pokemon.txt"

GAME_SAV = os.getenv("SAV")

PROJECT_ROOT_DIR = Path("..")

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

# Block order lookup for unshuffling
# Given shift value, returns order to read blocks as [A, B, C, D] indices
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
    row = df[df['species'] == species].iloc[0]
    type1 = row['type1']
    type2 = row['type2'] if pd.notna(row['type2']) else None
    return type1, type2

# ── Gen IV decryption ─────────────────────────────────────────────────────────
def prng_next(seed):
    return (0x41C64E6D * seed + 0x6073) & 0xFFFFFFFF

def decrypt_block_data(data, seed):
    """Decrypt 128 bytes of ABCD block data using checksum as seed."""
    result = bytearray(data)
    state  = seed
    for i in range(0, 128, 2):
        state        = prng_next(state)
        key          = (state >> 16) & 0xFFFF
        word         = struct.unpack_from('<H', result, i)[0]
        struct.pack_into('<H', result, i, word ^ key)
    return bytes(result)

def unshuffle_blocks(data, pv):
    """Restore ABCD block order from shuffled encrypted data."""
    shift      = ((pv & 0x3E000) >> 0xD) % 24
    order      = BLOCK_ORDERS[shift]
    blocks     = [data[i*32:(i+1)*32] for i in range(4)]
    unshuffled = [None] * 4
    for dest, src in enumerate(order):
        unshuffled[dest] = blocks[src]
    return b''.join(unshuffled)

def decrypt_battle_stats(data, pv):
    """Decrypt battle stats (offset 0x88 onward) using personality value as seed."""
    result = bytearray(data)
    state  = pv
    for i in range(0, len(data), 2):
        state        = prng_next(state)
        key          = (state >> 16) & 0xFFFF
        word         = struct.unpack_from('<H', result, i)[0]
        struct.pack_into('<H', result, i, word ^ key)
    return bytes(result)

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
def parse_pokemon_gen4(raw, is_party=True):
    """Parse a single Gen IV Pokemon from raw bytes."""
    pv       = struct.unpack_from('<I', raw, 0x00)[0]
    checksum = struct.unpack_from('<H', raw, 0x06)[0]

    if pv == 0 and checksum == 0:
        return None  # empty slot

    # Decrypt and unshuffle the 128 byte ABCD block
    encrypted_blocks = raw[0x08:0x88]
    decrypted        = decrypt_block_data(encrypted_blocks, checksum)
    unshuffled       = unshuffle_blocks(decrypted, pv)

    # Block A (offset 0x00 within unshuffled)
    dex_num  = struct.unpack_from('<H', unshuffled, 0x00)[0]
    held_item   = struct.unpack_from('<H', unshuffled, 0x02)[0]
    ability_id  = unshuffled[0x0D]
    ev_hp       = unshuffled[0x10]
    ev_atk      = unshuffled[0x11]
    ev_def      = unshuffled[0x12]
    ev_spe      = unshuffled[0x13]
    ev_spa      = unshuffled[0x14]
    ev_spd      = unshuffled[0x15]

    # Block B (offset 0x20 within unshuffled)
    move1       = struct.unpack_from('<H', unshuffled, 0x20)[0]
    move2       = struct.unpack_from('<H', unshuffled, 0x22)[0]
    move3       = struct.unpack_from('<H', unshuffled, 0x24)[0]
    move4       = struct.unpack_from('<H', unshuffled, 0x26)[0]
    ivs_data    = struct.unpack_from('<I', unshuffled, 0x30)[0]
    iv_hp       = ivs_data & 0x1F
    iv_atk      = (ivs_data >> 5) & 0x1F
    iv_def      = (ivs_data >> 10) & 0x1F
    iv_spe      = (ivs_data >> 15) & 0x1F
    iv_spa      = (ivs_data >> 20) & 0x1F
    iv_spd      = (ivs_data >> 25) & 0x1F
    is_egg        = (ivs_data >> 30) & 0x01
    is_nicknamed  = (ivs_data >> 31) & 0x01

    # Block C (offset 0x40 within unshuffled) — nickname
    nickname_raw = unshuffled[0x40:0x56]
    nickname     = decode_nickname(nickname_raw) if is_nicknamed else ""
    #nickname = get_species_name(species_id)

    # Block D (offset 0x60 within unshuffled) — met location
    location_met_id = struct.unpack_from('<H', unshuffled, 0x60)[0]
    location_met    = get_location_name(location_met_id)

    nature  = NATURES[pv % 25]
    species = get_species_name(dex_num)

    # Level from battle stats (party only)
    exp_level = None
    if is_party and len(raw) >= 0x8D:
        battle_raw   = raw[0x88:]
        battle_dec   = decrypt_battle_stats(battle_raw, pv)
        exp_level        = battle_dec[0x04] if len(battle_dec) > 0x04 else None

    # Pokemon's Typing
    type1, type2 = get_type(species)

    return {
        'species':      species,
        'dex_num':      dex_num,
        'nickname':     nickname,
        'exp_level':     exp_level,
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
    }

# ── Save block selection ──────────────────────────────────────────────────────
def get_latest_small_block(sav_data):
    """Return the most recent small block by comparing save indices."""
    # Save index is stored near the end of the small block
    # HGSS small block is 0xF700 bytes, footer at end
    idx1 = struct.unpack_from('<I', sav_data, 0x0CF2C - 4)[0]
    idx2 = struct.unpack_from('<I', sav_data, 0x40000 + 0x0CF2C - 4)[0]
    if idx1 >= idx2:
        return sav_data[SMALL_BLOCK_1_OFFSET:]
    else:
        return sav_data[SMALL_BLOCK_2_OFFSET:]

# ── Party reader ──────────────────────────────────────────────────────────────
def read_party(sav_path):
    with open(sav_path, 'rb') as f:
        sav_data = f.read()

    # Scan both possible small block locations for valid party data
    # Try known HGSS party offsets: 0x00098 and 0x40098
    for base in [0x00098, 0x40098]:
        party = []
        for i in range(PARTY_SIZE):
            offset = base + i * PARTY_POKEMON_SIZE
            if offset + PARTY_POKEMON_SIZE > len(sav_data):
                break
            raw = sav_data[offset:offset + PARTY_POKEMON_SIZE]
            pv  = struct.unpack_from('<I', raw, 0x00)[0]
            chk = struct.unpack_from('<H', raw, 0x06)[0]
            if pv == 0 and chk == 0:
                continue
            mon = parse_pokemon_gen4(raw, is_party=True)
            if mon and mon['dex_num'] > 0:
                party.append(mon)
        if party:
            print(f"DEBUG: found {len(party)} party pokemon at base 0x{base:05X}")
            return party

    print("DEBUG: no party found at known offsets, scanning...")
    return []

# ── Showdown formatter ────────────────────────────────────────────────────────
'''Abomasnow @ Leftovers
Level: 100
Adamant Nature
Ability: Snow Warning
EVs: 252 HP / 252 Atk / 4 SpD
IVs: 3 Atk / 3 Def / 3 SpA
- Wood Hammer
- Ice Shard
- Protect
- Leech Seed'''
def to_showdown(party):
    lines = []
    for p in party:
        if p['is_egg']:
            continue
        #nickname = p['nickname']
        species  = p['species']

        # header = f"{nickname} ({species})" if nickname and nickname != species else species
        header = f"{species}"
        if p['held_item']:
            header += f" @ {p['held_item']}"
        lines.append(header)
        if p['exp_level'] is not None:
            lines.append(f"Level: {p['exp_level']}")
        
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
        lines.append("")
    return "\n".join(lines)

def export_party(sav_path):
    party  = read_party(sav_path)
    output = to_showdown(party)
    with open(OUTPUT_TXT, 'a', encoding='utf-8') as f:
        f.write("=== PARTY ===\n\n")
        f.write(output)
    print(output)
    print(f"✅ Party exported to {OUTPUT_TXT}")

# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else GAME_SAV
    export_party(path)
