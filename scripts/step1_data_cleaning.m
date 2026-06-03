% step1_data_cleaning.m
% Phase 1: 数据清洗与时空探索性分析 (EDA)
% 功能：读取CSV、提取早高峰订单、K-Means空间聚类、识别潮汐站点、绘制潮汐流量图

clear; clc; close all;

%% ==================== 参数设置 ====================
data_path = 'C:/Users/33294/Desktop/paper_project/Data/Mobike Data/mobike_shanghai_sample_updated.csv';
fig_path = 'C:/Users/33294/Desktop/paper_project/figures/';
K_clusters = 10;  % K-Means聚类数

% 上海经纬度到米制坐标的近似转换因子
% 1度纬度 ≈ 111 km; 1度经度 ≈ cos(31.23°) × 111 ≈ 95.0 km
lat_to_m = 111000;  % 1度纬度对应的米数
lon_to_m = 95000;   % 1度经度在上海纬度对应的米数

%% ==================== 1. 数据读取 ====================
fprintf('正在读取数据...\n');
data = readtable(data_path, 'VariableNamingRule', 'preserve');
fprintf('数据读取完成，共 %d 条记录\n', height(data));

% 查看数据概况
fprintf('字段列表: %s\n', strjoin(data.Properties.VariableNames, ', '));
fprintf('经纬度范围:\n');
fprintf('  start_location_x: [%f, %f]\n', min(data.start_location_x), max(data.start_location_x));
fprintf('  start_location_y: [%f, %f]\n', min(data.start_location_y), max(data.start_location_y));
fprintf('  end_location_x: [%f, %f]\n', min(data.end_location_x), max(data.end_location_x));
fprintf('  end_location_y: [%f, %f]\n', min(data.end_location_y), max(data.end_location_y));

%% ==================== 2. 数据清洗 ====================
fprintf('\n=== 数据清洗 ===\n');

% 2.1 过滤异常坐标（超出上海合理范围）
shanghai_lon_range = [120.8, 122.0];  % 上海经度合理范围
shanghai_lat_range = [30.6, 31.9];    % 上海纬度合理范围

valid_mask = (data.start_location_x >= shanghai_lon_range(1) & ...
              data.start_location_x <= shanghai_lon_range(2) & ...
              data.start_location_y >= shanghai_lat_range(1) & ...
              data.start_location_y <= shanghai_lat_range(2) & ...
              data.end_location_x >= shanghai_lon_range(1) & ...
              data.end_location_x <= shanghai_lon_range(2) & ...
              data.end_location_y >= shanghai_lat_range(1) & ...
              data.end_location_y <= shanghai_lat_range(2));

data_clean = data(valid_mask, :);
fprintf('清洗后记录数: %d (移除 %d 条异常坐标记录)\n', height(data_clean), height(data) - height(data_clean));

% 2.2 解析时间字段
% start_time格式: '2016-08-20 06:57'
data_clean.start_datetime = datetime(data_clean.start_time, 'InputFormat', 'yyyy-MM-dd HH:mm');
data_clean.end_datetime = datetime(data_clean.end_time, 'InputFormat', 'yyyy-MM-dd HH:mm');

% 提取小时
data_clean.start_hour = hour(data_clean.start_datetime);
data_clean.end_hour = hour(data_clean.end_datetime);

% 提取日期
data_clean.start_date = dateshift(data_clean.start_datetime, 'start', 'day');

% 统计日期范围
unique_dates = unique(data_clean.start_date);
fprintf('日期范围: %s 到 %s, 共 %d 天\n', ...
    string(unique_dates(1)), string(unique_dates(end)), length(unique_dates));

%% ==================== 3. 经纬度转米制坐标 ====================
fprintf('\n=== 坐标转换 ===\n');

% 将经纬度转换为以上海中心(121.47, 31.23)为原点的米制坐标
ref_lon = 121.47;  % 参考经度（上海中心大约位置）
ref_lat = 31.23;   % 参考纬度

data_clean.start_x_m = (data_clean.start_location_x - ref_lon) * lon_to_m;
data_clean.start_y_m = (data_clean.start_location_y - ref_lat) * lat_to_m;
data_clean.end_x_m = (data_clean.end_location_x - ref_lon) * lon_to_m;
data_clean.end_y_m = (data_clean.end_location_y - ref_lat) * lat_to_m;

fprintf('米制坐标范围 (km):\n');
fprintf('  start_x: [%f, %f] km\n', min(data_clean.start_x_m)/1000, max(data_clean.start_x_m)/1000);
fprintf('  start_y: [%f, %f] km\n', min(data_clean.start_y_m)/1000, max(data_clean.start_y_m)/1000);

%% ==================== 4. 早高峰订单提取 ====================
fprintf('\n=== 早高峰订单提取 ===\n');

morning_peak = data_clean(data_clean.start_hour >= 7 & data_clean.start_hour <= 9, :);
fprintf('早高峰(7:00-9:00)订单数: %d\n', height(morning_peak));

%% ==================== 5. K-Means空间聚类 ====================
fprintf('\n=== K-Means空间聚类 ===\n');

% 5.1 对早高峰起点(流出)聚类
start_coords = [morning_peak.start_x_m, morning_peak.start_y_m];
[idx_start, C_start] = kmeans(start_coords, K_clusters, 'Replicates', 5, 'MaxIter', 500);

% 将聚类中心转回经纬度
C_start_lon = C_start(:,1) / lon_to_m + ref_lon;
C_start_lat = C_start(:,2) / lat_to_m + ref_lat;

fprintf('起点聚类中心经纬度:\n');
for i = 1:K_clusters
    fprintf('  Cluster %d: (%.4f, %.4f) - %d orders\n', ...
        i, C_start_lon(i), C_start_lat(i), sum(idx_start == i));
end

% 5.2 对早高峰终点(流入)聚类
end_coords = [morning_peak.end_x_m, morning_peak.end_y_m];
[idx_end, C_end] = kmeans(end_coords, K_clusters, 'Replicates', 5, 'MaxIter', 500);

C_end_lon = C_end(:,1) / lon_to_m + ref_lon;
C_end_lat = C_end(:,2) / lat_to_m + ref_lat;

fprintf('\n终点聚类中心经纬度:\n');
for i = 1:K_clusters
    fprintf('  Cluster %d: (%.4f, %.4f) - %d orders\n', ...
        i, C_end_lon(i), C_end_lat(i), sum(idx_end == i));
end

%% ==================== 6. 识别潮汐站点 ====================
fprintf('\n=== 识别潮汐站点 ===\n');

% 6.1 计算每个起点聚类中心的早高峰流出量
start_cluster_outflow = zeros(K_clusters, 1);
for i = 1:K_clusters
    start_cluster_outflow(i) = sum(idx_start == i);
end

% 6.2 计算每个终点聚类中心的早高峰流入量
end_cluster_inflow = zeros(K_clusters, 1);
for i = 1:K_clusters
    end_cluster_inflow(i) = sum(idx_end == i);
end

% 6.3 使用全天的数据，对每个聚类区域计算24小时净流量
% 首先需要将全天数据分配到聚类中
% 对全天起点数据，使用早高峰起点聚类中心进行分配
all_start_coords = [data_clean.start_x_m, data_clean.start_y_m];
all_end_coords = [data_clean.end_x_m, data_clean.end_y_m];

% 使用pdist2计算每个点到各聚类中心的距离，分配到最近的簇
dist_start = pdist2(all_start_coords, C_start);
[~, idx_all_start] = min(dist_start, [], 2);

dist_end = pdist2(all_end_coords, C_end);
[~, idx_all_end] = min(dist_end, [], 2);

% 6.4 找出净流入最大（CBD/地铁站）和净流出最大（住宅区）的聚类
% 计算早高峰各区域的净流量 = 流入 - 流出
% 对于起点聚类：流出 = 从该区域出发的订单数
% 对于终点聚类：流入 = 到达该区域的订单数

% 为了统一分析，我们使用终点聚类中心作为"区域"定义
% 对每个终点聚类区域：
%   流出 = 以该区域为起点（idx_all_start对应）的订单数
%   流入 = 以该区域为终点（idx_all_end对应）的订单数

% 但起点和终点聚类是分开做的，需要统一区域定义
% 更好的方法：对全天所有位置（起点+终点合并）做一次统一聚类

all_locations = [data_clean.start_x_m; data_clean.end_x_m; ...
                 data_clean.start_y_m; data_clean.end_y_m];
% 实际上应该合并起点和终点的坐标
all_points_x = [data_clean.start_x_m; data_clean.end_x_m];
all_points_y = [data_clean.start_y_m; data_clean.end_y_m];
all_points = [all_points_x, all_points_y];

[idx_all, C_all] = kmeans(all_points, K_clusters, 'Replicates', 5, 'MaxIter', 500);
C_all_lon = C_all(:,1) / lon_to_m + ref_lon;
C_all_lat = C_all(:,2) / lat_to_m + ref_lat;

fprintf('\n统一聚类中心经纬度:\n');
for i = 1:K_clusters
    fprintf('  Cluster %d: (%.4f, %.4f)\n', i, C_all_lon(i), C_all_lat(i));
end

% 6.5 将全天起点和终点分配到统一聚类
dist_start_to_all = pdist2([data_clean.start_x_m, data_clean.start_y_m], C_all);
[~, start_cluster] = min(dist_start_to_all, [], 2);

dist_end_to_all = pdist2([data_clean.end_x_m, data_clean.end_y_m], C_all);
[~, end_cluster] = min(dist_end_to_all, [], 2);

% 6.6 计算每个聚类区域24小时的净流量
net_flow_24h = zeros(K_clusters, 24);  % [cluster, hour]

for h = 0:23
    % 流入：终点在该区域且还车时间在该小时的订单
    inflow_mask = (data_clean.end_hour == h);
    for c = 1:K_clusters
        net_flow_24h(c, h+1) = sum(end_cluster(inflow_mask) == c) - sum(start_cluster(data_clean.start_hour == h) == c);
    end
end

% 6.7 找出早高峰净流入最大和净流出最大的区域
% 使用7:00-9:00三个小时的净流量之和作为早高峰指标
morning_net = sum(net_flow_24h(:, 8:10), 2);  % 7:00-9:00的净流量总和
[max_inflow_val, max_inflow_cluster] = max(morning_net);
[max_outflow_val, max_outflow_cluster] = min(morning_net);

fprintf('\n=== 潮汐站点识别结果 ===\n');
fprintf('早高峰净流入最大区域: Cluster %d (%.4f, %.4f), 净流入 = %d\n', ...
    max_inflow_cluster, C_all_lon(max_inflow_cluster), C_all_lat(max_inflow_cluster), max_inflow_val);
fprintf('早高峰净流出最大区域: Cluster %d (%.4f, %.4f), 净流出 = %d\n', ...
    max_outflow_cluster, C_all_lon(max_outflow_cluster), C_all_lat(max_outflow_cluster), max_outflow_val);

% 保存关键变量供后续脚本使用
save('C:/Users/33294/Desktop/paper_project/scripts/eda_results.mat', ...
    'data_clean', 'C_all', 'C_all_lon', 'C_all_lat', 'net_flow_24h', ...
    'max_inflow_cluster', 'max_outflow_cluster', 'K_clusters', ...
    'start_cluster', 'end_cluster', 'lon_to_m', 'lat_to_m', 'ref_lon', 'ref_lat');

fprintf('\nEDA结果已保存到 eda_results.mat\n');

%% ==================== 7. 绘图 ====================
fprintf('\n=== 绘图 ===\n');
% 确保figures目录存在
if ~exist(fig_path, 'dir')
    mkdir(fig_path);
end

% 7.1 空间分布散点图 + 聚类中心
fig1 = figure('Position', [100, 100, 800, 600]);
hold on;
% 绘制所有订单的起点（抽样以避免过于密集）
sample_idx = randperm(height(data_clean), min(5000, height(data_clean)));
scatter(data_clean.start_location_x(sample_idx), data_clean.start_location_y(sample_idx), ...
    3, [0.3, 0.3, 0.8], '.');
% 绘制聚类中心
scatter(C_all_lon, C_all_lat, 100, 'r', 'p', 'LineWidth', 2, 'MarkerFaceColor', 'r');
for i = 1:K_clusters
    text(C_all_lon(i)+0.01, C_all_lat(i)+0.01, sprintf('C%d', i), 'FontSize', 10, 'Color', 'r', 'FontWeight', 'bold');
end
% 标注潮汐站点
scatter(C_all_lon(max_inflow_cluster), C_all_lat(max_inflow_cluster), ...
    200, [1, 0, 0], 'p', 'LineWidth', 3, 'MarkerFaceColor', [1, 0.5, 0.5]);
scatter(C_all_lon(max_outflow_cluster), C_all_lat(max_outflow_cluster), ...
    200, [0, 0, 1], 'p', 'LineWidth', 3, 'MarkerFaceColor', [0.5, 0.5, 1]);
title('上海市共享单车订单空间分布与K-Means聚类结果', 'FontSize', 14);
xlabel('经度 (°E)', 'FontSize', 12);
ylabel('纬度 (°N)', 'FontSize', 12);
legend('订单起点(抽样)', '聚类中心', 'Location', 'best');
grid on;
set(gca, 'FontSize', 11);
hold off;
exportgraphics(fig1, [fig_path, 'spatial_distribution_clustering.png'], 'Resolution', 300);
fprintf('图1已保存: spatial_distribution_clustering.png\n');

% 7.2 潮汐流量24小时变化图
fig2 = figure('Position', [100, 100, 900, 500]);
hours = 0:23;
plot(hours, net_flow_24h(max_inflow_cluster, :), 'r-o', 'LineWidth', 2, 'MarkerSize', 6);
hold on;
plot(hours, net_flow_24h(max_outflow_cluster, :), 'b-s', 'LineWidth', 2, 'MarkerSize', 6);
% 标注零线
yline(0, 'k--', 'LineWidth', 1);
% 标注早高峰区域
xline(7, ':', '早高峰开始', 'LabelHorizontalAlignment', 'left', 'FontSize', 9);
xline(9, ':', '早高峰结束', 'LabelHorizontalAlignment', 'right', 'FontSize', 9);
% 标注晚高峰区域
xline(17, ':', '晚高峰开始', 'LabelHorizontalAlignment', 'left', 'FontSize', 9);
xline(19, ':', '晚高峰结束', 'LabelHorizontalAlignment', 'right', 'FontSize', 9);

title(sprintf('潮汐站点24小时净流量变化\n(净流入站: Cluster %d (%.4f°E, %.4f°N) vs 净流出站: Cluster %d (%.4f°E, %.4f°N)', ...
    max_inflow_cluster, C_all_lon(max_inflow_cluster), C_all_lat(max_inflow_cluster), ...
    max_outflow_cluster, C_all_lon(max_outflow_cluster), C_all_lat(max_outflow_cluster)), 'FontSize', 12);
xlabel('小时 (h)', 'FontSize', 12);
ylabel('净流量 (流入 - 流出)', 'FontSize', 12);
legend(sprintf('净流入站(C%d)', max_inflow_cluster), sprintf('净流出站(C%d)', max_outflow_cluster), '零线', 'Location', 'best');
grid on;
set(gca, 'FontSize', 11, 'XTick', 0:23);
hold off;
exportgraphics(fig2, [fig_path, 'tidal_flow_24h.png'], 'Resolution', 300);
fprintf('图2已保存: tidal_flow_24h.png\n');

% 7.3 所有聚类区域的24小时净流量热力图
fig3 = figure('Position', [100, 100, 900, 500]);
imagesc(net_flow_24h);
colormap(redblue_cmap());
colorbar;
title('各聚类区域24小时净流量热力图', 'FontSize', 14);
xlabel('小时', 'FontSize', 12);
ylabel('聚类区域', 'FontSize', 12);
set(gca, 'XTick', 1:24, 'XTickLabel', 0:23, 'YTick', 1:K_clusters, 'FontSize', 10);
exportgraphics(fig3, [fig_path, 'net_flow_heatmap.png'], 'Resolution', 300);
fprintf('图3已保存: net_flow_heatmap.png\n');

fprintf('\n=== Phase 1 完成 ===\n');

%% ==================== 辅助函数 ====================
function cmap = redblue_cmap()
    % 创建红-白-蓝渐变色图
    n = 256;
    r = [linspace(0, 1, n/2), ones(1, n/2)];
    g = [linspace(0, 1, n/2), linspace(1, 0, n/2)];
    b = [ones(1, n/2), linspace(1, 0, n/2)];
    cmap = [r', g', b'];
end