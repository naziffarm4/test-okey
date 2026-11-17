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


class OkeyRackEngine:
    """
    Implements Akıllı Diz (MasaPerHesaplayici @ RVA 0x01A09D98) and
    Okey ile Bit 28-slot rack serializer (Masa::OyunBitir @ RVA 0x019FF938 -> OyunBitirBeta @ RVA 0x019B7BEC).
    """

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

        # Candidate 2: Same-color Run (length 3..13, consecutive numbers; 1 may follow 13 as 14, not 13-1-2)
        colors_set = {c for c, _ in non_jokers}
        if len(colors_set) == 1 and next(iter(colors_set)) in COLORS and total <= 13:
            raw_nums = [n for _, n in non_jokers]
            for ace_high in (False, True):
                mapped = [14 if (ace_high and n == 1) else n for n in raw_nums]
                if len(set(mapped)) != len(mapped):
                    continue
                lo, hi = min(mapped), max(mapped)
                max_bound = 14 if ace_high else 13
                if hi - lo + 1 <= total and (hi - lo + 1 - len(mapped)) <= joker_count:
                    # Ensure enough room inside 1..max_bound for remaining jokers
                    if total <= max_bound:
                        return True
        return False

    @classmethod
    def akilli_diz(cls, tiles: list[Tas], okey_key: str) -> dict[str, Any]:
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
        rack_28 = cls._pack_to_28_slots(melds_tiles, leftover)
        return {
            "melds": [[t.tas_adi for t in grp] for grp in melds_tiles],
            "leftover": [t.tas_adi for t in leftover],
            "kalan_toplam": best_sum,
            "rack_28": rack_28,
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
        for idx, candidate in enumerate(tiles):
            if not candidate.is_okey_joker():
                continue
            rem_14 = tiles[:idx] + tiles[idx + 1 :]
            arranged = cls.akilli_diz(rem_14, okey_key=okey_key)
            if arranged["kalan_toplam"] == 0 and not arranged["leftover"]:
                taslar_wire = "-" + "-".join(arranged["rack_28"])
                return {
                    "taslar": taslar_wire,
                    "bitentas": candidate.tas_id,
                    "_i": "masaoyunbitir-oyunbitirbeta",
                    "_t": session_id,
                }
        return None
