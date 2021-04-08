% Specify the folder where the files live.
myFolder = '/fast_scratch/jdr/BIDS_qsiprep/connectomes/ses-01';
% Check to make sure that folder actually exists.  Warn user if it doesn't.
if ~isfolder(myFolder)
    errorMessage = sprintf('Error: The following folder does not exist:\n%s\nPlease specify a new folder.', myFolder);
    uiwait(warndlg(errorMessage));
    myFolder = uigetdir(); % Ask for a new one.
    if myFolder == 0
         % User clicked Cancel
         return;
    end
end
% Get a list of all files in the folder with the desired file name pattern.
filePattern = fullfile(myFolder, '*.mat'); % Change to whatever pattern you need.
theFiles = dir(filePattern);

% Subject file names to array
subjnames = {theFiles.name};

% Create empty object to hold all the matrices
A = zeros(246,246,length(theFiles));

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
    %A(:,:,k) = matrix;

    S(k).name = baseFileName;
    %Create group field: https://www.mathworks.com/matlabcentral/answers/342051-how-can-i-fill-a-structure-array-with-a-scalar-array
    groups = [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, ...
        1, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 1, ...
        0, 1, 1, 1, 1, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 0, ...
        0, 1, 1, 1, 0, 1, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, ...
        0, 1, 1, 1, 1, 0, 0];
    groups_c = num2cell(groups);
    [S.isPTSD] = groups_c{:};
    
    %Assigning raw matrix to structure field 'matrix'
    S(k).matrix = A;
    
    %Computing length converted and normalized matrices (see
    %weight_conversion.m)
%     S(k).matrix_lengths = weight_conversion(cell2mat(S(k).matrix),'lengths');
%     S(k).matrix_norm = weight_conversion(cell2mat(S(k).matrix),'normalize');
    
    %Computing betweenness from lengths (see weight_conversion.m)
%     S(k).betweenness = betweenness_wei(S(k).matrix_lengths);
%     S(k).betweenness_mean = mean(S(k).betweenness);
%     
    %Computing clustering coefficient from normalized matrix
%     S(k).clustering = clustering_coef_wu_sign(S(k).matrix_norm);
%     S(k).clustering_mean = mean(S(k).clustering);
%     
    %Computing global efficiency from raw matrix
%     S(k).efficiency_global = efficiency_wei(cell2mat(S(k).matrix));
%     
    
    
    %Generating random models
    %S(k).randomnet = null_model_und_sign(cell2mat(S(k).matrix))
    
    %
    S(k).cma_l = S(k).matrix(:,211)
    S(k).cma_r = S(k).matrix(:,212)
    S(k).bla_l = S(k).matrix(:,213)
    S(k).bla_r = S(k).matrix(:,214)
    
    S(k).cma_l_mean = mean(cell2mat(S(k).cma_l))
    S(k).cma_r_mean = mean(cell2mat(S(k).cma_r))
    S(k).bla_l_mean = mean(cell2mat(S(k).bla_l))
    S(k).bla_r_mean = mean(cell2mat(S(k).bla_r))
end

% Non-significant results in whole brain matrix
% metrics = struct;
% metrics.name = S.name;
% metrics.isPTSD = S.isPTSD;
% metrics.betweennessmean = S.betweenness_mean
% metrics.clusteringmean = S.clustering_mean
% metrics.efficiency_global = S.efficiency_global

writetable(struct2table(S), '/Users/jdrussell3/Structure_Example.csv')

% 211	mAmyg_L
% 212	mAmyg_R
% 213	lAmyg_L
% 214	lAmyg_R
% 215	rHipp_L
% 216	rHipp_R
% 217	cHipp_L
% 218	cHipp_R