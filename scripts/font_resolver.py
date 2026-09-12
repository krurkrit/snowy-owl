"""Resolve ordered typography preferences against app font capabilities."""

import re


FONT_ROLES = ("ui", "monospace")
FONT_MODES = {"configuration", "runtime-stack", "user-setting", "unsupported"}
POSTSCRIPT_NAME = re.compile(r"^[!-~]{1,63}$")
POSTSCRIPT_FORBIDDEN = set("[](){}<>/%")


class FontConfigurationError(ValueError):
    """Raised when typography and an app font declaration are incompatible."""


def _has_required_metadata(metadata: dict, required: list) -> bool:
    """Return whether a font style provides valid app-required metadata."""
    if not all(property_name in metadata for property_name in required):
        return False
    postscript_name = metadata.get("postScriptName")
    if postscript_name is None:
        return True
    if not isinstance(postscript_name, str):
        return False
    return bool(POSTSCRIPT_NAME.fullmatch(postscript_name)) and not any(
        character in POSTSCRIPT_FORBIDDEN for character in postscript_name
    )


def resolve_font(typography: dict, role: str, capability: dict, app: str) -> dict:
    """Select the first supported family and style for one app font role.

    Args:
        typography: Global typography token values.
        role: Font role to resolve, such as ``ui`` or ``monospace``.
        capability: App font capability and available-font declaration.
        app: App name used in validation messages.

    Returns:
        The selected font plus compatible fallback candidates and metadata.

    Raises:
        FontConfigurationError: The role or capability cannot be resolved.
    """
    mode = capability.get("mode")
    if mode not in FONT_MODES:
        raise FontConfigurationError(f"{app}.{role}: invalid font mode '{mode}'")
    if mode == "unsupported":
        return {"mode": mode}

    config = typography.get(role)
    if not isinstance(config, dict):
        raise FontConfigurationError(f"{app}.{role}: missing typography role")

    fonts = config.get("fonts")
    available_fonts = capability.get("availableFonts")
    if not isinstance(fonts, list) or not isinstance(available_fonts, list):
        raise FontConfigurationError(
            f"{app}.{role}: fonts and availableFonts must be lists"
        )

    app_fonts = {
        entry.get("family", "").casefold(): entry
        for entry in available_fonts
        if isinstance(entry, dict) and isinstance(entry.get("family"), str)
    }
    required = capability.get("requiredProperties", [])
    if not isinstance(required, list):
        raise FontConfigurationError(
            f"{app}.{role}: requiredProperties must be a list"
        )

    compatible = []
    selected = None
    for font in fonts:
        if not isinstance(font, dict) or not isinstance(font.get("family"), str):
            raise FontConfigurationError(f"{app}.{role}: invalid typography font")
        app_font = app_fonts.get(font["family"].casefold())
        if not app_font:
            continue
        styles = font.get("styles")
        allowed_styles = app_font.get("styles")
        if not isinstance(styles, dict) or not isinstance(allowed_styles, list):
            raise FontConfigurationError(
                f"{app}.{role}.{font['family']}: styles must be declared"
            )
        style_order = [
            capability.get("style"),
            config.get("defaultStyle", "regular"),
            *styles,
        ]
        style_name = next(
            (
                name
                for name in dict.fromkeys(style_order)
                if name in styles
                and name in allowed_styles
                and _has_required_metadata(styles[name], required)
            ),
            None,
        )
        if style_name is None:
            continue
        candidate = {"font": font, "style": style_name, "metadata": styles[style_name]}
        compatible.append(candidate)
        if selected is None:
            selected = candidate

    if selected is None:
        raise FontConfigurationError(
            f"{app}.{role}: no preferred font has a compatible style and metadata"
        )

    font = selected["font"]
    style_name = selected["style"]
    metadata = selected["metadata"]
    return {
        "mode": mode,
        "family": font["family"],
        "fallbackFamilies": [item["font"]["family"] for item in compatible[1:]],
        "style": style_name,
        "weight": metadata.get("weight"),
        "slant": metadata.get("slant"),
        "fullName": metadata.get("fullName"),
        "postScriptName": metadata.get("postScriptName"),
        "candidates": [
            {
                "family": item["font"]["family"],
                "style": item["style"],
                **item["metadata"],
            }
            for item in compatible
        ],
    }


def resolve_app_fonts(typography: dict, mapping: dict, app: str) -> dict:
    """Resolve both required font roles declared by an app mapping.

    Args:
        typography: Global typography token values.
        mapping: App mapping containing font capabilities.
        app: App name used in validation messages.

    Returns:
        Resolved selections keyed by required font role.

    Raises:
        FontConfigurationError: A required role is missing or incompatible.
    """
    declarations = mapping.get("fonts")
    if not isinstance(declarations, dict):
        raise FontConfigurationError(f"{app}: missing fonts declaration")
    missing = [role for role in FONT_ROLES if role not in declarations]
    if missing:
        raise FontConfigurationError(f"{app}: missing font roles: {', '.join(missing)}")
    return {
        role: resolve_font(typography, role, declarations[role], app)
        for role in FONT_ROLES
    }


def css_font_stack(selection: dict) -> str:
    """Format a resolved family list as a CSS font stack.

    Args:
        selection: Resolved font selection from :func:`resolve_font`.

    Returns:
        A comma-separated CSS font-family value.
    """
    generic = {"cursive", "fantasy", "monospace", "sans-serif", "serif", "system-ui"}
    families = [selection["family"], *selection.get("fallbackFamilies", [])]
    return ", ".join(
        family if family in generic else f'"{family}"' for family in families
    )
