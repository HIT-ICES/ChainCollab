import vm from "vm";

const DSL_PREFIX = "dsl:";
const JS_PREFIX = "js:";
const DSL_VERSION = "compute-dsl/v1";
const JS_VERSION = "compute-js/v1";
const MAX_DEPTH = 64;
const DEFAULT_JS_TIMEOUT_MS = 300;
const MAX_JS_TIMEOUT_MS = 5000;
const MAX_JS_CODE_LENGTH = 12000;

function isPlainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function toFiniteNumber(value, label = "value") {
  const n = Number(value);
  if (!Number.isFinite(n)) {
    throw new Error(`${label} is not a finite number`);
  }
  return n;
}

function avg(values) {
  if (!values.length) return 0;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

function median(values) {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2
    ? sorted[mid]
    : (sorted[mid - 1] + sorted[mid]) / 2;
}

function stddev(values) {
  if (!values.length) return 0;
  const m = avg(values);
  const variance =
    values.reduce((acc, n) => acc + (n - m) ** 2, 0) / values.length;
  return Math.sqrt(variance);
}

function weightedMean(values, weights) {
  if (!Array.isArray(values) || !Array.isArray(weights)) {
    throw new Error("weightedMean requires arrays");
  }
  if (!values.length || values.length !== weights.length) {
    throw new Error("weightedMean requires same-length non-empty arrays");
  }
  const v = values.map((x, i) => toFiniteNumber(x, `values[${i}]`));
  const w = weights.map((x, i) => toFiniteNumber(x, `weights[${i}]`));
  const totalW = w.reduce((a, b) => a + b, 0);
  if (totalW === 0) {
    throw new Error("weightedMean total weight cannot be zero");
  }
  const total = v.reduce((acc, x, i) => acc + x * w[i], 0);
  return total / totalW;
}

function clamp(value, lo, hi) {
  const x = toFiniteNumber(value, "clamp.value");
  const low = toFiniteNumber(lo, "clamp.lo");
  const high = toFiniteNumber(hi, "clamp.hi");
  return Math.min(Math.max(x, low), high);
}

function tokenizeExpression(expression) {
  const tokens = [];
  let i = 0;
  while (i < expression.length) {
    const ch = expression[i];
    if (/\s/.test(ch)) {
      i += 1;
      continue;
    }
    if (/\d/.test(ch) || (ch === "." && /\d/.test(expression[i + 1] || ""))) {
      let j = i + 1;
      while (j < expression.length && /[\d.]/.test(expression[j])) {
        j += 1;
      }
      const raw = expression.slice(i, j);
      if ((raw.match(/\./g) || []).length > 1) {
        throw new Error(`invalid number literal: ${raw}`);
      }
      tokens.push({ type: "number", value: raw });
      i = j;
      continue;
    }
    if (/[A-Za-z_]/.test(ch)) {
      let j = i + 1;
      while (j < expression.length && /[A-Za-z0-9_]/.test(expression[j])) {
        j += 1;
      }
      tokens.push({ type: "ident", value: expression.slice(i, j) });
      i = j;
      continue;
    }
    if ("+-*/%^()".includes(ch)) {
      tokens.push({ type: "op", value: ch });
      i += 1;
      continue;
    }
    throw new Error(`unsupported token: '${ch}'`);
  }
  return tokens;
}

function toRpn(tokens) {
  const output = [];
  const ops = [];
  const precedence = {
    "u-": 4,
    "^": 3,
    "*": 2,
    "/": 2,
    "%": 2,
    "+": 1,
    "-": 1
  };
  const rightAssoc = { "^": true, "u-": true };

  let prevType = "start";
  for (const token of tokens) {
    if (token.type === "number" || token.type === "ident") {
      output.push(token);
      prevType = "value";
      continue;
    }

    if (token.value === "(") {
      ops.push(token);
      prevType = "(";
      continue;
    }
    if (token.value === ")") {
      while (ops.length && ops[ops.length - 1].value !== "(") {
        output.push(ops.pop());
      }
      if (!ops.length) {
        throw new Error("unmatched ')'");
      }
      ops.pop();
      prevType = "value";
      continue;
    }

    let op = token.value;
    if (op === "-" && (prevType === "start" || prevType === "(" || prevType === "op")) {
      op = "u-";
    }

    while (ops.length) {
      const top = ops[ops.length - 1];
      if (top.value === "(") {
        break;
      }
      const p1 = precedence[op];
      const p2 = precedence[top.value];
      if (
        p2 > p1 ||
        (p2 === p1 && !rightAssoc[op])
      ) {
        output.push(ops.pop());
      } else {
        break;
      }
    }
    ops.push({ type: "op", value: op });
    prevType = "op";
  }

  while (ops.length) {
    const op = ops.pop();
    if (op.value === "(") {
      throw new Error("unmatched '('");
    }
    output.push(op);
  }
  return output;
}

function evalRpn(rpn, inputs) {
  const stack = [];
  for (const token of rpn) {
    if (token.type === "number") {
      stack.push(Number(token.value));
      continue;
    }
    if (token.type === "ident") {
      if (!(token.value in inputs)) {
        throw new Error(`unknown variable: ${token.value}`);
      }
      stack.push(toFiniteNumber(inputs[token.value], token.value));
      continue;
    }
    if (token.value === "u-") {
      const a = stack.pop();
      if (a === undefined) {
        throw new Error("invalid unary '-'");
      }
      stack.push(-a);
      continue;
    }
    const b = stack.pop();
    const a = stack.pop();
    if (a === undefined || b === undefined) {
      throw new Error(`invalid operator '${token.value}'`);
    }
    switch (token.value) {
      case "+":
        stack.push(a + b);
        break;
      case "-":
        stack.push(a - b);
        break;
      case "*":
        stack.push(a * b);
        break;
      case "/":
        stack.push(a / b);
        break;
      case "%":
        stack.push(a % b);
        break;
      case "^":
        stack.push(a ** b);
        break;
      default:
        throw new Error(`unsupported operator: ${token.value}`);
    }
  }
  if (stack.length !== 1) {
    throw new Error("invalid expression");
  }
  return stack[0];
}

function evalLegacyExpression(expression, inputs) {
  const rpn = toRpn(tokenizeExpression(expression));
  return evalRpn(rpn, inputs);
}

function evalNode(node, ctx, depth = 0) {
  if (depth > MAX_DEPTH) {
    throw new Error("dsl exceeds max recursion depth");
  }

  if (Array.isArray(node)) {
    return node.map((item) => evalNode(item, ctx, depth + 1));
  }
  if (node === null || typeof node === "number" || typeof node === "string" || typeof node === "boolean") {
    return node;
  }
  if (!isPlainObject(node)) {
    throw new Error("invalid dsl node");
  }
  if ("const" in node) {
    return node.const;
  }
  if ("var" in node) {
    if (!(node.var in ctx.inputs)) {
      throw new Error(`dsl variable not found: ${node.var}`);
    }
    return ctx.inputs[node.var];
  }
  if ("array" in node) {
    if (!Array.isArray(node.array)) {
      throw new Error("dsl array must be an array");
    }
    return node.array.map((item) => evalNode(item, ctx, depth + 1));
  }
  if ("object" in node) {
    if (!isPlainObject(node.object)) {
      throw new Error("dsl object must be an object");
    }
    const out = {};
    for (const [k, v] of Object.entries(node.object)) {
      out[k] = evalNode(v, ctx, depth + 1);
    }
    return out;
  }
  if (!node.op) {
    throw new Error("dsl op missing");
  }

  const op = String(node.op).toLowerCase();
  const args = Array.isArray(node.args) ? node.args : [];
  const values = args.map((arg) => evalNode(arg, ctx, depth + 1));
  const nums = () => values.map((v, i) => toFiniteNumber(v, `${op}.args[${i}]`));

  switch (op) {
    case "list":
      return values;
    case "add":
    case "sum":
      return nums().reduce((a, b) => a + b, 0);
    case "sub": {
      const a = nums();
      if (a.length === 0) return 0;
      if (a.length === 1) return -a[0];
      return a.slice(1).reduce((acc, n) => acc - n, a[0]);
    }
    case "mul":
      return nums().reduce((a, b) => a * b, 1);
    case "div": {
      const [a, b] = nums();
      return a / b;
    }
    case "mod": {
      const [a, b] = nums();
      return a % b;
    }
    case "pow": {
      const [a, b] = nums();
      return a ** b;
    }
    case "min":
      return Math.min(...nums());
    case "max":
      return Math.max(...nums());
    case "avg":
    case "mean": {
      const a = nums();
      return a.length ? a.reduce((x, y) => x + y, 0) / a.length : 0;
    }
    case "median": {
      const a = nums().sort((x, y) => x - y);
      if (!a.length) return 0;
      const mid = Math.floor(a.length / 2);
      return a.length % 2 ? a[mid] : (a[mid - 1] + a[mid]) / 2;
    }
    case "stddev": {
      const a = nums();
      if (!a.length) return 0;
      const mean = a.reduce((x, y) => x + y, 0) / a.length;
      const variance = a.reduce((acc, n) => acc + (n - mean) ** 2, 0) / a.length;
      return Math.sqrt(variance);
    }
    case "weighted_mean": {
      const [vRaw, wRaw] = values;
      if (!Array.isArray(vRaw) || !Array.isArray(wRaw) || vRaw.length !== wRaw.length || !vRaw.length) {
        throw new Error("weighted_mean requires two arrays with same non-zero length");
      }
      const v = vRaw.map((x, i) => toFiniteNumber(x, `weighted_mean.values[${i}]`));
      const w = wRaw.map((x, i) => toFiniteNumber(x, `weighted_mean.weights[${i}]`));
      const totalW = w.reduce((a, b) => a + b, 0);
      if (totalW === 0) {
        throw new Error("weighted_mean total weight cannot be zero");
      }
      const total = v.reduce((acc, x, i) => acc + x * w[i], 0);
      return total / totalW;
    }
    case "abs":
      return Math.abs(toFiniteNumber(values[0], "abs.arg"));
    case "round": {
      const x = toFiniteNumber(values[0], "round.arg");
      const digits = values.length > 1 ? Math.trunc(toFiniteNumber(values[1], "round.digits")) : 0;
      const factor = 10 ** digits;
      return Math.round(x * factor) / factor;
    }
    case "floor":
      return Math.floor(toFiniteNumber(values[0], "floor.arg"));
    case "ceil":
      return Math.ceil(toFiniteNumber(values[0], "ceil.arg"));
    case "clamp": {
      const [x, lo, hi] = nums();
      return Math.min(Math.max(x, lo), hi);
    }
    case "gt":
      return toFiniteNumber(values[0], "gt.left") > toFiniteNumber(values[1], "gt.right");
    case "gte":
      return toFiniteNumber(values[0], "gte.left") >= toFiniteNumber(values[1], "gte.right");
    case "lt":
      return toFiniteNumber(values[0], "lt.left") < toFiniteNumber(values[1], "lt.right");
    case "lte":
      return toFiniteNumber(values[0], "lte.left") <= toFiniteNumber(values[1], "lte.right");
    case "eq":
      return values[0] === values[1];
    case "neq":
      return values[0] !== values[1];
    case "and":
      return values.every(Boolean);
    case "or":
      return values.some(Boolean);
    case "not":
      return !Boolean(values[0]);
    case "if":
      return Boolean(values[0]) ? values[1] : values[2];
    case "concat":
      return values.map((v) => String(v)).join("");
    case "number":
      return toFiniteNumber(values[0], "number.arg");
    case "string":
      return String(values[0] ?? "");
    case "bool":
      return Boolean(values[0]);
    default:
      throw new Error(`unsupported dsl op: ${node.op}`);
  }
}

function normalizeDslSpec(raw) {
  if (!isPlainObject(raw)) {
    throw new Error("dsl payload must be an object");
  }
  if (raw.version && raw.version !== DSL_VERSION) {
    throw new Error(`unsupported dsl version: ${raw.version}`);
  }
  const expr = raw.expr ?? raw;
  return {
    mode: "dsl",
    version: raw.version || DSL_VERSION,
    kind: raw.kind || "generic",
    cast: raw.cast || null,
    expr
  };
}

function normalizeJsSpec(raw) {
  if (!isPlainObject(raw)) {
    throw new Error("js payload must be an object");
  }
  if (raw.version && raw.version !== JS_VERSION) {
    throw new Error(`unsupported js version: ${raw.version}`);
  }
  if (typeof raw.code !== "string" || !raw.code.trim()) {
    throw new Error("js code is required");
  }
  if (raw.code.length > MAX_JS_CODE_LENGTH) {
    throw new Error(
      `js code too long (max ${MAX_JS_CODE_LENGTH} chars)`
    );
  }
  const timeoutMsRaw =
    raw.timeoutMs == null ? DEFAULT_JS_TIMEOUT_MS : Number(raw.timeoutMs);
  if (!Number.isFinite(timeoutMsRaw) || timeoutMsRaw <= 0) {
    throw new Error("js timeoutMs must be a positive number");
  }
  const timeoutMs = Math.min(Math.trunc(timeoutMsRaw), MAX_JS_TIMEOUT_MS);
  return {
    mode: "js",
    engine: "js",
    version: raw.version || JS_VERSION,
    cast: raw.cast || null,
    timeoutMs,
    code: raw.code
  };
}

function normalizeObjectSpec(raw) {
  if (raw.engine === "js" || raw.mode === "js" || "code" in raw) {
    return normalizeJsSpec(raw);
  }
  return normalizeDslSpec(raw);
}

function parseTaskSpec(taskSpec) {
  if (isPlainObject(taskSpec)) {
    return normalizeObjectSpec(taskSpec);
  }
  if (typeof taskSpec !== "string") {
    throw new Error("taskSpec must be a string");
  }

  const trimmed = taskSpec.trim();
  if (!trimmed) {
    throw new Error("empty taskSpec");
  }

  if (trimmed.startsWith(DSL_PREFIX)) {
    const dsl = JSON.parse(trimmed.slice(DSL_PREFIX.length));
    return normalizeDslSpec(dsl);
  }
  if (trimmed.startsWith(JS_PREFIX)) {
    const jsPayload = trimmed.slice(JS_PREFIX.length).trim();
    if (!jsPayload) {
      throw new Error("empty js task payload");
    }
    if (jsPayload.startsWith("{")) {
      return normalizeJsSpec(JSON.parse(jsPayload));
    }
    const wrappedCode =
      /(^|[\s;])return[\s(]/.test(jsPayload) || jsPayload.includes(";")
        ? jsPayload
        : `return (${jsPayload});`;
    return normalizeJsSpec({ code: wrappedCode });
  }
  if (trimmed.startsWith("{")) {
    const spec = JSON.parse(trimmed);
    return normalizeObjectSpec(spec);
  }
  return { mode: "legacy-expression", expression: trimmed };
}

function applyCast(value, cast) {
  if (!cast) {
    return value;
  }
  switch (cast) {
    case "number":
      return toFiniteNumber(value, "cast.number");
    case "string":
      return String(value ?? "");
    case "bool":
      return Boolean(value);
    case "json":
      return JSON.stringify(value);
    default:
      throw new Error(`unsupported cast: ${cast}`);
  }
}

export function encodeDslTask(spec) {
  return `${DSL_PREFIX}${JSON.stringify({
    version: DSL_VERSION,
    ...spec
  })}`;
}

export function executeTaskSpec(taskSpec, inputs) {
  const parsed = parseTaskSpec(taskSpec);
  if (parsed.mode === "legacy-expression") {
    return evalLegacyExpression(parsed.expression, inputs);
  }
  if (parsed.mode === "js") {
    return executeJsSpec(parsed, inputs);
  }
  const result = evalNode(parsed.expr, { inputs });
  return applyCast(result, parsed.cast);
}

export function toChainString(value) {
  if (value === null || value === undefined) {
    return "";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

function buildJsHelpers() {
  return Object.freeze({
    mean: (arr) => avg(arr.map((x, i) => toFiniteNumber(x, `mean[${i}]`))),
    median: (arr) =>
      median(arr.map((x, i) => toFiniteNumber(x, `median[${i}]`))),
    stddev: (arr) =>
      stddev(arr.map((x, i) => toFiniteNumber(x, `stddev[${i}]`))),
    weightedMean,
    clamp,
    toNumber: (value, label = "value") => toFiniteNumber(value, label),
    round: (value, digits = 0) => {
      const n = toFiniteNumber(value, "round.value");
      const d = Math.trunc(toFiniteNumber(digits, "round.digits"));
      const factor = 10 ** d;
      return Math.round(n * factor) / factor;
    }
  });
}

function buildSafeInputs(inputs) {
  const source = isPlainObject(inputs) ? inputs : {};
  const safe = {};
  for (const [k, v] of Object.entries(source)) {
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(k)) {
      continue;
    }
    if (
      v === null ||
      typeof v === "string" ||
      typeof v === "number" ||
      typeof v === "boolean"
    ) {
      safe[k] = v;
      continue;
    }
    try {
      safe[k] = JSON.parse(JSON.stringify(v));
    } catch (err) {
      throw new Error(`input "${k}" is not serializable`);
    }
  }
  return Object.freeze(safe);
}

function executeJsSpec(spec, inputs) {
  const safeInputs = buildSafeInputs(inputs);
  const helpers = buildJsHelpers();
  const aliases = Object.keys(safeInputs);
  const destruct =
    aliases.length > 0 ? `const { ${aliases.join(", ")} } = inputs;` : "";

  const source = [
    '"use strict";',
    "const inputs = globalThis.__inputs;",
    "const helpers = globalThis.__helpers;",
    destruct,
    "(() => {",
    spec.code,
    "})()"
  ].join("\n");

  const sandbox = {
    Math,
    Number,
    String,
    Boolean,
    JSON,
    __inputs: safeInputs,
    __helpers: helpers
  };
  const context = vm.createContext(sandbox, {
    name: "compute-task-js",
    codeGeneration: { strings: false, wasm: false }
  });
  const script = new vm.Script(source, {
    filename: "compute-task.js"
  });
  const result = script.runInContext(context, { timeout: spec.timeoutMs });

  if (result === undefined) {
    throw new Error("js task returned undefined");
  }
  return applyCast(result, spec.cast);
}
