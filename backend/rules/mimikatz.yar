rule Mimikatz_Core_Strings : malware family
{
    meta:
        description = "Detects well-known Mimikatz strings"
        author = "Aegis-AI"
    strings:
        $a = "mimikatz" ascii nocase
        $b = "sekurlsa::logonpasswords" ascii nocase
        $c = "lsadump::sam" ascii nocase
    condition:
        1 of them
}

rule Mimikatz_Credential_Access : malware family
{
    meta:
        description = "Detects LSASS dumping behavior strings"
        author = "Aegis-AI"
    strings:
        $a = "SeDebugPrivilege" ascii nocase
        $b = "MiniDumpWriteDump" ascii nocase
        $c = "wdigest" ascii nocase
    condition:
        2 of them
}
