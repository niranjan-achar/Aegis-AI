rule Emotet_Imports : malware family
{
    meta:
        description = "Heuristic Emotet-like import combination"
        author = "Aegis-AI"
    strings:
        $a = "LoadLibraryA" ascii
        $b = "GetProcAddress" ascii
        $c = "URLDownloadToFileW" ascii
        $d = "WinExec" ascii
    condition:
        3 of them
}

rule Emotet_Process_Discovery : malware family
{
    meta:
        description = "Emotet-like process enumeration strings"
        author = "Aegis-AI"
    strings:
        $a = "CreateToolhelp32Snapshot" ascii
        $b = "Process32First" ascii
        $c = "Process32Next" ascii
    condition:
        all of them
}
