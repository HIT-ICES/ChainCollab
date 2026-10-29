package main

import (
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"go/ast"
	"go/parser"
	"go/printer"
	"go/token"
	"os"
	"sort"
	"strings"
)

type FieldInfo struct {
	Name string `json:"name"`
	Type string `json:"type"`
}

type StructInfo struct {
	Name   string      `json:"name"`
	Fields []FieldInfo `json:"fields"`
}

type FunctionInfo struct {
	Name     string   `json:"name"`
	Receiver string   `json:"receiver,omitempty"`
	Params   []string `json:"params"`
	Results  []string `json:"results"`
}

type ConditionInfo struct {
	Function  string `json:"function"`
	Condition string `json:"condition"`
}

type SwitchInfo struct {
	Function string `json:"function"`
	Tag      string `json:"tag"`
}

type AssignmentInfo struct {
	Function string   `json:"function"`
	LHS      []string `json:"lhs"`
	RHS      []string `json:"rhs"`
}

type CallInfo struct {
	Function string   `json:"function"`
	Callee   string   `json:"callee"`
	Args     []string `json:"args"`
}

type Output struct {
	Structs       []StructInfo      `json:"structs"`
	StateFields   []FieldInfo       `json:"state_fields"`
	Functions     []FunctionInfo    `json:"functions"`
	IfConditions  []ConditionInfo   `json:"if_conditions"`
	Switches      []SwitchInfo      `json:"switches"`
	Assignments   []AssignmentInfo  `json:"assignments"`
	ExternalCalls []CallInfo        `json:"external_calls"`
	Calls         []CallInfo        `json:"calls"`
	StringLiterals []string         `json:"string_literals"`
}

func render(fset *token.FileSet, node any) string {
	if node == nil {
		return ""
	}
	var buf bytes.Buffer
	if err := printer.Fprint(&buf, fset, node); err != nil {
		return ""
	}
	return buf.String()
}

func exprList(fset *token.FileSet, exprs []ast.Expr) []string {
	out := make([]string, 0, len(exprs))
	for _, expr := range exprs {
		out = append(out, render(fset, expr))
	}
	return out
}

func typeList(fset *token.FileSet, fieldList *ast.FieldList) []string {
	if fieldList == nil {
		return nil
	}
	var result []string
	for _, field := range fieldList.List {
		typeName := render(fset, field.Type)
		if len(field.Names) == 0 {
			result = append(result, typeName)
			continue
		}
		for range field.Names {
			result = append(result, typeName)
		}
	}
	return result
}

func receiverName(fset *token.FileSet, fn *ast.FuncDecl) string {
	if fn.Recv == nil || len(fn.Recv.List) == 0 {
		return ""
	}
	return render(fset, fn.Recv.List[0].Type)
}

func collectStruct(fset *token.FileSet, spec *ast.TypeSpec) *StructInfo {
	structType, ok := spec.Type.(*ast.StructType)
	if !ok {
		return nil
	}
	info := &StructInfo{Name: spec.Name.Name}
	for _, field := range structType.Fields.List {
		fieldType := render(fset, field.Type)
		if len(field.Names) == 0 {
			info.Fields = append(info.Fields, FieldInfo{Name: fieldType, Type: fieldType})
			continue
		}
		for _, name := range field.Names {
			info.Fields = append(info.Fields, FieldInfo{Name: name.Name, Type: fieldType})
		}
	}
	return info
}

func isExternalCall(callee string) bool {
	if strings.Contains(callee, "oracle.") || strings.Contains(callee, "json.") || strings.Contains(callee, "fmt.") || strings.Contains(callee, "ctx.") {
		return true
	}
	if strings.Contains(callee, ".GetStub") || strings.Contains(callee, ".GetClientIdentity") || strings.Contains(callee, ".InvokeChaincode") {
		return true
	}
	return strings.HasPrefix(callee, "shim.") || strings.HasPrefix(callee, "contractapi.")
}

func main() {
	input := flag.String("input", "", "Path to Go source.")
	output := flag.String("output", "", "Output JSON path.")
	flag.Parse()

	if *input == "" || *output == "" {
		fmt.Fprintln(os.Stderr, "--input and --output are required")
		os.Exit(1)
	}

	fset := token.NewFileSet()
	file, err := parser.ParseFile(fset, *input, nil, parser.ParseComments)
	if err != nil {
		fmt.Fprintf(os.Stderr, "parse failed: %v\n", err)
		os.Exit(1)
	}

	result := Output{}
	stringLiteralSet := map[string]struct{}{}

	for _, decl := range file.Decls {
		genDecl, ok := decl.(*ast.GenDecl)
		if !ok {
			continue
		}
		for _, spec := range genDecl.Specs {
			typeSpec, ok := spec.(*ast.TypeSpec)
			if !ok {
				continue
			}
			info := collectStruct(fset, typeSpec)
			if info == nil {
				continue
			}
			result.Structs = append(result.Structs, *info)
			if info.Name == "StateMemory" {
				result.StateFields = append(result.StateFields, info.Fields...)
			}
		}
	}

	for _, decl := range file.Decls {
		fn, ok := decl.(*ast.FuncDecl)
		if !ok {
			continue
		}
		fnInfo := FunctionInfo{
			Name:     fn.Name.Name,
			Receiver: receiverName(fset, fn),
			Params:   typeList(fset, fn.Type.Params),
			Results:  typeList(fset, fn.Type.Results),
		}
		result.Functions = append(result.Functions, fnInfo)

		ast.Inspect(fn.Body, func(node ast.Node) bool {
			switch n := node.(type) {
			case *ast.IfStmt:
				result.IfConditions = append(result.IfConditions, ConditionInfo{
					Function: fn.Name.Name,
					Condition: render(fset, n.Cond),
				})
			case *ast.SwitchStmt:
				result.Switches = append(result.Switches, SwitchInfo{
					Function: fn.Name.Name,
					Tag: render(fset, n.Tag),
				})
			case *ast.AssignStmt:
				result.Assignments = append(result.Assignments, AssignmentInfo{
					Function: fn.Name.Name,
					LHS: exprList(fset, n.Lhs),
					RHS: exprList(fset, n.Rhs),
				})
			case *ast.CallExpr:
				call := CallInfo{
					Function: fn.Name.Name,
					Callee: render(fset, n.Fun),
					Args: exprList(fset, n.Args),
				}
				result.Calls = append(result.Calls, call)
				if isExternalCall(call.Callee) {
					result.ExternalCalls = append(result.ExternalCalls, call)
				}
			case *ast.BasicLit:
				if n.Kind.String() == "STRING" {
					value := strings.Trim(n.Value, "`\"")
					if value != "" {
						stringLiteralSet[value] = struct{}{}
					}
				}
			}
			return true
		})
	}

	for literal := range stringLiteralSet {
		result.StringLiterals = append(result.StringLiterals, literal)
	}
	sort.Strings(result.StringLiterals)

	payload, err := json.MarshalIndent(result, "", "  ")
	if err != nil {
		fmt.Fprintf(os.Stderr, "marshal failed: %v\n", err)
		os.Exit(1)
	}
	if err := os.WriteFile(*output, payload, 0o644); err != nil {
		fmt.Fprintf(os.Stderr, "write failed: %v\n", err)
		os.Exit(1)
	}
}
