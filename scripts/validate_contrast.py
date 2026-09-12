#!/usr/bin/env python3
"""Validate contrast and generate the Snowy Owl token dashboard."""

import argparse
import copy
import html
import re
import sys
from pathlib import Path

if __package__:
    from .token_resolver import (
        REFERENCE_PATTERN,
        TokenConflictError,
        TokenHeaderError,
        TokenReferenceError,
        app_token_document_paths,
        load_token_documents,
        load_token_header,
        load_token_metadata,
        load_yaml,
        resolve_references,
        token_document_paths,
        token_namespace,
    )
else:
    from token_resolver import (
        REFERENCE_PATTERN,
        TokenConflictError,
        TokenHeaderError,
        TokenReferenceError,
        app_token_document_paths,
        load_token_documents,
        load_token_header,
        load_token_metadata,
        load_yaml,
        resolve_references,
        token_document_paths,
        token_namespace,
    )

ROOT = Path(__file__).resolve().parents[1]
APP_REFERENCE_PATTERN = re.compile(
    r"\{([A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)+)\}"
)
APP_SOURCE_SUFFIXES = {
    ".css",
    ".json",
    ".jsonc",
    ".ps1",
    ".toml",
    ".yaml",
    ".yml",
}


def luminance(h):
    """Return WCAG relative luminance for a hexadecimal RGB color.

    Args:
        h: Color in ``#RRGGBB`` form.

    Returns:
        Relative luminance from 0.0 through 1.0.
    """
    rgb = [int(h[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    rgb = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]


def contrast(a, b):
    """Return the unrounded WCAG contrast ratio between two RGB colors.

    Args:
        a: First color in ``#RRGGBB`` form.
        b: Second color in ``#RRGGBB`` form.

    Returns:
        Contrast ratio from 1.0 through 21.0.
    """
    x, y = luminance(a), luminance(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


def calculate_contrast_rows(contrast_config):
    """Evaluate every configured contrast rule against the project minimum.

    Args:
        contrast_config: Resolved contrast-policy and rule mapping.

    Returns:
        Rule tuples containing name, colors, ratio, and pass status.
    """
    minimum = float(contrast_config["policy"]["minimum"])
    rows = []
    for rule in contrast_config["rules"]:
        ratio = contrast(rule["foreground"], rule["background"])
        rows.append(
            (
                rule["name"],
                rule["foreground"],
                rule["background"],
                ratio,
                ratio >= minimum,
            )
        )
    return rows


def flatten_variables(values, prefix=""):
    """Yield dotted paths and scalar values from a nested token mapping."""
    for name, value in values.items():
        variable_name = f"{prefix}.{name}" if prefix else name
        if isinstance(value, dict):
            yield from flatten_variables(value, variable_name)
        else:
            yield variable_name, value


def find_app_token_reference_sources(app_directory):
    """Map token references to the app files that contain them directly.

    Args:
        app_directory: App adapter directory to search recursively.

    Returns:
        Token paths mapped to relative source-file paths.
    """
    references = {}
    for path in app_directory.rglob("*"):
        if path.is_file() and path.suffix.lower() in APP_SOURCE_SUFFIXES:
            content = path.read_text(encoding="utf-8")
            if path.suffix.lower() in {".yaml", ".yml"} and "snowyOwl:" in content:
                continue
            source = path.relative_to(app_directory).as_posix()
            for reference in APP_REFERENCE_PATTERN.findall(content):
                references.setdefault(reference, set()).add(source)
    return references


def find_app_token_references(app_directory):
    """Return all token references found in supported app source files."""
    return set(find_app_token_reference_sources(app_directory))


def analyze_document_usage(documents, app_reference_sources):
    """Analyze direct, indirect, and token-to-token usage.

    Args:
        documents: Unresolved token documents keyed by namespace.
        app_reference_sources: Token paths mapped to direct app source files.

    Returns:
        Per-namespace usage details for every scalar token.
    """
    values = {
        f"{namespace}.{name}": value
        for namespace, document in documents.items()
        for name, value in flatten_variables(document)
    }
    usage = {
        namespace: {
            variable: {"apps": set(), "direct_apps": set(), "variables": set()}
            for variable in values
            if variable.startswith(f"{namespace}.")
        }
        for namespace in documents
    }

    def expand(reference):
        return {
            variable
            for variable in values
            if variable == reference or variable.startswith(f"{reference}.")
        }

    for source, value in values.items():
        if not isinstance(value, str):
            continue
        match = REFERENCE_PATTERN.fullmatch(value)
        if match:
            usage[source.split(".", 1)[0]][source]["reference"] = match.group(1)
            for target in expand(match.group(1)):
                usage[target.split(".", 1)[0]][target]["variables"].add(source)

    for reference, sources in app_reference_sources.items():
        for target in expand(reference):
            details = usage[target.split(".", 1)[0]][target]
            details["apps"].update(sources)
            if target == reference:
                details["direct_apps"].update(sources)

    changed = True
    while changed:
        changed = False
        for source, value in values.items():
            if not isinstance(value, str):
                continue
            match = REFERENCE_PATTERN.fullmatch(value)
            if not match:
                continue
            source_details = usage[source.split(".", 1)[0]][source]
            for target in expand(match.group(1)):
                target_apps = usage[target.split(".", 1)[0]][target]["apps"]
                before = len(target_apps)
                target_apps.update(source_details["apps"])
                changed |= before != len(target_apps)
    return usage


def get_variable_status(details):
    """Classify a token by its effective and superseded references."""
    if details.get("apps"):
        return "used"
    if (
        details.get("variables")
    ):
        return "referenced"
    if details.get("superseded_variables"):
        return "historical"
    return "unused"


def _nested_value(document, path):
    """Read a dotted scalar path from a nested token document."""
    value = document
    for part in path.split("."):
        value = value[part]
    return value


def analyze_token_overrides(token_directory, apps_directory, allow_conflicts=False):
    """Collect effective global and app-specific color overrides.

    Args:
        token_directory: Directory containing global token layers.
        apps_directory: Directory containing app adapters and local layers.
        allow_conflicts: Use directly declared app values when layers conflict.

    Returns:
        Usage details keyed by namespace and fully qualified token path.
    """
    global_paths = token_document_paths(token_directory)
    layers = [
        (path, token_namespace(path), load_token_header(path), load_yaml(path))
        for path in global_paths
    ]
    global_tokens = load_token_documents(token_directory)
    details = {}

    global_declarations = {}
    for path, namespace, metadata, document in layers:
        if metadata["type"] != "color":
            continue
        for name, raw_value in flatten_variables(document):
            global_declarations.setdefault((namespace, name), []).append(
                (metadata["hierarchy"], path, raw_value)
            )

    for (namespace, name), declarations in global_declarations.items():
        declarations = sorted(
            declarations, key=lambda item: (item[0], str(item[1]))
        )
        if len(declarations) < 2:
            continue
        history = []
        for index, (_, source_path, raw_value) in enumerate(declarations):
            try:
                declared_value = resolve_references(raw_value, global_tokens)
            except TokenReferenceError:
                declared_value = raw_value
            source = source_path.relative_to(token_directory).as_posix()
            item = {
                "value": declared_value,
                "source": source,
                "active": index == len(declarations) - 1,
            }
            reference_match = REFERENCE_PATTERN.fullmatch(str(raw_value))
            if reference_match:
                item["reference"] = reference_match.group(1)
            if not item["active"]:
                item["overridden_by"] = declarations[index + 1][1].relative_to(
                    token_directory
                ).as_posix()
            history.append(item)
        variable = f"{namespace}.{name}"
        superseded_references = {
            item["reference"]
            for item in history
            if not item["active"] and item.get("reference")
        }
        if superseded_references:
            details.setdefault(namespace, {}).setdefault(variable, {})[
                "superseded_references"
            ] = superseded_references
        if len({str(item["value"]) for item in history}) < 2:
            continue
        details.setdefault(namespace, {}).setdefault(variable, {})[
            "global_override"
        ] = {"history": history}

    for app_directory in sorted(apps_directory.iterdir()):
        if not app_directory.is_dir():
            continue
        app_paths = app_token_document_paths(app_directory)
        if not app_paths:
            continue
        try:
            app_tokens = load_token_documents(token_directory, [app_directory])
        except TokenConflictError:
            if not allow_conflicts:
                raise
            app_tokens = None

        app_declarations = {}
        for path in app_paths:
            metadata = load_token_header(path)
            if metadata["type"] != "color":
                continue
            namespace = token_namespace(path)
            for name, raw_value in flatten_variables(load_yaml(path)):
                app_declarations.setdefault((namespace, name), []).append(
                    (metadata["hierarchy"], path, raw_value)
                )

        for (namespace, name), declarations in app_declarations.items():
            app_only = False
            try:
                original = _nested_value(global_tokens[namespace], name)
            except (KeyError, TypeError):
                original = None
                app_only = True
            active = max(declarations, key=lambda item: (item[0], str(item[1])))
            if app_tokens is not None:
                active_value = _nested_value(app_tokens[namespace], name)
            else:
                try:
                    active_value = resolve_references(active[2], global_tokens)
                except TokenReferenceError:
                    active_value = active[2]
            if not app_only and original == active_value:
                continue
            variable = f"{namespace}.{name}"
            variable_details = details.setdefault(namespace, {}).setdefault(
                variable, {}
            )
            if app_only:
                variable_details["app_only"] = True
            reference_match = REFERENCE_PATTERN.fullmatch(str(active[2]))
            if reference_match:
                variable_details["reference"] = reference_match.group(1)
            override_details = variable_details.setdefault("app_overrides", {})
            sorted_declarations = sorted(
                declarations, key=lambda item: (item[0], str(item[1]))
            )
            for index, declaration in enumerate(sorted_declarations):
                _, path, raw_value = declaration
                try:
                    declared_value = resolve_references(
                        raw_value, app_tokens or global_tokens
                    )
                except TokenReferenceError:
                    declared_value = raw_value
                if original == declared_value and declaration != active:
                    continue
                source = path.relative_to(apps_directory).as_posix()
                override_details[source] = {
                    "value": declared_value,
                    "active": declaration == active,
                }
                if declaration != active:
                    override_details[source]["overridden_by"] = (
                        sorted_declarations[index + 1][1]
                        .relative_to(apps_directory)
                        .as_posix()
                    )
                reference_match = REFERENCE_PATTERN.fullmatch(str(raw_value))
                if reference_match:
                    override_details[source]["reference"] = reference_match.group(1)
    return details


def merge_usage_details(usage, overrides, app_reference_sources=None):
    """Merge override annotations and propagate app-only token usage."""
    for namespace, variables in overrides.items():
        namespace_usage = usage.setdefault(namespace, {})
        for variable, override_details in variables.items():
            namespace_usage.setdefault(
                variable, {"apps": set(), "direct_apps": set(), "variables": set()}
            ).update(override_details)

    variables = {
        variable: details
        for namespace_usage in usage.values()
        for variable, details in namespace_usage.items()
    }

    def expand(reference):
        return {
            variable
            for variable in variables
            if variable == reference or variable.startswith(f"{reference}.")
        }

    for reference, sources in (app_reference_sources or {}).items():
        for target in expand(reference):
            variables[target].setdefault("apps", set()).update(sources)
            if target == reference:
                variables[target].setdefault("direct_apps", set()).update(sources)

    for source, source_details in variables.items():
        reference = source_details.get("reference")
        if not reference:
            continue
        for target in expand(reference):
            variables[target].setdefault("variables", set()).add(source)

    for source, source_details in variables.items():
        for reference in source_details.get("superseded_references", set()):
            for target in expand(reference):
                variables[target].setdefault("superseded_variables", set()).add(
                    source
                )

    changed = True
    while changed:
        changed = False
        for source_details in variables.values():
            reference = source_details.get("reference")
            if not reference:
                continue
            for target in expand(reference):
                target_apps = variables[target].setdefault("apps", set())
                before = len(target_apps)
                target_apps.update(source_details.get("apps", set()))
                changed |= before != len(target_apps)
    return usage


def include_app_only_variables(tokens, variable_usage):
    """Add representative app-only values to a copy used by the report."""
    report_tokens = copy.deepcopy(tokens)
    for namespace, variables in variable_usage.items():
        for variable, details in variables.items():
            if not details.get("app_only"):
                continue
            active = [
                (source, override["value"])
                for source, override in details.get("app_overrides", {}).items()
                if override["active"]
            ]
            if not active:
                continue
            value = sorted(active)[0][1]
            path = variable.split(".")[1:]
            target = report_tokens.setdefault(namespace, {})
            for part in path[:-1]:
                target = target.setdefault(part, {})
            target.setdefault(path[-1], value)
    return report_tokens


def format_token_error(error, root=ROOT):
    """Format token validation failures as concise command-line guidance."""
    if not isinstance(error, TokenConflictError):
        return f"ERROR: {error}"

    files = []
    for path in error.files:
        try:
            path = path.relative_to(root)
        except ValueError:
            pass
        files.append(f"  - {path}")
    return "\n".join(
        [
            "ERROR: Token override conflict",
            f"  Variable: {error.namespace}.{error.token_path}",
            f"  Hierarchy: {error.hierarchy}",
            "  These files assign different values:",
            *files,
            "  Fix: increase snowyOwl.hierarchy in the file that should override.",
        ]
    )


def build_variable_cards(namespace, values, variable_usage=None):
    """Render HTML cards for every scalar token in one namespace."""
    variable_usage = variable_usage or {}
    cards = []
    for name, value in flatten_variables(values):
        variable = f"{namespace}.{name}"
        token_id = f"token-{report_section_id(variable)}"
        escaped_value = html.escape(str(value))
        details = variable_usage.get(variable, {})
        status = get_variable_status(details)
        status_label = status.replace("-", " ").title()
        relationships = set(details.get("variables", set()))
        superseded_relationships = set(details.get("superseded_variables", set()))
        superseded_relationships.difference_update(relationships)
        apps = details.get("apps", set())
        app_overrides = details.get("app_overrides", {})
        global_override = details.get("global_override")
        reference = details.get("reference")
        app_only = details.get("app_only", False)

        def reference_link(
            markup, target, tooltip_text=None, show_tooltip=True
        ):
            label = tooltip_text or f"Value from {target}"
            escaped_label = html.escape(label)
            tooltip = (
                f'<span class="value-tooltip" role="tooltip">'
                f"{escaped_label}</span>"
                if show_tooltip
                else ""
            )
            return (
                f'<a class="color-reference" '
                f'href="#token-{report_section_id(target)}" '
                f'aria-label="{escaped_label}">{markup}{tooltip}</a>'
            )

        def usage_list(
            items,
            link_tokens=False,
            direct_items=None,
            overrides=None,
            superseded_items=None,
        ):
            direct_items = direct_items or set()
            overrides = overrides or {}
            superseded_items = superseded_items or set()
            list_items = []
            for item in sorted(items):
                if link_tokens:
                    item_class = (
                        ' class="historical-use"'
                        if item in superseded_items
                        else ""
                    )
                    badge = (
                        '<span class="usage-kind">Historical</span>'
                        if item in superseded_items
                        else ""
                    )
                    list_items.append(
                        f'<li{item_class}><a href="#token-{report_section_id(item)}">'
                        f"{html.escape(item)}</a>{badge}</li>"
                    )
                    continue
                if item in overrides:
                    override = overrides[item]
                    code_class = "app-override-value"
                    if override["active"]:
                        code_class += " active-override"
                    else:
                        code_class += " superseded"
                    override_code = (
                        f'<code class="{code_class}">'
                        f'{html.escape(str(override["value"]))}</code>'
                    )
                    if not override["active"]:
                        tooltip_parts = []
                        if override.get("reference"):
                            tooltip_parts.append(
                                f'Value from {override["reference"]}'
                            )
                        tooltip_parts.append(
                            f'Overridden by {override["overridden_by"]}'
                        )
                        tooltip_text = ". ".join(tooltip_parts)
                        if override.get("reference"):
                            override_code = reference_link(
                                override_code,
                                override["reference"],
                                tooltip_text=tooltip_text,
                                show_tooltip=False,
                            )
                        escaped_tooltip = html.escape(tooltip_text)
                        tooltip_markup = "<br>".join(
                            html.escape(part) for part in tooltip_parts
                        )
                        override_code = (
                            '<span class="overridden-color app-overridden-color" tabindex="0" '
                            f'aria-label="{escaped_tooltip}">{override_code}'
                            '<span class="override-tooltip" role="tooltip">'
                            f"{tooltip_markup}</span></span>"
                        )
                    elif override.get("reference"):
                        override_code = reference_link(
                            override_code, override["reference"]
                        )
                    list_items.append(
                        '<li class="override-use">'
                        f'<span class="app-name">{html.escape(item)}</span>'
                        '<span class="app-override">'
                        f'{override_code}'
                        "</span></li>"
                    )
                    continue
                use_class = "direct-use" if item in direct_items else "indirect-use"
                use_label = "Direct" if item in direct_items else "Indirect"
                list_items.append(
                    f'<li class="{use_class}">'
                    f'<span class="app-name">{html.escape(item)}</span>'
                    f'<span class="usage-kind">{use_label}</span></li>'
                )
            return f'<ul class="usage-list">{"".join(list_items)}</ul>'

        def color_code(code, extra_class="", link_target=None):
            classes = f"color-value{extra_class}"
            markup = f'<code class="{classes}">{html.escape(str(code))}</code>'
            if link_target:
                return reference_link(markup, link_target)
            return markup

        if app_only:
            color_value = '<span class="app-only-label">App-only</span>'
        elif global_override:
            history_codes = []
            for item in global_override["history"]:
                if item["active"]:
                    history_codes.append(
                        color_code(
                            item["value"], " override-value", item.get("reference")
                        )
                    )
                    continue
                tooltip_parts = []
                if item.get("reference"):
                    tooltip_parts.append(f'Value from {item["reference"]}')
                tooltip_parts.append(f'Overridden by {item["overridden_by"]}')
                tooltip_text = ". ".join(tooltip_parts)
                aria_label = html.escape(tooltip_text)
                tooltip = "<br>".join(html.escape(part) for part in tooltip_parts)
                historical_code = color_code(item["value"], " original-value")
                if item.get("reference"):
                    historical_code = reference_link(
                        historical_code,
                        item["reference"],
                        tooltip_text=tooltip_text,
                        show_tooltip=False,
                    )
                history_codes.append(
                    '<span class="overridden-color" tabindex="0" '
                    f'aria-label="{aria_label}">'
                    f'{historical_code}'
                    f'<span class="override-tooltip" role="tooltip">{tooltip}</span>'
                    "</span>"
                )
            color_value = (
                '<span class="color-values global-override">'
                f'{"".join(history_codes)}</span>'
            )
        else:
            color_value = color_code(value, link_target=reference)

        cards.append(
            "\n".join(
                [
                    f'      <article class="token" id="{token_id}">',
                    '        <div class="token-preview">',
                    (
                        '          <div class="swatch" '
                        f'style="background: {escaped_value}" '
                        f'aria-label="Color {escaped_value}"></div>'
                    ),
                    f'          <div class="text-sample" style="color: {escaped_value}">owl</div>',
                    f"          {color_value}",
                    f'          <span class="status {status}">{status_label}</span>',
                    "        </div>",
                    f'        <code class="variable-name">{html.escape(variable)}</code>',
                    '        <div class="usage-breakdown">',
                    '          <div class="usage-row variable-usage"><strong>Variables</strong>'
                    f"{usage_list(relationships | superseded_relationships, link_tokens=True, superseded_items=superseded_relationships)}</div>",
                    '          <div class="usage-row app-usage"><strong>Apps</strong>'
                    f"{usage_list(set(apps) | set(app_overrides), direct_items=details.get('direct_apps', set()), overrides=app_overrides)}</div>",
                    "        </div>",
                    "      </article>",
                ]
            )
        )
    return cards


def css_font_stack(font_config, default):
    """Build a CSS font-family stack from a typography token role."""
    families = [
        item.get("family") if isinstance(item, dict) else item
        for item in font_config.get("fonts", [])
    ]
    families = [family for family in families if isinstance(family, str)]
    if not families:
        return default
    generic_families = {"cursive", "fantasy", "monospace", "sans-serif", "serif"}
    return ", ".join(
        family if family in generic_families else f'"{family}"' for family in families
    )


def build_font_cards(typography):
    """Render typography preview cards from resolved font tokens."""
    cards = []
    for namespace, config in typography.items():
        if not isinstance(config, dict):
            continue
        title = namespace.replace("-", " ").title()
        sample = "Aa Bb Cc 0123 — Snowy Owl"
        families = [
            item.get("family") if isinstance(item, dict) else item
            for item in config.get("fonts", [])
        ]
        primary = families[0] if families else "Not specified"
        fallback = families[1:]
        stack = css_font_stack(config, namespace)
        metadata = [f"Primary: {primary}"]
        default_style = config.get("defaultStyle", "regular")
        primary_config = config.get("fonts", [{}])[0] if families else {}
        style = primary_config.get("styles", {}).get(default_style, {})
        if style.get("postScriptName"):
            metadata.append(f"PostScript: {style['postScriptName']}")
        metadata.append(f"Style: {default_style}")
        metadata.append(f"Fallback: {', '.join(fallback) if fallback else 'none'}")
        cards.append(
            "\n".join(
                [
                    '      <article class="font-card">',
                    f"        <h3>{title}</h3>",
                    f'        <p class="font-sample" style="font-family: {html.escape(stack, quote=True)}">{html.escape(sample)}</p>',
                    f"        <p>{html.escape('; '.join(metadata))}</p>",
                    "      </article>",
                ]
            )
        )
    return cards


def group_report_metadata(token_metadata):
    """Group merged token namespaces into metadata-driven report sections."""
    groups = {}
    for document in token_metadata:
        key = (document["name"], document["type"])
        group = groups.setdefault(
            key,
            {
                "name": document["name"],
                "type": document["type"],
                "namespaces": [],
            },
        )
        group["namespaces"].append(document["namespace"])
    return list(groups.values())


def report_section_id(name):
    """Convert a report label or token path into a stable HTML identifier."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def report_type_icon(document_type):
    """Return the navigation icon SVG for a report document type."""
    paths = {
        "contrast-rules": '<path d="M4 19V9m6 10V5m6 14v-7m4 7V3"/>',
        "color": '<circle cx="12" cy="12" r="8"/><path d="M12 4a8 8 0 0 0 0 16Z"/>',
        "typography": '<path d="M5 6V4h14v2M12 4v16m-4 0h8"/>',
    }
    path = paths.get(document_type, '<circle cx="12" cy="12" r="7"/>')
    return (
        '<svg class="nav-icon" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true">{path}</svg>'
    )


def report_token_value(tokens, token_metadata, document_type, path, fallback):
    """Read a report theme value by metadata type instead of token filename.

    Args:
        tokens: Resolved documents keyed by namespace.
        token_metadata: Metadata describing each token document.
        document_type: Metadata type to search.
        path: Property path within the matching document.
        fallback: Value returned when the property is unavailable.

    Returns:
        The resolved property value or ``fallback``.
    """
    for metadata in token_metadata:
        if metadata["type"] != document_type:
            continue
        value = tokens.get(metadata["namespace"], {})
        for part in path:
            if not isinstance(value, dict) or part not in value:
                break
            value = value[part]
        else:
            return value
    return fallback


def report_font_configs(tokens, token_metadata):
    """Collect typography configurations declared by report metadata."""
    configs = []
    for metadata in token_metadata:
        if metadata["type"] != "typography":
            continue
        document = tokens.get(metadata["namespace"], {})
        configs.extend(
            config
            for config in document.values()
            if isinstance(config, dict) and config.get("fonts")
        )
    return configs


def summarize_usage(namespaces, tokens, variable_usage):
    """Count variables in each report usage state for namespaces."""
    counts = {
        "used": 0,
        "referenced": 0,
        "historical": 0,
        "unused": 0,
    }
    for namespace in namespaces:
        for name, _ in flatten_variables(tokens[namespace]):
            variable = f"{namespace}.{name}"
            status = get_variable_status(
                variable_usage.get(namespace, {}).get(variable, {})
            )
            counts[status] += 1
    return counts


def build_html_report(
    rows,
    minimum,
    tokens=None,
    variable_usage=None,
    token_metadata=None,
    validation_skipped=False,
):
    """Build the self-contained token and accessibility dashboard.

    Args:
        rows: Evaluated contrast-rule rows.
        minimum: Required project contrast ratio.
        tokens: Resolved documents keyed by namespace.
        variable_usage: Direct and indirect usage details by namespace.
        token_metadata: Metadata controlling report sections.
        validation_skipped: Display a warning that policy checks were bypassed.

    Returns:
        Complete HTML document text.
    """
    cards = []
    for name, foreground, background, ratio, passes in rows:
        result = "PASS" if passes else "FAIL"
        cards.append(
            "\n".join(
                [
                    f'      <article class="pair {result.lower()}">',
                    (
                        '        <div class="sample" '
                        f'style="color: {html.escape(foreground)}; '
                        f'background: {html.escape(background)}">'
                        f'{html.escape(name)}</div>'
                    ),
                    '        <dl>',
                    f'          <div><dt>Foreground</dt><dd>{html.escape(foreground)}</dd></div>',
                    f'          <div><dt>Background</dt><dd>{html.escape(background)}</dd></div>',
                    f'          <div><dt>Ratio</dt><dd>{ratio:.4f}:1</dd></div>',
                    f'          <div><dt>Result</dt><dd>{result}</dd></div>',
                    '        </dl>',
                    '      </article>',
                ]
            )
        )

    variable_usage = variable_usage or {}
    tokens = include_app_only_variables(tokens or {}, variable_usage)
    debug_banner = (
        '        <p class="debug-banner" role="status">Validation skipped — '
        "this report is for visual debugging only.</p>"
        if validation_skipped
        else ""
    )
    report_groups = group_report_metadata(token_metadata or [])
    navigation = []
    report_sections = []
    for group_index, group in enumerate(report_groups):
        section_id = report_section_id(group["name"])
        current = ' aria-current="page"' if group_index == 0 else ""
        navigation.append(
            f'      <a class="nav-link" href="#{section_id}"{current}>'
            f'{report_type_icon(group["type"])}'
            f'{html.escape(group["name"])}</a>'
        )
        report_sections.extend(
            [
                f'    <section class="report-section" id="{section_id}">',
                f"      <h2>{html.escape(group['name'])}</h2>",
            ]
        )
        if group["type"] == "contrast-rules":
            report_sections.extend(
                [
                    '      <div class="summary">',
                    f"        <span>Project minimum: <strong>{minimum}:1</strong></span>",
                    '        <div class="wcag-popover" tabindex="0" aria-describedby="wcag-tooltip">',
                    '          <span class="wcag-trigger">WCAG</span>',
                    '          <div class="wcag-tooltip" id="wcag-tooltip" role="tooltip">',
                    "            <p><strong>Contrast standards</strong></p>",
                    '            <table aria-label="WCAG contrast thresholds">',
                    "              <thead><tr><th>Target</th><th>Minimum</th></tr></thead>",
                    "              <tbody>",
                    "                <tr><td>AA normal text</td><td>4.5:1</td></tr>",
                    "                <tr><td>AA large text</td><td>3:1</td></tr>",
                    "                <tr><td>AAA normal text</td><td>7:1</td></tr>",
                    "                <tr><td>AAA large text</td><td>4.5:1</td></tr>",
                    f"                <tr><td>Snowy Owl required pairs</td><td>{minimum}:1</td></tr>",
                    "              </tbody>",
                    "            </table>",
                    "          </div>",
                    "        </div>",
                    "      </div>",
                    "      <h3>Required pairs</h3>",
                    '      <div class="pairs" aria-label="Required contrast pairs">',
                    *cards,
                    "      </div>",
                ]
            )
        elif group["type"] == "color":
            counts = summarize_usage(
                group["namespaces"], tokens, variable_usage
            )
            total = sum(counts.values())
            report_sections.extend(
                [
                    '      <div class="color-overview">',
                    '        <div class="color-summary" aria-label="Color variable status summary">',
                    f"          <span><strong>{total}</strong> variables</span>",
                    f"          <span><strong>{counts['used']}</strong> used</span>",
                    f"          <span><strong>{counts['referenced']}</strong> referenced</span>",
                    f"          <span><strong>{counts['historical']}</strong> historical</span>",
                    f"          <span><strong>{counts['unused']}</strong> unused</span>",
                    '          <div class="status-popover" tabindex="0" aria-describedby="status-tooltip" aria-label="Color status definitions">',
                    '            <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/></svg>',
                    '            <div class="status-tooltip" id="status-tooltip" role="tooltip">',
                    "            <p><strong>Color status</strong></p>",
                    '            <div class="status-definition"><span class="status used">Used</span><span>Reaches an app.</span></div>',
                    '            <div class="status-definition"><span class="status referenced">Referenced</span><span>Used by other active variables.</span></div>',
                    '            <div class="status-definition"><span class="status historical">Historical</span><span>Referenced only by overridden values.</span></div>',
                    '            <div class="status-definition"><span class="status unused">Unused</span><span>Has no references.</span></div>',
                    "            </div>",
                    "          </div>",
                    "        </div>",
                    "      </div>",
                ]
            )
            for namespace in group["namespaces"]:
                namespace_title = namespace.replace("-", " ").title()
                report_sections.extend(
                    [
                        f"      <h3>{html.escape(namespace_title)}</h3>",
                        f'      <div class="tokens" aria-label="{html.escape(namespace_title)}">',
                        *build_variable_cards(
                            namespace,
                            tokens[namespace],
                            variable_usage.get(namespace, {}),
                        ),
                        "      </div>",
                    ]
                )
        elif group["type"] == "typography":
            for namespace in group["namespaces"]:
                report_sections.extend(
                    [
                        f'      <div class="fonts" aria-label="{html.escape(group["name"])}">',
                        *build_font_cards(tokens[namespace]),
                        "      </div>",
                    ]
                )
        else:
            raise ValueError(f"Unsupported report type: {group['type']}")
        report_sections.append("    </section>")

    token_metadata = token_metadata or []
    light_background = report_token_value(
        tokens, token_metadata, "color", ("light", "background"), "#F8F9FA"
    )
    dark_background = report_token_value(
        tokens, token_metadata, "color", ("dark", "background"), "#18191B"
    )
    light_surface = report_token_value(
        tokens, token_metadata, "color", ("light", "secondaryBackground"), "#F1F3F5"
    )
    dark_surface = report_token_value(
        tokens, token_metadata, "color", ("dark", "secondaryBackground"), "#202225"
    )
    light_foreground = report_token_value(
        tokens, token_metadata, "color", ("light", "foreground"), "#34383C"
    )
    dark_foreground = report_token_value(
        tokens, token_metadata, "color", ("dark", "foreground"), "#F8F9FA"
    )
    light_primary = report_token_value(
        tokens, token_metadata, "color", ("light", "accent"), "#1450A0"
    )
    dark_primary = report_token_value(
        tokens, token_metadata, "color", ("dark", "accent"), "#FD7E14"
    )
    font_configs = report_font_configs(tokens, token_metadata)
    ui_config = next(
        (
            config
            for config in font_configs
            if "monospace" not in " ".join(map(str, config.values())).lower()
        ),
        {},
    )
    monospace_config = next(
        (
            config
            for config in font_configs
            if "mono" in " ".join(map(str, config.values())).lower()
        ),
        {},
    )
    ui_font_stack = css_font_stack(ui_config, 'Inter, "Noto Sans", sans-serif')
    monospace_font_stack = css_font_stack(
        monospace_config, '"JetBrains Mono", monospace'
    )

    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '  <meta charset="utf-8">',
            '  <meta name="viewport" content="width=device-width, initial-scale=1">',
            "  <title>Snowy Owl Token Usage and Accessibility</title>",
            "  <style>",
            f"    :root {{ --page-background: {light_background}; --page-foreground: {light_foreground}; --surface: {light_surface}; --primary: {light_primary}; --text-secondary: color-mix(in srgb, var(--page-foreground) 76%, transparent); --divider: color-mix(in srgb, var(--page-foreground) 16%, transparent); --action-hover: color-mix(in srgb, var(--page-foreground) 8%, transparent); --action-selected: color-mix(in srgb, var(--primary) 12%, transparent); --card-shadow: hsla(220, 30%, 5%, .07) 0 4px 16px 0, hsla(220, 25%, 10%, .07) 0 8px 16px -5px; color-scheme: light; font-family: {ui_font_stack}; }}",
            f'    :root[data-theme="dark"] {{ --page-background: {dark_background}; --page-foreground: {dark_foreground}; --surface: {dark_surface}; --primary: {dark_primary}; --text-secondary: color-mix(in srgb, var(--page-foreground) 72%, transparent); --divider: color-mix(in srgb, var(--page-foreground) 24%, transparent); --action-hover: color-mix(in srgb, var(--page-foreground) 10%, transparent); --action-selected: color-mix(in srgb, var(--primary) 14%, transparent); --card-shadow: hsla(220, 30%, 5%, .7) 0 4px 16px 0, hsla(220, 25%, 10%, .8) 0 8px 16px -5px; color-scheme: dark; }}',
            "    * { box-sizing: border-box; }",
            "    body { margin: 0; background: var(--page-background); color: var(--page-foreground); font-size: .875rem; font-weight: 400; line-height: 1.5; transition: background-color .2s, color .2s; }",
            "    .dashboard { display: grid; grid-template-columns: 15rem minmax(0, 1fr); min-height: 100vh; }",
            "    .sidebar { position: sticky; top: 0; height: 100vh; border-right: 1px solid var(--divider); background: var(--surface); }",
            "    .sidebar-header { display: flex; align-items: center; gap: .75rem; min-height: 4rem; padding: .75rem 1rem; }",
            "    .owl-logo { width: 2rem; height: 2rem; color: var(--primary); stroke: currentColor; }",
            "    .sidebar-title { font-size: 1.125rem; font-weight: 600; line-height: 1.5; }",
            "    .sidebar-divider { border-top: 1px solid var(--divider); }",
            "    .sidebar nav { display: grid; gap: .125rem; padding: .5rem; }",
            "    .nav-link { display: flex; align-items: center; gap: .5rem; min-height: 2.5rem; padding: .375rem .5rem; border-radius: .5rem; color: inherit; font-family: inherit; font-size: .875rem; font-weight: 500; line-height: 1.43; text-decoration: none; }",
            "    .nav-link:hover, .nav-link:focus-visible { background: var(--action-hover); outline: none; }",
            "    .nav-link[aria-current=\"page\"] { background: var(--action-selected); color: var(--primary); }",
            "    .nav-icon { width: 1.25rem; height: 1.25rem; margin-right: .25rem; flex: 0 0 auto; }",
            "    .content-shell { min-width: 0; }",
            "    .report-content { width: min(106.25rem, calc(100% - 3rem)); margin: 0 auto; padding: 1.5rem 0 3rem; }",
            "    .page-header { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: 2rem; padding-top: .75rem; }",
            "    h1 { margin: 0; font-size: 1.5rem; font-weight: 600; line-height: 1.5; }",
            "    h2 { margin: 0 0 1rem; font-size: 1.125rem; font-weight: 600; line-height: 1.5; }",
            "    h3 { margin: 1.5rem 0 1rem; font-size: 1.125rem; font-weight: 600; line-height: 1.5; }",
            "    .breadcrumbs { display: flex; gap: .375rem; margin-bottom: .375rem; color: var(--text-secondary); font-size: .75rem; font-weight: 400; line-height: 1.5; }",
            "    .breadcrumbs strong { color: var(--page-foreground); font-weight: 500; }",
            "    .report-section { scroll-margin-top: 1.5rem; margin-bottom: 3rem; }",
            "    .color-overview { margin-bottom: 1rem; }",
            "    .color-summary { display: flex; flex-wrap: wrap; align-items: center; gap: .5rem 1.5rem; color: var(--text-secondary); }",
            "    .color-summary strong { color: var(--page-foreground); font-weight: 600; }",
            "    .status-popover { position: relative; display: grid; width: 2rem; height: 2rem; place-items: center; margin-left: -.75rem; border-radius: 50%; color: var(--text-secondary); }",
            "    .status-popover:hover, .status-popover:focus-visible { background: var(--action-hover); color: var(--page-foreground); outline: none; }",
            "    .status-popover svg { width: 1.25rem; height: 1.25rem; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; }",
            "    .status-tooltip { position: absolute; z-index: 10; top: calc(100% + .5rem); right: 0; width: 19rem; padding: 1rem; border: 1px solid var(--divider); border-radius: .5rem; background: var(--surface); box-shadow: var(--card-shadow); color: var(--page-foreground); visibility: hidden; opacity: 0; pointer-events: auto; transform: translateY(-.25rem); transition: opacity .15s ease, transform .15s ease; }",
            "    .status-popover:hover .status-tooltip, .status-popover:focus .status-tooltip, .status-popover:focus-within .status-tooltip, .status-popover.popover-open .status-tooltip { visibility: visible; opacity: 1; transform: translateY(0); }",
            "    .status-tooltip p { margin: 0 0 .5rem; }",
            "    .status-tooltip p:last-child { margin-bottom: 0; }",
            "    .status-tooltip b { font-weight: 600; }",
            "    .status-definition { display: grid; grid-template-columns: 7.5rem 1fr; gap: .75rem; align-items: start; margin-top: .5rem; }",
            "    .status-definition .status { min-width: 0; }",
            "    button { display: grid; width: 2.75rem; height: 2.75rem; place-items: center; padding: .5rem; border: 0; border-radius: 50%; background: transparent; color: var(--primary); cursor: pointer; transition: background-color .15s, box-shadow .15s; }",
            "    button:hover, button:focus-visible { background: var(--action-hover); outline: 2px solid var(--primary); outline-offset: 2px; }",
            "    .theme-icon { width: 1.25rem; height: 1.25rem; stroke: currentColor; }",
            "    .icon-sun { display: none; }",
            '    :root[data-theme="dark"] .icon-sun { display: block; }',
            '    :root[data-theme="dark"] .icon-moon { display: none; }',
            "    .visually-hidden { position: absolute; width: 1px; height: 1px; padding: 0; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }",
            "    .summary { display: flex; align-items: center; gap: .75rem; margin-bottom: 1.5rem; }",
            "    .wcag-popover { position: relative; border-radius: 999px; }",
            "    .wcag-trigger { display: inline-block; padding: .25rem .625rem; border-radius: 999px; background: var(--action-selected); color: var(--primary); font-size: .8125rem; font-weight: 500; line-height: 1.5; }",
            "    .wcag-popover:hover .wcag-trigger, .wcag-popover:focus-visible .wcag-trigger { outline: 2px solid var(--primary); outline-offset: 2px; }",
            "    .wcag-tooltip { position: absolute; z-index: 10; top: calc(100% + .5rem); left: 0; width: min(32rem, calc(100vw - 3rem)); padding: 1rem; border: 1px solid var(--divider); border-radius: .5rem; background: var(--surface); box-shadow: var(--card-shadow); visibility: hidden; opacity: 0; pointer-events: auto; transform: translateY(-.25rem); transition: opacity .15s ease, transform .15s ease; }",
            "    .wcag-popover:hover .wcag-tooltip, .wcag-popover:focus .wcag-tooltip, .wcag-popover:focus-within .wcag-tooltip, .wcag-popover.popover-open .wcag-tooltip { visibility: visible; opacity: 1; transform: translateY(0); }",
            "    .wcag-tooltip p { margin-top: 0; }",
            "    table { width: 100%; border-collapse: collapse; }",
            "    th, td { padding: .625rem .75rem; border-bottom: 1px solid var(--divider); text-align: left; }",
            "    th { font-weight: 600; }",
            "    .pairs { display: grid; grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr)); gap: 1rem; }",
            "    .pair { overflow: hidden; border: 1px solid var(--divider); border-radius: .5rem; background: var(--surface); box-shadow: var(--card-shadow); }",
            "    .sample { padding: 2rem 1rem; font-size: 1.125rem; font-weight: 600; text-align: center; }",
            "    dl { margin: 0; padding: .75rem 1rem; }",
            "    dl div { display: flex; justify-content: space-between; gap: 1rem; padding: .125rem 0; }",
            "    dt { color: var(--text-secondary); font-size: .75rem; font-weight: 400; line-height: 1.5; }",
            f"    code, dd {{ font-family: {monospace_font_stack}; }}",
            "    dd { margin: 0; }",
            "    .pass dd:last-child { color: #12633D; font-weight: 500; }",
            "    .fail dd:last-child { color: #A52834; font-weight: 500; }",
            "    .report-section > p, .font-card > p:last-child { color: var(--text-secondary); }",
            "    .debug-banner { margin: 0 0 1rem; padding: .75rem 1rem; border: 1px solid #FFC107; border-radius: .5rem; background: color-mix(in srgb, #FFC107 14%, transparent); color: var(--page-foreground); }",
            "    .tokens { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; align-items: start; }",
            "    .token { display: grid; grid-template-columns: 7.25rem 1fr; gap: .75rem 1rem; align-items: start; align-content: start; padding: 1rem; border: 1px solid var(--divider); border-radius: .5rem; background: var(--surface); box-shadow: var(--card-shadow); scroll-margin-top: 1.5rem; transition: background-color .15s ease, border-color .15s ease; }",
            "    .token:hover { background: var(--action-hover); }",
            "    .token:target { border-color: var(--primary); outline: 2px solid color-mix(in srgb, var(--primary) 28%, transparent); }",
            "    .token-preview { display: grid; grid-row: 1 / 4; justify-items: center; gap: .375rem; text-align: center; }",
            "    .swatch { width: 4rem; height: 3rem; border: 1px solid var(--divider); border-radius: .5rem; }",
            "    .text-sample { font-size: .875rem; font-weight: 400; line-height: 1.5; }",
            "    .color-value { font-size: .875rem; }",
            "    .app-only-label { padding: .125rem .5rem; border: 1px solid var(--primary); border-radius: 999px; color: var(--primary); font-size: .75rem; font-weight: 500; }",
            "    .color-values { display: grid; gap: .125rem; }",
            "    .original-value { color: var(--text-secondary); text-decoration: line-through; }",
            "    .override-value { color: var(--page-foreground); }",
            "    .color-reference { position: relative; display: inline-block; color: var(--primary); text-decoration: none; }",
            "    .color-reference:hover { text-decoration: underline; }",
            "    .overridden-color { position: relative; display: inline-block; }",
            "    .app-overridden-color .override-tooltip { display: none; }",
            "    .app-floating-tooltip { position: fixed; z-index: 100; width: max-content; max-width: 18rem; padding: .375rem .5rem; border-radius: .375rem; background: var(--page-foreground); color: var(--page-background); font-size: .75rem; font-weight: 400; line-height: 1.4; pointer-events: none; }",
            "    .override-tooltip, .value-tooltip { position: absolute; z-index: 30; bottom: calc(100% + .5rem); left: 50%; width: max-content; max-width: 18rem; padding: .375rem .5rem; border-radius: .375rem; background: var(--page-foreground); color: var(--page-background); font-size: .75rem; font-weight: 400; line-height: 1.4; text-decoration: none; opacity: 0; pointer-events: none; transform: translate(-50%, .25rem); transition: opacity .15s ease, transform .15s ease; }",
            "    .overridden-color:hover .override-tooltip, .overridden-color:focus .override-tooltip, .overridden-color:focus-within .override-tooltip, .color-reference:hover .value-tooltip, .color-reference:focus .value-tooltip { opacity: 1; transform: translate(-50%, 0); }",
            "    .variable-name { font-size: .875rem; font-weight: 500; line-height: 1.5; }",
            "    .usage-list a { color: var(--primary); text-decoration: none; }",
            "    .usage-list a:hover { text-decoration: underline; }",
            "    .token code { overflow-wrap: anywhere; }",
            "    .usage-breakdown { display: grid; grid-template-columns: 1fr; gap: .5rem; font-size: .875rem; }",
            "    .usage-breakdown div { min-width: 0; padding: .625rem; border: 1px solid var(--divider); border-radius: .5rem; background: var(--page-background); }",
            "    .usage-breakdown strong { display: block; font-size: .75rem; font-weight: 400; line-height: 1.5; color: var(--text-secondary); }",
            "    .usage-list { margin: .25rem 0 0; padding: 0; overflow-y: auto; list-style: none; scrollbar-gutter: stable; }",
            "    .variable-usage .usage-list { height: 3.75rem; }",
            "    .app-usage .usage-list { height: 7.25rem; }",
            "    .usage-list li { padding: .125rem 0; overflow-wrap: anywhere; }",
            "    .app-usage li, .variable-usage li { display: flex; align-items: center; justify-content: space-between; gap: .75rem; min-height: 1.75rem; padding: .125rem 0; }",
            "    .historical-use a { color: var(--text-secondary); text-decoration: line-through; }",
            "    .app-name { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }",
            "    .app-override { display: inline-flex; flex: 0 0 auto; align-items: center; gap: .375rem; }",
            "    .app-override-value { font-size: .75rem; }",
            "    .app-override-value.active-override { padding: .0625rem .375rem; border: 1px solid var(--primary); border-radius: 999px; color: var(--primary); background: color-mix(in srgb, var(--primary) 12%, transparent); }",
            "    .app-override-value.superseded { color: var(--text-secondary); text-decoration: line-through; }",
            "    .usage-kind { flex: 0 0 auto; min-width: 3.75rem; padding: .0625rem .375rem; border: 1px solid var(--divider); border-radius: 999px; color: var(--text-secondary); background: var(--action-hover); font-size: .6875rem; font-weight: 500; line-height: 1.5; text-align: center; }",
            "    .direct-use .usage-kind { border-color: #12633D; color: #12633D; background: color-mix(in srgb, #12633D 12%, transparent); }",
            "    .historical-use .usage-kind { border-color: var(--primary); color: var(--primary); background: var(--action-selected); }",
            '    :root[data-theme="dark"] .direct-use .usage-kind { color: var(--page-foreground); }',
            '    :root[data-theme="dark"] .app-override-value.active-override { color: var(--page-foreground); }',
            "    .fonts { display: grid; grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr)); gap: 1rem; }",
            "    .font-card { padding: 1rem; border: 1px solid var(--divider); border-radius: .5rem; background: var(--surface); box-shadow: var(--card-shadow); }",
            "    .font-card h3, .font-card p { margin: 0 0 .75rem; }",
            "    .font-sample { font-size: 1.125rem; }",
            "    .status { display: inline-block; min-width: 6.5rem; padding: .125rem .5rem; border: 1px solid currentColor; border-radius: 999px; font-size: .8125rem; font-weight: 500; line-height: 1.5; text-align: center; }",
            "    .status.used { color: #12633D; background: color-mix(in srgb, #12633D 12%, transparent); }",
            "    .status.referenced { color: #8A3F00; background: color-mix(in srgb, #FFC107 16%, transparent); }",
            "    .status.historical { color: var(--primary); background: var(--action-selected); }",
            "    .status.unused { color: #A52834; background: color-mix(in srgb, #A52834 12%, transparent); }",
            '    :root[data-theme="dark"] .status.used, :root[data-theme="dark"] .status.referenced, :root[data-theme="dark"] .status.historical, :root[data-theme="dark"] .status.unused, :root[data-theme="dark"] .historical-use .usage-kind { color: var(--page-foreground); }',
            "    @media (max-width: 52rem) { .dashboard { grid-template-columns: 1fr; } .sidebar { position: sticky; z-index: 20; height: auto; border-right: 0; border-bottom: 1px solid var(--divider); } .sidebar-header, .sidebar-divider { display: none; } .sidebar nav { display: flex; overflow-x: auto; } .nav-link { flex: 0 0 auto; } .report-content { width: min(100% - 2rem, 72rem); padding-top: 1rem; } }",
            "    @media (max-width: 44rem) { .tokens { grid-template-columns: 1fr; } .token { grid-template-columns: 6.75rem 1fr; } .wcag-tooltip { position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); } }",
            "  </style>",
            "</head>",
            "<body>",
            '  <div class="dashboard">',
            '    <aside class="sidebar">',
            '      <div class="sidebar-header">',
            '        <svg class="owl-logo" viewBox="0 0 32 32" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 10 4 5l7 3a12 12 0 0 1 10 0l7-3-3 5a12 12 0 1 1-18 0Z"/><circle cx="11" cy="15" r="2.5"/><circle cx="21" cy="15" r="2.5"/><path d="m14 20 2 2 2-2"/></svg>',
            '        <span class="sidebar-title">Dashboard</span>',
            '      </div>',
            '      <div class="sidebar-divider"></div>',
            '      <nav aria-label="Report sections">',
            *navigation,
            "      </nav>",
            "    </aside>",
            '    <div class="content-shell">',
            '      <main class="report-content">',
            '        <header class="page-header">',
            '          <div><div class="breadcrumbs"><span>Dashboard</span><span>/</span><strong>Tokens</strong></div><h1>Token dashboard</h1></div>',
            '          <button id="theme-toggle" type="button" aria-pressed="false" aria-label="Use dark background" title="Use dark background">',
            '            <svg class="theme-icon icon-moon" viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8Z"/></svg>',
            '            <svg class="theme-icon icon-sun" viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.42-1.42M17.66 6.34l1.41-1.41"/></svg>',
            '            <span class="visually-hidden">Use dark background</span>',
            "          </button>",
            "        </header>",
            debug_banner,
            *report_sections,
            "      </main>",
            "    </div>",
            "  </div>",
            "  <script>",
            "    const root = document.documentElement;",
            '    const themeToggle = document.getElementById("theme-toggle");',
            "    function setTheme(theme) {",
            "      root.dataset.theme = theme;",
            '      const dark = theme === "dark";',
            '      const label = dark ? "Use light background" : "Use dark background";',
            '      themeToggle.setAttribute("aria-pressed", String(dark));',
            '      themeToggle.setAttribute("aria-label", label);',
            '      themeToggle.setAttribute("title", label);',
            '      themeToggle.querySelector(".visually-hidden").textContent = label;',
            "    }",
            '    setTheme(window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");',
            '    themeToggle.addEventListener("click", () => {',
            '      setTheme(root.dataset.theme === "dark" ? "light" : "dark");',
            "    });",
            '    document.querySelectorAll(".nav-link").forEach((link) => {',
            '      link.addEventListener("click", () => {',
            '        document.querySelectorAll(".nav-link").forEach((item) => item.removeAttribute("aria-current"));',
            '        link.setAttribute("aria-current", "page");',
            "      });",
            "    });",
            "    const appTooltip = document.createElement(\"div\");",
            "    appTooltip.className = \"app-floating-tooltip\";",
            "    appTooltip.setAttribute(\"role\", \"tooltip\");",
            "    appTooltip.hidden = true;",
            "    document.body.append(appTooltip);",
            "    function hideAppTooltip() { appTooltip.hidden = true; }",
            "    function showAppTooltip(trigger) {",
            "      const source = trigger.querySelector(\".override-tooltip\");",
            "      if (!source) return;",
            "      appTooltip.innerHTML = source.innerHTML;",
            "      appTooltip.hidden = false;",
            "      const rect = trigger.getBoundingClientRect();",
            "      const margin = 8;",
            "      const left = Math.max(margin, Math.min(rect.right - appTooltip.offsetWidth, window.innerWidth - appTooltip.offsetWidth - margin));",
            "      const top = Math.min(rect.bottom + margin, window.innerHeight - appTooltip.offsetHeight - margin);",
            "      appTooltip.style.left = `${left}px`;",
            "      appTooltip.style.top = `${top}px`;",
            "    }",
            "    document.querySelectorAll(\".app-overridden-color\").forEach((trigger) => {",
            "      trigger.addEventListener(\"mouseenter\", () => showAppTooltip(trigger));",
            "      trigger.addEventListener(\"mouseleave\", hideAppTooltip);",
            "      trigger.addEventListener(\"focusin\", () => showAppTooltip(trigger));",
            "      trigger.addEventListener(\"focusout\", hideAppTooltip);",
            "    });",
            "    window.addEventListener(\"scroll\", hideAppTooltip, true);",
            "    window.addEventListener(\"resize\", hideAppTooltip);",
            "    function addDelayedPopover(selector) {",
            "      document.querySelectorAll(selector).forEach((popover) => {",
            "        let closeTimer;",
            "        const open = () => { clearTimeout(closeTimer); popover.classList.add(\"popover-open\"); };",
            "        const closeLater = () => { closeTimer = setTimeout(() => popover.classList.remove(\"popover-open\"), 1000); };",
            "        popover.addEventListener(\"mouseenter\", open);",
            "        popover.addEventListener(\"mouseleave\", closeLater);",
            "        popover.addEventListener(\"focusin\", open);",
            "        popover.addEventListener(\"focusout\", closeLater);",
            "      });",
            "    }",
            "    addDelayedPopover(\".status-popover, .wcag-popover\");",
            "  </script>",
            "</body>",
            "</html>",
            "",
        ]
    )


def parse_args():
    """Parse command-line output options for contrast validation."""
    parser = argparse.ArgumentParser(description="Validate Snowy Owl contrast pairs.")
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="update docs/ACCESSIBILITY.md",
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="generate docs/index.html with rendered color samples and variables",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="generate debugging output without enforcing app, contrast, or font policy",
    )
    return parser.parse_args()


def main():
    """Validate global and app-layer contrast, then generate requested reports."""
    args = parse_args()
    if args.skip_validation:
        print(
            "WARNING: Validation skipped; generated documentation is for debugging only.",
            flush=True,
        )
    token_directory = ROOT / "tokens"
    tokens = load_token_documents(token_directory)
    token_metadata = load_token_metadata(token_directory)
    contrast_namespaces = [
        document["namespace"]
        for document in token_metadata
        if document["type"] == "contrast-rules"
    ]
    if len(contrast_namespaces) != 1:
        raise ValueError("Exactly one token document must have type 'contrast-rules'")
    contrast_config = tokens[contrast_namespaces[0]]
    minimum = float(contrast_config["policy"]["minimum"])
    rows = calculate_contrast_rows(contrast_config)
    for name, fg, bg, ratio, ok in rows:
        print(
            f"{'PASS' if ok else 'FAIL'} {name:22} {fg} on {bg}: {ratio:.4f}:1",
            flush=True,
        )
    app_rows = []
    for app_directory in sorted((ROOT / "apps").iterdir()):
        if args.skip_validation:
            break
        if not app_directory.is_dir() or not app_token_document_paths(app_directory):
            continue
        app_tokens = load_token_documents(token_directory, [app_directory])
        current_rows = calculate_contrast_rows(app_tokens[contrast_namespaces[0]])
        app_rows.extend(current_rows)
        for name, fg, bg, ratio, ok in current_rows:
            print(
                f"{'PASS' if ok else 'FAIL'} "
                f"{app_directory.name}/{name:22} {fg} on {bg}: {ratio:.4f}:1",
                flush=True,
            )
    report = [
        "# Accessibility Report",
        "",
        f"Project minimum: **{minimum}:1** (Snowy Owl policy; stricter than WCAG AAA 7:1 for",
        "normal text).",
        "",
        "| Pair              | Front     | Back      |   Ratio | Result |",
        "| ----------------- | --------- | --------- | ------: | ------ |",
    ]
    for name, fg, bg, ratio, ok in rows:
        result = "PASS" if ok else "FAIL"
        ratio_text = f"{ratio:.2f}:1"
        report.append(
            f"| {name:<17} | `{fg}` | `{bg}` | {ratio_text:>7} | {result:<6} |"
        )
    if args.markdown:
        (ROOT / "docs/ACCESSIBILITY.md").write_text(
            "\n".join(report) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    if args.html:
        html_path = ROOT / "docs/index.html"
        raw_tokens = load_token_documents(token_directory, resolve=False)
        color_documents = {
            document["namespace"]: raw_tokens[document["namespace"]]
            for document in token_metadata
            if document["type"] == "color"
        }
        app_reference_sources = find_app_token_reference_sources(ROOT / "apps")
        variable_usage = analyze_document_usage(
            color_documents, app_reference_sources
        )
        merge_usage_details(
            variable_usage,
            analyze_token_overrides(
                token_directory,
                ROOT / "apps",
                allow_conflicts=args.skip_validation,
            ),
            app_reference_sources,
        )
        html_path.write_text(
            build_html_report(
                rows,
                minimum,
                tokens,
                variable_usage,
                token_metadata,
                validation_skipped=args.skip_validation,
            ),
            encoding="utf-8",
            newline="\n",
        )
        print(f"HTML report: {html_path}")
    if args.skip_validation:
        return 0
    return 1 if any(not row[4] for row in (*rows, *app_rows)) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (TokenHeaderError, TokenReferenceError) as error:
        print(format_token_error(error), file=sys.stderr)
        sys.exit(1)
