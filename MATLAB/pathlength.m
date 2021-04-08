% Create an empty array to hold each graph statistic (zeros(x_length,y_length)
charpathlength = zeros(length(theFiles),1);
% Create an empty matrix to hold each vertex statistic

for k = 1 : length(theFiles)
    % Concatenate the folder name and the file name
    baseFileName = theFiles(k).name;
    fullFileName = fullfile(theFiles(k).folder, baseFileName);
    fprintf(1, 'Now reading %s\n', fullFileName);
    
    % Load the mat file
    loadedfile = load(fullFileName);
    
    % Assign the netcc matrix to an object
    matrix = loadedfile.netcc;
    
    % Threshold the matrix
    matrix10 = threshold_proportional(matrix, .10);
    
    % Compute the network statistic and assign it to the array created
    % above
    %clustering(k,:) = clustering_coef_wu(matrix10)
    charpathlength(k) = charpath(matrix10)
    % Convert the matrix to a table and assign row and column names
    %clusttable = array2table(clustering, 'RowNames', subjnames)
    
end

