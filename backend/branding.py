"""Product display defaults; never migrate persisted settings or identifiers."""

PRODUCT_NAME = "IN-EDITAONE"
PRODUCT_NAME_KO = "인에디타원"
PRODUCT_DESCRIPTION = "INIT One-Stop Data Editing&Imputation Solution"
DEFAULT_LOGO = "./assets/ineditaone_compact_en_white.png"

_LEGACY_DISPLAY_NAMES = frozenset({
    "INIT Data Editing System", "Data Editing System",
    "INIT-Data Editing Platform System", "INIT DATA EDITING PLATFORM SYSTEM",
    "IN-DEPS", "인뎁스",
})
_LEGACY_LOGOS = frozenset({
    "init-logo.png", "indeps_compact_en.png", "indeps_compact_en_white.png",
    "indeps_compact_ko.png", "indeps_compact_bilingual.png",
    "indeps_banner_en.png", "indeps_banner_ko.png", "indeps_banner_bilingual.png",
})


def display_branding(display_name: str = "", logo_image: str = "") -> dict[str, str]:
    """Map exact historic defaults on read, preserving all custom names/URLs."""
    name = display_name.strip()
    logo = logo_image.strip()
    if not name or name in _LEGACY_DISPLAY_NAMES:
        name = PRODUCT_DESCRIPTION
    if not logo or any(logo == prefix + filename for prefix in ("./assets/", "/assets/", "assets/") for filename in _LEGACY_LOGOS):
        logo = DEFAULT_LOGO
    return {"systemDisplayName": name, "systemLogoImage": logo}
