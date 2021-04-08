for k = 1 : length(theFiles)
    writematrix(cell2mat(S(k).matrix), strtok(S(k).name, '_'), 'Delimiter', 'tab')
end