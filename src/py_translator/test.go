package main

import "fmt"

type A struct {
	Name string
}

type B struct {
	Age int
}

func main() {
	a := &A{Name: "Alice"}
	pA := interface{}(a)
	b, ok := pA.(*B)
	if !ok {
		fmt.Println("类型转换失败")
		return
	}
	fmt.Println(b)
}
