@echo on
echo "***** batch file running" >> F:\Applications\dashboard\logs\out.log
time /T >> F:\Applications\dashboard\logs\out.log

whoami 1>> F:\Applications\dashboard\logs\out.log 2>&1
echo "whoami" 1>> F:\Applications\dashboard\logs\out.log 2>&1

F:
echo "F:" 1>> F:\Applications\dashboard\logs\out.log 2>&1
cd F:\Applications\dashboard
echo "cd" 1>> F:\Applications\dashboard\logs\out.log 2>&1

call C:\ProgramData\Anaconda3\condabin\activate.bat py311streamlit 1>> F:\Applications\dashboard\logs\out.log 2>&1
echo "call" 1>> F:\Applications\dashboard\logs\out.log 2>&1
rem call conda list 1>> F:\Applications\dashboard\logs\out.log 2>&1

echo "START streamlit run app.py " >> F:\Applications\dashboard\logs\out.log
C:\ProgramData\Anaconda3\envs\py311streamlit\python.exe app.py 1>> F:\Applications\dashboard\logs\out.log 2>&1

rem pause
time /T >> F:\Applications\dashboard\logs\out.log
echo "***** batch file exiting" >> F:\Applications\dashboard\logs\out.log
