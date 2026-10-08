"""Param-fidelity rules X001–X004 for FMLint.

FileMaker's fmxmlsnippet parser **silently discards** child elements whose
tag name does not match what the step expects: the step imports fine, but
the parameter quietly falls back to its default value. These bugs are
invisible at the XML-schema level and only manifest at runtime (e.g. a
"Go to Record" that never advances, a Card window that opens as Document).

These rules validate each <Step>'s child elements against the step catalog
(`params[].xmlElement` et al. — see agent/catalogs/CATALOG_SCHEMA.md), so
the silent-discard class of bugs is caught by the linter instead of being
memorized as prose rules.

Only catalog entries with status "complete" are enforced — per the schema
contract, only those entries are fully reliable. Unknown catalog types are
skipped rather than failed (forward-compatibility rule).
"""

import difflib

from ..engine import rule, LintRule
from ..types import Diagnostic, Severity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _top_level_element(param: dict):
    """Return the direct-child element name a param contributes to a Step.

    Resolution order mirrors CATALOG_SCHEMA.md: a param nested under a
    parentElement or wrapped by a wrapperElement surfaces as that container;
    otherwise the base of xmlElement ("El" or "El/@attr" → "El").
    """
    parent = param.get("parentElement")
    if isinstance(parent, str) and parent:
        return parent
    wrapper = param.get("wrapperElement")
    if isinstance(wrapper, str) and wrapper:
        return wrapper
    xml_el = param.get("xmlElement")
    if isinstance(xml_el, str) and xml_el:
        return xml_el.split("/")[0]
    return None


def _allowed_children(entry: dict) -> set:
    """Build the set of expected direct-child element names for a step."""
    allowed = set()
    for param in entry.get("params", []):
        if not isinstance(param, dict):
            continue
        top = _top_level_element(param)
        if top:
            allowed.add(top)
        ptype = param.get("type", "")
        # Bare calculation params serialize as a <Calculation> child even
        # when xmlElement carries a different logical name.
        if ptype in ("calculation", "calc") :
            allowed.add("Calculation")
        # fieldOrVariable (and textMarker'd params) emit a leading <Text/>
        # marker plus a <Field> element.
        if ptype == "fieldOrVariable" or param.get("textMarker"):
            allowed.add("Text")
            allowed.add("Field")
        # findRequests params serialize as the <Query> subtree.
        if ptype == "findRequests":
            allowed.add("Query")
    return allowed


def _entry_is_enforceable(entry) -> bool:
    """Enforce only complete catalog entries (schema contract §status)."""
    return bool(entry) and entry.get("status") == "complete"


# Elements FileMaker emits/tolerates but the catalog deliberately does not
# model as params. They are never a mistyped parameter name, so flagging
# them would only produce noise:
#   - Text: bare <Text/> markers appear next to field/variable targets in
#     more step families than the catalog models with `textMarker`.
#   - Animation: FileMaker Go-only; desktop FM drops it benignly on paste
#     and at least one entry (Go to Related Record, `notesAnimation`)
#     excludes it from params by design.
GLOBAL_ALLOWED = {"Text", "Animation"}

# Script Workspace editor state, not step parameters. FileMaker adds these to
# EVERY step when copying to the clipboard (DisableStepCollapsed is the fold
# state, the fmxmlsnippet counterpart of SaXML's <Boolean type="Collapsed">).
# They never appear in catalog params and are harmless on paste.
EDITOR_STATE_ELEMENTS = {"DisableStepCollapsed"}


# ---------------------------------------------------------------------------
# X001 — unknown-param-element
# ---------------------------------------------------------------------------

@rule
class UnknownParamElement(LintRule):
    """Child element not recognized by the step's catalog params.

    FileMaker silently discards it and the parameter falls back to its
    default (e.g. <State> instead of <Set> on Set Error Capture leaves
    error capture OFF; <Option>/<ExitAfterLast> on Go to Record leave the
    step with no parameters at all).
    """

    rule_id = "X001"
    name = "unknown-param-element"
    category = "param-fidelity"
    default_severity = Severity.ERROR
    formats = {"xml"}
    tier = 1

    def check_xml(self, parse_result, catalog, context, config):
        if parse_result.root is None:
            return []
        sev = self.severity(config)
        diags = []
        for idx, step in enumerate(parse_result.steps):
            name = step.get("name", "")
            entry = catalog.get(name)
            if not _entry_is_enforceable(entry):
                continue
            allowed = _allowed_children(entry)
            for child in list(step):
                tag = child.tag
                if tag in allowed or tag in GLOBAL_ALLOWED or tag in EDITOR_STATE_ELEMENTS:
                    continue
                suggestion = difflib.get_close_matches(tag, sorted(allowed), n=1, cutoff=0.5)
                hint = None
                if suggestion:
                    hint = f'Did you mean <{suggestion[0]}>? Check the catalog params for "{name}".'
                elif allowed:
                    hint = f'Expected elements for "{name}": {", ".join(sorted(allowed))}.'
                else:
                    hint = f'"{name}" takes no child elements.'
                diags.append(Diagnostic(
                    rule_id=self.rule_id,
                    severity=sev,
                    message=(
                        f'Step {idx + 1} "{name}": <{tag}> is not a recognized '
                        f"parameter element — FileMaker will silently discard it "
                        f"and use the parameter's default value."
                    ),
                    line=0,
                    fix_hint=hint,
                ))
        return diags


# ---------------------------------------------------------------------------
# X002 — missing-discriminator
# ---------------------------------------------------------------------------

@rule
class MissingDiscriminator(LintRule):
    """A param governed by a discriminator appears without it.

    Catalog params may declare `discriminator`: a sibling param (typically
    an enum) that governs their form/presence. Without the discriminator
    element FileMaker falls back to its default and silently ignores the
    governed param — e.g. <Layout> without <LayoutDestination> on
    New Window / Go to Layout is ignored and the window opens on the
    current layout.
    """

    rule_id = "X002"
    name = "missing-discriminator"
    category = "param-fidelity"
    default_severity = Severity.ERROR
    formats = {"xml"}
    tier = 1

    def check_xml(self, parse_result, catalog, context, config):
        if parse_result.root is None:
            return []
        sev = self.severity(config)
        diags = []
        for idx, step in enumerate(parse_result.steps):
            name = step.get("name", "")
            entry = catalog.get(name)
            if not _entry_is_enforceable(entry):
                continue
            child_tags = {child.tag for child in list(step)}
            for param in entry.get("params", []):
                if not isinstance(param, dict):
                    continue
                disc = param.get("discriminator")
                if not isinstance(disc, str) or not disc:
                    continue
                governed = _top_level_element(param)
                disc_el = disc.split("/")[0]
                if governed and governed in child_tags and disc_el not in child_tags:
                    diags.append(Diagnostic(
                        rule_id=self.rule_id,
                        severity=sev,
                        message=(
                            f'Step {idx + 1} "{name}": <{governed}> is present but its '
                            f"discriminator <{disc_el}> is missing — FileMaker will "
                            f"silently ignore <{governed}> and use the default behavior."
                        ),
                        line=0,
                        fix_hint=(
                            f'Add <{disc_el} value="..."/> before <{governed}> '
                            f"(e.g. <{disc_el} value=\"SelectedLayout\"/> for layout refs)."
                        ),
                    ))
        return diags


# ---------------------------------------------------------------------------
# X003 — known-silent-discard-patterns
# ---------------------------------------------------------------------------

@rule
class KnownSilentDiscardPatterns(LintRule):
    """Hand-verified silent-discard combinations the generic rules can't see.

    1. New Window with NewWndStyles Style="Card" but no Styles bitmask
       attribute → FileMaker ignores Style and opens a Document window.
    2. Perform Script with <FileReference> nested inside <Script> → the
       cross-file script reference does not resolve ("unknown script").
    3. Perform Script cross-file <FileReference> without a
       <UniversalPathList> child → same unresolved-reference symptom.
    """

    rule_id = "X003"
    name = "known-silent-discard-patterns"
    category = "param-fidelity"
    default_severity = Severity.ERROR
    formats = {"xml"}
    tier = 1

    def check_xml(self, parse_result, catalog, context, config):
        if parse_result.root is None:
            return []
        sev = self.severity(config)
        diags = []
        for idx, step in enumerate(parse_result.steps):
            name = step.get("name", "")

            # -- Pattern 1: Card window without the Styles bitmask ---------
            if name == "New Window":
                for styles_el in step.iter("NewWndStyles"):
                    if styles_el.get("Style") == "Card" and not styles_el.get("Styles"):
                        diags.append(Diagnostic(
                            rule_id=self.rule_id,
                            severity=sev,
                            message=(
                                f'Step {idx + 1} "New Window": Style="Card" without the '
                                f'numeric Styles bitmask attribute — FileMaker ignores '
                                f"Style and opens the window as Document."
                            ),
                            line=0,
                            fix_hint=(
                                'Add the Styles bitmask, e.g. Styles="3222339600" '
                                "(Card, dim parent, no chrome except Close)."
                            ),
                        ))

            # -- Patterns 2 & 3: Perform Script cross-file reference -------
            if name in ("Perform Script", "Perform Script on Server"):
                for script_el in step.findall("Script"):
                    if script_el.find("FileReference") is not None:
                        diags.append(Diagnostic(
                            rule_id=self.rule_id,
                            severity=sev,
                            message=(
                                f'Step {idx + 1} "{name}": <FileReference> is nested inside '
                                f"<Script> — it must be a SIBLING of <Script>, or the "
                                f"cross-file script reference will not resolve."
                            ),
                            line=0,
                            fix_hint=(
                                "Move <FileReference id name> up to be a direct child of "
                                "the Step, before <Script>."
                            ),
                        ))
                for fileref_el in step.findall("FileReference"):
                    is_external = bool(fileref_el.get("id")) and bool(fileref_el.get("name"))
                    if not fileref_el.get("name") and fileref_el.find("UniversalPathList") is not None:
                        # Ruta sin name: FileMaker resuelve la fuente de datos por name y, sin él,
                        # descarta la ruta al pegar → "<unknown> from file: \"\"" (verificado 2026-10).
                        diags.append(Diagnostic(
                            rule_id=self.rule_id, severity=sev, line=0,
                            message=(f'Step {idx + 1} "{name}": <FileReference> con <UniversalPathList> '
                                     f"pero sin name — FileMaker descarta la referencia al pegar "
                                     f"(el guion queda <unknown>)."),
                            fix_hint=('Pon el nombre de la fuente de datos externa en name '
                                      '(vale id="0": FileMaker la resuelve por nombre).'),
                        ))
                        continue
                    if not is_external:
                        # <FileReference/> vacío = llamada al mismo archivo (ruido del conversor);
                        # el catálogo dice "omit entirely for same-file calls". Informativo, no error.
                        diags.append(Diagnostic(
                            rule_id=self.rule_id, severity=Severity.INFO, line=0,
                            message=(f'Step {idx + 1} "{name}": <FileReference> vacío — ruido del conversor en '
                                     f"una llamada al mismo archivo; FileMaker lo ignora."),
                            fix_hint="Omite <FileReference> en llamadas al mismo archivo.",
                        ))
                        continue
                    if fileref_el.find("UniversalPathList") is None:
                        diags.append(Diagnostic(
                            rule_id=self.rule_id,
                            severity=sev,
                            message=(
                                f'Step {idx + 1} "{name}": <FileReference> without a '
                                f"<UniversalPathList> child — the external file reference "
                                f"will not resolve (script shows as unknown)."
                            ),
                            line=0,
                            fix_hint=(
                                "Add <UniversalPathList>file:FilenameWithoutExtension"
                                "</UniversalPathList> inside <FileReference>."
                            ),
                        ))
        return diags


# ---------------------------------------------------------------------------
# X004 — perform-script-child-order
# ---------------------------------------------------------------------------

_PS_ORDER = {"FileReference": 0, "Calculated": 1, "Calculation": 2, "Script": 3}
_PARAM_LIKE = (";", "JSONSetElement", "\n")


@rule
class PerformScriptChildOrder(LintRule):
    """Perform Script: el orden de los hijos decide si el destino resuelve.

    Forma que produce FileMaker: DisableStepCollapsed → FileReference →
    Calculated (by name) → Calculation (parámetro) → Script (destino, ÚLTIMO).
    Con <Script> antes que <Calculation>/<FileReference> el paste se acepta
    pero el paso queda `From list ; ""` y no llama a nada. Además,
    <Calculated> es el modo by-name (su contenido es el NOMBRE del script),
    excluyente con <Script>: un parámetro envuelto en <Calculated> mata el paso.
    """

    rule_id = "X004"
    name = "perform-script-child-order"
    category = "param-fidelity"
    default_severity = Severity.ERROR
    formats = {"xml"}
    tier = 1

    def check_xml(self, parse_result, catalog, context, config):
        if parse_result.root is None:
            return []
        sev = self.severity(config)
        diags = []
        for idx, step in enumerate(parse_result.steps):
            name = step.get("name", "")
            if name not in ("Perform Script", "Perform Script on Server"):
                continue
            tags = [c.tag for c in list(step) if c.tag in _PS_ORDER]
            ranks = [_PS_ORDER[t] for t in tags]
            if ranks != sorted(ranks):
                diags.append(Diagnostic(
                    rule_id=self.rule_id, severity=sev, line=0,
                    message=(f'Step {idx + 1} "{name}": orden de hijos {tags} — <Script> debe ir el último '
                             f"(FileReference → Calculated → Calculation → Script); si no, FileMaker deja "
                             f"el destino sin resolver y el paso no llama a nada."),
                    fix_hint="Reordena los hijos: FileReference, Calculated, Calculation, Script.",
                ))
            calculated = step.find("Calculated")
            if calculated is not None:
                calc = calculated.find("Calculation")
                text = (calc.text or "") if calc is not None else ""
                if step.find("Script") is not None:
                    # by name + by id a la vez: paso muerto seguro → ERROR
                    diags.append(Diagnostic(
                        rule_id=self.rule_id, severity=sev, line=0,
                        message=(f'Step {idx + 1} "{name}": <Calculated> es el modo by name (su contenido es el '
                                 f"NOMBRE del script) y excluye a <Script>; aquí parece el parámetro."),
                        fix_hint=("El parámetro va en un <Calculation> suelto, hermano de <Script>; "
                                  "usa <Calculated> solo para llamar por nombre."),
                    ))
                elif any(m in text for m in _PARAM_LIKE):
                    # Solo heurística de contenido: un by name legítimo puede ser una expresión
                    # (selector/router) → WARNING, nunca bloquea
                    diags.append(Diagnostic(
                        rule_id=self.rule_id, severity=Severity.WARNING, line=0,
                        message=(f'Step {idx + 1} "{name}": <Calculated> (by name) con contenido que parece '
                                 f"un parámetro ({text[:40]!r}…). Si es el nombre calculado del script, ignora este aviso."),
                        fix_hint="El parámetro va en <Calculation> suelto; <Calculated> solo lleva el nombre del script.",
                    ))
        return diags
