function [data] = diode_gpib(CurL,CurH,CurInc,fname)
pause on
%*****************************************************************************
%Initialize Matlab function parameters
	comp = 105; %max out compliance--nothing to harm here
	dvmRange = 10;
    testVolts = 0e-3;
	Volts = 0e-3;
    Vav = 0e-3;
    CurR=0e-3;
    newTempl=0;
    newTempu=0;
    Tlav=0;
    Tuav=0;
    Data=[0 0 0 0];
    NewData = [0 0 0 0];
    if ishold==0
        hold;
    end
 %*****************************************************************************
%create and open instrument objects, and echo their names
	lakeshore = visa('ni','gpib0::12::INSTR');
	fopen(lakeshore);
		fprintf(lakeshore,'*IDN?');
	lakeshoreName = fscanf(lakeshore);

	keithley1 = visa('ni','gpib0::13::INSTR');
    keithley2 = visa('ni','gpib0::14::INSTR');
	fopen(keithley1);
	fprintf(keithley1,'*IDN?');
    keithley1Name = fscanf(keithley1);
    fopen(keithley2);
    fprintf(keithley2,'*IDN?');
    keithley2Name = fscanf(keithley2);

	disp('Successfully connected to:');
	disp(lakeshoreName(1:end-2)); %eliminates trailing whitespace
	disp(keithley1Name(1:end-2));  
    disp(keithley2Name(1:end-2));
    disp(' ');

%*****************************************************************************
%Initialize the 6220&2182
		fprintf(keithley1,'*RST');
        fprintf(keithley1,'SOUR:CURR:COMP %e', comp);
		fprintf(keithley1,'SOUR:CURR:RANG:AUTO ON');
        fprintf(keithley2,'*RST');	
        fprintf(keithley2,'*CLS');
        
        fprintf(keithley2,'SAMP:COUN 1');
        fprintf(keithley2,'READ?');
        testVolts=fscanf(keithley2,'%e');
        disp(testVolts);

%*******************************************************************************	
%The measurement	
	disp('Strike any key...');
	pause
    CurR=CurL;
    fprintf(keithley1,'OUTP ON');
    while CurR<CurH+CurInc
%Set the current and turn on the 6220
		fprintf(keithley1,'SOUR:CURR %e',CurR);
%Take the average of imax measurements for each point 
    Vsum=0;
    Tlsum=0;
    Tusum=0;
    Volts=0;
    imax=1;
    i=0;
        while i<imax
        %temp data
        fprintf(lakeshore,'KRDG?a');
        newTempl = fscanf(lakeshore,'%f');
        Tlsum=Tlsum+newTempl;
        fprintf(lakeshore,'KRDG?b');
        newTempu = fscanf(lakeshore,'%f');
        Tusum=Tusum+newTempu;
		pause(.1);
        fprintf(keithley2,'READ?');
        Volts=fscanf(keithley2,'%e');
        disp(Volts);
        Vsum = Vsum + Volts;
        i=i+1;
        end
        
    Vav=Vsum/imax;
    Tlav=Tlsum/imax;
    Tuav=Tusum/imax;
    disp(CurR);
    disp(Vav);
    plot(Vav,CurR,'*');
    NewData = [Vav, CurR, Tlsum, Tusum];
    Data = [Data; NewData];   
    pause(.1); 
    Vav=0;
    Vsum=0;
    CurR = CurR + CurInc;
    end
%*******************************************************************************		
		fprintf(keithley1,'OUTP OFF');
        fprintf(keithley1,'SOUR:CLE');
        Data = Data(2:end,:);
        plot(Data(:,1),Data(:,2),'d','Color','r');
%save data file to folder as tabs-delimited text file
	cd 'C:\Documents and Settings\Student\My Documents\MATLAB\supercond\data';
%fname = ['sc' datestr(now,30) '.txt'];
	fname = [fname '.txt'];
	dlmwrite (fname,Data,'-append','delimiter','\t','precision',10,'newline','pc');
		
%close instrument objects and delete them
	fclose(lakeshore);
	fclose(keithley1);
    fclose(keithley2);
	delete(instrfind);
	disp('diode_gpib.m was successfully closed.')
end