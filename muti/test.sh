#!/bin/zsh

base_command="python3.10 test.py test 10 784d3988f9ef4910bbecbb5ad6ac1ac9592683d0476ca1ddced58209542d4217"

for value in $(seq 110 10 150); do
    command="$base_command $value"
    
    echo "Running: $command"
    
    eval $command
    
done