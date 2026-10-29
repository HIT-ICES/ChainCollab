#!/usr/bin/env node
const fs = require("fs");
const path = require("path");
function parseArgs(argv) {
  const args = {};
  for (let i = 2; i < argv.length; i += 1) {
    const key = argv[i];
    const value = argv[i + 1];
    if (key.startsWith("--")) {
      args[key.slice(2)] = value;
      i += 1;
    }
  }
  return args;
}

function loadAstFromSolcOutput(raw) {
  const cleaned = raw.replace(/^>>> Cannot retry compilation with SMT because there are no SMT solvers available\.\n/m, "");
  const parsed = JSON.parse(cleaned);
  const sourceName = Object.keys(parsed.sources || {})[0];
  if (!sourceName || !parsed.sources[sourceName].ast) {
    throw new Error("Failed to obtain Solidity AST from solc output.");
  }
  return parsed.sources[sourceName].ast;
}

function text(node) {
  if (!node) return "";
  if (node.nodeType === "ElementaryTypeNameExpression" && node.typeName) return text(node.typeName);
  if (node.nodeType === "IdentifierPath" && node.name) return node.name;
  if (node.nodeType === "Identifier") return node.name;
  if (node.nodeType === "MemberAccess") return `${text(node.expression)}.${node.memberName}`;
  if (node.nodeType === "IndexAccess") return `${text(node.baseExpression)}[${text(node.indexExpression)}]`;
  if (node.nodeType === "FunctionCall") return text(node.expression);
  if (node.nodeType === "BinaryOperation") return `${text(node.leftExpression)} ${node.operator} ${text(node.rightExpression)}`;
  if (node.nodeType === "UnaryOperation") return `${node.operator || ""}${text(node.subExpression)}`;
  if (node.nodeType === "TupleExpression") return (node.components || []).map(text).join(", ");
  if (node.nodeType === "VariableDeclaration" && node.name) return node.name;
  if (typeof node.name === "string" && node.name) return node.name;
  if (typeof node.memberName === "string" && node.memberName) return node.memberName;
  if (typeof node.value === "string") return node.value;
  return node.nodeType || "";
}

function collectParameters(parameters) {
  return (parameters?.parameters || []).map((item) => ({
    name: item.name || "",
    type: text(item.typeName),
  }));
}

function walk(node, state) {
  if (!node || typeof node !== "object") return;

  const prevContract = state.currentContract;
  const prevFunction = state.currentFunction;

  if (node.nodeType === "ContractDefinition") {
    state.currentContract = node.name || "";
    state.output.contracts.push({
      name: node.name || "",
      kind: node.contractKind || "",
    });
  }

  if (node.nodeType === "EnumDefinition") {
    state.output.enums.push({
      contract: state.currentContract,
      name: node.name || "",
      values: (node.members || []).map((item) => item.name),
    });
  }

  if (node.nodeType === "EventDefinition") {
    state.output.events.push({
      contract: state.currentContract,
      name: node.name || "",
      parameters: collectParameters(node.parameters),
    });
  }

  if (node.nodeType === "VariableDeclaration" && node.stateVariable) {
    state.output.state_variables.push({
      contract: state.currentContract,
      name: node.name || "",
      type: text(node.typeName),
      visibility: node.visibility || "",
    });
  }

  if (node.nodeType === "StructDefinition" && node.name === "StateMemory") {
    for (const member of node.members || []) {
      state.output.state_variables.push({
        contract: state.currentContract,
        name: member.name || "",
        type: text(member.typeName),
        container: "StateMemory",
      });
    }
  }

  if (node.nodeType === "FunctionDefinition") {
    state.currentFunction = node.name || node.kind || "";
    state.output.functions.push({
      contract: state.currentContract,
      name: state.currentFunction,
      kind: node.kind || "",
      visibility: node.visibility || "",
      state_mutability: node.stateMutability || "",
      modifiers: (node.modifiers || []).map((item) => text(item.modifierName)),
      parameters: collectParameters(node.parameters),
      returns: collectParameters(node.returnParameters),
    });
  }

  if (node.nodeType === "IfStatement") {
    state.output.if_conditions.push({
      contract: state.currentContract,
      function: state.currentFunction,
      condition: text(node.condition),
    });
  }

  if (node.nodeType === "Assignment") {
    state.output.assignments.push({
      contract: state.currentContract,
      function: state.currentFunction,
      lhs: text(node.leftHandSide),
      rhs: text(node.rightHandSide),
      operator: node.operator || "=",
    });
  }

  if (node.nodeType === "FunctionCall") {
    const callee = text(node.expression);
    const args = (node.arguments || []).map(text);
    const callInfo = {
      contract: state.currentContract,
      function: state.currentFunction,
      callee,
      arguments: args,
    };
    state.output.calls.push(callInfo);
    if (callee === "require" || callee === "assert") {
      state.output.requires.push(callInfo);
    } else if (callee.includes(".") || callee.startsWith("IOracle") || callee.startsWith("IIdentityRegistry")) {
      state.output.external_calls.push(callInfo);
    }
  }

  if (node.nodeType === "Literal" && typeof node.value === "string" && node.value) {
    state.literalSet.add(node.value);
  }

  for (const value of Object.values(node)) {
    if (Array.isArray(value)) {
      value.forEach((item) => walk(item, state));
    } else if (value && typeof value === "object" && value.nodeType) {
      walk(value, state);
    }
  }

  state.currentContract = prevContract;
  state.currentFunction = prevFunction;
}

function main() {
  const args = parseArgs(process.argv);
  if (!args["ast-json"] || !args.output) {
    throw new Error("--ast-json and --output are required");
  }
  const ast = loadAstFromSolcOutput(fs.readFileSync(path.resolve(args["ast-json"]), "utf8"));
  const state = {
    currentContract: "",
    currentFunction: "",
    literalSet: new Set(),
    output: {
      contracts: [],
      state_variables: [],
      enums: [],
      functions: [],
      requires: [],
      assignments: [],
      events: [],
      external_calls: [],
      calls: [],
      if_conditions: [],
      string_literals: [],
    },
  };
  walk(ast, state);
  state.output.string_literals = Array.from(state.literalSet).sort();
  fs.writeFileSync(path.resolve(args.output), `${JSON.stringify(state.output, null, 2)}\n`, "utf8");
}

main();
