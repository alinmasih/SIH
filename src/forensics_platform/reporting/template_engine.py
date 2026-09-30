"""
Lightweight, secure HTML template engine for forensic and sanitization reports.

Supports:
- Variable interpolation: {{ var }} and {{ object.property }}
- Filters: {{ var|bytes }}, {{ var|date }}, {{ var|hash }}, {{ var|upper }}, {{ var|default("N/A") }}
- Conditionals: {% if expr %} ... {% elif expr %} ... {% else %} ... {% endif %}
- Iteration: {% for item in items %} ... {{ loop.index }} ... {% endfor %}
- Inlining CSS assets for 100% self-contained portable HTML/PDFs
"""

from datetime import datetime, timezone
from pathlib import Path
import html
import re
from typing import Any, Dict, List, Optional, Union


def format_bytes(size: Optional[Union[int, float]]) -> str:
    """Format bytes into human-readable string (B, KB, MB, GB, TB)."""
    if size is None:
        return "N/A"
    try:
        n = float(size)
    except (ValueError, TypeError):
        return str(size)

    if n < 0:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if abs(n) < 1024.0:
            if unit == "B":
                return f"{int(n)} B"
            return f"{n:.2f} {unit}"
        n /= 1024.0
    return f"{n:.2f} EB"


def format_datetime(val: Optional[Union[datetime, str]], fmt: str = "%Y-%m-%d %H:%M:%S UTC") -> str:
    """Format datetime object or ISO string."""
    if val is None:
        return "N/A"
    if isinstance(val, datetime):
        return val.strftime(fmt)
    if isinstance(val, str):
        try:
            dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
            return dt.strftime(fmt)
        except Exception:
            return val
    return str(val)


def format_hash(val: Optional[str], length: int = 16) -> str:
    """Shorten hash with ellipsis or return mono tag."""
    if not val:
        return "N/A"
    s = str(val)
    if len(s) > length:
        return f"{s[:length]}..."
    return s


def render_pill(status: Optional[str]) -> str:
    """Render a colored status pill."""
    st = str(status or "unknown").lower()
    if st in ("valid", "pass", "completed", "success", "verified", "active"):
        cls = "pill-success"
    elif st in ("invalid", "fail", "failed", "danger", "error"):
        cls = "pill-danger"
    elif st in ("partial", "warning", "pending", "running"):
        cls = "pill-warning"
    elif st in ("info", "clear", "purge", "hdd", "ssd", "nvme"):
        cls = "pill-info"
    else:
        cls = "pill-muted"
    return f'<span class="pill {cls}">{html.escape(str(status).upper())}</span>'


class TemplateEngine:
    """
    Lightweight, robust template renderer for report generation.
    """

    def __init__(self, template_dir: Optional[Union[str, Path]] = None):
        if template_dir is None:
            self.template_dir = Path(__file__).parent / "templates"
        else:
            self.template_dir = Path(template_dir)
        self.assets_dir = Path(__file__).parent / "assets"

        self.filters = {
            "bytes": format_bytes,
            "date": format_datetime,
            "hash": format_hash,
            "pill": render_pill,
            "upper": lambda v: str(v or "").upper(),
            "lower": lambda v: str(v or "").lower(),
            "escape": lambda v: html.escape(str(v or "")),
        }

    def get_inline_css(self, css_filename: str = "report.css") -> str:
        """Read CSS asset file for inlining in standalone HTML."""
        css_path = self.assets_dir / css_filename
        if css_path.exists():
            return css_path.read_text(encoding="utf-8")
        return "/* report.css not found */"

    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Load template file and render with context."""
        tpl_path = self.template_dir / template_name
        if not tpl_path.exists():
            raise FileNotFoundError(f"Template not found: {tpl_path}")
        content = tpl_path.read_text(encoding="utf-8")
        return self.render_string(content, context)

    def render_string(self, template_str: str, context: Dict[str, Any]) -> str:
        """Render a template string with given context."""
        ctx = dict(context)
        # Add default filters and helpers if not present
        if "inline_css" not in ctx:
            ctx["inline_css"] = self.get_inline_css()
        if "now" not in ctx:
            ctx["now"] = datetime.now(timezone.utc)

        # Step 1: Remove comments {# ... #}
        clean_text = re.sub(r"\{#.*?#\}", "", template_str, flags=re.DOTALL)

        # Step 2: Process control blocks (for, if) recursively
        rendered = self._eval_blocks(clean_text, ctx)

        # Step 3: Replace variable expressions {{ ... }}
        rendered = self._eval_vars(rendered, ctx)

        return rendered

    def _eval_blocks(self, text: str, ctx: Dict[str, Any]) -> str:
        """Process loops and conditionals in template text."""
        # Find outer-most block tag: {% for ... %} or {% if ... %}
        block_pattern = re.compile(
            r"\{%\s*(for|if)\s+([^%]+?)\s*%\}(.*?)\{%\s*end\1\s*%\}",
            re.DOTALL
        )

        pos = 0
        result = []
        while True:
            m = block_pattern.search(text, pos)
            if not m:
                result.append(text[pos:])
                break

            result.append(text[pos:m.start()])
            tag_type = m.group(1)
            expr = m.group(2).strip()
            body = m.group(3)

            if tag_type == "for":
                result.append(self._render_for_block(expr, body, ctx))
            elif tag_type == "if":
                result.append(self._render_if_block(expr, body, ctx))

            pos = m.end()

        return "".join(result)

    def _render_for_block(self, expr: str, body: str, ctx: Dict[str, Any]) -> str:
        """Execute {% for item in iterable %} body {% endfor %}."""
        # Expecting: "item in items" or "key, val in items"
        match = re.match(r"^(\w+)\s+in\s+(.+)$", expr)
        if not match:
            return ""

        var_name = match.group(1)
        iterable_expr = match.group(2).strip()
        iterable = self._resolve_expr(iterable_expr, ctx)

        if not iterable:
            return ""

        output = []
        items = list(iterable)
        total = len(items)

        for idx, val in enumerate(items):
            loop_ctx = dict(ctx)
            loop_ctx[var_name] = val
            loop_ctx["loop"] = {
                "index": idx + 1,
                "index0": idx,
                "first": idx == 0,
                "last": idx == (total - 1),
                "length": total,
            }
            # Recursively evaluate inner blocks if any
            evaluated_body = self._eval_blocks(body, loop_ctx)
            # Evaluate variables in this iteration
            output.append(self._eval_vars(evaluated_body, loop_ctx))

        return "".join(output)

    def _render_if_block(self, expr: str, body: str, ctx: Dict[str, Any]) -> str:
        """Execute {% if expr %} ... {% elif ... %} ... {% else %} ... {% endif %}."""
        # Split by {% elif expr %} and {% else %}
        branches = []
        # Find all branch points
        pattern = re.compile(r"\{%\s*(elif\s+[^%]+|else)\s*%\}")
        last_idx = 0
        current_expr = expr

        for m in pattern.finditer(body):
            branch_body = body[last_idx:m.start()]
            branches.append((current_expr, branch_body))
            tag = m.group(1).strip()
            if tag.startswith("elif"):
                current_expr = tag[4:].strip()
            else:
                current_expr = "True"
            last_idx = m.end()

        branches.append((current_expr, body[last_idx:]))

        # Evaluate branches in order
        for cond_expr, branch_body in branches:
            if self._is_truthy(cond_expr, ctx):
                evaluated = self._eval_blocks(branch_body, ctx)
                return self._eval_vars(evaluated, ctx)

        return ""

    def _is_truthy(self, expr: str, ctx: Dict[str, Any]) -> bool:
        """Evaluate a boolean condition safely."""
        expr = expr.strip()
        if expr == "True":
            return True
        if expr == "False":
            return False

        # Check for equality: a == b or a != b
        eq_match = re.match(r"^(.+?)\s*(==|!=|>=|<=|>|<)\s*(.+)$", expr)
        if eq_match:
            left_val = self._resolve_expr(eq_match.group(1).strip(), ctx)
            op = eq_match.group(2)
            right_raw = eq_match.group(3).strip()
            right_val = self._parse_literal(right_raw, ctx)

            try:
                if op == "==":
                    return str(left_val) == str(right_val) or left_val == right_val
                elif op == "!=":
                    return str(left_val) != str(right_val) and left_val != right_val
                elif op == ">=":
                    return float(left_val or 0) >= float(right_val or 0)
                elif op == "<=":
                    return float(left_val or 0) <= float(right_val or 0)
                elif op == ">":
                    return float(left_val or 0) > float(right_val or 0)
                elif op == "<":
                    return float(left_val or 0) < float(right_val or 0)
            except Exception:
                return False

        # Check for negation: not a
        if expr.startswith("not "):
            return not self._is_truthy(expr[4:].strip(), ctx)

        val = self._resolve_expr(expr, ctx)
        return bool(val)

    def _parse_literal(self, raw: str, ctx: Dict[str, Any]) -> Any:
        """Parse literal strings ('...'), numbers, or resolve variable."""
        if (raw.startswith("'") and raw.endswith("'")) or (raw.startswith('"') and raw.endswith('"')):
            return raw[1:-1]
        if raw.isdigit():
            return int(raw)
        try:
            return float(raw)
        except ValueError:
            pass
        return self._resolve_expr(raw, ctx)

    def _eval_vars(self, text: str, ctx: Dict[str, Any]) -> str:
        """Replace {{ var | filter }} expressions in text."""
        var_pattern = re.compile(r"\{\{\s*(.+?)\s*\}\}")

        def replace_var(match: re.Match) -> str:
            expr = match.group(1).strip()
            parts = [p.strip() for p in expr.split("|")]
            var_expr = parts[0]
            val = self._resolve_expr(var_expr, ctx)

            # Apply filters
            for f in parts[1:]:
                # Check for filter arguments like default("N/A")
                f_match = re.match(r"^(\w+)(?:\((.*)\))?$", f)
                if not f_match:
                    continue
                f_name = f_match.group(1)
                f_arg = f_match.group(2)

                if f_name == "default":
                    if not val:
                        arg_str = (f_arg or "").strip().strip("'\"")
                        val = arg_str
                elif f_name in self.filters:
                    val = self.filters[f_name](val)

            if val is None:
                return ""
            return str(val)

        return var_pattern.sub(replace_var, text)

    def _resolve_expr(self, expr: str, ctx: Dict[str, Any]) -> Any:
        """Resolve a dotted path like case.case_number or dict['key']."""
        if not expr:
            return None

        # Clean any quotes if literal string
        if (expr.startswith("'") and expr.endswith("'")) or (expr.startswith('"') and expr.endswith('"')):
            return expr[1:-1]

        tokens = expr.split(".")
        root = tokens[0]
        if root not in ctx:
            return None

        current = ctx[root]
        for token in tokens[1:]:
            if current is None:
                return None
            if isinstance(current, dict):
                current = current.get(token)
            else:
                current = getattr(current, token, None)
                if callable(current):
                    try:
                        current = current()
                    except Exception:
                        pass
        return current
