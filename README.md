# What
This tool allows to convert Rain World save game file into a human readable text file. Text file can be then edited (or parts of it commented with hashes) and converted back to save with updated checksum.

The primary purpose of this tool is to narrow down the save game part that is crashing the game.

# How
This is a command line tool that works as a python script. First install required libraries

    pip install beautifulsoup4 lxml

Then find your save game location. For Windows it will be most probably

    C:\Users\%USERNAME%\AppData\LocalLow\Videocult\Rain World\sav

For XBOX Play Anywhere PC version in some subfolder of 

    C:\Users\%USERNAME%\AppData\Local\Packages\49827AkuparaGames.RainWorld_mfvawhmf9sssr\SystemAppData\wgs

Once savegame file is located (and backed up!) we can run the tool like this:

    python rwsave.py -d sav 

Two files are created sav.tpl and sav.txt. First one is encapsulating XML that becomes a template. Second one is text file with humand redable save data. This file can be edited with notepad. In particular one can find using bisection the part that is causing the white screen with black square error. In my case this was

    CAMPAIGNTIME<mpdB>Artificer<mpdB>0<mpdB>963574035588652<mpdB>180847335368954<mpdB>0<mpdB>1098800<mpdB>1852075<mpdA>

which I have commented out.

After all the redactions one can convert .tpl and .txt back to sav file with

    python rwsave.py -e sav.txt sav.tpl sav

This creates sav file with updated checksum. If put into savegame folder it should now introduce changes to the game.

# Fix shortcut
To fix the CAMPAIGNTIME by copying last two values or capping the numbers one can use `-f` fix option. 


    python rwsave.py -f sav
    
Original file is first backed up and then overwritten.

# License
MIT
