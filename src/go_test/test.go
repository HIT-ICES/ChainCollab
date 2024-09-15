package main

import "fmt"

type TestStruct struct{}

type MyString string

func (t *TestStruct) TestFunc() string {
	return "Hello World1"
}

func (t TestStruct) TestFunc2() string {
	return "Hello World2"
}

type TestInterface interface {
	TestFunc() string
}

func main() {
	t := TestStruct{}

	s := t.TestFunc()
	fmt.Println(s)

	if _, ok := interface{}(t).(TestInterface); ok {
		fmt.Println("t 符合 TestInterface 接口")
	} else {
		fmt.Println("t 不符合 TestInterface 接口")
	}

	test := MyString("Hello World")
	testByte := []byte(test)
	fmt.Print(testByte)
	n := 3
	fmt.Print([]byte(n))

}
