from __future__ import annotations

import re

from tests.support.rendered_style_browser_harness import computed_style, open_rendered_style_page


def _rgb(value: str) -> tuple[float, float, float]:
    numbers = [float(item) for item in re.findall(r"[\d.]+", value)[:3]]
    if len(numbers) != 3:
        raise AssertionError(f"Cannot parse browser color: {value!r}")
    return tuple(number / 255 for number in numbers)


def _luminance(value: str) -> float:
    channels = []
    for channel in _rgb(value):
        channels.append(channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _contrast(foreground: str, background: str) -> float:
    lighter, darker = sorted((_luminance(foreground), _luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def test_computed_input_shells_have_one_border_and_no_cross_surface_leakage() -> None:
    manager, browser, page = open_rendered_style_page()
    try:
        itinerary_shell = computed_style(page, '[data-surface="itinerary"] [data-baseweb="input"]')
        itinerary_input = computed_style(page, "#itinerary-name")
        explorer_shell = computed_style(page, "#project-search")
        explorer_wrapper = computed_style(page, '#project-search')
        project_baseweb = computed_style(page, '.st-key-project_explorer_workspace [data-baseweb="input"]')

        assert itinerary_shell["borderBottomWidth"] == "1px"
        assert itinerary_input["borderBottomWidth"] == "0px"
        assert itinerary_input["backgroundColor"] == "rgba(0, 0, 0, 0)"
        assert itinerary_shell["backgroundColor"] == "rgba(255, 253, 248, 0.72)"
        assert project_baseweb["backgroundColor"] == "rgb(255, 255, 255)"
        assert explorer_shell["backgroundColor"] == "rgba(0, 0, 0, 0)"
        assert explorer_wrapper["borderBottomWidth"] == "0px"
    finally:
        browser.close()
        manager.stop()


def test_computed_apply_and_disabled_button_contrast_is_readable() -> None:
    manager, browser, page = open_rendered_style_page()
    try:
        apply_style = computed_style(page, "#apply-project-filter")
        disabled_style = computed_style(page, 'button[disabled]')

        assert _contrast(apply_style["color"], apply_style["backgroundColor"]) >= 4.5
        assert _contrast(disabled_style["color"], disabled_style["backgroundColor"]) >= 4.5
        assert apply_style["backgroundColor"] == "rgb(35, 52, 70)"
        assert apply_style["color"] == "rgb(255, 255, 255)"
        assert disabled_style["opacity"] == "1"
    finally:
        browser.close()
        manager.stop()


def test_computed_focus_state_is_visible_on_the_owned_wrapper() -> None:
    manager, browser, page = open_rendered_style_page()
    try:
        page.locator("#project-search").focus()
        wrapper = computed_style(page, '.st-key-project_explorer_workspace [data-baseweb="input"]')
        assert "rgba(168, 153, 134, 0.15)" in wrapper["boxShadow"]
        assert wrapper["borderBottomColor"] != "rgb(207, 196, 179)"
    finally:
        browser.close()
        manager.stop()


def test_owned_rows_do_not_create_page_overflow_at_target_widths() -> None:
    for width in (1440, 1024, 768):
        manager, browser, page = open_rendered_style_page(width=width, height=900)
        try:
            overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            assert overflow <= 0
            assert page.locator("#project-search").get_attribute("placeholder") == "Name, folder or reference"
            assert page.locator("#apply-project-filter").is_visible()
        finally:
            browser.close()
            manager.stop()
