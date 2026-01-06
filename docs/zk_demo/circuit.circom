pragma circom 2.1.4;

// 证明者知道 a, b, c，使得 y = a * b + c
template DeterministicCompute() {
    signal input a;
    signal input b;
    signal input c;
    signal output y;

    y <== a * b + c;
}

component main = DeterministicCompute();
