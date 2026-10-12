# Chat 27 analysis results (run once against ANALYSIS_PLAN_2026-11)

Seed 20261012; 2000 bootstrap resamples within field; Holm across the five fields; alpha 0.05.

## Inclusion

- drawn and matched (run input): 601
- 1. status ok: 599
- 2. name match approved (high confidence): 599
- 3. OpenAlex coverage 0.25-4 x list citations: 596

Excluded (field, group, reason):
- ECO-B: status: skipped_over_80000_citations
- ECO-R: status: skipped_over_80000_citations
- MAT-B: coverage outside 0.25-4
- ECO-S: coverage outside 0.25-4
- MAT-R: coverage outside 0.25-4

Included per cell (S / B / C / R):
- ENG: S 33 / B 34 / C 33 / R 22 = 122
- PHY: S 34 / B 37 / C 36 / R 23 = 130
- MED: S 30 / B 32 / C 33 / R 22 = 117
- MAT: S 34 / B 30 / C 31 / R 17 = 112  (R below 20: described, not tested)
- ECO: S 33 / B 35 / C 29 / R 18 = 115  (R below 20: described, not tested)

## A. Validation

| Field | n | V1 ρ | V1 median diff (points) | V2 ρ | flag |
|---|---|---|---|---|---|
| ENG | 122 | 0.94 | -1.3 | 0.95 |  |
| PHY | 130 | 0.93 | -1.6 | 0.93 |  |
| MED | 117 | 0.93 | -1.1 | 0.95 |  |
| MAT | 112 | 0.96 | -1.7 | 0.95 |  |
| ECO | 115 | 0.95 | -0.7 | 0.90 |  |

## B. H1, primary: full Level-2 set per field

| Field | n | rule | D [95% CI] | Q [95% CI] |
|---|---|---|---|---|
| ENG | 122 | Self-citations: list rule | 0.0077 [0.0053, 0.0143] | 13.1% [4.9%, 21.3%] |
| ENG | 122 | Self-citations: also network | 0.0227 [0.0124, 0.0449] | 20.5% [10.7%, 30.3%] |
| ENG | 122 | Self-citations: fractional (equal) | 0.0028 [0.0017, 0.0064] | 4.9% [0.8%, 13.9%] |
| ENG | 122 | Credit: equal shares | 0.0832 [0.0483, 0.1472] | 32.8% [24.6%, 47.5%] |
| ENG | 122 | Credit: harmonic shares | 0.1221 [0.0780, 0.1939] | 41.8% [32.8%, 54.1%] |
| ENG | 122 | h: list rule | 0.0151 [0.0095, 0.0271] | 13.9% [9.0%, 26.2%] |
| ENG | 122 | h -> hm | 0.0894 [0.0622, 0.1395] | 36.1% [26.2%, 47.5%] |
| PHY | 130 | Self-citations: list rule | 0.0178 [0.0114, 0.0310] | 18.5% [10.0%, 30.0%] |
| PHY | 130 | Self-citations: also network | 0.0635 [0.0412, 0.0996] | 30.8% [19.2%, 43.8%] |
| PHY | 130 | Self-citations: fractional (equal) | 0.0043 [0.0025, 0.0102] | 10.8% [1.5%, 18.5%] |
| PHY | 130 | Credit: equal shares | 0.2395 [0.1692, 0.3336] | 50.8% [43.8%, 63.8%] |
| PHY | 130 | Credit: harmonic shares | 0.3103 [0.2264, 0.4198] | 56.9% [46.2%, 69.2%] |
| PHY | 130 | h: list rule | 0.0304 [0.0201, 0.0481] | 23.1% [16.2%, 34.6%] |
| PHY | 130 | h -> hm | 0.2974 [0.2124, 0.4087] | 60.0% [50.8%, 71.5%] |
| MED | 117 | Self-citations: list rule | 0.0029 [0.0023, 0.0062] | 6.8% [0.9%, 17.9%] |
| MED | 117 | Self-citations: also network | 0.0099 [0.0070, 0.0184] | 8.5% [5.1%, 23.1%] |
| MED | 117 | Self-citations: fractional (equal) | 0.0007 [0.0005, 0.0021] | 3.4% [0.0%, 10.3%] |
| MED | 117 | Credit: equal shares | 0.1945 [0.1280, 0.2867] | 53.8% [42.7%, 64.1%] |
| MED | 117 | Credit: harmonic shares | 0.2407 [0.1668, 0.3440] | 59.0% [47.9%, 69.2%] |
| MED | 117 | h: list rule | 0.0071 [0.0050, 0.0132] | 7.7% [3.4%, 19.7%] |
| MED | 117 | h -> hm | 0.2389 [0.1560, 0.3454] | 52.1% [41.9%, 63.2%] |
| MAT | 112 | Self-citations: list rule | 0.0238 [0.0153, 0.0425] | 19.6% [11.6%, 33.0%] |
| MAT | 112 | Self-citations: also network | 0.0456 [0.0293, 0.0753] | 24.1% [17.0%, 40.2%] |
| MAT | 112 | Self-citations: fractional (equal) | 0.0076 [0.0051, 0.0157] | 12.5% [4.5%, 22.3%] |
| MAT | 112 | Credit: equal shares | 0.0721 [0.0509, 0.1080] | 33.9% [25.0%, 46.5%] |
| MAT | 112 | Credit: harmonic shares | 0.0915 [0.0659, 0.1317] | 34.8% [27.7%, 50.9%] |
| MAT | 112 | h: list rule | 0.0446 [0.0304, 0.0716] | 26.8% [18.8%, 41.1%] |
| MAT | 112 | h -> hm | 0.1569 [0.1056, 0.2270] | 45.5% [34.8%, 58.0%] |
| ECO | 115 | Self-citations: list rule | 0.0087 [0.0034, 0.0205] | 8.7% [3.5%, 19.2%] |
| ECO | 115 | Self-citations: also network | 0.0149 [0.0072, 0.0311] | 13.9% [6.1%, 24.3%] |
| ECO | 115 | Self-citations: fractional (equal) | 0.0029 [0.0009, 0.0082] | 3.5% [0.0%, 13.9%] |
| ECO | 115 | Credit: equal shares | 0.0606 [0.0382, 0.1023] | 31.3% [22.6%, 44.3%] |
| ECO | 115 | Credit: harmonic shares | 0.0810 [0.0544, 0.1284] | 37.4% [28.7%, 50.4%] |
| ECO | 115 | h: list rule | 0.0151 [0.0080, 0.0285] | 14.8% [7.8%, 26.1%] |
| ECO | 115 | h -> hm | 0.1616 [0.1054, 0.2433] | 53.0% [40.0%, 63.5%] |

Ratios (credit / self), bootstrap interval, one-sided p, Holm p (tested fields only):

| Field | ratio | value [95% CI] | p | p Holm |
|---|---|---|---|---|
| ENG | D:credit_equal/self_list | 10.77 [5.13, 18.98] | <0.001 | 0.002 |
| ENG | Q:credit_equal/self_list | 2.50 [1.56, 6.67] | <0.001 | 0.002 |
| ENG | D:credit_harmonic/self_list | 15.81 [7.78, 25.34] | <0.001 | 0.002 |
| ENG | Q:credit_harmonic/self_list | 3.19 [1.92, 8.40] | <0.001 | 0.002 |
| ENG | D:h_credit/h_self | 5.90 [3.30, 9.76] | <0.001 | 0.002 |
| ENG | Q:h_credit/h_self | 2.59 [1.31, 4.27] | 0.002 | 0.005 |
| ENG | D:credit_equal/self_network | 3.67 [1.66, 7.77] | 0.001 | 0.003 |
| ENG | Q:credit_equal/self_network | 1.60 [1.12, 3.31] | 0.008 | 0.017 |
| ENG | D:credit_harmonic/self_network | 5.39 [2.48, 10.98] | <0.001 | 0.002 |
| ENG | Q:credit_harmonic/self_network | 2.04 [1.37, 4.08] | 0.001 | 0.003 |
| PHY | D:credit_equal/self_list | 13.44 [7.83, 21.24] | <0.001 | 0.002 |
| PHY | Q:credit_equal/self_list | 2.75 [1.83, 5.08] | <0.001 | 0.002 |
| PHY | D:credit_harmonic/self_list | 17.42 [10.21, 26.94] | <0.001 | 0.002 |
| PHY | Q:credit_harmonic/self_list | 3.08 [1.89, 5.73] | <0.001 | 0.002 |
| PHY | D:h_credit/h_self | 9.79 [5.98, 14.82] | <0.001 | 0.002 |
| PHY | Q:h_credit/h_self | 2.60 [1.73, 3.73] | <0.001 | 0.002 |
| PHY | D:credit_equal/self_network | 3.77 [2.46, 5.74] | <0.001 | 0.002 |
| PHY | Q:credit_equal/self_network | 1.65 [1.23, 2.68] | <0.001 | 0.004 |
| PHY | D:credit_harmonic/self_network | 4.89 [3.15, 7.54] | <0.001 | 0.002 |
| PHY | Q:credit_harmonic/self_network | 1.85 [1.26, 3.00] | <0.001 | 0.002 |
| MED | D:credit_equal/self_list | 66.21 [26.82, 95.38] | <0.001 | 0.002 |
| MED | Q:credit_equal/self_list | 7.87 [3.00, 49.00] (inf in 20) | <0.001 | 0.002 |
| MED | D:credit_harmonic/self_list | 81.94 [34.83, 115.13] | <0.001 | 0.002 |
| MED | Q:credit_harmonic/self_list | 8.62 [3.26, 57.00] (inf in 20) | <0.001 | 0.002 |
| MED | D:h_credit/h_self | 33.61 [15.76, 52.84] | <0.001 | 0.002 |
| MED | Q:h_credit/h_self | 6.78 [2.60, 15.25] | <0.001 | 0.002 |
| MED | D:credit_equal/self_network | 19.72 [10.04, 29.91] | <0.001 | 0.002 |
| MED | Q:credit_equal/self_network | 6.30 [2.31, 10.00] | <0.001 | 0.002 |
| MED | D:credit_harmonic/self_network | 24.41 [12.57, 36.97] | <0.001 | 0.002 |
| MED | Q:credit_harmonic/self_network | 6.90 [2.54, 11.17] | <0.001 | 0.002 |
| MAT | D:credit_equal/self_list | 3.03 [1.71, 5.15] | <0.001 | 0.002 |
| MAT | Q:credit_equal/self_list | 1.73 [1.02, 3.00] | 0.025 | 0.025 |
| MAT | D:credit_harmonic/self_list | 3.85 [2.08, 6.85] | <0.001 | 0.002 |
| MAT | Q:credit_harmonic/self_list | 1.77 [1.07, 3.54] | 0.014 | 0.014 |
| MAT | D:h_credit/h_self | 3.52 [2.03, 5.60] | <0.001 | 0.002 |
| MAT | Q:h_credit/h_self | 1.70 [0.98, 2.65] | 0.037 | 0.037 |
| MAT | D:credit_equal/self_network | 1.58 [0.92, 2.73] | 0.046 | 0.046 |
| MAT | Q:credit_equal/self_network | 1.41 [0.79, 2.10] | 0.191 | 0.191 |
| MAT | D:credit_harmonic/self_network | 2.00 [1.16, 3.47] | 0.007 | 0.007 |
| MAT | Q:credit_harmonic/self_network | 1.44 [0.86, 2.48] | 0.091 | 0.091 |
| ECO | D:credit_equal/self_list | 6.95 [2.98, 17.24] | <0.001 | 0.002 |
| ECO | Q:credit_equal/self_list | 3.60 [1.64, 9.25] (inf in 2) | <0.001 | 0.002 |
| ECO | D:credit_harmonic/self_list | 9.28 [4.00, 23.06] | <0.001 | 0.002 |
| ECO | Q:credit_harmonic/self_list | 4.30 [1.95, 11.69] (inf in 2) | <0.001 | 0.002 |
| ECO | D:h_credit/h_self | 10.70 [5.20, 20.71] | <0.001 | 0.002 |
| ECO | Q:h_credit/h_self | 3.59 [1.86, 6.88] (inf in 1) | <0.001 | 0.002 |
| ECO | D:credit_equal/self_network | 4.07 [2.05, 8.42] | <0.001 | 0.002 |
| ECO | Q:credit_equal/self_network | 2.25 [1.29, 4.86] | <0.001 | 0.004 |
| ECO | D:credit_harmonic/self_network | 5.45 [2.80, 11.14] | <0.001 | 0.002 |
| ECO | Q:credit_harmonic/self_network | 2.69 [1.56, 5.89] | <0.001 | 0.002 |

## B. H1, secondary: random reference group only

| Field | n | rule | D [95% CI] | Q [95% CI] |
|---|---|---|---|---|
| ENG | 22 | Self-citations: list rule | 0.0158 [0.0034, 0.0663] | 18.2% [0.0%, 45.5%] |
| ENG | 22 | Self-citations: also network | 0.0395 [0.0069, 0.1573] | 36.4% [0.0%, 54.5%] |
| ENG | 22 | Self-citations: fractional (equal) | 0.0068 [0.0000, 0.0354] | 27.3% [0.0%, 40.9%] |
| ENG | 22 | Credit: equal shares | 0.2213 [0.0204, 0.6087] | 36.4% [4.5%, 72.7%] |
| ENG | 22 | Credit: harmonic shares | 0.2530 [0.0330, 0.6556] | 36.4% [13.6%, 72.7%] |
| ENG | 22 | h: list rule | 0.0323 [0.0075, 0.1105] | 22.7% [0.0%, 54.5%] |
| ENG | 22 | h -> hm | 0.0603 [0.0135, 0.1868] | 36.4% [4.5%, 63.6%] |
| PHY | 23 | Self-citations: list rule | 0.0158 [0.0020, 0.0728] | 8.7% [0.0%, 43.5%] |
| PHY | 23 | Self-citations: also network | 0.0168 [0.0010, 0.0758] | 0.0% [0.0%, 43.5%] |
| PHY | 23 | Self-citations: fractional (equal) | 0.0099 [0.0000, 0.0637] | 0.0% [0.0%, 34.8%] |
| PHY | 23 | Credit: equal shares | 0.1433 [0.0447, 0.3430] | 47.8% [17.4%, 78.3%] |
| PHY | 23 | Credit: harmonic shares | 0.1789 [0.0697, 0.4241] | 47.8% [26.1%, 78.3%] |
| PHY | 23 | h: list rule | 0.0153 [0.0030, 0.0636] | 8.7% [0.0%, 47.8%] |
| PHY | 23 | h -> hm | 0.2180 [0.0703, 0.4701] | 47.8% [21.7%, 78.3%] |
| MED | 22 | Self-citations: list rule | 0.0034 [0.0000, 0.0307] | 0.0% [0.0%, 22.7%] |
| MED | 22 | Self-citations: also network | 0.0090 [0.0000, 0.0579] | 9.1% [0.0%, 27.3%] |
| MED | 22 | Self-citations: fractional (equal) | 0.0011 [0.0000, 0.0170] | 0.0% [0.0%, 18.2%] |
| MED | 22 | Credit: equal shares | 0.1355 [0.0490, 0.3193] | 63.6% [18.2%, 77.3%] |
| MED | 22 | Credit: harmonic shares | 0.2326 [0.0978, 0.5284] | 77.3% [27.3%, 86.4%] |
| MED | 22 | h: list rule | 0.0096 [0.0011, 0.0494] | 22.7% [0.0%, 40.9%] |
| MED | 22 | h -> hm | 0.2793 [0.0899, 0.6381] | 50.0% [22.7%, 81.8%] |
| MAT | 17 | Self-citations: list rule | 0.0515 [0.0000, 0.2340] | 11.8% [0.0%, 52.9%] |
| MAT | 17 | Self-citations: also network | 0.0588 [0.0025, 0.2650] | 11.8% [0.0%, 58.8%] |
| MAT | 17 | Self-citations: fractional (equal) | 0.0490 [0.0000, 0.2321] | 11.8% [0.0%, 47.1%] |
| MAT | 17 | Credit: equal shares | 0.1127 [0.0398, 0.3263] | 58.8% [11.8%, 76.5%] |
| MAT | 17 | Credit: harmonic shares | 0.1275 [0.0297, 0.3666] | 47.1% [5.9%, 76.5%] |
| MAT | 17 | h: list rule | 0.0701 [0.0075, 0.2496] | 35.3% [5.9%, 64.7%] |
| MAT | 17 | h -> hm | 0.2670 [0.0998, 0.6106] | 64.7% [23.5%, 88.2%] |
| ECO | 18 | Self-citations: list rule | 0.0021 [0.0000, 0.0313] | 0.0% [0.0%, 22.2%] |
| ECO | 18 | Self-citations: also network | 0.0041 [0.0000, 0.0375] | 0.0% [0.0%, 33.3%] |
| ECO | 18 | Self-citations: fractional (equal) | 0.0021 [0.0000, 0.0313] | 0.0% [0.0%, 22.2%] |
| ECO | 18 | Credit: equal shares | 0.0248 [0.0000, 0.1336] | 22.2% [0.0%, 44.4%] |
| ECO | 18 | Credit: harmonic shares | 0.0640 [0.0042, 0.2513] | 22.2% [0.0%, 61.1%] |
| ECO | 18 | h: list rule | 0.0036 [0.0000, 0.0222] | 5.6% [0.0%, 27.8%] |
| ECO | 18 | h -> hm | 0.1167 [0.0187, 0.3731] | 38.9% [5.6%, 77.8%] |

Ratios (credit / self), bootstrap interval, one-sided p, Holm p (tested fields only):

| Field | ratio | value [95% CI] | p | p Holm |
|---|---|---|---|---|
| ENG | D:credit_equal/self_list | 14.00 [0.64, 90.04] (inf in 7) | 0.051 | 0.051 |
| ENG | Q:credit_equal/self_list | 2.00 [0.33, 11.80] (inf in 311) | 0.178 | 0.178 |
| ENG | D:credit_harmonic/self_list | 16.00 [1.27, 107.73] (inf in 7) | 0.011 | 0.011 |
| ENG | Q:credit_harmonic/self_list | 2.00 [0.56, 12.00] (inf in 311) | 0.118 | 0.118 |
| ENG | D:h_credit/h_self | 1.86 [0.48, 7.74] (inf in 1) | 0.170 | 0.170 |
| ENG | Q:h_credit/h_self | 1.60 [0.25, 8.00] (inf in 61) | 0.384 | 0.384 |
| ENG | D:credit_equal/self_network | 5.60 [0.23, 33.00] (inf in 1) | 0.147 | 0.147 |
| ENG | Q:credit_equal/self_network | 1.00 [0.25, 10.00] (inf in 110) | 0.285 | 0.285 |
| ENG | D:credit_harmonic/self_network | 6.40 [0.57, 38.56] (inf in 1) | 0.075 | 0.075 |
| ENG | Q:credit_harmonic/self_network | 1.00 [0.50, 10.00] (inf in 110) | 0.190 | 0.190 |
| PHY | D:credit_equal/self_list | 9.06 [1.90, 60.22] (inf in 15) | 0.004 | 0.008 |
| PHY | Q:credit_equal/self_list | 5.50 [0.93, 14.00] (inf in 273) | 0.038 | 0.077 |
| PHY | D:credit_harmonic/self_list | 11.31 [2.32, 75.40] (inf in 15) | <0.001 | 0.002 |
| PHY | Q:credit_harmonic/self_list | 5.50 [1.14, 14.00] (inf in 273) | 0.014 | 0.028 |
| PHY | D:h_credit/h_self | 14.21 [2.42, 72.53] (inf in 2) | 0.001 | 0.004 |
| PHY | Q:h_credit/h_self | 5.50 [0.91, 15.00] (inf in 162) | 0.038 | 0.091 |
| PHY | D:credit_equal/self_network | 8.53 [1.68, 68.85] (inf in 33) | 0.003 | 0.009 |
| PHY | Q:credit_equal/self_network | inf [1.00, 14.00] (inf in 290) | 0.036 | 0.073 |
| PHY | D:credit_harmonic/self_network | 10.65 [2.21, 71.89] (inf in 33) | <0.001 | 0.001 |
| PHY | Q:credit_harmonic/self_network | inf [1.15, 14.00] (inf in 290) | 0.016 | 0.033 |
| MED | D:credit_equal/self_list | 40.00 [2.74, 2255128227281371.00] (inf in 623) | 0.002 | 0.006 |
| MED | Q:credit_equal/self_list | inf [1.25, 13.00] (inf in 1396) | 0.007 | 0.021 |
| MED | D:credit_harmonic/self_list | 68.67 [4.67, 3299331402611566.00] (inf in 623) | <0.001 | 0.001 |
| MED | Q:credit_harmonic/self_list | inf [1.67, 17.00] (inf in 1396) | 0.002 | 0.007 |
| MED | D:h_credit/h_self | 29.04 [4.58, 237.68] (inf in 9) | 0.002 | 0.004 |
| MED | Q:h_credit/h_self | 2.20 [1.00, 16.00] (inf in 297) | 0.030 | 0.091 |
| MED | D:credit_equal/self_network | 15.00 [1.70, 1149772243135582.00] (inf in 183) | 0.008 | 0.017 |
| MED | Q:credit_equal/self_network | 7.00 [1.00, 14.00] (inf in 988) | 0.014 | 0.042 |
| MED | D:credit_harmonic/self_network | 25.75 [2.73, 2045438315950652.25] (inf in 183) | 0.001 | 0.003 |
| MED | Q:credit_harmonic/self_network | 8.50 [1.20, 18.00] (inf in 988) | 0.008 | 0.025 |
| MAT (not tested) | D:credit_equal/self_list | 2.19 [0.37, 68.52] (inf in 81) | 0.190 | – |
| MAT (not tested) | Q:credit_equal/self_list | 5.00 [0.38, 11.00] (inf in 268) | 0.175 | – |
| MAT (not tested) | D:credit_harmonic/self_list | 2.48 [0.24, 73.05] (inf in 81) | 0.187 | – |
| MAT (not tested) | Q:credit_harmonic/self_list | 4.00 [0.25, 10.00] (inf in 268) | 0.214 | – |
| MAT (not tested) | D:h_credit/h_self | 3.81 [0.73, 34.06] (inf in 3) | 0.056 | – |
| MAT (not tested) | Q:h_credit/h_self | 1.83 [0.60, 11.00] (inf in 32) | 0.105 | – |
| MAT (not tested) | D:credit_equal/self_network | 1.92 [0.34, 39.50] (inf in 29) | 0.231 | – |
| MAT (not tested) | Q:credit_equal/self_network | 5.00 [0.33, 10.00] (inf in 162) | 0.223 | – |
| MAT (not tested) | D:credit_harmonic/self_network | 2.17 [0.22, 41.56] (inf in 29) | 0.218 | – |
| MAT (not tested) | Q:credit_harmonic/self_network | 4.00 [0.22, 9.00] (inf in 162) | 0.254 | – |
| ECO (not tested) | D:credit_equal/self_list | 12.00 [0.00, 142852259046325.28] (inf in 1110) | 0.210 | – |
| ECO (not tested) | Q:credit_equal/self_list | inf [0.00, 5.00] (inf in 1609) | 0.356 | – |
| ECO (not tested) | D:credit_harmonic/self_list | 31.00 [1.00, 357337432618641.69] (inf in 1110) | 0.029 | – |
| ECO (not tested) | Q:credit_harmonic/self_list | inf [1.00, 8.00] (inf in 1609) | 0.111 | – |
| ECO (not tested) | D:h_credit/h_self | 32.20 [3.65, 388.95] (inf in 160) | 0.004 | – |
| ECO (not tested) | Q:h_credit/h_self | 7.00 [0.50, 12.97] (inf in 718) | 0.067 | – |
| ECO (not tested) | D:credit_equal/self_network | 6.00 [0.00, 126.90] (inf in 612) | 0.300 | – |
| ECO (not tested) | Q:credit_equal/self_network | inf [0.00, 6.00] (inf in 1207) | 0.420 | – |
| ECO (not tested) | D:credit_harmonic/self_network | 15.50 [0.33, 28384031264940.50] (inf in 612) | 0.079 | – |
| ECO (not tested) | Q:credit_harmonic/self_network | inf [0.00, 8.00] (inf in 1207) | 0.172 | – |

## E1. H1 without researchers with share_links_trunc > 0.10

| Field | n | rule | D [95% CI] | Q [95% CI] |
|---|---|---|---|---|
| ENG | 121 | Self-citations: list rule | 0.0078 [0.0054, 0.0151] | 11.6% [5.0%, 22.3%] |
| ENG | 121 | Self-citations: also network | 0.0230 [0.0124, 0.0456] | 20.7% [10.7%, 30.6%] |
| ENG | 121 | Self-citations: fractional (equal) | 0.0028 [0.0018, 0.0067] | 5.0% [0.8%, 14.0%] |
| ENG | 121 | Credit: equal shares | 0.0623 [0.0428, 0.0958] | 33.1% [24.0%, 46.3%] |
| ENG | 121 | Credit: harmonic shares | 0.1016 [0.0686, 0.1554] | 43.8% [31.4%, 53.7%] |
| ENG | 121 | h: list rule | 0.0143 [0.0089, 0.0254] | 14.0% [8.3%, 26.4%] |
| ENG | 121 | h -> hm | 0.0878 [0.0591, 0.1359] | 35.5% [25.6%, 47.9%] |
| PHY | 125 | Self-citations: list rule | 0.0160 [0.0107, 0.0283] | 14.4% [8.8%, 28.8%] |
| PHY | 125 | Self-citations: also network | 0.0613 [0.0394, 0.0985] | 28.0% [19.2%, 44.8%] |
| PHY | 125 | Self-citations: fractional (equal) | 0.0042 [0.0024, 0.0100] | 4.8% [1.6%, 17.6%] |
| PHY | 125 | Credit: equal shares | 0.2109 [0.1528, 0.2945] | 48.0% [43.2%, 64.0%] |
| PHY | 125 | Credit: harmonic shares | 0.2767 [0.1988, 0.3765] | 56.8% [44.8%, 67.2%] |
| PHY | 125 | h: list rule | 0.0291 [0.0199, 0.0467] | 24.8% [15.2%, 34.4%] |
| PHY | 125 | h -> hm | 0.2788 [0.2006, 0.3852] | 61.6% [49.6%, 71.2%] |
| MED | 111 | Self-citations: list rule | 0.0032 [0.0025, 0.0072] | 5.4% [0.9%, 17.1%] |
| MED | 111 | Self-citations: also network | 0.0105 [0.0076, 0.0203] | 14.4% [5.4%, 24.3%] |
| MED | 111 | Self-citations: fractional (equal) | 0.0008 [0.0005, 0.0024] | 1.8% [0.0%, 10.8%] |
| MED | 111 | Credit: equal shares | 0.1738 [0.1176, 0.2622] | 55.0% [41.4%, 64.0%] |
| MED | 111 | Credit: harmonic shares | 0.2207 [0.1550, 0.3186] | 57.7% [46.8%, 68.5%] |
| MED | 111 | h: list rule | 0.0077 [0.0052, 0.0155] | 9.9% [3.6%, 21.6%] |
| MED | 111 | h -> hm | 0.2303 [0.1521, 0.3346] | 50.5% [41.4%, 63.1%] |
| MAT | 112 | Self-citations: list rule | 0.0238 [0.0153, 0.0425] | 19.6% [11.6%, 33.0%] |
| MAT | 112 | Self-citations: also network | 0.0456 [0.0293, 0.0753] | 24.1% [17.0%, 40.2%] |
| MAT | 112 | Self-citations: fractional (equal) | 0.0076 [0.0051, 0.0157] | 12.5% [4.5%, 22.3%] |
| MAT | 112 | Credit: equal shares | 0.0721 [0.0509, 0.1080] | 33.9% [25.0%, 46.5%] |
| MAT | 112 | Credit: harmonic shares | 0.0915 [0.0659, 0.1317] | 34.8% [27.7%, 50.9%] |
| MAT | 112 | h: list rule | 0.0446 [0.0304, 0.0716] | 26.8% [18.8%, 41.1%] |
| MAT | 112 | h -> hm | 0.1569 [0.1056, 0.2270] | 45.5% [34.8%, 58.0%] |
| ECO | 115 | Self-citations: list rule | 0.0087 [0.0034, 0.0205] | 8.7% [3.5%, 19.2%] |
| ECO | 115 | Self-citations: also network | 0.0149 [0.0072, 0.0311] | 13.9% [6.1%, 24.3%] |
| ECO | 115 | Self-citations: fractional (equal) | 0.0029 [0.0009, 0.0082] | 3.5% [0.0%, 13.9%] |
| ECO | 115 | Credit: equal shares | 0.0606 [0.0382, 0.1023] | 31.3% [22.6%, 44.3%] |
| ECO | 115 | Credit: harmonic shares | 0.0810 [0.0544, 0.1284] | 37.4% [28.7%, 50.4%] |
| ECO | 115 | h: list rule | 0.0151 [0.0080, 0.0285] | 14.8% [7.8%, 26.1%] |
| ECO | 115 | h -> hm | 0.1616 [0.1054, 0.2433] | 53.0% [40.0%, 63.5%] |

Ratios (credit / self), bootstrap interval, one-sided p, Holm p (tested fields only):

| Field | ratio | value [95% CI] | p | p Holm |
|---|---|---|---|---|
| ENG | D:credit_equal/self_list | 7.98 [4.47, 11.75] | <0.001 | 0.002 |
| ENG | Q:credit_equal/self_list | 2.86 [1.48, 7.00] | <0.001 | 0.002 |
| ENG | D:credit_harmonic/self_list | 13.00 [6.94, 19.50] | <0.001 | 0.002 |
| ENG | Q:credit_harmonic/self_list | 3.79 [1.85, 7.86] | <0.001 | 0.002 |
| ENG | D:h_credit/h_self | 6.13 [3.41, 10.03] | <0.001 | 0.002 |
| ENG | Q:h_credit/h_self | 2.53 [1.33, 4.38] | 0.001 | 0.003 |
| ENG | D:credit_equal/self_network | 2.71 [1.49, 5.15] | <0.001 | 0.002 |
| ENG | Q:credit_equal/self_network | 1.60 [1.08, 3.20] | 0.014 | 0.029 |
| ENG | D:credit_harmonic/self_network | 4.41 [2.29, 8.41] | <0.001 | 0.002 |
| ENG | Q:credit_harmonic/self_network | 2.12 [1.34, 4.00] | 0.001 | 0.003 |
| PHY | D:credit_equal/self_list | 13.17 [7.68, 19.54] | <0.001 | 0.002 |
| PHY | Q:credit_equal/self_list | 3.33 [1.86, 5.83] | <0.001 | 0.002 |
| PHY | D:credit_harmonic/self_list | 17.29 [9.98, 25.75] | <0.001 | 0.002 |
| PHY | Q:credit_harmonic/self_list | 3.94 [1.93, 6.38] | <0.001 | 0.002 |
| PHY | D:h_credit/h_self | 9.57 [5.71, 14.54] | <0.001 | 0.002 |
| PHY | Q:h_credit/h_self | 2.48 [1.70, 3.94] | <0.001 | 0.002 |
| PHY | D:credit_equal/self_network | 3.44 [2.30, 5.26] | <0.001 | 0.002 |
| PHY | Q:credit_equal/self_network | 1.71 [1.19, 2.71] | <0.001 | 0.002 |
| PHY | D:credit_harmonic/self_network | 4.52 [2.96, 7.06] | <0.001 | 0.002 |
| PHY | Q:credit_harmonic/self_network | 2.03 [1.25, 2.97] | <0.001 | 0.003 |
| MED | D:credit_equal/self_list | 53.67 [21.80, 76.71] | <0.001 | 0.002 |
| MED | Q:credit_equal/self_list | 10.17 [2.96, 30.50] (inf in 32) | <0.001 | 0.002 |
| MED | D:credit_harmonic/self_list | 68.15 [28.61, 94.76] | <0.001 | 0.002 |
| MED | Q:credit_harmonic/self_list | 10.67 [3.18, 34.50] (inf in 32) | <0.001 | 0.002 |
| MED | D:h_credit/h_self | 29.72 [13.63, 51.27] | <0.001 | 0.002 |
| MED | Q:h_credit/h_self | 5.09 [2.33, 13.60] | <0.001 | 0.002 |
| MED | D:credit_equal/self_network | 16.49 [8.42, 24.33] | <0.001 | 0.002 |
| MED | Q:credit_equal/self_network | 3.81 [2.14, 9.29] (inf in 1) | <0.001 | 0.002 |
| MED | D:credit_harmonic/self_network | 20.94 [10.71, 31.23] | <0.001 | 0.002 |
| MED | Q:credit_harmonic/self_network | 4.00 [2.32, 10.00] (inf in 1) | <0.001 | 0.002 |
| MAT | D:credit_equal/self_list | 3.03 [1.71, 5.15] | <0.001 | 0.002 |
| MAT | Q:credit_equal/self_list | 1.73 [1.02, 3.00] | 0.025 | 0.025 |
| MAT | D:credit_harmonic/self_list | 3.85 [2.08, 6.85] | <0.001 | 0.002 |
| MAT | Q:credit_harmonic/self_list | 1.77 [1.07, 3.54] | 0.014 | 0.014 |
| MAT | D:h_credit/h_self | 3.52 [2.03, 5.60] | <0.001 | 0.002 |
| MAT | Q:h_credit/h_self | 1.70 [0.98, 2.65] | 0.037 | 0.037 |
| MAT | D:credit_equal/self_network | 1.58 [0.92, 2.73] | 0.046 | 0.046 |
| MAT | Q:credit_equal/self_network | 1.41 [0.79, 2.10] | 0.191 | 0.191 |
| MAT | D:credit_harmonic/self_network | 2.00 [1.16, 3.47] | 0.007 | 0.007 |
| MAT | Q:credit_harmonic/self_network | 1.44 [0.86, 2.48] | 0.091 | 0.091 |
| ECO | D:credit_equal/self_list | 6.95 [2.98, 17.24] | <0.001 | 0.002 |
| ECO | Q:credit_equal/self_list | 3.60 [1.64, 9.25] (inf in 2) | <0.001 | 0.002 |
| ECO | D:credit_harmonic/self_list | 9.28 [4.00, 23.06] | <0.001 | 0.002 |
| ECO | Q:credit_harmonic/self_list | 4.30 [1.95, 11.69] (inf in 2) | <0.001 | 0.002 |
| ECO | D:h_credit/h_self | 10.70 [5.20, 20.71] | <0.001 | 0.002 |
| ECO | Q:h_credit/h_self | 3.59 [1.86, 6.88] (inf in 1) | <0.001 | 0.002 |
| ECO | D:credit_equal/self_network | 4.07 [2.05, 8.42] | <0.001 | 0.002 |
| ECO | Q:credit_equal/self_network | 2.25 [1.29, 4.86] | <0.001 | 0.003 |
| ECO | D:credit_harmonic/self_network | 5.45 [2.80, 11.14] | <0.001 | 0.002 |
| ECO | Q:credit_harmonic/self_network | 2.69 [1.56, 5.89] | <0.001 | 0.002 |

### Pooled random reference (n=102, ranked across fields)

- Self-citations: list rule: D 0.0086 [0.0053, 0.0181]; Q 11.8% [3.9%, 23.5%]
- Self-citations: also network: D 0.0167 [0.0104, 0.0316]; Q 19.6% [7.8%, 30.4%]
- Self-citations: fractional (equal): D 0.0031 [0.0016, 0.0086]; Q 5.9% [1.0%, 13.7%]
- Credit: equal shares: D 0.1689 [0.1137, 0.2489]; Q 48.0% [38.2%, 63.7%]
- Credit: harmonic shares: D 0.2089 [0.1426, 0.3016]; Q 46.1% [42.2%, 64.7%]
- h: list rule: D 0.0173 [0.0093, 0.0372]; Q 10.8% [7.8%, 26.5%]
- h -> hm: D 0.2403 [0.1526, 0.3703]; Q 49.0% [38.2%, 61.8%]
- D:credit_equal/self_list: 19.73 [8.68, 32.91], p <0.001
- Q:credit_equal/self_list: 4.08 [2.30, 12.01], p <0.001
- D:credit_harmonic/self_list: 24.40 [10.49, 42.40], p <0.001
- Q:credit_harmonic/self_list: 3.92 [2.36, 12.75], p <0.001
- D:h_credit/h_self: 13.87 [5.64, 29.14], p <0.001
- Q:h_credit/h_self: 4.55 [1.84, 6.43], p <0.001
- D:credit_equal/self_network: 10.14 [5.14, 16.97], p <0.001
- Q:credit_equal/self_network: 2.45 [1.68, 5.88], p <0.001
- D:credit_harmonic/self_network: 12.53 [6.20, 21.20], p <0.001
- Q:credit_harmonic/self_network: 2.35 [1.75, 6.43], p <0.001

## B. H1, Level 1 analogue (all listed scientists per field)

| Field | listed | self-cit.-only entrants | D self (c→c ns) | Q self | D credit (c ns→composite) | Q credit | top-100k change, self | top-100k change, credit (lower bound) |
|---|---|---|---|---|---|---|---|---|
| ENG | 19,516 | 5.0% | 0.0225 | 18.0% | 0.0897 | 39.8% | 6.5% of 4,442 | 9.3% of 4,317 |
| PHY | 21,480 | 7.2% | 0.0297 | 22.2% | 0.0881 | 38.5% | 11.8% of 10,226 | 11.4% of 9,226 |
| MED | 74,888 | 2.8% | 0.0059 | 9.9% | 0.0757 | 36.5% | 2.3% of 35,424 | 19.0% of 36,337 |
| MAT | 2,971 | 7.3% | 0.0581 | 27.0% | 0.0763 | 36.1% | 10.5% of 1,299 | 1.1% of 1,232 |
| ECO | 4,838 | 2.9% | 0.0084 | 10.7% | 0.0584 | 32.6% | 0.9% of 2,960 | 1.4% of 3,268 |

Whole list: 243,949 listed; 10,178 self-citation-only entrants.

## C. H2–H4

H2 (co-author share of self-citations rises with team size; Spearman, one-sided):

| Field | n | median co-author share of self [95% CI] | median team size | ρ | p | p Holm |
|---|---|---|---|---|---|---|
| ENG | 122 | 40.6% [34.8%, 45.0%] | 3.0 | 0.27 | 0.001 | 0.004 |
| PHY | 130 | 51.0% [47.9%, 54.9%] | 4.0 | 0.35 | <0.001 | <0.001 |
| MED | 116 | 64.4% [60.6%, 68.1%] | 6.0 | 0.15 | 0.055 | 0.091 |
| MAT | 112 | 36.7% [31.4%, 39.4%] | 2.0 | 0.31 | <0.001 | 0.002 |
| ECO | 115 | 35.7% [32.0%, 41.7%] | 3.0 | 0.16 | 0.045 | 0.091 |

Pooled: ρ 0.45 (n 595), p <0.001. Observed order of field medians: MED > PHY > ENG > MAT > ECO; expected MED > PHY > ENG > ECO, MAT.

H3 (network share B > C, Mann–Whitney one-sided; network share vs list cprat (ns), Spearman one-sided):

| Field | n B / C | median network B | median network C | Cliff's δ | p | p Holm | ρ(network, cprat ns) | p Holm | B excess bundling removed by network [95% CI] |
|---|---|---|---|---|---|---|---|---|---|
| ENG | 34 / 33 | 8.1% | 3.5% | 0.61 | <0.001 | <0.001 | 0.49 | <0.001 | 8% [5%, 9%] |
| PHY | 37 / 36 | 11.0% | 5.1% | 0.58 | <0.001 | <0.001 | 0.59 | <0.001 | 10% [7%, 13%] |
| MED | 32 / 33 | 12.0% | 4.5% | 0.57 | <0.001 | <0.001 | 0.61 | <0.001 | 10% [7%, 12%] |
| MAT | 30 / 31 | 12.7% | 7.4% | 0.51 | <0.001 | <0.001 | 0.49 | <0.001 | 15% [6%, 18%] |
| ECO | 35 / 29 | 6.2% | 2.3% | 0.70 | <0.001 | <0.001 | 0.50 | <0.001 | 7% [4%, 8%] |

Pooled ρ(network, cprat ns) 0.58, p <0.001.

H4 (own share S > C, Mann–Whitney one-sided):

| Field | n S / C | median own S | median own C | Cliff's δ | p | p Holm |
|---|---|---|---|---|---|---|
| ENG | 33 / 33 | 13.8% | 4.7% | 0.83 | <0.001 | <0.001 |
| PHY | 34 / 36 | 11.8% | 5.5% | 0.68 | <0.001 | <0.001 |
| MED | 30 / 33 | 5.1% | 2.4% | 0.58 | <0.001 | <0.001 |
| MAT | 34 / 31 | 20.1% | 5.0% | 0.98 | <0.001 | <0.001 |
| ECO | 33 / 29 | 6.8% | 2.7% | 0.66 | <0.001 | <0.001 |

## E1. H2–H4 without share_links_trunc > 0.10

H2 (co-author share of self-citations rises with team size; Spearman, one-sided):

| Field | n | median co-author share of self [95% CI] | median team size | ρ | p | p Holm |
|---|---|---|---|---|---|---|
| ENG | 121 | 40.6% [34.8%, 45.0%] | 3.0 | 0.25 | 0.003 | 0.009 |
| PHY | 125 | 50.2% [46.2%, 53.9%] | 4.0 | 0.34 | <0.001 | <0.001 |
| MED | 110 | 64.9% [60.9%, 68.3%] | 6.0 | 0.13 | 0.081 | 0.091 |
| MAT | 112 | 36.7% [31.7%, 39.5%] | 2.0 | 0.31 | <0.001 | 0.002 |
| ECO | 115 | 35.7% [32.0%, 41.3%] | 3.0 | 0.16 | 0.045 | 0.091 |

Pooled: ρ 0.43 (n 583), p <0.001. Observed order of field medians: MED > PHY > ENG > MAT > ECO; expected MED > PHY > ENG > ECO, MAT.

H3 (network share B > C, Mann–Whitney one-sided; network share vs list cprat (ns), Spearman one-sided):

| Field | n B / C | median network B | median network C | Cliff's δ | p | p Holm | ρ(network, cprat ns) | p Holm | B excess bundling removed by network [95% CI] |
|---|---|---|---|---|---|---|---|---|---|
| ENG | 34 / 33 | 8.1% | 3.5% | 0.61 | <0.001 | <0.001 | 0.49 | <0.001 | 8% [5%, 9%] |
| PHY | 37 / 35 | 11.0% | 5.0% | 0.60 | <0.001 | <0.001 | 0.59 | <0.001 | 10% [7%, 13%] |
| MED | 30 / 33 | 12.0% | 4.5% | 0.58 | <0.001 | <0.001 | 0.64 | <0.001 | 10% [7%, 12%] |
| MAT | 30 / 31 | 12.7% | 7.4% | 0.51 | <0.001 | <0.001 | 0.49 | <0.001 | 15% [6%, 18%] |
| ECO | 35 / 29 | 6.2% | 2.3% | 0.70 | <0.001 | <0.001 | 0.50 | <0.001 | 7% [4%, 8%] |

Pooled ρ(network, cprat ns) 0.59, p <0.001.

H4 (own share S > C, Mann–Whitney one-sided):

| Field | n S / C | median own S | median own C | Cliff's δ | p | p Holm |
|---|---|---|---|---|---|---|
| ENG | 33 / 33 | 13.8% | 4.7% | 0.83 | <0.001 | <0.001 |
| PHY | 31 / 35 | 13.4% | 5.5% | 0.73 | <0.001 | <0.001 |
| MED | 28 / 33 | 5.4% | 2.4% | 0.60 | <0.001 | <0.001 |
| MAT | 34 / 31 | 20.1% | 5.0% | 0.98 | <0.001 | <0.001 |
| ECO | 33 / 29 | 6.8% | 2.7% | 0.66 | <0.001 | <0.001 |

## D. H5: share of h kept under each rule (median [95% CI]); citations kept (median)

| Field | excl_own | excl_shared | excl_network | frac_equal | frac_harmonic | frac_network |
|---|---|---|---|---|---|---|
| ENG | h 94.4% [93.3%, 95.5%]; cites 91.0% | h 90.7% [88.6%, 91.5%]; cites 83.7% | h 85.9% [84.5%, 88.9%]; cites 78.0% | h 94.8% [94.0%, 95.6%]; cites 92.8% | h 95.4% [94.3%, 96.1%]; cites 92.7% | h 90.8% [88.9%, 92.1%]; cites 85.0% |
| PHY | h 94.4% [93.3%, 95.0%]; cites 91.3% | h 89.0% [87.5%, 90.0%]; cites 82.1% | h 82.3% [80.3%, 85.0%]; cites 73.1% | h 94.7% [93.7%, 95.2%]; cites 92.0% | h 94.9% [93.8%, 95.6%]; cites 92.6% | h 87.8% [86.5%, 90.0%]; cites 81.9% |
| MED | h 97.4% [96.6%, 97.9%]; cites 96.3% | h 92.3% [91.8%, 93.3%]; cites 89.3% | h 88.4% [87.2%, 89.8%]; cites 80.7% | h 96.5% [96.0%, 97.1%]; cites 95.8% | h 96.9% [96.3%, 97.3%]; cites 96.1% | h 93.1% [92.3%, 94.2%]; cites 90.2% |
| MAT | h 92.6% [90.7%, 94.0%]; cites 89.3% | h 88.1% [85.7%, 89.2%]; cites 81.9% | h 80.0% [77.2%, 83.9%]; cites 71.4% | h 92.6% [91.2%, 93.4%]; cites 90.6% | h 92.6% [91.4%, 93.2%]; cites 90.6% | h 85.2% [82.0%, 87.5%]; cites 80.2% |
| ECO | h 97.4% [97.0%, 97.8%]; cites 96.0% | h 95.7% [94.4%, 96.2%]; cites 92.5% | h 93.9% [93.0%, 94.7%]; cites 88.2% | h 97.3% [97.0%, 97.7%]; cites 96.4% | h 97.2% [96.9%, 97.7%]; cites 96.2% | h 95.5% [94.4%, 96.2%]; cites 92.3% |

Paired Wilcoxon (one-sided; zero differences dropped):

| Test | Field | n | n non-zero | share higher | share lower | p | p Holm |
|---|---|---|---|---|---|---|---|
| frac_equal>excl_shared | ENG | 122 | 96 | 78.7% | 0.0% | <0.001 | <0.001 |
| frac_equal>excl_shared | PHY | 130 | 114 | 87.7% | 0.0% | <0.001 | <0.001 |
| frac_equal>excl_shared | MED | 117 | 105 | 89.7% | 0.0% | <0.001 | <0.001 |
| frac_equal>excl_shared | MAT | 112 | 100 | 89.3% | 0.0% | <0.001 | <0.001 |
| frac_equal>excl_shared | ECO | 115 | 70 | 60.9% | 0.0% | <0.001 | <0.001 |
| frac_harmonic>excl_shared | ENG | 122 | 97 | 79.5% | 0.0% | <0.001 | <0.001 |
| frac_harmonic>excl_shared | PHY | 130 | 115 | 88.5% | 0.0% | <0.001 | <0.001 |
| frac_harmonic>excl_shared | MED | 117 | 107 | 91.5% | 0.0% | <0.001 | <0.001 |
| frac_harmonic>excl_shared | MAT | 112 | 98 | 87.5% | 0.0% | <0.001 | <0.001 |
| frac_harmonic>excl_shared | ECO | 115 | 66 | 57.4% | 0.0% | <0.001 | <0.001 |
| frac_network>excl_network | ENG | 122 | 87 | 71.3% | 0.0% | <0.001 | <0.001 |
| frac_network>excl_network | PHY | 130 | 107 | 82.3% | 0.0% | <0.001 | <0.001 |
| frac_network>excl_network | MED | 117 | 97 | 82.9% | 0.0% | <0.001 | <0.001 |
| frac_network>excl_network | MAT | 112 | 91 | 81.2% | 0.0% | <0.001 | <0.001 |
| frac_network>excl_network | ECO | 115 | 57 | 49.6% | 0.0% | <0.001 | <0.001 |

## E. Sensitivity

- E1: 12 researchers with share_links_trunc > 0.10 removed ({'ENG': 1, 'PHY': 5, 'MED': 6, 'MAT': 0, 'ECO': 0}); results above.
- E2: not applicable — every included match is high-confidence (hand review of `check` rows was skipped in Chat 26); identical to the primary analysis.
- E3: skipped above 80,000 OpenAlex citations: {'ECO-B': 1, 'ECO-R': 1}.

## Table 1 of the note

| Field | Listed (L1) | Self-cit.-only entrants (L1) | Included (L2) | Median team size | Own | Co-author | Network | h kept, list rule | h kept, fractional (equal) | V1 ρ |
|---|---|---|---|---|---|---|---|---|---|---|
| Engineering | 19,516 | 5.0% | 122 | 3.0 | 9.0% | 6.0% | 4.4% | 90.7% | 94.8% | 0.94 |
| Physics & Astronomy | 21,480 | 7.2% | 130 | 4.0 | 8.7% | 7.3% | 7.8% | 89.0% | 94.7% | 0.93 |
| Clinical Medicine | 74,888 | 2.8% | 117 | 6.0 | 3.7% | 6.5% | 7.2% | 92.3% | 96.5% | 0.93 |
| Mathematics & Statistics | 2,971 | 7.3% | 112 | 2.0 | 10.7% | 5.7% | 10.2% | 88.1% | 92.6% | 0.96 |
| Economics & Business | 4,838 | 2.9% | 115 | 3.0 | 4.0% | 2.7% | 3.4% | 95.7% | 97.3% | 0.95 |
