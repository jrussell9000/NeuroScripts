% The following code loads .mat files containing connectome matrices

% Specify the folder where the files live.
myFolder = '/fast_scratch/jdr/BIDS_qsiprep/connectomes/all';

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

    % Add name of each matrix file as a structure field
    S(k).name = baseFileName;

  
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

% Non-significant results in whole brain matrix
% metrics = struct;
% metrics.name = S.name;
% metrics.isPTSD = S.isPTSD;
% metrics.betweennessmean = S.betweenness_mean
% metrics.clusteringmean = S.clustering_mean
% metrics.efficiency_global = S.efficiency_global

%writetable(struct2table(S), '/Users/jdrussell3/all_connectomes.csv')

% 211	mAmyg_L
% 212	mAmyg_R
% 213	lAmyg_L
% 214	lAmyg_R
% 215	rHipp_L
% 216	rHipp_R
% 217	cHipp_L
% 218	cHipp_R