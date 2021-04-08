%############################################
%#### Collecting All Connectome Matrices ####
%############################################

% Specify the folder where the files live.
myFolder = '/fast_scratch/jdr/BIDS_qsiprep/connectomes/streamlines/all';
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

    %Create group field: https://www.mathworks.com/matlabcentral/answers/342051-how-can-i-fill-a-structure-array-with-a-scalar-array
    groups = [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, ...
        1, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 1, ...
        0, 1, 1, 1, 1, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 0, ...
        0, 1, 1, 1, 0, 1, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, ...
        0, 1, 1, 1, 1, 0, 0];
    groups_c = num2cell(groups);
    [S.isPTSD] = groups_c{:};
    
    % Assigning raw matrix to structure field 'matrix'
    S(k).T1_matrix = A;

end

clearvars -except S
