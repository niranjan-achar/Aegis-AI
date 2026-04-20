rule Generic_Shellcode_GetPC : malware
{
    meta:
        description = "Basic shellcode-like byte pattern"
        author = "Aegis-AI"
    strings:
        $a = { E8 00 00 00 00 5B 81 C3 }
        $b = { FC E8 ?? ?? ?? ?? 60 89 E5 }
    condition:
        any of them
}

rule Encoded_Shellcode_Decoder : malware
{
    meta:
        description = "Common XOR decoder stub signature"
        author = "Aegis-AI"
    strings:
        $a = { 31 C9 80 34 0E ?? 41 E2 FA }
    condition:
        $a
}
