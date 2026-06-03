load('C:/Users/33294/Desktop/paper_project/scripts/eda_results.mat');
fprintf('start_date class: %s\n', class(data_clean.start_date));
fprintf('start_datetime class: %s\n', class(data_clean.start_datetime));
fprintf('start_date sample (first 5):\n');
for i = 1:min(5,length(data_clean.start_date))
    fprintf('  [%d] = %s\n', i, char(data_clean.start_date(i)));
end
fprintf('start_datetime sample (first 5):\n');
for i = 1:min(5,length(data_clean.start_datetime))
    fprintf('  [%d] = %s\n', i, char(data_clean.start_datetime(i)));
end

% Try different matching
am1 = (start_cluster==3) & (data_clean.start_hour==8);
fprintf('Cluster 3, hour 8: %d events\n', sum(am1));

% Check what dates exist
ud = unique(data_clean.start_date(am1));
fprintf('Unique dates in cluster 3 hour 8:\n');
for i = 1:length(ud)
    fprintf('  %s\n', char(ud(i)));
end

% Use first available date
if length(ud) > 0
    test_date = ud(1);
    am = (start_cluster==3) & (data_clean.start_hour==8) & (data_clean.start_date==test_date);
    fprintf('Test date: %s, events: %d\n', char(test_date), sum(am));
    
    dn = datenum(data_clean.start_datetime(am));
    ts = double(dn) * 86400 - floor(double(dn)) * 86400;
    ts = sort(ts);
    ia = diff(ts);
    fprintf('Total events: %d\n', length(ts));
    fprintf('Unique timestamps: %d\n', length(unique(round(ts,6))));
    fprintf('Duplicate rate: %.2f%%\n', 100*(length(ts)-length(unique(round(ts,6))))/length(ts));
    fprintf('Zero intervals: %d/%d\n', sum(ia==0), length(ia));
    fprintf('Intervals < 1s: %d/%d\n', sum(ia<1), length(ia));
    fprintf('Intervals < 10s: %d/%d\n', sum(ia<10), length(ia));
    fprintf('Intervals < 60s: %d/%d\n', sum(ia<60), length(ia));
    fprintf('Mean interval: %.2f s\n', mean(ia));
    fprintf('Median interval: %.2f s\n', median(ia));
    fprintf('Time stamps (first 10):\n');
    for i = 1:min(10,length(ts))
        fprintf('  %.6f\n', ts(i));
    end
    fprintf('Inter-arrivals (first 10):\n');
    for i = 1:min(10,length(ia))
        fprintf('  %.6f\n', ia(i));
    end
end