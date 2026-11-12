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
	"strings"
)

type FieldInfo struct {
	Name string `json:"name"`
	Type string `json:"type"`
}

type IfInfo struct {
	Condition string `json:"condition"`
	Then      string `json:"then"`
	Else      string `json:"else,omitempty"`
}

type CallInfo struct {
	Callee string   `json:"callee"`
	Args   []string `json:"args"`
}

type AssignmentInfo struct {
	LHS []string `json:"lhs"`
	RHS []string `json:"rhs"`
}

type FunctionInfo struct {
	Name        string           `json:"name"`
	Receiver    string           `json:"receiver,omitempty"`
	Body        string           `json:"body"`
	Calls       []CallInfo       `json:"calls"`
	Assignments []AssignmentInfo `json:"assignments"`
	Ifs         []IfInfo         `json:"ifs"`
}

type Output struct {
	Contract    string       `json:"contract"`
	Structs     []string     `json:"structs"`
	StateFields []FieldInfo  `json:"state_fields"`
	Functions   []FunctionInfo `json:"functions"`
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

func exprList(fset *token.FileSet, items []ast.Expr) []string {
	out := make([]string, 0, len(items))
	for _, item := range items {
		out = append(out, render(fset, item))
	}
	return out
}

func fieldType(fset *token.FileSet, field *ast.Field) []FieldInfo {
	if field == nil {
		return nil
	}
	typeName := render(fset, field.Type)
	if len(field.Names) == 0 {
		return []FieldInfo{{Name: typeName, Type: typeName}}
	}
	fields := make([]FieldInfo, 0, len(field.Names))
	for _, name := range field.Names {
		fields = append(fields, FieldInfo{Name: name.Name, Type: typeName})
	}
	return fields
}

func receiverName(fset *token.FileSet, fn *ast.FuncDecl) string {
	if fn.Recv == nil || len(fn.Recv.List) == 0 {
		return ""
	}
	return render(fset, fn.Recv.List[0].Type)
}

func main() {
	input := flag.String("input", "", "Go source file")
	output := flag.String("output", "", "Output JSON file")
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

	result := Output{Contract: file.Name.Name}
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
			result.Structs = append(result.Structs, typeSpec.Name.Name)
			structType, ok := typeSpec.Type.(*ast.StructType)
			if !ok {
				continue
			}
			if typeSpec.Name.Name != "StateMemory" {
				continue
			}
			for _, field := range structType.Fields.List {
				result.StateFields = append(result.StateFields, fieldType(fset, field)...)
			}
		}
	}

	for _, decl := range file.Decls {
		fn, ok := decl.(*ast.FuncDecl)
		if !ok {
			continue
		}
		info := FunctionInfo{
			Name:     fn.Name.Name,
			Receiver: receiverName(fset, fn),
			Body:     strings.TrimSpace(render(fset, fn.Body)),
		}
		if fn.Body != nil {
			ast.Inspect(fn.Body, func(node ast.Node) bool {
				switch item := node.(type) {
				case *ast.CallExpr:
					info.Calls = append(info.Calls, CallInfo{
						Callee: render(fset, item.Fun),
						Args:   exprList(fset, item.Args),
					})
				case *ast.AssignStmt:
					info.Assignments = append(info.Assignments, AssignmentInfo{
						LHS: exprList(fset, item.Lhs),
						RHS: exprList(fset, item.Rhs),
					})
				case *ast.IfStmt:
					elseText := ""
					if item.Else != nil {
						elseText = render(fset, item.Else)
					}
					info.Ifs = append(info.Ifs, IfInfo{
						Condition: render(fset, item.Cond),
						Then:      render(fset, item.Body),
						Else:      elseText,
					})
				}
				return true
			})
		}
		result.Functions = append(result.Functions, info)
	}

	payload, err := json.MarshalIndent(result, "", "  ")
	if err != nil {
		fmt.Fprintf(os.Stderr, "marshal failed: %v\n", err)
		os.Exit(1)
	}
	if err := os.WriteFile(*output, append(payload, '\n'), 0o644); err != nil {
		fmt.Fprintf(os.Stderr, "write failed: %v\n", err)
		os.Exit(1)
	}
}

