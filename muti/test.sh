#!/bin/zsh

base_command="python3.10 test.py test 50 b2de16e1129c0c6f6d6f481cf461aca1c2f11a0385720bf6623fcb4758f8d433"

for value in $(seq 110 10 130); do
    command="$base_command $value"
    
    echo "Running: $command"
    
    eval $command
    
done