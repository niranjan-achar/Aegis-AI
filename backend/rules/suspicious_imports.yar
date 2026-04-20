rule Suspicious_Process_Injection_APIs : malware
{
    meta:
        description = "Flags a common process injection API mix"
        author = "Aegis-AI"
    strings:
        $a = "VirtualAllocEx" ascii
        $b = "WriteProcessMemory" ascii
        $c = "CreateRemoteThread" ascii
    condition:
        all of them
}

rule Suspicious_Persistence_APIs : malware
{
    meta:
        description = "Flags registry/service persistence strings"
        author = "Aegis-AI"
    strings:
        $a = "RegSetValueEx" ascii
        $b = "CreateService" ascii
        $c = "schtasks" ascii nocase
    condition:
        2 of them
}

rule Suspicious_Networking_APIs : malware
{
    meta:
        description = "Flags downloader and C2 networking strings"
        author = "Aegis-AI"
    strings:
        $a = "InternetOpen" ascii
        $b = "InternetConnect" ascii
        $c = "HttpSendRequest" ascii
        $d = "URLDownloadToFile" ascii
    condition:
        2 of them
}
