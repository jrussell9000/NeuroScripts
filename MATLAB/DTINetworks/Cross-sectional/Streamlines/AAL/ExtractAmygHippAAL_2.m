

for k = 1 : length(theFiles)
    
    % Concatenate the folder name and the file name
    baseFileName = theFiles(k).name;
    fullFileName = fullfile(theFiles(k).folder, baseFileName);
    fprintf(1, 'Now reading %s\n', fullFileName);
    
    % Load the mat file
    loadedfile = load(fullFileName);
    
    % Assign the netcc matrix to an object
    matrix = loadedfile.brainnetome246_sift_radius2_count_connectivity;
    
    % Add the matrix to the empty object (A) created above
    A = num2cell(matrix);

    % Add name of each matrix file as a structure field
    S(k).name = baseFileName;

    %Create group field: https://www.mathworks.com/matlabcentral/answers/342051-how-can-i-fill-a-structure-array-with-a-scalar-array
    groups = [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, ...
        1, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 1, ...
        0, 1, 1, 1, 1, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 0, ...
        0, 1, 1, 1, 0, 1, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, ...
        0, 1, 1, 1, 1, 0, 0];
    groups_c = num2cell(groups);
    [S.isPTSD] = groups_c{:};
    
    % Assigning raw matrix to structure field 'matrix'
    S(k).matrix = A;

    % Extracting weights for connections to regions of interest and
    % computing the means
    
    % Amygdala subnuclei
    S(k).cma_l = S(k).matrix(:,211)
    S(k).cma_r = S(k).matrix(:,212)
    S(k).bla_l = S(k).matrix(:,213)
    S(k).bla_r = S(k).matrix(:,214)
    
    S(k).cma_l_mean = mean(cell2mat(S(k).cma_l))
    S(k).cma_r_mean = mean(cell2mat(S(k).cma_r))
    S(k).bla_l_mean = mean(cell2mat(S(k).bla_l))
    S(k).bla_r_mean = mean(cell2mat(S(k).bla_r))
    
    % Hippocampal subfields
    S(k).rHipp_L = S(k).matrix(:,215)
    S(k).rHipp_R = S(k).matrix(:,216)
    S(k).cHipp_L = S(k).matrix(:,217)
    S(k).cHipp_R = S(k).matrix(:,218)
    
    S(k).rHipp_L_mean = mean(cell2mat(S(k).rHipp_L))
    S(k).rHipp_R_mean = mean(cell2mat(S(k).rHipp_R))
    S(k).cHipp_L_mean = mean(cell2mat(S(k).cHipp_L))
    S(k).cHipp_R_mean = mean(cell2mat(S(k).cHipp_R))

end

% NOTE! Must delete all non-scalar fields before writing table to csv
% or else file will be blank
writetable(struct2table(S), '/Users/jdrussell3/Structure_Example.csv')

% 211	mAmyg_L
% 212	mAmyg_R
% 213	lAmyg_L
% 214	lAmyg_R
% 215	rHipp_L
% 216	rHipp_R
% 217	cHipp_L
% 218	cHipp_R