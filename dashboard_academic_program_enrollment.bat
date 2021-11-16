@echo on
echo "***** batch file running" >> E:\Applications\dashboard\logs\out.log
time /T >> E:\Applications\dashboard\logs\out.log

whoami 1>> E:\Applications\dashboard\logs\out.log 2>&1
echo "whoami" 1>> E:\Applications\dashboard\logs\out.log 2>&1

e:
echo "e:" 1>> E:\Applications\dashboard\logs\out.log 2>&1
cd E:\Applications\dashboard
echo "cd" 1>> E:\Applications\dashboard\logs\out.log 2>&1

call C:\ProgramData\Anaconda3\condabin\activate.bat E:\Applications\dashboard\envs 1>> E:\Applications\dashboard\logs\out.log 2>&1
echo "call" 1>> E:\Applications\dashboard\logs\out.log 2>&1
rem call conda list 1>> E:\Applications\dashboard\logs\out.log 2>&1

echo "START streamlit run app.py " >> E:\Applications\dashboard\logs\out.log
E:\Applications\dashboard\envs\python.exe app.py 1>> E:\Applications\dashboard\logs\out.log 2>&1

rem pause
time /T >> E:\Applications\dashboard\logs\out.log
echo "***** batch file exiting" >> E:\Applications\dashboard\logs\out.log
