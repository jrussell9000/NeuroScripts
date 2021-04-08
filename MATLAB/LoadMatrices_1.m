% Specify the folder where the files live.
myFolder = '/fast_scratch/jdr/resting/3dNetCorr/netcorr/netcc/mat/';
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
subjnames = {theFiles.name}

% Create empty object to hold all the matrices
A = zeros(244,244,length(theFiles));

for k = 1 : length(theFiles)
    % Concatenate the folder name and the file name
    baseFileName = theFiles(k).name;
    fullFileName = fullfile(theFiles(k).folder, baseFileName);
    fprintf(1, 'Now reading %s\n', fullFileName);
    
    % Load the mat file
    loadedfile = load(fullFileName);
    
    % Assign the netcc matrix to an object
    matrix = loadedfile.netcc;
    
    % Add the matrix to the empty object (A) created above
    A(:,:,k) = matrix;
    % Threshold the matrix
    
end

config.thresh = 0.1:.02:.4
mtpcgen =  MTPC_generate_metrics(A,config)
config.varnames = {'isPTSD'}
config.terms = [1]


design = zeros(length(theFiles),1)

metrics = MTPC_evaluate_metrics(mtpcgen, design, config)