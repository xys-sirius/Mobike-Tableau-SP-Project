# 共享单车潮汐调度模型论文项目

## 论文标题
基于非齐次生灭过程的共享单车潮汐现象建模与动态调度优化——以上海市真实订单数据为例

## 项目结构
```
paper_project/
├── Data/
│   └── Mobike Data/
│       ├── mobike_shanghai_sample_updated.csv  (102,361条订单记录)
│       └── MOBIKE 样本数据说明(data_description).pdf
├── scripts/          (MATLAB脚本)
├── figures/          (生成的图表)
├── paper/            (LaTeX论文草稿)
└── README.md
```

## 执行Phase
- [x] Phase 0: 项目结构搭建
- [ ] Phase 1: 数据清洗与时空EDA (step1_data_cleaning.m)
- [ ] Phase 2: NHPP统计推断与检验 (step2_poisson_test.m)
- [ ] Phase 3: Gillespie仿真 (step3_gillespie_sim.m)
- [ ] Phase 4: 动态调度优化 (step4_optimization.m)
- [ ] Phase 5: ODE数值求解 (step5_ode_solution.m)
- [ ] Phase 6: LaTeX论文全文撰写

## 数据概况
- 总记录数: 102,361
- 字段: orderid, bikeid, userid, start_time, start_location_x/y, end_time, end_location_x/y, track
- 时间范围: 2016年8月
- 无缺失值
- track字段: "#"分隔的经纬度轨迹点序列