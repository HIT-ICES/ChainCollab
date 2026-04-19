# Experiment 2 Semantic Verification Summary

| Case | Type | DSL Globals | DSL Messages | DSL Flows | Go Coverage | Solidity Coverage | Assertion Check | Notes |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| Blood_analysis | positive | 7 | 6 | 11 | 100.00% | 100.00% | PASS | No major gaps in sampled rules. |
| Hotel_Booking | positive | 15 | 13 | 21 | 100.00% | 100.00% | PASS | No major gaps in sampled rules. |
| ManagementSystem | positive | 7 | 6 | 11 | 100.00% | 100.00% | PASS | No major gaps in sampled rules. |
| Pizza_Order | positive | 8 | 8 | 14 | 100.00% | 100.00% | PASS | No major gaps in sampled rules. |
| Purchase | positive | 10 | 8 | 13 | 100.00% | 100.00% | PASS | No major gaps in sampled rules. |
| Rental_Claim | positive | 9 | 8 | 12 | 100.00% | 100.00% | PASS | No major gaps in sampled rules. |
| SupplyChain | positive | 12 | 11 | 16 | 100.00% | 100.00% | PASS | No major gaps in sampled rules. |
| SupplyChainPaper | positive | 14 | 13 | 19 | 100.00% | 100.00% | PASS | No major gaps in sampled rules. |
| customer | positive | 20 | 13 | 22 | 100.00% | 100.00% | PASS | No major gaps in sampled rules. |
| manufactory | positive | 12 | 10 | 14 | 100.00% | 100.00% | PASS | No major gaps in sampled rules. |

## Assertion Coverage

| ID | Dimension | Mode | Targets | Positive | Negative Trigger | Status |
| --- | --- | --- | --- | ---: | ---: | --- |
| SV01 | structural | positive | go,solidity | 100.00% (10/10) | N/A | covered |
| SV02 | structural | positive | go,solidity | 100.00% (10/10) | N/A | covered |
| SV03 | structural | positive | go,solidity | 100.00% (10/10) | N/A | covered |
| SV04 | structural | positive | go,solidity | 100.00% (10/10) | N/A | covered |
| SV05 | structural | positive | go,solidity | 100.00% (10/10) | N/A | covered |
| SV06 | structural | positive | go,solidity | 100.00% (10/10) | N/A | covered |
| SV07 | structural | positive | go,solidity | N/A | N/A | unobserved |
| SV08 | control | positive | go,solidity | 100.00% (10/10) | N/A | covered |
| SV09 | control | both | go | 100.00% (10/10) | N/A | positive_only |
| SV10 | control | both | solidity | 100.00% (10/10) | N/A | positive_only |
| SV11 | control | both | go | 100.00% (10/10) | N/A | positive_only |
| SV12 | control | both | solidity | 100.00% (10/10) | N/A | positive_only |
| SV13 | control | both | solidity | 100.00% (10/10) | N/A | positive_only |
| SV14 | control | both | go,solidity | 100.00% (10/10) | N/A | positive_only |
