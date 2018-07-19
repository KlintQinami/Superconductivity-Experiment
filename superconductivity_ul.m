function [data] = supercond_ul(tempFollow,tParam,sampleCurr,dvmRange,ptInterval,fname)
%[data] = supercond(tempFollow,tParam,sampleCurr,dvmRange,ptInterval)
%
%Collects and logs data for the superconductivity experiment.
%
%Input:
%       tempFollow: The program can be run in two modes.  In the mode with
%           tempFollow set to f (follow), the program collects data until
%           the temperature tParam is reached.
%           In the mode with tempFollow set to a (alone), the program
%           collects tParam number of data points and is not sensitive to
%           any particular temperature.
%       tParam: See notes for tempFollow.
%       sampleCurr: The magnitude of the current in amperes sent through
%           the sample in delta mode.  This program uses delta mode
%           exclusively, which provides the sample with a square wave 
%           current to eliminate effects of leads with finite temperature.
%       dvmRange: Sets the measurement range of the digital voltmeter in
%           volts.  Care must be taken to keep all data points in range, 
%           otherwise the device will return an error and the data may not 
%           be logged.
%       ptInterval: The time interval in seconds to wait before collecting
%           the next data point.  The time between successive points will 
%           always be slightly longer, as the time for receiving data from
%           the device is not counted in this number.
%
%Suggested input values:
%       sampleCurr: 0.01
%       dvmRange: 1
%       ptInterval: 1
%
%Output:
%       data: A 4-column matrix.  First column is chip temperature, second
%           is the current supplied, third is the voltage read, fourth is
%           the resistance calculated as V/I.  This matrix is saved into a
%           tabs-delimited ASCII text file in the supcerond\data folder.
%
%If the program exits with errors, call delete(instrfind) at the command
%prompt to reset the hardware connections.
%
%David Tam, Columbia University Dept. of Physics, May 2010
%tam@phys.columbia.edu
%Modified by Ben Nachumi, peripatetic1@yahoo.com, April, 2011

%set parameters
%NOTE: do not change these or some data might be lost in transit
numDeltaPoints =25; %number of individual delta mode measurements to be averaged for each data point
%ptTotal =10; %total number of data points collected
deltaDelay = 0.1; %delay

%initialize some things
pause on
data = [0 0 0 0 0 0];

%check operating method
if isequal(tempFollow,'f') || isequal(tempFollow,'a')
else disp('Parameter tempFollow must be either f or a.  Type "help supercond."')
    return
end


%create and open instrument objects, and echo their names
lakeshore = visa('ni','gpib0::12::INSTR');
fopen(lakeshore);
fprintf(lakeshore,'*IDN?');
lakeshoreName = fscanf(lakeshore);

keithley = visa('ni','gpib0::13::INSTR');
fopen(keithley);
fprintf(keithley,'*IDN?');
keithleyName = fscanf(keithley);

disp('Successfully connected to:')
disp(lakeshoreName(1:end-2)) %eliminates trailing whitespace
disp(keithleyName(1:end-2))  %eliminates trailing whitespace
disp(' ')

%check keithley internal setup
fprintf(keithley,'SOUR:DELT:NVPR?');
is2182aConnected = fscanf(keithley);
if is2182aConnected ==1,
    disp('WARNING: Voltmeter is not connected.')
    disp(' ')
end

%set up voltmeter
fprintf(keithley,'SYST:COMM:SER:SEND "VOLT:RANGE %s"',num2str(dvmRange));

%set up keithley for delta mode
%as in ref manual, p. 5-29
disp('Strike any key to arm the Keithley...')
pause
fprintf(keithley,'*RST');
fprintf(keithley,'SOUR:DELT:HIGH %e',sampleCurr);
fprintf(keithley,'SOUR:DELT:DEL %e',deltaDelay);
fprintf(keithley,'SOUR:DELT:COUN %s',num2str(numDeltaPoints));
fprintf(keithley,'TRAC:POIN %s',num2str(numDeltaPoints));
fprintf(keithley,'TRAC:CLE');
fprintf(keithley,'SOUR:DELT:ARM');
pause(max([0.01 numDeltaPoints*(8/10000)])) %it takes 8 seconds to arm the keithley with a 10,000 point buffer
pause(2)
disp('...Keithley is armed.')
disp(' ')

%start heater and begin logging data points
disp('Strike any key to begin the heating cycle and start logging data...')
pause
%preview of for loop;
%measure
%fprintf(keithley,'INIT:IMM')
%pause(numDeltaPoints*deltaDelay + 0.1);
%read out the buffer;
%fprintf(keithley,'TRAC:DATA?')
%pause(numDeltaPoints*deltaDelay + 0.1);
%fscanf(keithley);

%initialize values to be collected
newTempu = 0;
newTempl = 0;
newDiode = 0;
avgVoltage = 0;
avgOhms = 0;
newData = [0 0 0 0 0 0];
if ishold==0;
    hold
end
%repeat for all points
if tempFollow=='f'
    
    fprintf(lakeshore,'KRDG?a');
    newTempl = fscanf(lakeshore,'%f');
    tempSign = sign(newTempl-tParam);
    
    newTempSign=tempSign;
    while isequal(newTempSign,tempSign)
        %temp data
        fprintf(lakeshore,'KRDG?a');
        newTempl = fscanf(lakeshore,'%f');
        fprintf(lakeshore,'SRDG?a');
        newDiode = fscanf(lakeshore,'%f');
        fprintf(lakeshore,'KRDG?b');
        newTempu = fscanf(lakeshore,'%f');
        
        %keithley data
        fprintf(keithley,'INIT:IMM');
        pause(numDeltaPoints*deltaDelay + 0.1);
        fprintf(keithley,'TRAC:DATA?');
        pause(numDeltaPoints*deltaDelay + 0.1);
        fscanf(keithley);
        fprintf(keithley,'CALC2:FORM MEAN');
        fprintf(keithley,'CALC2:STAT ON');
        fprintf(keithley,'CALC2:IMM');
        fprintf(keithley,'CALC2:DATA?');
        avgVoltage = fscanf(keithley,'%e');
        avgOhms = avgVoltage/sampleCurr;
        
        newData = [newTempu, newTempl, newDiode, sampleCurr, avgVoltage, avgOhms];
        data = [data; newData];
        plot(newTempl,avgOhms);
        pause(ptInterval)
        
        newTempSign = sign(newTempl-tParam);
    end
    
elseif tempFollow=='a'
    for thisPoint=1:tParam
        
        %temp data
        fprintf(lakeshore,'KRDG?a');
        newTempl = fscanf(lakeshore,'%f');
        fprintf(lakeshore,'SRDG?a');
        newDiode = fscanf(lakeshore,'%f');
        fprintf(lakeshore,'KRDG?b');
        newTempu = fscanf(lakeshore,'%f');
        %keithley data
        fprintf(keithley,'INIT:IMM');
        pause(numDeltaPoints*deltaDelay + 0.1);
        fprintf(keithley,'TRAC:DATA?');
        pause(numDeltaPoints*deltaDelay + 0.1);
        fscanf(keithley);
        fprintf(keithley,'CALC2:FORM MEAN');
        fprintf(keithley,'CALC2:STAT ON');
        fprintf(keithley,'CALC2:IMM');
        fprintf(keithley,'CALC2:DATA?');
        avgVoltage = fscanf(keithley,'%e');
        avgOhms = avgVoltage/sampleCurr;
        
        newData = [newTempl, newTempu, newDiode, sampleCurr, avgVoltage, avgOhms];
        data = [data; newData];
        plot(newTempl, avgOhms);
        pause(ptInterval)
        
    end
end

%eliminate leading zero row in data matrix
data = data(2:end,:);

%disarm keithley
fprintf(keithley,'SOUR:SWE:ABOR');
fprintf(keithley,'TRAC:CLE');

%plot resistance data over temperature
plot(data(:,1),data(:,6),'d');

%save data file to folder as tabs-delimited text file
cd 'C:\Documents and Settings\Student\My Documents\MATLAB\supercond\data';
%fname = ['sc' datestr(now,30) '.txt'];
fname = [fname '.txt'];
dlmwrite (fname,data,'-append','delimiter','\t','precision',10,'newline','pc');

%close instrument objects and delete them
fclose(lakeshore);
fclose(keithley);
delete(instrfind);

disp('supercond.m was successfully closed.')

cd 'C:\Documents and Settings\Student\My Documents\Conductivity Experiment\MatLab functions';

end
