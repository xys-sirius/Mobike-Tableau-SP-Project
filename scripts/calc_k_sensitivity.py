"""K-sensitivity analysis: compute P0_max and PK_max for various K using ODE."""
import scipy.io as sio
import numpy as np

d = sio.loadmat(r'C:\Users\33294\Desktop\paper_project\scripts\poisson_test_results.mat')
lambda_hourly = d['lambda_hourly'].ravel()
mu_hourly = d['mu_hourly'].ravel()
lambda_hourly_RES = d['lambda_hourly_RES'].ravel()
mu_hourly_RES = d['mu_hourly_RES'].ravel()

print('CBD lambda:', np.round(lambda_hourly, 1))
print('CBD mu:', np.round(mu_hourly, 1))
print('RES lambda:', np.round(lambda_hourly_RES, 1))
print('RES mu:', np.round(mu_hourly_RES, 1))


def solve_ode_pks(K, lam_hourly_arr, mu_hourly_arr, N0, T_total=24, dt=0.005):
    """Solve M(t)/M(t)/1/K Kolmogorov Forward ODE.
    
    lam_hourly_arr, mu_hourly_arr: per-hour rates for each hour (1..24)
    dt: time step in hours (0.005 hr = 18 seconds)
    Returns max P0 and max PK as percentages.
    """
    n_steps = int(T_total / dt)
    
    # Build rate arrays for each time step (per-hour rates, unchanged)
    hr_idx = np.floor(np.arange(n_steps) * dt).astype(int)  # 0..23
    lam_per_hour = lam_hourly_arr[hr_idx]   # per-hour rate
    mu_per_hour = mu_hourly_arr[hr_idx]     # per-hour rate
    
    P = np.zeros(K + 1)
    P[N0] = 1.0
    P0_max, PK_max = 0.0, 0.0
    
    for j in range(n_steps - 1):
        lam = lam_per_hour[j]
        mu = mu_per_hour[j]
        
        # Kolmogorov forward equations: dP/dt = P * Q
        dP = np.zeros(K + 1)
        dP[0] = -lam * P[0] + mu * P[1]
        for i in range(1, K):
            dP[i] = lam * P[i - 1] - (lam + mu) * P[i] + mu * P[i + 1]
        dP[K] = lam * P[K - 1] - mu * P[K]
        
        # Euler step: P(t+dt) = P(t) + dP/dt * dt
        P = P + dP * dt
        P = np.maximum(P, 0)
        P = P / P.sum()  # numerical stability
        
        if P[0] > P0_max:
            P0_max = P[0]
        if P[K] > PK_max:
            PK_max = P[K]
    
    return 100 * P0_max, 100 * PK_max


print()
print('=== CBD ODE K-sensitivity ===')
for K in [40, 50, 60, 80]:
    N0 = min(25, K - 1)
    p0, pk = solve_ode_pks(K, lambda_hourly, mu_hourly, N0)
    print(f'K={K}: P0_max={p0:.2f}%  PK_max={pk:.2f}%')

print()
print('=== RES ODE K-sensitivity ===')
for K in [40, 80]:
    N0 = min(40, K - 1)
    p0, pk = solve_ode_pks(K, lambda_hourly_RES, mu_hourly_RES, N0)
    print(f'K={K}: P0_max={p0:.2f}%  PK_max={pk:.2f}%')