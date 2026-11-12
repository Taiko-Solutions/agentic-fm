"""Live evaluation rules C004–C005 for FMLint.

These are tier-3 rules that validate calculations against a live FileMaker
engine via AGFMEvaluation through OData. They require OData connectivity
and developer confirmation before execution.
"""

import json

from ..engine import rule, LintRule
from ..odata import (
    BridgeError,
    ODataConfigError,
    ScriptMissing,
    bridge_call,
    load_solutions,
    resolve,
)
from ..types import Diagnostic, Severity

# Errores del puente AGFMAgentCall que invalidan toda la tanda.
AGENT_FATAL_ERRORS = ("agent_unreachable", "mode_not_allowed")


def _evaluate_expression(target, expression, layout=None):
    """Evalúa un cálculo por el destino resuelto (el principal, con o sin data_source).

    Devuelve el veredicto ya desenvuelto (dict). Lanza BridgeError / ODataConfigError.
    """
    param = {"expression": expression}
    if layout:
        param["layout"] = layout
    if target.data_source is None:
        return bridge_call(target.odata, "AGFMEvaluation", json.dumps(param))
    param = {"mode": "evaluate", **param, "data_source": target.data_source}
    return bridge_call(target.odata, "AGFMAgentCall", json.dumps(param))


def _bridge_error_message(exc, target):
    if isinstance(exc, ScriptMissing):
        if exc.script == "AGFMAgentCall":
            return (f"{target.main} no tiene AGFMAgentCall: "
                    "actualiza el add-on agentic-fm del archivo principal")
        return (f"{target.main} no tiene {exc.script}: "
                "instala o actualiza el add-on agentic-fm")
    if exc.status in (401, 403):
        return f"credenciales OData rechazadas ({exc.status}) en {target.main}: revisa automation.json"
    if exc.status == 404:
        return (f"{target.main}: no se encuentra AGFMScriptBridge o la base de datos (404): "
                "revisa automation.json y el add-on")
    return f"no se pudo contactar con FileMaker Server ({exc.reason})"


# ---------------------------------------------------------------------------
# C004 — live-eval-error
# ---------------------------------------------------------------------------

@rule
class LiveEvalError(LintRule):
    """Validate calculations against the live FileMaker engine via OData."""

    rule_id = "C004"
    name = "live-eval-error"
    category = "calculations"
    default_severity = Severity.ERROR
    formats = {"xml", "hr"}
    tier = 3
    requires_confirmation = True

    def _extract_calcs_xml(self, steps):
        """Extract (step_index, calc_text) from XML steps."""
        calcs = []
        for idx, step in enumerate(steps):
            for calc in step.iter("Calculation"):
                if calc.text and calc.text.strip():
                    calcs.append((idx + 1, calc.text.strip()))
        return calcs

    def _extract_calcs_hr(self, lines):
        """Extract (line_number, calc_text) from HR lines."""
        calcs = []
        for ln in lines:
            if ln.is_comment or not ln.bracket_content:
                continue
            # The bracket content itself is the expression for most steps
            if ln.params:
                # For Set Variable, the calc is the last param
                calc = ln.params[-1].strip()
                if calc:
                    calcs.append((ln.line_number, calc))
        return calcs

    def _warn(self, message):
        return Diagnostic(
            rule_id="C005",
            severity=Severity.WARNING,
            message=f"Evaluación en vivo omitida: {message}",
            line=0,
        )

    def _evaluate_calcs(self, calcs, context):
        """Evalúa los cálculos y devuelve diagnósticos. Ante un fallo de
        transporte o de configuración emite un único aviso C005 y corta."""
        if not context or not context._project_root:
            return []
        try:
            solutions = load_solutions(context._project_root)
        except ODataConfigError as exc:
            return [self._warn(str(exc))]
        has_base_url = any(
            isinstance(e, dict)
            and isinstance(e.get("odata"), dict)
            and e["odata"].get("base_url")
            for e in solutions.values()
        )
        if not has_base_url:
            return []  # la regla no aplica

        try:
            target = resolve(solutions, context.solution_name)
        except ODataConfigError as exc:
            return [self._warn(str(exc))]

        diags = []
        cache = {}
        layout = context.layout_name if context.available else None

        for line, calc_text in calcs:
            cache_key = (calc_text, layout)
            if cache_key in cache:
                result = cache[cache_key]
            else:
                try:
                    result = _evaluate_expression(target, calc_text, layout)
                except ODataConfigError as exc:
                    diags.append(self._warn(str(exc)))
                    break
                except BridgeError as exc:
                    diags.append(self._warn(_bridge_error_message(exc, target)))
                    break
                cache[cache_key] = result

            if not isinstance(result, dict):
                diags.append(self._warn(
                    f"respuesta inesperada de {target.main}: {str(result)[:80]!r}"
                ))
                break

            err = result.get("error")
            if err in AGENT_FATAL_ERRORS:
                where = (
                    f"AGFM Agent de la fuente de datos «{target.data_source}»"
                    if target.data_source is not None
                    else "AGFMEvaluation"
                )
                diags.append(self._warn(
                    f"{target.main}: {where} no responde (error {result.get('error_code', '?')}): "
                    "pega AGFM Agent en ese archivo o revisa data_source"
                ))
                break
            if err:
                detail = str(err)[:80]
                if result.get("message"):
                    detail += f" ({str(result['message'])[:120]})"
                diags.append(self._warn(
                    f"respuesta inesperada de {target.main}: {detail}"
                ))
                break

            if not result.get("success", True):
                error_code = result.get("error_code", "unknown")
                diags.append(Diagnostic(
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    message=(
                        f"Calculation invalid in FileMaker engine "
                        f"(error {error_code}): {calc_text[:80]}"
                    ),
                    line=line,
                ))
            elif str(result.get("result", "")).strip() == "?":
                # EvaluationError solo captura errores de sintaxis; una función
                # personalizada desconocida, una referencia inexistente o una
                # función no soportada evalúan a "?" con success:true.
                diags.append(Diagnostic(
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    message=(
                        f'Calculation evaluated to "?" in FileMaker engine — '
                        f"likely an unknown custom function, missing reference, "
                        f"or unsupported feature: {calc_text[:80]}"
                    ),
                    line=line,
                ))

        return diags

    def check_xml(self, parse_result, catalog, context, config):
        if not parse_result.ok:
            return []
        calcs = self._extract_calcs_xml(parse_result.steps)
        return self._evaluate_calcs(calcs, context)

    def check_hr(self, lines, catalog, context, config):
        calcs = self._extract_calcs_hr(lines)
        return self._evaluate_calcs(calcs, context)


# ---------------------------------------------------------------------------
# C005 — live-eval-warning (reserved for non-fatal eval issues)
# ---------------------------------------------------------------------------

@rule
class LiveEvalWarning(LintRule):
    """Reserved for non-fatal issues detected by AGFMEvaluation.

    Currently a stub — C004 handles the primary eval flow. This rule
    can be enhanced to detect warnings like deprecated functions, implicit
    type coercions, or context-dependent evaluation differences.
    """

    rule_id = "C005"
    name = "live-eval-warning"
    category = "calculations"
    default_severity = Severity.WARNING
    formats = {"xml", "hr"}
    tier = 3
    requires_confirmation = True

    def check_xml(self, parse_result, catalog, context, config):
        return []

    def check_hr(self, lines, catalog, context, config):
        return []
