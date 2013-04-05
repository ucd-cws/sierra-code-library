
sleep_duration = 15000 ; how often to check, in milliseconds. 60000 is a full minute

Loop
{
	IfWinExist, ahk_class #32770 ; use autohotkey's window spy to confirm this is it for you. This seemed to be consistent across all errors like this on Windows Server 2008
	{
		ControlClick, Button2, ahk_class #32770 ; sends the click. Button2 is the control name and then the following is that window name again
	}
	Sleep, sleep_duration ; wait for the time set above
}
	