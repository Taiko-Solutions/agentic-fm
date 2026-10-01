#!/bin/bash
# agent/scripts/test_explode_layouts.sh — fmparse.sh + fmcontext.sh con las dos disposiciones del exploder:
# 0.7.1 (custom_functions/ + custom_functions_sanitized/ + value_lists/) y 0.5.1 (custom_function_stubs/ + value_list_stubs/).
# Usa un exploder falso: copia la carpeta plantilla cuyo path está escrito dentro del "export". Uso: bash agent/scripts/test_explode_layouts.sh
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
fail() { echo "❌ $1"; exit 1; }
pass() { echo "✅ $1"; }
command -v xmllint >/dev/null || fail "xmllint not available (fmcontext.sh needs it; on Linux: apt-get install libxml2-utils)"

cat > "$T/fake-exploder" <<'PY'
#!/usr/bin/env python3
import pathlib, shutil, sys
if sys.argv[1:] == ["--version"]:
    print("fm-xml-export-exploder 0.7.1"); sys.exit(0)
args = [a for a in sys.argv[1:] if not a.startswith("--") and a != "domain"]
source, target = pathlib.Path(args[-2]), pathlib.Path(args[-1])
template = pathlib.Path(next(source.glob("*.xml")).read_text().strip())
shutil.copytree(template, target, dirs_exist_ok=True)
PY
chmod +x "$T/fake-exploder"

cf_xml() { # id name params body
  printf '<?xml version="1.0" encoding="UTF-8"?>\n<CustomFunction access="All" id="%s" name="%s"><Calculation><Text><![CDATA[%s]]></Text></Calculation><Display>%s</Display><ObjectList membercount="%s">%s</ObjectList></CustomFunction>\n' \
    "$1" "$2" "$4" "$2" "$(echo "$3" | wc -w | tr -d ' ')" "$(for p in $3; do printf '<Parameter name="%s"/>' "$p"; done)"
}
vl_custom='<?xml version="1.0" encoding="UTF-8"?>
<ValueList id="2" name="Statuses"><Source value="Custom"/><CustomValues><Text><![CDATA[Draft
Sent]]></Text></CustomValues></ValueList>'
vl_field='<?xml version="1.0" encoding="UTF-8"?>
<ValueList id="1" name="Invoice IDs"><Source value="FromField"/><Field><PrimaryField><FieldReference id="1" name="InvoiceID"><TableOccurrenceReference id="1001" name="Invoices"/></FieldReference></PrimaryField></Field></ValueList>'

make_template() { # dir layout(new|legacy)
  local d="$1/Demo"; mkdir -p "$1/_/Demo" "$1/scripts/Demo" "$1/script_stubs/Demo" "$1/tables/Demo"
  echo '<Metadata/>' > "$1/_/Demo/metadata.xml"
  echo '<Script id="1" name="Hello"/>' > "$1/script_stubs/Demo/Hello - ID 1.xml"
  if [[ "$2" == new ]]; then
    mkdir -p "$1/custom_functions/Demo/Helpers - ID 50" "$1/custom_functions_sanitized/Demo/Helpers - ID 50" "$1/value_lists/Demo"
    cf_xml 1 FormatMoney "amount" "Round ( amount ; 2 )" > "$1/custom_functions/Demo/FormatMoney - ID 1.xml"
    echo "Round ( amount ; 2 )" > "$1/custom_functions_sanitized/Demo/FormatMoney - ID 1.txt"
    cf_xml 2 TaxRate "" "0.21" > "$1/custom_functions/Demo/Helpers - ID 50/TaxRate - ID 2.xml"
    echo "0.21" > "$1/custom_functions_sanitized/Demo/Helpers - ID 50/TaxRate - ID 2.txt"
    cf_xml 9 ApiKey "" '"sk-secret"' > "$1/custom_functions/Demo/ApiKey - ID 9.xml"
    echo '"sk-secret"' > "$1/custom_functions_sanitized/Demo/ApiKey - ID 9.txt"
    echo "$vl_custom" > "$1/value_lists/Demo/Statuses - ID 2.xml"; echo "$vl_field" > "$1/value_lists/Demo/Invoice IDs - ID 1.xml"
  else
    mkdir -p "$1/custom_function_stubs/Demo" "$1/value_list_stubs/Demo"
    cf_xml 1 FormatMoney "amount" "Round ( amount ; 2 )" > "$1/custom_function_stubs/Demo/FormatMoney - ID 1.xml"
    cf_xml 9 ApiKey "" '"sk-secret"' > "$1/custom_function_stubs/Demo/ApiKey - ID 9.xml"
    echo "$vl_custom" > "$1/value_list_stubs/Demo/Statuses - ID 2.xml"
  fi
}

run_case() { # name layout — sets C (no command substitution: a failure inside would be silent under set -e)
  C="$T/$1"; mkdir -p "$C/agent/config" "$C/agent/xml_parsed" "$T/tpl-$1" "$T/desk-$1"
  cp "$REPO_ROOT/fmparse.sh" "$REPO_ROOT/fmcontext.sh" "$C/"
  make_template "$T/tpl-$1" "$2"
  echo "$T/tpl-$1" > "$T/desk-$1/Demo.xml"
  echo '{"Demo": {"custom_functions": ["ApiKey"]}}' > "$C/agent/config/removals.json"
  if ! (cd "$C" && FM_XML_EXPLODER_BIN="$T/fake-exploder" ./fmparse.sh -s Demo "$T/desk-$1/Demo.xml" > "$T/$1.log" 2>&1); then
    cat "$T/$1.log"; fail "$1: fmparse.sh exited non-zero"
  fi
}

# --- disposición 0.7.1 ---------------------------------------------------
run_case new new
[[ -z "$(find "$C/agent/xml_parsed" -name 'ApiKey - ID 9.*')" ]] || fail "0.7.1: removals.json left ApiKey behind: $(find "$C/agent/xml_parsed" -name 'ApiKey - ID 9.*')"
pass "0.7.1: removals.json deletes the custom function in custom_functions/ and custom_functions_sanitized/"
grep -q '^FormatMoney|1|amount|All|FormatMoney|functional|$' "$C/agent/context/Demo/custom_functions.index" || fail "0.7.1: custom_functions.index lacks FormatMoney: $(cat "$C/agent/context/Demo/custom_functions.index")"
grep -q '^TaxRate|2||All|TaxRate|constant|Helpers$' "$C/agent/context/Demo/custom_functions.index" || fail "0.7.1: TaxRate not classified as constant in a folder"
pass "0.7.1: custom_functions.index is generated from custom_functions/ with sanitized bodies"
grep -q '^Statuses|2|Custom|Draft,Sent$' "$C/agent/context/Demo/value_lists.index" || fail "0.7.1: value_lists.index lacks Statuses with name/id: $(cat "$C/agent/context/Demo/value_lists.index")"
grep -q '^Invoice IDs|1|FromField|(field-based)$' "$C/agent/context/Demo/value_lists.index" || fail "0.7.1: FromField list not marked (field-based)"
pass "0.7.1: value_lists.index has names, ids and (field-based)"

# --- disposición 0.5.1 ---------------------------------------------------
run_case legacy legacy
[[ -z "$(find "$C/agent/xml_parsed" -name 'ApiKey - ID 9.*')" ]] || fail "0.5.1: removals.json left ApiKey behind"
grep -q '^FormatMoney|1|amount|All|FormatMoney|functional|$' "$C/agent/context/Demo/custom_functions.index" || fail "0.5.1: custom_functions.index lacks FormatMoney"
grep -q '^Statuses|2|Custom|Draft,Sent$' "$C/agent/context/Demo/value_lists.index" || fail "0.5.1: value_lists.index lacks Statuses (value_list_stubs/)"
pass "0.5.1: legacy folders still work"
echo "all explode-layout tests passed"
