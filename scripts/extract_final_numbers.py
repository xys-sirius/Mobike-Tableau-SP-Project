#!/usr/bin/env python3
"""提取论文所需的所有关键数值"""
import numpy as np
from scipy.io import loadmat

sim = loadmat('C:/Users/33294/Desktop/paper_project/scripts/simulation_results.mat')
disp = loadmat('C:/Users/33294/Desktop/paper_project/scripts/dispatch_results.mat')
pt = loadmat('C:/Users/33294/Desktop/paper_project/scripts/poisson_test_results.mat')

CBD, RES = int(sim['cluster_CBD'][0,0]), int(sim['cluster_RES'][0,0])
K_CBD, K_RES = int(sim['K_CBD'][0,0]), int(sim['K_RES'][0,0])
N_CBD, N_RES = 200, 5761  # trajs x timesteps

def pct(mat, val, K): return float(np.sum(mat==val)/(N_CBD*N_RES)*100)

lh_CBD = pt['lambda_hourly'].flatten()
mh_CBD = pt['mu_hourly'].flatten()
lh_RES = pt['lambda_hourly_RES'].flatten()
mh_RES = pt['mu_hourly_RES'].flatten()

print("="*60)
print("论文关键数值汇总")
print("="*60)

# Step2
print("\n--- §2: NHPP Validation ---")
print(f"地铁站(CBD): Cluster {CBD}, K={K_CBD}")
print(f"住宅区(RES): Cluster {RES}, K={K_RES}")
print(f"CBD λ(8h)={lh_CBD[8]:.1f}, μ(8h)={mh_CBD[8]:.1f}  (早高峰净流入={mh_CBD[8]-lh_CBD[8]:.1f})")
print(f"CBD λ(18h)={lh_CBD[18]:.1f}, μ(18h)={mh_CBD[18]:.1f}  (晚高峰净流出={lh_CBD[18]-mh_CBD[18]:.1f})")
print(f"RES λ(8h)={lh_RES[8]:.1f}, μ(8h)={mh_RES[8]:.1f}  (早高峰净流出={lh_RES[8]-mh_RES[8]:.1f})")
print(f"RES λ(18h)={lh_RES[18]:.1f}, μ(18h)={mh_RES[18]:.1f}  (晚高峰净流入={mh_RES[18]-lh_RES[18]:.1f})")

# Step3
print("\n--- §3: Gillespie + ODE ---")
for name, mat, K in [("CBD", sim['all_traj_CBD'], K_CBD), ("RES", sim['all_traj_RES'], K_RES)]:
    p0 = pct(mat, 0, K)
    pk = pct(mat, K, K)
    print(f"{name}: P(N=0)={p0:.2f}%, P(N=K)={pk:.2f}%")

cost_CBD = float(sim['cost_CBD'][0,0])
cost_RES = float(sim['cost_RES'][0,0])
total = cost_CBD + cost_RES
print(f"CBD cost: {cost_CBD:.2f} ¥")
print(f"RES cost: {cost_RES:.2f} ¥")
print(f"Total (no dispatch): {total:.2f} ¥")

# Step4
print("\n--- §4: Dispatch Optimization ---")
s_CBD = float(disp['saving_CBD'][0,0])
s_RES = float(disp['saving_RES'][0,0])
s_total = float(disp['total_saving'][0,0])
print(f"CBD dispatch saving: {s_CBD:+.1f}%")
print(f"RES dispatch saving: {s_RES:+.1f}%")
print(f"Total saving: {s_total:+.1f}%")
print(f"Total with dispatch: {float(disp['total_optimized'][0,0]):.2f} ¥")

# Rate summary by tidal phase
print("\n--- Tidal Phase Summary ---")
for name, lam, mu in [("CBD", lh_CBD, mh_CBD), ("RES", lh_RES, mh_RES)]:
    am_peak = np.argmax(mu - lam)
    pm_peak = np.argmax(lam - mu)
    print(f"{name}: max net-inflow at {am_peak}h (μ-λ={mu[am_peak]-lam[am_peak]:.1f}),"
          f" max net-outflow at {pm_peak}h (λ-μ={lam[pm_peak]-mu[pm_peak]:.1f})")

print("\n" + "="*60)
print("汇总完成。所有图片位于 figures/ 目录。")