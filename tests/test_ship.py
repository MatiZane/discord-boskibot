from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

from miku_bot.ship_card import CARD_H, CARD_W, render_ship_card
from miku_bot.ship_logic import build_ship_name, calculate_ship, format_display_name, normalize_ship_key


def test_ship_is_deterministic_and_symmetric() -> None:
    ab = calculate_ship("matizane", "cheawon")
    ba = calculate_ship("cheawon", "matizane")
    case_variant = calculate_ship("  @Matizane ", "CHEAWON")

    assert 0 <= ab.percent <= 100
    assert ab.percent == ba.percent
    assert ab.percent == case_variant.percent
    assert ab.name_b == "Cheawon"


def test_self_ship_gives_100_and_special_comment() -> None:
    res = calculate_ship("matizane", "MATIZANE")
    assert res.percent == 100
    assert res.is_self_ship is True
    assert res.tier == "high"


def test_display_name_and_ship_name_helpers() -> None:
    assert normalize_ship_key("  @MatiZane  ") == "matizane"
    assert format_display_name("cheawon") == "Cheawon"
    assert format_display_name("ChaeWon") == "ChaeWon"
    assert build_ship_name("Miku", "Fuutarou") == "Miarou"


def test_render_ship_card_produces_valid_png_and_handles_corrupt_avatar() -> None:
    # Create one valid avatar PNG and pass one corrupt byte sequence to test fallback resilience.
    sample_avatar = io.BytesIO()
    Image.new("RGB", (128, 128), (110, 180, 240)).save(sample_avatar, format="PNG")

    res = calculate_ship("matizane", "cheawon")
    png_bytes = render_ship_card(res, avatar_a_bytes=sample_avatar.getvalue(), avatar_b_bytes=b"not-an-image")
    with Image.open(io.BytesIO(png_bytes)) as img:
        assert img.format == "PNG"
        assert img.size == (CARD_W, CARD_H)
        assert img.mode == "RGBA"

    # Save visual QA preview under tests/out (gitignored)
    out_dir = Path(__file__).parent / "out"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "ship-preview-default.png").write_bytes(png_bytes)

    high_res = calculate_ship("Miku", "Miku")
    (out_dir / "ship-preview-100.png").write_bytes(render_ship_card(high_res, sample_avatar.getvalue(), None))
