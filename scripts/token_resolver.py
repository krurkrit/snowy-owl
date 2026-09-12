"""Load layered YAML token documents and resolve cross-document references."""

import re
from pathlib import Path
from typing import Any, Iterable

import yaml

REFERENCE_PATTERN = re.compile(r"^\{([A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*)\}$")
METADATA_KEY = "snowyOwl"


class TokenReferenceError(ValueError):
    """Raised when a token reference is missing or cyclic."""


class TokenHeaderError(ValueError):
    """Raised when a token document has invalid Snowy Owl metadata."""


class TokenConflictError(TokenHeaderError):
    """Describe conflicting token values declared at one hierarchy."""

    def __init__(self, namespace, token_path, hierarchy, files):
        """Store conflict details for command-line error formatting."""
        self.namespace = namespace
        self.token_path = token_path
        self.hierarchy = hierarchy
        self.files = tuple(files)
        super().__init__(
            f"Token '{namespace}.{token_path}' has different values at "
            f"hierarchy {hierarchy}"
        )


def _read_document(path: Path) -> Any:
    """Parse one UTF-8 YAML document without transforming its content."""
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_token_header(path: Path) -> dict[str, Any]:
    """Read metadata from a token document's ``snowyOwl`` property.

    Args:
        path: YAML token document to inspect.

    Returns:
        Normalized name, type, and hierarchy metadata.

    Raises:
        TokenHeaderError: The metadata is missing or invalid.
    """
    document = _read_document(path)
    metadata = document.get(METADATA_KEY) if isinstance(document, dict) else None
    if (
        not isinstance(metadata, dict)
        or not isinstance(metadata.get("name"), str)
        or not isinstance(metadata.get("type"), str)
    ):
        raise TokenHeaderError(
            f"Invalid token metadata in '{path}'; expected "
            "'snowyOwl: { name: Name, type: document-type }'"
        )
    hierarchy = metadata.get("hierarchy", 0)
    if not isinstance(hierarchy, int) or isinstance(hierarchy, bool) or hierarchy < 0:
        raise TokenHeaderError(
            f"Invalid token metadata in '{path}'; "
            "'snowyOwl.hierarchy' must be a non-negative integer"
        )
    return {
        "name": metadata["name"],
        "type": metadata["type"],
        "hierarchy": hierarchy,
    }


def load_yaml(path: Path) -> Any:
    """Load one UTF-8 YAML document and remove token metadata.

    Args:
        path: YAML document to load.

    Returns:
        Parsed YAML content without the top-level ``snowyOwl`` property.
    """
    document = _read_document(path)
    if isinstance(document, dict) and METADATA_KEY in document:
        document = dict(document)
        del document[METADATA_KEY]
    return document


def token_namespace(path: Path) -> str:
    """Return the filename prefix used as a token namespace.

    Args:
        path: Token document path, such as ``colors.override.yaml``.

    Returns:
        The prefix before the first period, such as ``colors``.
    """
    return path.name.split(".", 1)[0]


def token_document_paths(token_directory: Path) -> list[Path]:
    """Return global token documents in stable filename order.

    Args:
        token_directory: Directory containing global YAML token documents.

    Returns:
        Sorted paths for files ending in ``.yaml`` or ``.yml``.
    """
    return sorted((*token_directory.glob("*.yaml"), *token_directory.glob("*.yml")))


def app_token_document_paths(app_directory: Path) -> list[Path]:
    """Discover app-local YAML documents that declare Snowy Owl metadata.

    Args:
        app_directory: App directory to search recursively.

    Returns:
        Sorted paths for valid app-local token documents.

    Raises:
        TokenHeaderError: A discovered Snowy Owl document has invalid metadata.
    """
    paths = sorted((*app_directory.rglob("*.yaml"), *app_directory.rglob("*.yml")))
    result = []
    for path in paths:
        document = _read_document(path)
        if isinstance(document, dict) and METADATA_KEY in document:
            load_token_header(path)
            result.append(path)
    return result


def _merge(target, incoming, path=(), allow_override=True):
    """Deeply merge one mapping, optionally rejecting conflicting leaves."""
    if not isinstance(incoming, dict):
        raise TokenHeaderError("Token document content must be a mapping")
    for key, value in incoming.items():
        location = (*path, str(key))
        if key not in target:
            target[key] = value
        elif isinstance(target[key], dict) and isinstance(value, dict):
            _merge(target[key], value, location, allow_override)
        elif allow_override:
            target[key] = value
        elif target[key] != value:
            raise TokenHeaderError(
                "Conflicting token values at the same hierarchy: "
                + ".".join(location)
            )
    return target


def _load_layered_documents(
    paths: Iterable[Path],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Merge raw documents by namespace and hierarchy and select metadata."""
    layers = []
    for path in paths:
        header = load_token_header(path)
        layers.append((token_namespace(path), path, header, load_yaml(path)))

    documents = {}
    metadata = []
    for namespace in sorted({layer[0] for layer in layers}):
        namespace_layers = [layer for layer in layers if layer[0] == namespace]
        types = {layer[2]["type"] for layer in namespace_layers}
        if len(types) != 1:
            raise TokenHeaderError(
                f"Token namespace '{namespace}' cannot contain multiple document types"
            )
        merged = {}
        hierarchies = sorted({layer[2]["hierarchy"] for layer in namespace_layers})
        for hierarchy in hierarchies:
            level = {}
            same_level = [
                layer
                for layer in namespace_layers
                if layer[2]["hierarchy"] == hierarchy
            ]
            try:
                for _, _, _, document in sorted(
                    same_level, key=lambda layer: str(layer[1])
                ):
                    _merge(level, document, allow_override=False)
            except TokenHeaderError as error:
                token_path = str(error).rsplit(": ", 1)[-1]
                raise TokenConflictError(
                    namespace,
                    token_path,
                    hierarchy,
                    [layer[1] for layer in same_level],
                ) from None
            _merge(merged, level, allow_override=True)
        documents[namespace] = merged
        highest = max(
            namespace_layers,
            key=lambda layer: (layer[2]["hierarchy"], str(layer[1])),
        )[2]
        metadata.append({"namespace": namespace, **highest})
    return documents, metadata


def _load_scoped_documents(
    token_directory: Path, override_directories: Iterable[Path]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Resolve hierarchy inside each scope, then overlay scopes in order."""
    documents, metadata = _load_layered_documents(
        token_document_paths(token_directory)
    )
    metadata_by_namespace = {
        document["namespace"]: document for document in metadata
    }
    for directory in override_directories:
        paths = app_token_document_paths(Path(directory))
        if not paths:
            continue
        overrides, override_metadata = _load_layered_documents(paths)
        override_metadata_by_namespace = {
            document["namespace"]: document for document in override_metadata
        }
        for namespace, override in overrides.items():
            if namespace in documents:
                global_type = metadata_by_namespace[namespace]["type"]
                app_type = override_metadata_by_namespace[namespace]["type"]
                if global_type != app_type:
                    raise TokenHeaderError(
                        f"Token namespace '{namespace}' has global type "
                        f"'{global_type}' but app type '{app_type}'"
                    )
                _merge(documents[namespace], override, allow_override=True)
            else:
                documents[namespace] = override
            metadata_by_namespace[namespace] = override_metadata_by_namespace[
                namespace
            ]
    return documents, list(metadata_by_namespace.values())


def load_token_metadata(
    token_directory: Path, override_directories: Iterable[Path] = ()
) -> list[dict[str, Any]]:
    """Return metadata for each merged token namespace.

    Args:
        token_directory: Directory containing the base token layers.
        override_directories: App scopes applied after the global scope.

    Returns:
        One normalized metadata mapping per namespace.

    Raises:
        TokenHeaderError: Layer metadata or same-level values conflict.
    """
    _, metadata = _load_scoped_documents(token_directory, override_directories)
    return metadata


def load_token_documents(
    token_directory: Path,
    override_directories: Iterable[Path] = (),
    *,
    resolve: bool = True,
) -> dict[str, Any]:
    """Merge token layers by hierarchy and optionally resolve references.

    Args:
        token_directory: Directory containing the base token layers.
        override_directories: App scopes applied after the global scope.
        resolve: Resolve token references when true.

    Returns:
        Namespace-to-document mapping after hierarchy merging.

    Raises:
        TokenHeaderError: Layer metadata or same-level values conflict.
        TokenReferenceError: A resolved reference is missing or cyclic.
    """
    documents, _ = _load_scoped_documents(token_directory, override_directories)
    return resolve_documents(documents) if resolve else documents


def load_token_documents_from_paths(
    paths: Iterable[Path], *, resolve: bool = True
) -> dict[str, Any]:
    """Merge an explicit collection of token document layers.

    Args:
        paths: Token document paths to merge by namespace and hierarchy.
        resolve: Resolve token references when true.

    Returns:
        Namespace-to-document mapping after hierarchy merging.

    Raises:
        TokenHeaderError: Layer metadata or same-level values conflict.
        TokenReferenceError: A resolved reference is missing or cyclic.
    """
    documents, _ = _load_layered_documents(paths)
    return resolve_documents(documents) if resolve else documents


def resolve_documents(documents: dict[str, Any]) -> dict[str, Any]:
    """Resolve all references in a namespace-to-document mapping.

    Args:
        documents: Raw documents keyed by token namespace.

    Returns:
        A new mapping whose token references are resolved.

    Raises:
        TokenReferenceError: A reference is missing or cyclic.
    """
    return {
        namespace: _resolve_value(document, documents, ())
        for namespace, document in documents.items()
    }


def resolve_references(value: Any, documents: dict[str, Any]) -> Any:
    """Resolve references in an arbitrary value using token namespaces.

    Args:
        value: Scalar or nested value that may contain token references.
        documents: Raw documents keyed by token namespace.

    Returns:
        The value with all exact token references resolved.

    Raises:
        TokenReferenceError: A reference is missing or cyclic.
    """
    return _resolve_value(value, documents, ())


def _resolve_value(value: Any, documents: dict[str, Any], trail: tuple[str, ...]) -> Any:
    """Recursively resolve references while retaining scalar value types."""
    if isinstance(value, str):
        match = REFERENCE_PATTERN.fullmatch(value)
        if match:
            return _resolve_path(match.group(1), documents, trail)
        return value
    if isinstance(value, list):
        return [_resolve_value(item, documents, trail) for item in value]
    if isinstance(value, dict):
        return {key: _resolve_value(item, documents, trail) for key, item in value.items()}
    return value


def _resolve_path(reference: str, documents: dict[str, Any], trail: tuple[str, ...]) -> Any:
    """Resolve one dotted path and reject missing or cyclic references."""
    if reference in trail:
        chain = " -> ".join((*trail, reference))
        raise TokenReferenceError(f"Cyclic token reference: {chain}")

    value: Any = documents
    traversed = []
    for part in reference.split("."):
        traversed.append(part)
        if not isinstance(value, dict) or part not in value:
            location = ".".join(traversed)
            raise TokenReferenceError(
                f"Unknown token reference '{reference}' at '{location}'"
            )
        value = value[part]
    return _resolve_value(value, documents, (*trail, reference))
