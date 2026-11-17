from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Any

EVENT_REQUIRED_KEYS: dict[str, tuple[str, ...]] = {
    "OnIstakayiGuncelle": ("t",),
    "OnMasaTaslariGuncelle": ("mid", "kt", "ot", "ok", "ms", "yt", "el", "es", "cn", "rx", "tc", "cl"),
    "OnTasCek": ("tas", "yon", "tip", "kt", "tc", "dc", "cl"),
    "OnTasAt": ("tas", "yon", "ms", "tc", "cl"),
    "SiraGeldi_Derived": ("Sira", "sure"),
    "OnOyunBitir": ("Baslik", "BitenTas", "CanakKirildi", "Kazananlar", "Taslar"),
    "OnOyunBitirHata": ("hata",),
}

COLORS = ("k", "m", "s", "y")


def validate_http_command_envelope(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"valid": False, "reason": "payload_not_dict"}
    has_e = isinstance(payload.get("_e"), str) and bool(payload["_e"])
    has_i = isinstance(payload.get("_i"), str) and bool(payload["_i"])
    if has_e == has_i:
        return {"valid": False, "reason": "must_have_exactly_one_of__e_or__i"}
    if has_i and not (isinstance(payload.get("_t"), str) and bool(payload["_t"])):
        return {"valid": False, "reason": "in_session__i_requires__t"}
    return {"valid": True, "mode": "pre_auth" if has_e else "in_session"}


def validate_server_envelope(envelope: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(envelope, dict) or not isinstance(envelope.get("s"), list):
        return {"valid": False, "reason": "missing_s_array"}
    for idx, item in enumerate(envelope["s"]):
        if not isinstance(item, dict) or not isinstance(item.get("i"), str) or "d" not in item:
            return {"valid": False, "reason": f"invalid_item_at_{idx}"}
    return {"valid": True, "count": len(envelope["s"])}


def validate_event_payload(event_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    if event_name not in EVENT_REQUIRED_KEYS:
        return {"valid": False, "reason": f"unknown_event_{event_name}"}
    if not isinstance(payload, dict):
        return {"valid": False, "reason": "payload_not_dict"}
    missing = [k for k in EVENT_REQUIRED_KEYS[event_name] if k not in payload]
    if missing:
        return {"valid": False, "reason": "missing_keys", "missing": missing}

    if event_name == "OnOyunBitir":
        if not isinstance(payload["Kazananlar"], list) or not isinstance(payload["Taslar"], list):
            return {"valid": False, "reason": "invalid_OnOyunBitir_lists"}
    elif event_name == "OnOyunBitirHata":
        if not isinstance(payload["hata"], list):
            return {"valid": False, "reason": "invalid_hata_list"}
        for entry in payload["hata"]:
            if not all(k in entry for k in ("Per", "Tip", "Taslar")):
                return {"valid": False, "reason": "invalid_hata_entry"}
    return {"valid": True, "event": event_name}


@dataclass(frozen=True)
class Tas:
    """
    Matches Tas::TasOlustur @ RVA 0x01A1265C & MasaPerHesaplayici::IsOkeyTile @ RVA 0x01A0A210.
    Wire format: '<TasID>-<TasRenk>-<TasSayi>', e.g. '12-k-12', '53-o-0'.
    """

    tas_adi: str
    tas_id: str
    tas_renk: str
    tas_sayi: str
    tas_rakam: int
    tas_key: str
    okeymi: bool

    @classmethod
    def from_wire(cls, wire: str, okey_key: str = "") -> Tas:
        parts = wire.strip().split("-")
        if len(parts) != 3:
            raise ValueError(f"Invalid wire tile format: {wire!r}")
        tas_id, tas_renk, tas_sayi = parts
        tas_rakam = int(tas_sayi)
        tas_key = f"{tas_renk}-{tas_sayi}"
        okeymi = bool(okey_key and tas_key == okey_key)
        return cls(
            tas_adi=wire.strip(),
            tas_id=tas_id,
            tas_renk=tas_renk,
            tas_sayi=tas_sayi,
            tas_rakam=tas_rakam,
            tas_key=tas_key,
            okeymi=okeymi,
        )

    def is_okey_joker(self) -> bool:
        if self.okeymi:
            return True
        if self.tas_renk == "o" and self.tas_id not in ("53", "106"):
            return True
        return False

    def effective_key(self, okey_key: str) -> str:
        if self.tas_id in ("53", "106") and okey_key:
            return okey_key
        return self.tas_key

    def effective_color_num(self, okey_key: str) -> tuple[str, int]:
        ek = self.effective_key(okey_key)
        c, n = ek.split("-", 1)
        return c, int(n)


class Rack28Model:
    """
    28-slot Okey rack model (Slots 0..13 upper row, 14..27 lower row).
    Enforces unique physical TasID invariant and supports non-destructive snapshots.
    """

    SLOT_COUNT = 28

    def __init__(self, slots: list[Tas | None] | None = None) -> None:
        if slots is None:
            self._slots: list[Tas | None] = [None] * self.SLOT_COUNT
        else:
            if len(slots) != self.SLOT_COUNT:
                raise ValueError(f"Rack requires exactly {self.SLOT_COUNT} slots, got {len(slots)}")
            seen: set[str] = set()
            for t in slots:
                if t is not None:
                    if t.tas_id in seen:
                        raise ValueError(f"Duplicate TasID {t.tas_id!r} on rack")
                    seen.add(t.tas_id)
            self._slots = list(slots)

    @classmethod
    def from_tiles(cls, tiles: list[Tas], positions: list[int] | None = None) -> Rack28Model:
        slots: list[Tas | None] = [None] * cls.SLOT_COUNT
        if positions is None:
            if len(tiles) > cls.SLOT_COUNT:
                raise ValueError("Too many tiles for 28-slot rack")
            for idx, t in enumerate(tiles):
                slots[idx] = t
        else:
            if len(positions) != len(tiles):
                raise ValueError("positions length must match tiles length")
            for pos, t in zip(positions, tiles):
                if not (0 <= pos < cls.SLOT_COUNT) or slots[pos] is not None:
                    raise ValueError(f"Invalid or colliding rack slot index: {pos}")
                slots[pos] = t
        return cls(slots)

    def clone(self) -> Rack28Model:
        return Rack28Model(list(self._slots))

    def tiles(self) -> list[Tas]:
        return [t for t in self._slots if t is not None]

    def move_tile(self, src_slot: int, dst_slot: int) -> None:
        if not (0 <= src_slot < self.SLOT_COUNT and 0 <= dst_slot < self.SLOT_COUNT):
            raise IndexError("Slot index out of 0..27 range")
        self._slots[src_slot], self._slots[dst_slot] = self._slots[dst_slot], self._slots[src_slot]

    def to_slot_ids(self) -> list[str]:
        return [t.tas_id if t is not None else "Bos" for t in self._slots]

    def to_oyunbitir_wire(self) -> str:
        """Matches Masa::OyunBitir @ RVA 0x019FF938: '-' + 28 '-' separated TasID/'Bos' tokens."""
        return "-" + "-".join(self.to_slot_ids())


class OkeyRackEngine:
    """
    Implements Akıllı Diz (MasaPerHesaplayici @ RVA 0x01A09D98, both Per and Çift modes,
    non-destructive alternative preview, disjoint tile invariant) and Okey ile Bit 28-slot
    serializer (Masa::OyunBitir @ RVA 0x019FF938 -> OyunBitirBeta @ RVA 0x019B7BEC).
    """

    @staticmethod
    def assert_disjoint_tile_usage(input_tiles: list[Tas], grouped: list[list[Tas]], leftover: list[Tas]) -> None:
        expected_ids = [t.tas_id for t in input_tiles]
        if len(set(expected_ids)) != len(expected_ids):
            raise ValueError("Input hand contains duplicate physical TasID")
        used_ids = [t.tas_id for grp in grouped for t in grp] + [t.tas_id for t in leftover]
        if len(used_ids) != len(set(used_ids)) or set(used_ids) != set(expected_ids):
            raise ValueError("Tile reuse or loss detected across combinations")

    @staticmethod
    def _is_valid_meld(non_jokers: list[tuple[str, int]], joker_count: int) -> bool:
        total = len(non_jokers) + joker_count
        if total < 3:
            return False
        if not non_jokers:
            return total >= 3

        # Candidate 1: Color Set (3 or 4 tiles, same number 1..13, all distinct colors)
        if total <= 4:
            nums = {n for _, n in non_jokers}
            colors = [c for c, _ in non_jokers]
            if len(nums) == 1 and len(set(colors)) == len(colors) and all(c in COLORS for c in colors):
                return True

        # Candidate 2: Same-color Run (length 3..13, consecutive numbers; 1 may follow 13 as 14, never 13-1-2)
        colors_set = {c for c, _ in non_jokers}
        if len(colors_set) == 1 and next(iter(colors_set)) in COLORS and total <= 13:
            raw_nums = [n for _, n in non_jokers]
            for ace_high in (False, True):
                if ace_high and 1 not in raw_nums:
                    continue
                mapped = [14 if (ace_high and n == 1) else n for n in raw_nums]
                if len(set(mapped)) != len(mapped):
                    continue
                lo, hi = min(mapped), max(mapped)
                if ace_high and lo == 2:
                    # Rejects 13-1-2 wraparound when mapped has 2..14 span > total
                    pass
                max_bound = 14 if ace_high else 13
                min_bound = 2 if ace_high else 1
                span = hi - lo + 1
                if span <= total and (span - len(mapped)) <= joker_count:
                    # Total window of length `total` must fit inside [min_bound, max_bound]
                    if total <= (max_bound - min_bound + 1):
                        return True
        return False

    @classmethod
    def akilli_diz_cift(cls, tiles: list[Tas], okey_key: str) -> dict[str, Any]:
        """Calculates optimal pair (Çift) arrangement using identical color+number pairs + wild Okey jokers."""
        if len({t.tas_id for t in tiles}) != len(tiles):
            raise ValueError("Duplicate physical TasID in hand")

        jokers = [t for t in tiles if t.is_okey_joker()]
        regulars = [t for t in tiles if not t.is_okey_joker()]

        by_key: dict[str, list[Tas]] = {}
        for t in regulars:
            by_key.setdefault(t.effective_key(okey_key), []).append(t)

        pairs: list[list[Tas]] = []
        singles: list[Tas] = []
        for grp in by_key.values():
            idx = 0
            while idx + 1 < len(grp):
                pairs.append([grp[idx], grp[idx + 1]])
                idx += 2
            if idx < len(grp):
                singles.append(grp[idx])

        # Pair highest-point singles with wild Okey jokers first to minimize kalan_toplam
        singles.sort(key=lambda t: t.effective_color_num(okey_key)[1], reverse=True)
        rem_jokers = list(jokers)
        paired_single_ids: set[str] = set()
        for s_tile in singles:
            if not rem_jokers:
                break
            j_tile = rem_jokers.pop(0)
            pairs.append([s_tile, j_tile])
            paired_single_ids.add(s_tile.tas_id)

        while len(rem_jokers) >= 2:
            pairs.append([rem_jokers.pop(0), rem_jokers.pop(0)])

        leftover = [s for s in singles if s.tas_id not in paired_single_ids] + rem_jokers
        cls.assert_disjoint_tile_usage(tiles, pairs, leftover)

        kalan_toplam = sum(0 if t.is_okey_joker() else t.effective_color_num(okey_key)[1] for t in leftover)
        rack_28 = cls._pack_to_28_slots(pairs, leftover)
        return {
            "mode": "cift",
            "pairs": [[t.tas_adi for t in grp] for grp in pairs],
            "melds": [[t.tas_adi for t in grp] for grp in pairs],
            "cift_sayisi": len(pairs),
            "leftover": [t.tas_adi for t in leftover],
            "kalan_toplam": kalan_toplam,
            "rack_28": rack_28,
        }

    @classmethod
    def akilli_diz(cls, tiles: list[Tas], okey_key: str, mode: str = "per") -> dict[str, Any]:
        if mode == "cift":
            return cls.akilli_diz_cift(tiles, okey_key=okey_key)
        if len({t.tas_id for t in tiles}) != len(tiles):
            raise ValueError("Duplicate physical TasID in hand")

        n = len(tiles)
        eff = [None if t.is_okey_joker() else t.effective_color_num(okey_key) for t in tiles]
        points = [0 if t.is_okey_joker() else t.effective_color_num(okey_key)[1] for t in tiles]

        valid_masks: list[int] = []
        for size in range(3, min(6, n) + 1):
            for idxs in combinations(range(n), size):
                nj = [eff[i] for i in idxs if eff[i] is not None]
                jc = size - len(nj)
                if cls._is_valid_meld(nj, jc):
                    mask = 0
                    for i in idxs:
                        mask |= 1 << i
                    valid_masks.append(mask)

        memo: dict[int, tuple[int, list[int]]] = {}

        def solve(used_mask: int, start_idx: int) -> tuple[int, list[int]]:
            if used_mask in memo:
                return memo[used_mask]
            rem_sum = sum(points[i] for i in range(n) if not (used_mask & (1 << i)))
            best_sum = rem_sum
            best_melds: list[int] = []
            for m_idx in range(start_idx, len(valid_masks)):
                m = valid_masks[m_idx]
                if used_mask & m:
                    continue
                cand_sum, cand_melds = solve(used_mask | m, m_idx + 1)
                if cand_sum < best_sum:
                    best_sum = cand_sum
                    best_melds = [m, *cand_melds]
                    if best_sum == 0:
                        break
            memo[used_mask] = (best_sum, best_melds)
            return best_sum, best_melds

        best_sum, chosen_masks = solve(0, 0)
        used_all = 0
        melds_tiles: list[list[Tas]] = []
        for m in chosen_masks:
            used_all |= m
            group = [tiles[i] for i in range(n) if (m & (1 << i))]
            group.sort(key=lambda t: (99 if t.is_okey_joker() else t.effective_color_num(okey_key)[1]))
            melds_tiles.append(group)

        leftover = [tiles[i] for i in range(n) if not (used_all & (1 << i))]
        cls.assert_disjoint_tile_usage(tiles, melds_tiles, leftover)
        rack_28 = cls._pack_to_28_slots(melds_tiles, leftover)
        return {
            "mode": "per",
            "melds": [[t.tas_adi for t in grp] for grp in melds_tiles],
            "leftover": [t.tas_adi for t in leftover],
            "kalan_toplam": best_sum,
            "rack_28": rack_28,
        }

    @classmethod
    def suggest_alternatives(cls, rack: Rack28Model, okey_key: str) -> dict[str, Any]:
        """
        Computes Seri/Renk ('per') and Pair ('cift') arrangements on a cloned snapshot
        without mutating the user's existing 28-slot rack layout.
        """
        original_snapshot = rack.to_slot_ids()
        hand_tiles = rack.clone().tiles()
        per_plan = cls.akilli_diz(hand_tiles, okey_key=okey_key, mode="per")
        cift_plan = cls.akilli_diz(hand_tiles, okey_key=okey_key, mode="cift")
        assert rack.to_slot_ids() == original_snapshot, "User rack must never be mutated during preview"
        recommended = "cift" if (cift_plan["cift_sayisi"] >= 7 and cift_plan["kalan_toplam"] == 0) or (
            cift_plan["cift_sayisi"] >= 5 and cift_plan["kalan_toplam"] < per_plan["kalan_toplam"]
        ) else "per"
        return {
            "original_rack_28": original_snapshot,
            "per_alternative": per_plan,
            "cift_alternative": cift_plan,
            "recommended_mode": recommended,
        }

    @staticmethod
    def _pack_to_28_slots(melds: list[list[Tas]], leftover: list[Tas]) -> list[str]:
        slots = ["Bos"] * 28
        cursor = 0
        for grp in melds:
            # Keep melds from splitting across the row boundary (slot 13 -> 14) when possible
            if cursor < 14 and cursor + len(grp) > 14:
                cursor = 14
            for t in grp:
                if cursor < 28:
                    slots[cursor] = t.tas_id
                    cursor += 1
            if cursor not in (14, 28) and cursor < 28:
                cursor += 1  # Leave one 'Bos' separator between melds

        # Place leftover tiles from the right end of row 2 backwards
        rev_pos = 27
        for t in reversed(leftover):
            while rev_pos >= 0 and slots[rev_pos] != "Bos":
                rev_pos -= 1
            if rev_pos >= 0:
                slots[rev_pos] = t.tas_id
                rev_pos -= 1
        return slots

    @classmethod
    def build_okey_ile_bit_command(
        cls,
        *,
        tiles: list[Tas],
        okey_key: str,
        session_id: str,
    ) -> dict[str, str] | None:
        if len(tiles) != 15:
            return None
        if len({t.tas_id for t in tiles}) != 15:
            raise ValueError("15-tile hand contains duplicate physical TasID")

        for idx, candidate in enumerate(tiles):
            if not candidate.is_okey_joker():
                continue
            rem_14 = tiles[:idx] + tiles[idx + 1 :]
            # Path A: 14 tiles form valid Seri/Renk melds with 0 leftover
            arranged_per = cls.akilli_diz(rem_14, okey_key=okey_key, mode="per")
            if arranged_per["kalan_toplam"] == 0 and not arranged_per["leftover"]:
                taslar_wire = "-" + "-".join(arranged_per["rack_28"])
                return {
                    "taslar": taslar_wire,
                    "bitentas": candidate.tas_id,
                    "_i": "masaoyunbitir-oyunbitirbeta",
                    "_t": session_id,
                }
            # Path B: 14 tiles form 7 valid pairs (Çift bitiş + Okey ile Bit) with 0 leftover
            arranged_cift = cls.akilli_diz(rem_14, okey_key=okey_key, mode="cift")
            if arranged_cift["cift_sayisi"] == 7 and not arranged_cift["leftover"]:
                taslar_wire = "-" + "-".join(arranged_cift["rack_28"])
                return {
                    "taslar": taslar_wire,
                    "bitentas": candidate.tas_id,
                    "_i": "masaoyunbitir-oyunbitirbeta",
                    "_t": session_id,
                }
        return None
