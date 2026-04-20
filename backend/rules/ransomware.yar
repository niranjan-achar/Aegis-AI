rule Ransomware_Extensions : malware
{
    meta:
        description = "Generic ransomware extension hints"
        author = "Aegis-AI"
    strings:
        $a = ".locked" ascii nocase
        $b = ".encrypted" ascii nocase
        $c = ".wnry" ascii nocase
    condition:
        1 of them
}

rule Shadow_Copy_Deletion : malware
{
    meta:
        description = "Detects shadow copy deletion behavior strings"
        author = "Aegis-AI"
    strings:
        $a = "vssadmin delete shadows" ascii nocase
        $b = "wbadmin delete catalog" ascii nocase
        $c = "bcdedit /set {default} recoveryenabled no" ascii nocase
    condition:
        1 of them
}
