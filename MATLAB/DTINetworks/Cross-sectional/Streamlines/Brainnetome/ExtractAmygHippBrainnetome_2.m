
for k = 1 : length(S)
    % Extracting weights for connections to regions of interest and
    % computing the means
    
    % Amygdala subnuclei
    S(k).cma_l_T1 = S(k).T1_matrix(:,211)
    S(k).cma_r_T1 = S(k).T1_matrix(:,212)
    S(k).bla_l_T1 = S(k).T1_matrix(:,213)
    S(k).bla_r_T1 = S(k).T1_matrix(:,214)
    
    S(k).cma_l_mean_T1 = mean(cell2mat(S(k).cma_l_T1))
    S(k).cma_r_mean_T1 = mean(cell2mat(S(k).cma_r_T1))
    S(k).bla_l_mean_T1 = mean(cell2mat(S(k).bla_l_T1))
    S(k).bla_r_mean_T1 = mean(cell2mat(S(k).bla_r_T1))
    
    S(k).cma_l_T2 = S(k).T2_matrix(:,211)
    S(k).cma_r_T2 = S(k).T2_matrix(:,212)
    S(k).bla_l_T2 = S(k).T2_matrix(:,213)
    S(k).bla_r_T2 = S(k).T2_matrix(:,214)
    
    S(k).cma_l_mean_T2 = mean(cell2mat(S(k).cma_l_T2))
    S(k).cma_r_mean_T2 = mean(cell2mat(S(k).cma_r_T2))
    S(k).bla_l_mean_T2 = mean(cell2mat(S(k).bla_l_T2))
    S(k).bla_r_mean_T2 = mean(cell2mat(S(k).bla_r_T2))
    
end

% NOTE! Must manually delete all non-scalar fields before writing table to csv
% or else file will be blank
writetable(struct2table(S), '/Users/jdrussell3/AmygHipp_streamlines_Brainnetome.csv')

% 211	mAmyg_L
% 212	mAmyg_R
% 213	lAmyg_L
% 214	lAmyg_R
% 215	rHipp_L
% 216	rHipp_R
% 217	cHipp_L
% 218	cHipp_R

PTSDmean = zeros(246,1)
for i = 1 : length(S)
    if S(i).isPTSD == 1
        PTSDmean = PTSDmean + cell2mat(S(i).cma_l);
    end
end
PTSD = horzcat(roi,normalize(PTSDmean))
CTRLmean = zeros(246,1)





