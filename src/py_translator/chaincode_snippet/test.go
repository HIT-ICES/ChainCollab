package main

import "fmt"

type Person struct {
	Name string
	Age  int
}

func main() {
	var i interface{} = Person{"Alice", 30}

	// 类型断言为 Person 类型的值
	p := i.(Person)

	// 修改原始值
	p.Name = "Bob"

	// 查看原始值是否发生改变
	fmt.Println(i.(Person).Name) // 输出 Alice

	// 类型断言为 Person 类型的指针
	pPointer := i.(*Person)

	// 通过指针修改原始值
	pPointer.Name = "Charlie"

	// 查看原始值是否发生改变
	fmt.Println(i.(Person).Name) // 输出 Charlie
}
