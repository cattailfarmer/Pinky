Subject: RiemannHypothesis Math Tools

Description: Deterministic Python tools for finite Riemann Hypothesis adjacent math processing.

These scripts compute numerical traces only. They do not prove RH, certify zeros, or import old symbolic framework modules as authority.

Run from `C:\Project\Pinky\RiemannHypothesis` with the project virtual environment:

```powershell
.\.venv\Scripts\python.exe tools\scripts\zeta_eval.py --sigma 0.5 --t 14.134725 --dps 80
.\.venv\Scripts\python.exe tools\scripts\critical_line_scan.py --t-min 14 --t-max 15 --step 0.1 --refine
.\.venv\Scripts\python.exe tools\scripts\zero_probe.py --start 1 --count 3 --dps 80
.\.venv\Scripts\python.exe tools\scripts\functional_equation_check.py --sigma 2 --t 3 --equation xi
.\.venv\Scripts\python.exe tools\scripts\prime_count_compare.py --x 10 --x 100 --x 1000
.\.venv\Scripts\python.exe tools\scripts\special_prime_profile.py
.\.venv\Scripts\python.exe tools\scripts\special_prime_scan.py --limit 10000
.\.venv\Scripts\python.exe tools\scripts\prime_family_distribution.py --x 1000 --x 10000 --x 100000
.\.venv\Scripts\python.exe tools\scripts\prime_family_intervals.py --x 1000 --x 10000 --x 100000
.\.venv\Scripts\python.exe tools\scripts\prime_power_decomposition.py --x 100 --x 200 --x 500 --include-events
.\.venv\Scripts\python.exe tools\scripts\prime_emergence_shell_signature.py --x 100 --x 200 --x 500 --x 1000 --x 2000 --x 5000 --include-members
.\.venv\Scripts\python.exe tools\scripts\explicit_formula_probe.py --x 100 --x 200 --x 500 --zero-count 5 --zero-count 10 --zero-count 20
.\.venv\Scripts\python.exe tools\scripts\zero_window_probe.py --x 100 --x 200 --x 500 --zero-count 5 --zero-count 10 --zero-count 20 --zero-count 40 --zero-count 80 --window sharp --window fejer --window lanczos --window hann
.\.venv\Scripts\python.exe tools\scripts\explicit_residual_stability_atlas.py --x 100 --x 150 --x 200 --x 300 --x 500 --x 800 --x 1000 --zero-count 10 --zero-count 20 --zero-count 40 --zero-count 80 --zero-count 120 --window sharp --window fejer --window lanczos --window hann
.\.venv\Scripts\python.exe tools\scripts\zero_height_cutoff_atlas.py --x 100 --x 150 --x 200 --x 300 --x 500 --x 800 --x 1000 --zero-height 20 --zero-height 40 --zero-height 80 --zero-height 120 --zero-height 160 --zero-height 220 --window sharp --window fejer --window lanczos --window hann
.\.venv\Scripts\python.exe tools\scripts\scale_tied_zero_height_atlas.py --x 100 --x 150 --x 200 --x 300 --x 500 --x 800 --x 1000 --scale-law log --multiplier 4 --multiplier 6 --multiplier 8 --multiplier 12 --multiplier 16 --multiplier 24 --multiplier 32 --window sharp --window fejer --window lanczos --window hann
.\.venv\Scripts\python.exe tools\scripts\scale_law_comparison_atlas.py --x 100 --x 150 --x 200 --x 300 --x 500 --x 800 --x 1000 --scale-law log --scale-law sqrt --scale-law sqrt_log --window sharp --window fejer --window lanczos --window hann
.\.venv\Scripts\python.exe tools\scripts\lambda_mellin_bridge_atlas.py --n-bound 50 --n-bound 100 --n-bound 200 --sample 2,0 --sample 2,14.134725141734693790457251983562 --sample 1.5,14.134725141734693790457251983562 --multiplier 16 --multiplier 32 --window sharp --window fejer --window lanczos --window hann
.\.venv\Scripts\python.exe tools\scripts\partial_summation_bridge_atlas.py --n-bound 50 --n-bound 100 --n-bound 200 --sample 2,0 --sample 2,14.134725141734693790457251983562 --sample 1.5,14.134725141734693790457251983562 --multiplier 16 --multiplier 32 --window sharp --window fejer --window lanczos --window hann
.\.venv\Scripts\python.exe tools\scripts\cesaro_mellin_bridge_atlas.py --n-bound 50 --n-bound 100 --n-bound 200 --sample 2,0 --sample 2,14.134725141734693790457251983562 --sample 1.5,14.134725141734693790457251983562 --multiplier 16 --multiplier 32 --window sharp --window fejer --window lanczos --window hann --kernel sharp --kernel cesaro --kernel hann
.\.venv\Scripts\python.exe tools\scripts\bias_tuned_kernel_bridge_atlas.py --n-bound 50 --n-bound 100 --n-bound 200 --sample 2,0 --sample 2,14.134725141734693790457251983562 --sample 1.5,14.134725141734693790457251983562 --multiplier 16 --multiplier 32 --window sharp --window fejer --window lanczos --window hann --alpha 0 --alpha 0.25 --alpha 0.5 --alpha 0.75 --alpha 1
.\.venv\Scripts\python.exe tools\scripts\euler_product_probe.py --sample 2,0 --sample 2,14.134725141734693790457251983562 --sample 1.5,14.134725141734693790457251983562 --prime-bound 10 --prime-bound 100 --prime-bound 500
.\.venv\Scripts\python.exe tools\scripts\lambda_oscilloscope_probe.py --sigma 1.5 --sigma 0.5 --t-min 0 --t-max 30 --step 1 --prime-power-bound 100 --window hard
.\.venv\Scripts\python.exe tools\scripts\lambda_window_cutoff_scan.py --sigma 1.5 --sigma 1.05 --t-min 0 --t-max 30 --step 0.5 --prime-power-bound 100 --prime-power-bound 500 --window hard --window fejer
.\.venv\Scripts\python.exe tools\scripts\lambda_phasor_reference_contribution.py --sigma 1.5 --sigma 1.05 --offset -0.5 --offset 0 --offset 0.5 --prime-power-bound 100 --prime-power-bound 500 --window hard --window fejer
.\.venv\Scripts\python.exe tools\scripts\sigma_boundary_probe.py --sigma 2 --sigma 1.5 --sigma 1.25 --sigma 1.1 --sigma 1.05 --t 0 --t 14.134725141734693790457251983562 --prime-bound 100 --prime-bound 500
.\.venv\Scripts\python.exe tools\scripts\t_axis_boundary_probe.py --sigma 1.5 --sigma 1.05 --t 0 --t 5 --t 10 --t 14.134725141734693790457251983562 --t 20 --t 21.0220396387715549926284795938969 --t 25.0108575801456887632137909925628 --t 30 --prime-bound 100 --prime-bound 500
.\.venv\Scripts\python.exe tools\scripts\vertical_resonance_scan.py --sigma 1.5 --sigma 1.05 --t-min 0 --t-max 30 --step 0.5 --prime-bound 500
.\.venv\Scripts\python.exe tools\scripts\exponential_shift_probe.py --base 65537 --exponent 1923 --exponent 3205 --shift 2 --shift -2
.\.venv\Scripts\python.exe tools\scripts\exponential_power_shift_probe.py --base 65537 --exponent-base 641 --exponent-power 3 --exponent-power 5
.\.venv\Scripts\python.exe tools\scripts\coefficient_power_shift_probe.py --coefficient 65537 --power-base 641 --power 3 --power 5 --fixed-shift 1 --fixed-shift -1 --shift-mode plus_n --shift-mode minus_n
.\.venv\Scripts\python.exe tools\scripts\irregular_prime_scan.py --limit 200
.\.venv\Scripts\python.exe tools\scripts\irregular_prime_distribution.py --x 100 --x 200 --include-members
```
